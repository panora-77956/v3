# ui/workers/video_worker.py
"""
Video Generation Worker - Non-blocking video generation using QThread
Prevents UI freezing during video generation API calls
"""
import os
import shutil
import subprocess
import time

from PyQt5.QtCore import QThread, pyqtSignal

from services.account_manager import get_account_manager
from services.google.labs_flow_client import DEFAULT_PROJECT_ID, LabsFlowClient
from services.utils.video_downloader import VideoDownloader
from utils import config as cfg
from utils.filename_sanitizer import sanitize_filename


class VideoGenerationWorker(QThread):
    """
    Background worker for video generation to prevent UI freeze.
    
    Signals:
        progress_updated: Emitted when progress changes (scene_idx, total_scenes, status_message)
        scene_completed: Emitted when a scene video completes (scene_idx, video_path)
        all_completed: Emitted when all scenes complete (list of video_paths)
        error_occurred: Emitted on error (error_message)
        job_card: Emitted for video status updates (card_dict)
        log: Emitted for log messages (log_message)
    """

    # Signals
    progress_updated = pyqtSignal(int, int, str)  # scene_idx, total_scenes, status
    scene_completed = pyqtSignal(int, str)  # scene_idx, video_path
    all_completed = pyqtSignal(list)  # all video_paths
    error_occurred = pyqtSignal(str)  # error_message
    job_card = pyqtSignal(dict)  # card data for UI updates
    log = pyqtSignal(str)  # log messages

    def __init__(self, payload, parent=None):
        """
        Initialize video generation worker.
        
        Args:
            payload: Dictionary containing:
                - scenes: List of scene dictionaries with 'prompt' and 'aspect'
                - copies: Number of video copies per scene
                - model_key: Video model to use
                - title: Project title
                - dir_videos: Output directory for videos
                - upscale_4k: Whether to upscale to 4K
                - auto_download: Whether to auto-download videos
                - quality: Video quality (1080p, 720p, etc.)
            parent: Parent QObject
        """
        super().__init__(parent)
        self.payload = payload
        self.cancelled = False
        self.video_downloader = VideoDownloader(log_callback=lambda msg: self.log.emit(msg))

    def cancel(self):
        """Cancel the video generation operation."""
        self.cancelled = True
        self.log.emit("[INFO] Video generation cancelled by user")

    def _handle_labs_event(self, event):
        """Handle diagnostic events from LabsClient."""
        kind = event.get("kind", "")
        if kind == "video_generator_info":
            gen_type = event.get("generator_type", "Unknown")
            model = event.get("model_key", "")
            aspect = event.get("aspect_ratio", "")
            self.log.emit(f"[INFO] Video Generator: {gen_type} | Model: {model} | Aspect: {aspect}")
        elif kind == "api_call_info":
            endpoint_type = event.get("endpoint_type", "")
            num_req = event.get("num_requests", 0)
            self.log.emit(f"[INFO] API Call: {endpoint_type} endpoint | {num_req} request(s)")
        elif kind == "trying_model":
            model = event.get("model_key", "")
            self.log.emit(f"[DEBUG] Trying model: {model}")
        elif kind == "model_success":
            model = event.get("model_key", "")
            self.log.emit(f"[DEBUG] Model {model} succeeded")
        elif kind == "model_failed":
            model = event.get("model_key", "")
            error = event.get("error", "")
            self.log.emit(f"[WARN] Model {model} failed: {error}")
        elif kind == "operations_result":
            num_ops = event.get("num_operations", 0)
            self.log.emit(f"[DEBUG] API returned {num_ops} operations")
        elif kind == "start_one_result":
            count = event.get("operation_count", 0)
            requested = event.get("requested_copies", 0)
            self.log.emit(f"[INFO] Video generation: {count}/{requested} operations created")
        elif kind == "http_other_err":
            code = event.get("code", "")
            detail = event.get("detail", "")
            self.log.emit(f"[ERROR] HTTP {code}: {detail}")

    def _download(self, url, dst_path):
        """Download video from URL."""
        try:
            self.video_downloader.download(url, dst_path)
            return True
        except Exception as e:
            self.log.emit(f"[ERR] Download fail: {e}")
            return False

    def _make_thumb(self, video_path, out_dir, scene, copy):
        """Generate thumbnail from video."""
        try:
            os.makedirs(out_dir, exist_ok=True)
            thumb = os.path.join(out_dir, f"thumb_c{scene}_v{copy}.jpg")
            if shutil.which("ffmpeg"):
                cmd = ["ffmpeg", "-y", "-ss", "00:00:00", "-i", video_path,
                       "-frames:v", "1", "-q:v", "3", thumb]
                subprocess.run(cmd, check=True, capture_output=True)
                return thumb
        except Exception as e:
            self.log.emit(f"[WARN] Tạo thumbnail lỗi: {e}")
        return ""

    def run(self):
        """Execute video generation in background thread."""
        try:
            self._run_video()
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.log.emit(f"[ERR] Worker error: {e}")
            self.log.emit(f"[DEBUG] {error_details}")
            self.error_occurred.emit(str(e))

    def _run_video(self):
        """Main video generation logic."""
        p = self.payload
        st = cfg.load()

        # Ensure config is valid
        if not st or not isinstance(st, dict):
            self.log.emit("[ERROR] Configuration file is invalid or missing!")
            self.error_occurred.emit("Invalid configuration")
            return

        # Get account manager for multi-account support
        account_mgr = get_account_manager()

        # Check if multi-account mode is enabled
        if account_mgr.is_multi_account_enabled():
            enabled_accounts = account_mgr.get_enabled_accounts()
            self.log.emit(
                f"[INFO] Multi-account mode: {len(enabled_accounts)} accounts active"
            )

            # Log each account's details for transparency
            for idx, acc in enumerate(enabled_accounts, 1):
                token_count = len(acc.tokens)
                proj_id_short = (
                    acc.project_id[:12] + "..." if len(acc.project_id) > 12
                    else acc.project_id
                )
                self.log.emit(
                    f"[INFO]   Account {idx}: {acc.name} | "
                    f"Project: {proj_id_short} | Tokens: {token_count}"
                )

            self.log.emit(
                "[INFO] Using SEQUENTIAL processing with round-robin account distribution"
            )
            self.log.emit(
                "[WARN] Parallel processing not yet implemented in VideoWorker, "
                "using sequential"
            )

        copies = p["copies"]
        title = p["title"]
        dir_videos = p["dir_videos"]
        thumbs_dir = os.path.join(dir_videos, "thumbs")

        total_scenes = len(p["scenes"])
        jobs = []
        client_cache = {}

        # Event handler for diagnostic logging
        def on_labs_event(event):
            self._handle_labs_event(event)

        # Start video generation for each scene
        for scene_idx, scene in enumerate(p["scenes"], start=1):
            if self.cancelled:
                self.error_occurred.emit("Generation cancelled by user")
                return

            # Use actual_scene_num if provided (for retry), otherwise use scene_idx
            actual_scene_num = scene.get("actual_scene_num", scene_idx)

            # Update progress: Starting scene
            self.progress_updated.emit(
                actual_scene_num - 1, total_scenes, f"Submitting scene {actual_scene_num}..."
            )

            ratio = scene["aspect"]
            model_key = p.get("model_key", "")

            # Get account for this scene (multi-account or legacy)
            if account_mgr.is_multi_account_enabled():
                # Use round-robin account selection for this scene
                # Use scene_idx - 1 for round-robin (0-indexed), but actual_scene_num for display
                account = account_mgr.get_account_for_scene(scene_idx - 1)
                if not account:
                    self.log.emit("[ERROR] No enabled accounts available!")
                    self.error_occurred.emit("No enabled accounts")
                    return

                tokens = account.tokens
                project_id = account.project_id

                # Validate tokens
                if not tokens:
                    self.log.emit(f"[ERROR] Account '{account.name}' has no tokens!")
                    self.error_occurred.emit(f"Account '{account.name}' has no tokens")
                    return

                # Validate project_id
                if not project_id or not isinstance(project_id, str) or not project_id.strip():
                    self.log.emit(f"[ERROR] Account '{account.name}' has invalid project_id!")
                    self.error_occurred.emit(
                        f"Account '{account.name}' has invalid project_id"
                    )
                    return

                project_id = project_id.strip()
                proj_id_short = (
                    project_id[:12] + "..." if len(project_id) > 12
                    else project_id
                )
                self.log.emit(
                    f"[INFO] Scene {actual_scene_num}: Using account '{account.name}' | "
                    f"Project: {proj_id_short}"
                )
            else:
                # Legacy mode: use old tokens and default_project_id
                tokens = st.get("tokens") or []
                if not tokens:
                    self.log.emit(
                        "[ERROR] No Google Labs tokens configured! "
                        "Please add tokens in API Credentials."
                    )
                    self.error_occurred.emit("No tokens configured")
                    return

                # Get project_id with strict validation and fallback
                project_id = st.get("default_project_id")
                if not project_id or not isinstance(project_id, str) or not project_id.strip():
                    # Use fallback if missing/invalid
                    project_id = DEFAULT_PROJECT_ID
                    self.log.emit(f"[INFO] Using default project_id: {project_id}")
                else:
                    project_id = project_id.strip()
                    self.log.emit(f"[INFO] Using configured project_id: {project_id}")

                # Validate project_id format (should be UUID-like)
                if len(project_id) < 10:
                    self.log.emit(
                        f"[WARN] Project ID '{project_id}' seems invalid (too short), "
                        "using default"
                    )
                    project_id = DEFAULT_PROJECT_ID

            # Create or reuse client for this project_id
            if project_id not in client_cache:
                client_cache[project_id] = LabsFlowClient(tokens, on_event=on_labs_event)
            client = client_cache[project_id]

            # Single API call with copies parameter
            body = {
                "prompt": scene["prompt"],
                "copies": copies,
                "model": model_key,
                "aspect_ratio": ratio
            }
            self.log.emit(f"[INFO] Start scene {actual_scene_num} with {copies} copies in one batch…")
            rc = client.start_one(
                body, model_key, ratio, scene["prompt"], copies=copies, project_id=project_id
            )

            if rc > 0:
                # Only create cards for operations that actually exist in the API response
                actual_count = len(body.get("operation_names", []))

                if actual_count < copies:
                    self.log.emit(f"[WARN] Scene {actual_scene_num}: API returned {actual_count} operations but {copies} copies were requested")

                # Create cards only for videos that actually exist
                for copy_idx in range(1, actual_count + 1):
                    card = {
                        "scene": actual_scene_num,
                        "copy": copy_idx,
                        "status": "PROCESSING",
                        "json": scene["prompt"],
                        "url": "",
                        "path": "",
                        "thumb": "",
                        "dir": dir_videos
                    }
                    self.job_card.emit(card)

                    # Store card data with copy index for operation name mapping
                    job_info = {
                        'card': card,
                        'body': body,
                        'scene': actual_scene_num,
                        'copy': copy_idx
                    }
                    jobs.append(job_info)
            else:
                # All copies failed to start
                for copy_idx in range(1, copies + 1):
                    card = {
                        "scene": actual_scene_num,
                        "copy": copy_idx,
                        "status": "FAILED_START",
                        "error_reason": "Failed to start video generation",
                        "json": scene["prompt"],
                        "url": "",
                        "path": "",
                        "thumb": "",
                        "dir": dir_videos
                    }
                    self.job_card.emit(card)

        # Polling loop with improved error handling
        retry_count = {}
        download_retry_count = {}
        max_retries = 3
        max_download_retries = 5

        completed_videos = []

        for poll_round in range(120):
            if self.cancelled:
                self.log.emit("[INFO] Đã dừng xử lý theo yêu cầu người dùng.")
                return

            if not jobs:
                self.log.emit("[INFO] Tất cả video đã hoàn tất hoặc thất bại.")
                break

            # Update progress based on completed jobs
            completed_count = len(completed_videos)
            current_scene = min(completed_count + 1, total_scenes)
            self.progress_updated.emit(
                completed_count,
                total_scenes,
                f"Processing... ({completed_count}/{total_scenes} scenes completed)"
            )

            # Extract all operation names from all jobs
            names = []
            metadata = {}
            for job_info in jobs:
                job_dict = job_info['body']
                names.extend(job_dict.get("operation_names", []))
                op_meta = job_dict.get("operation_metadata", {})
                if op_meta:
                    metadata.update(op_meta)

            # Batch check with error handling
            try:
                rs = client.batch_check_operations(names, metadata)
            except Exception as e:
                self.log.emit(f"[WARN] Lỗi kiểm tra trạng thái (vòng {poll_round + 1}): {e}")
                time.sleep(10)
                continue

            new_jobs = []
            for job_info in jobs:
                card = job_info['card']
                job_dict = job_info['body']
                copy_idx = job_info['copy']

                # Get operation names list and map this copy to its operation
                op_names = job_dict.get("operation_names", [])
                if not op_names:
                    if 'no_op_count' not in job_info:
                        job_info['no_op_count'] = 0
                    job_info['no_op_count'] += 1

                    if job_info['no_op_count'] > 3:
                        sc = card['scene']
                        cp = card['copy']
                        self.log.emit(f"[WARN] Cảnh {sc} video {cp}: không có operation name sau 3 lần thử")
                    else:
                        new_jobs.append(job_info)
                    continue

                # Map copy index to the correct operation name
                op_index = copy_idx - 1
                if op_index >= len(op_names):
                    sc = card['scene']
                    cp = card['copy']
                    self.log.emit(f"[ERR] Cảnh {sc} video {cp}: operation index {op_index} out of bounds")
                    card["status"] = "FAILED"
                    card["error_reason"] = "Operation index out of bounds"
                    self.job_card.emit(card)
                    continue

                op_name = op_names[op_index]
                op_result = rs.get(op_name) or {}

                # Check raw API response
                raw_response = op_result.get('raw', {})
                status = raw_response.get('status', '')

                scene = card["scene"]
                copy_num = card["copy"]

                if status == 'MEDIA_GENERATION_STATUS_SUCCESSFUL':
                    # Extract video URL
                    op_metadata = raw_response.get('operation', {}).get('metadata', {})
                    video_info = op_metadata.get('video', {})
                    video_url = video_info.get('fifeUrl', '')

                    if video_url:
                        card["status"] = "READY"
                        card["url"] = video_url

                        self.log.emit(f"[SUCCESS] Scene {scene} Copy {copy_num}: Video ready!")

                        # Update progress: Downloading
                        self.progress_updated.emit(
                            scene - 1,
                            total_scenes,
                            f"Downloading scene {scene} copy {copy_num}..."
                        )

                        # Download video
                        raw_fn = f"{title}_scene{scene}_copy{copy_num}.mp4"
                        fn = sanitize_filename(raw_fn)
                        fp = os.path.join(dir_videos, fn)

                        self.log.emit(f"[INFO] Downloading scene {scene} copy {copy_num}...")

                        try:
                            if self._download(video_url, fp):
                                card["status"] = "DOWNLOADED"
                                card["path"] = fp

                                thumb = self._make_thumb(fp, thumbs_dir, scene, copy_num)
                                card["thumb"] = thumb

                                self.log.emit(f"[SUCCESS] ✓ Downloaded: {os.path.basename(fp)}")

                                # Track completed video and emit signal
                                if fp not in completed_videos:
                                    completed_videos.append(fp)
                                    self.scene_completed.emit(scene, fp)
                            else:
                                # Track download retries
                                download_key = f"{scene}_{copy_num}"
                                retries = download_retry_count.get(download_key, 0)
                                if retries < max_download_retries:
                                    download_retry_count[download_key] = retries + 1
                                    self.log.emit(f"[WARN] Download failed, will retry ({retries + 1}/{max_download_retries})")
                                    card["status"] = "DOWNLOAD_FAILED"
                                    card["url"] = video_url
                                    self.job_card.emit(card)
                                    new_jobs.append(job_info)
                                    continue
                                else:
                                    self.log.emit(f"[ERR] Download failed after {max_download_retries} attempts")
                                    card["status"] = "DOWNLOAD_FAILED"
                                    card["url"] = video_url
                                    card["error_reason"] = "Download failed after retries"
                                    self.job_card.emit(card)
                        except Exception as e:
                            download_key = f"{scene}_{copy_num}"
                            retries = download_retry_count.get(download_key, 0)
                            if retries < max_download_retries:
                                download_retry_count[download_key] = retries + 1
                                self.log.emit(f"[ERR] Download error: {e} - will retry ({retries + 1}/{max_download_retries})")
                                card["status"] = "DOWNLOAD_FAILED"
                                card["url"] = video_url
                                self.job_card.emit(card)
                                new_jobs.append(job_info)
                                continue
                            else:
                                self.log.emit(f"[ERR] Download error after {max_download_retries} attempts: {e}")
                                card["status"] = "DOWNLOAD_FAILED"
                                card["url"] = video_url
                                card["error_reason"] = f"Download error: {str(e)[:50]}"
                                self.job_card.emit(card)

                        self.job_card.emit(card)
                    else:
                        self.log.emit(f"[ERR] Scene {scene} Copy {copy_num}: No video URL in response")
                        card["status"] = "DONE_NO_URL"
                        card["error_reason"] = "No video URL in response"
                        self.job_card.emit(card)

                elif status == 'MEDIA_GENERATION_STATUS_FAILED':
                    # Extract error details
                    error_info = raw_response.get('operation', {}).get('error', {})
                    error_message = error_info.get('message', '')

                    # Categorize the error
                    if 'quota' in error_message.lower() or 'limit' in error_message.lower():
                        error_reason = "Vượt quota API"
                    elif 'policy' in error_message.lower() or 'content' in error_message.lower() or 'safety' in error_message.lower():
                        error_reason = "Nội dung không phù hợp"
                    elif 'timeout' in error_message.lower():
                        error_reason = "Timeout"
                    elif error_message:
                        error_reason = error_message[:80]
                    else:
                        error_reason = "Video generation failed"

                    card["status"] = "FAILED"
                    card["error_reason"] = error_reason
                    self.log.emit(f"[ERR] Scene {scene} Copy {copy_num} FAILED: {error_reason}")
                    self.job_card.emit(card)

                else:
                    # Still processing
                    card["status"] = "PROCESSING"
                    self.job_card.emit(card)
                    new_jobs.append(job_info)

            jobs = new_jobs

            if jobs:
                poll_info = f"vòng {poll_round + 1}/120"
                if poll_round >= 100:
                    self.log.emit(f"[WARN] Đang chờ {len(jobs)} video ({poll_info}) - sắp hết thời gian chờ!")
                else:
                    self.log.emit(f"[INFO] Đang chờ {len(jobs)} video ({poll_info})...")
                time.sleep(5)

        # Handle timeout
        if jobs:
            for job_info in jobs:
                card = job_info['card']
                card["status"] = "TIMEOUT"
                card["error_reason"] = "Video generation timed out"
                self.job_card.emit(card)
                self.log.emit(f"[TIMEOUT] Scene {card['scene']} Copy {card['copy']}: Generation timed out")

        # Emit completion signal
        self.all_completed.emit(completed_videos)
        self.log.emit(f"[INFO] Video generation completed: {len(completed_videos)} videos downloaded")
