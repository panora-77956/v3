import base64, mimetypes, json, time, requests, re
from typing import List, Dict, Optional, Tuple, Callable, Any


# Optional default_project_id from user config (non-breaking)
try:
    from utils import config as _cfg_mod  # type: ignore
    _cfg = getattr(_cfg_mod, "load", lambda: {})() if hasattr(_cfg_mod, "load") else {}
    _cfg_pid = None
    if isinstance(_cfg, dict):
        _cfg_pid = _cfg.get("default_project_id") or (_cfg.get("labs") or {}).get("default_project_id")
    if _cfg_pid:
        DEFAULT_PROJECT_ID = _cfg_pid  # override safely if present
except Exception:
    pass


# Support both package and flat layouts
try:
    from services.endpoints import UPLOAD_IMAGE_URL, I2V_URL, T2V_URL, BATCH_CHECK_URL
except Exception:  # pragma: no cover
    from endpoints import UPLOAD_IMAGE_URL, I2V_URL, T2V_URL, BATCH_CHECK_URL

DEFAULT_PROJECT_ID = "87b19267-13d6-49cd-a7ed-db19a90c9339"

# Prompt length limits for video generation API
MAX_PROMPT_LENGTH = 5000  # Maximum total prompt length
MAX_PLAIN_STRING_LENGTH = 4000  # Maximum length for plain string prompts
MAX_CHARACTER_DETAILS_LENGTH = 1500  # Maximum length for character details when truncating
MAX_SCENE_DESCRIPTION_LENGTH = 3000  # Maximum length for scene description when truncating

def _headers(bearer: str) -> dict:
    return {
        "authorization": f"Bearer {bearer}",
        "content-type": "application/json; charset=utf-8",
        "origin": "https://labs.google",
        "referer": "https://labs.google/",
        "user-agent": "Mozilla/5.0"
    }

def _encode_image_file(path: str):
    with open(path, "rb") as f:
        raw = f.read()
    b64 = base64.b64encode(raw).decode("utf-8")
    mime = mimetypes.guess_type(path)[0] or "image/jpeg"
    return b64, mime

_URL_PAT = re.compile(r'^(https?://|gs://)', re.I)
def _collect_urls_any(obj: Any) -> List[str]:
    urls=set(); KEYS={"gcsUrl","gcsUri","signedUrl","signedUri","downloadUrl","downloadUri","videoUrl","url","uri","fileUri"}
    def visit(x):
        if isinstance(x, dict):
            for k,v in x.items():
                if k in KEYS and isinstance(v,str) and _URL_PAT.match(v): urls.add(v)
                else: visit(v)
        elif isinstance(x, list):
            for it in x: visit(it)
        elif isinstance(x, str):
            if _URL_PAT.match(x): urls.add(x)
    visit(obj)
    lst=list(urls); lst.sort(key=lambda u: (0 if "/video/" in u else 1, len(u)))
    return lst

def _normalize_status(item: dict) -> str:
    if item.get("done") is True:
        if item.get("error"): return "FAILED"
        return "DONE"
    s=item.get("status") or ""
    if s in ("MEDIA_GENERATION_STATUS_SUCCEEDED","SUCCEEDED","SUCCESS"): return "DONE"
    if s in ("MEDIA_GENERATION_STATUS_FAILED","FAILED","ERROR"): return "FAILED"
    return "PROCESSING"

def _build_complete_prompt_text(prompt_data: Any) -> str:
    """
    Build a COMPLETE text prompt from JSON structure, preserving ALL fields.
    
    This function converts the full JSON prompt to a comprehensive text format
    that includes ALL information needed for video generation.
    
    Args:
        prompt_data: Full prompt JSON (dict) or text string
        
    Returns:
        Complete text prompt with all fields preserved in structured format
    """
    # If already a string, return as-is (backward compatibility)
    if isinstance(prompt_data, str):
        return prompt_data
    
    # If not dict, convert to string
    if not isinstance(prompt_data, dict):
        return str(prompt_data)
    
    # Build complete prompt text with ALL fields
    sections = []
    
    # 1. VISUAL STYLE (CRITICAL - was being lost!)
    constraints = prompt_data.get("constraints", {})
    visual_style_tags = constraints.get("visual_style_tags", [])
    if visual_style_tags:
        style_text = ", ".join(visual_style_tags)
        sections.append(f"VISUAL STYLE: {style_text}")
    
    # 2. CHARACTER DETAILS (preserve original, no injection!)
    character_details = prompt_data.get("character_details", "")
    if character_details:
        sections.append(f"CHARACTER CONSISTENCY:\n{character_details}")
    
    # 3. HARD LOCKS (critical consistency requirements)
    hard_locks = prompt_data.get("hard_locks", {})
    if hard_locks:
        locks = []
        for key, value in hard_locks.items():
            if value:
                locks.append(f"- {key.replace('_', ' ').title()}: {value}")
        if locks:
            sections.append("CONSISTENCY REQUIREMENTS:\n" + "\n".join(locks))
    
    # 4. SETTING DETAILS
    setting_details = prompt_data.get("setting_details", "")
    if setting_details:
        sections.append(f"SETTING: {setting_details}")
    
    # 5. KEY ACTION (main scene description - NEVER truncate!)
    key_action = prompt_data.get("key_action", "")
    
    # Also check localization for scene description
    if not key_action:
        localization = prompt_data.get("localization", {})
        if isinstance(localization, dict):
            for lang in ["vi", "en"]:
                if lang in localization:
                    lang_data = localization[lang]
                    if isinstance(lang_data, dict) and "prompt" in lang_data:
                        key_action = str(lang_data["prompt"])
                        break
    
    if key_action:
        sections.append(f"SCENE ACTION:\n{key_action}")
    
    # 6. TASK INSTRUCTIONS (IMPORTANT - includes voiceover directives!)
    task_instructions = prompt_data.get("Task_Instructions", [])
    if task_instructions and isinstance(task_instructions, list):
        instructions_text = "\n".join(f"- {instr}" for instr in task_instructions)
        sections.append(f"TASK INSTRUCTIONS:\n{instructions_text}")
    
    # 7. VOICEOVER (language and text)
    audio = prompt_data.get("audio", {})
    if isinstance(audio, dict):
        voiceover = audio.get("voiceover", {})
        if isinstance(voiceover, dict):
            vo_text = voiceover.get("text", "")
            vo_lang = voiceover.get("language", "")
            if vo_text:
                sections.append(f"VOICEOVER ({vo_lang}):\n{vo_text}")
    
    # 8. CAMERA DIRECTION
    camera_dir = prompt_data.get("camera_direction", [])
    if isinstance(camera_dir, list) and camera_dir:
        cam_text = []
        for cam in camera_dir:
            if isinstance(cam, dict):
                time = cam.get("t", "")
                shot = cam.get("shot", "")
                if time and shot:
                    cam_text.append(f"[{time}] {shot}")
        if cam_text:
            sections.append("CAMERA:\n" + "\n".join(cam_text))
    
    # 9. NEGATIVES (what to avoid)
    negatives = prompt_data.get("negatives", [])
    if negatives and isinstance(negatives, list):
        neg_text = "\n".join(f"- {neg}" for neg in negatives)
        sections.append(f"AVOID:\n{neg_text}")
    
    # Combine all sections with clear separators
    complete_prompt = "\n\n".join(sections)
    
    return complete_prompt

class LabsClient:
    MAX_RETRY_ATTEMPTS = 9  # Maximum total retry attempts across all tokens
    RETRY_SLEEP_MULTIPLIER = 0.7  # Multiplier for exponential backoff sleep time
    
    def __init__(self, bearers: List[str], timeout: Tuple[int,int]=(20,180), on_event: Optional[Callable[[dict], None]]=None):
        self.tokens=[t.strip() for t in (bearers or []) if t.strip()]
        if not self.tokens: raise ValueError("No Labs tokens provided")
        self._idx=0; self.timeout=timeout; self.on_event=on_event
        self._invalid_tokens=set()  # Track tokens that returned 401

    def _tok(self)->str:
        t=self.tokens[self._idx % len(self.tokens)]; self._idx+=1; return t

    def _emit(self, kind: str, **kw):
        if self.on_event:
            try: self.on_event({"kind":kind, **kw})
            except Exception: pass

    def _post(self, url: str, payload: dict) -> dict:
        last=None
        # Calculate available tokens and max attempts
        # Note: We don't directly iterate over tokens_to_try, instead we use round-robin
        # via self._tok() and skip invalid ones. tokens_to_try is used to:
        # 1. Determine max_attempts based on valid tokens
        # 2. Reset invalid_tokens set when all tokens are invalid
        tokens_to_try = [t for t in self.tokens if t not in self._invalid_tokens]
        if not tokens_to_try:
            # All tokens are invalid, try them anyway as a fallback
            tokens_to_try = self.tokens.copy()
            self._invalid_tokens.clear()
        
        max_attempts = min(3 * len(tokens_to_try), self.MAX_RETRY_ATTEMPTS)
        attempts_made = 0
        skip_count = 0  # Prevent infinite loop when all tokens are invalid
        max_skips = len(self.tokens) * 2  # Allow skipping all tokens twice
        
        while attempts_made < max_attempts and skip_count < max_skips:
            current_token = None
            try:
                # Get next token using round-robin rotation
                current_token = self._tok()
                # Skip if this token is marked invalid (don't count as an attempt)
                if current_token in self._invalid_tokens:
                    skip_count += 1
                    continue
                
                attempts_made += 1
                skip_count = 0  # Reset skip count when we make an actual attempt
                    
                r=requests.post(url, headers=_headers(current_token), json=payload, timeout=self.timeout)
                if r.status_code==200:
                    self._emit("http_ok", code=200)
                    try: return r.json()
                    except Exception: return {}
                
                # Handle 401 Unauthorized - mark token as invalid and skip to next immediately
                if r.status_code == 401:
                    self._invalid_tokens.add(current_token)
                    token_id = f"Token #{self.tokens.index(current_token) + 1}" if current_token in self.tokens else "Unknown token"
                    error_msg = f"{token_id} is invalid (401 Unauthorized)"
                    self._emit("http_other_err", code=401, detail=error_msg)
                    # Don't sleep, immediately try next token
                    last = requests.HTTPError(f"401 Client Error: Unauthorized for url: {url}")
                    continue
                    
                det=""
                try: det=r.json().get("error",{}).get("message","")[:300]
                except Exception: det=(r.text or "")[:300]
                self._emit("http_other_err", code=r.status_code, detail=det); r.raise_for_status()
            except requests.HTTPError as e:
                error_msg = str(e).lower()
                # Check if it's a 401 in the exception message
                if '401' in error_msg or 'unauthorized' in error_msg:
                    # Mark current token as invalid
                    if current_token:
                        self._invalid_tokens.add(current_token)
                    # Don't sleep, try next token immediately
                    last=e
                    continue
                last=e; time.sleep(self.RETRY_SLEEP_MULTIPLIER*(attempts_made))
            except Exception as e:
                last=e; time.sleep(self.RETRY_SLEEP_MULTIPLIER*(attempts_made))
        
        if last is None:
            last = Exception("All tokens are invalid or max attempts reached")
        raise last

    def upload_image_file(self, image_path: str, aspect_hint="IMAGE_ASPECT_RATIO_PORTRAIT")->Optional[str]:
        b64,mime=_encode_image_file(image_path)
        payload={"imageInput":{"rawImageBytes":b64,"mimeType":mime,"isUserUploaded":True,"aspectRatio":aspect_hint},
                 "clientContext":{"sessionId":f"{int(time.time()*1000)}"}}
        data=self._post(UPLOAD_IMAGE_URL,payload) or {}
        mid=(data.get("mediaGenerationId") or {}).get("mediaGenerationId")
        return mid

    def start_one(self, job: Dict, model_key: str, aspect_ratio: str, prompt_text: str, copies:int=1, project_id: Optional[str]=DEFAULT_PROJECT_ID)->int:
        """Start a scene with robust fallbacks: delay-after-upload, model ladder (I2V vs T2V), reupload-on-400, per-copy fallback, complete prompt preservation."""
        copies=max(1,int(copies)); base_seed=int(job.get("seed",0)) if str(job.get("seed","")).isdigit() else 0
        mid=job.get("media_id")
        
        # Log which video generator will be used
        generator_type = "Image-to-Video (I2V)" if mid else "Text-to-Video (T2V)"
        self._emit("video_generator_info", generator_type=generator_type, has_start_image=bool(mid), 
                   model_key=model_key, aspect_ratio=aspect_ratio, copies=copies, project_id=project_id)

        # Give backend a moment to index the uploaded image (avoids 400/500 immediately after upload)
        time.sleep(1.0)

        # IMPORTANT: choose fallbacks based on whether we're doing I2V (has start image) or T2V (no image)
        FALLBACKS_I2V={
            "VIDEO_ASPECT_RATIO_PORTRAIT":[
                "veo_3_1_i2v_s_fast_portrait_ultra","veo_3_1_i2v_s_fast_portrait","veo_3_1_i2v_s_portrait","veo_3_1_i2v_s"
            ],
            "VIDEO_ASPECT_RATIO_LANDSCAPE":[
                "veo_3_1_i2v_s_fast_ultra","veo_3_1_i2v_s_fast","veo_3_1_i2v_s"
            ],
            "VIDEO_ASPECT_RATIO_SQUARE":[
                "veo_3_1_i2v_s_fast","veo_3_1_i2v_s"
            ]
        }
        FALLBACKS_T2V={
            "VIDEO_ASPECT_RATIO_PORTRAIT":[
                "veo_3_1_t2v_fast_ultra","veo_3_1_t2v"
            ],
            "VIDEO_ASPECT_RATIO_LANDSCAPE":[
                "veo_3_1_t2v_fast_ultra","veo_3_1_t2v"
            ],
            "VIDEO_ASPECT_RATIO_SQUARE":[
                "veo_3_1_t2v_fast_ultra","veo_3_1_t2v"
            ]
        }
        fallbacks = FALLBACKS_I2V if mid else FALLBACKS_T2V
        # start with the user's chosen model, then ladder through same-family models for the aspect
        models=[model_key]+[m for m in fallbacks.get(aspect_ratio, []) if m!=model_key]

        # compose prompt text (build complete prompt with all fields)
        prompt=_build_complete_prompt_text(prompt_text)

        def _make_body(use_model, mid_val, copies_n):
            reqs=[]
            for k in range(copies_n):
                seed=base_seed+k
                item={"aspectRatio":aspect_ratio,"seed":seed,"videoModelKey":use_model,"textInput":{"prompt":prompt}}
                if mid_val: item["startImage"]={"mediaId":mid_val}
                reqs.append(item)
            body={"requests":reqs}
            if project_id: body["clientContext"]={"projectId":project_id}
            return body

        def _try(body):
            url=I2V_URL if mid else T2V_URL
            # Log the endpoint being called
            self._emit("api_call_info", endpoint=url, endpoint_type="I2V" if mid else "T2V", 
                      request_body_keys=list(body.keys()), num_requests=len(body.get("requests", [])))
            return self._post(url, body) or {}

        def _is_invalid(e: Exception)->bool:
            s=str(e).lower()
            return ("400" in str(e)) or ("invalid json" in s) or ("invalid argument" in s)

        # 1) Try batch with model fallbacks
        data=None; last_err=None
        for mkey in models:
            try:
                self._emit("trying_model", model_key=mkey, attempt="batch")
                data=_try(_make_body(mkey, mid, copies))
                last_err=None
                self._emit("model_success", model_key=mkey, has_data=data is not None)
                break
            except Exception as e:
                last_err=e
                self._emit("model_failed", model_key=mkey, error=str(e)[:200])
                if not _is_invalid(e): break

        # 2) If invalid and have image -> reupload once then retry ladder (I2V only)
        if last_err and _is_invalid(last_err) and mid and job.get("image_path"):
            try:
                new_mid=self.upload_image_file(job["image_path"])
                if new_mid:
                    job["media_id"]=new_mid; mid=new_mid
                    for mkey in models:
                        try:
                            data=_try(_make_body(mkey, mid, copies)); last_err=None; break
                        except Exception as e2:
                            last_err=e2
                            if not _is_invalid(e2): break
            except Exception as e3:
                last_err=e3

        # 3) Per-copy fallback (still invalid)
        job.setdefault("operation_names",[])
        job.setdefault("video_by_idx", [None]*copies)
        job.setdefault("thumb_by_idx", [None]*copies)
        job.setdefault("op_index_map", {})
        job.setdefault("operation_metadata", {})
        if data is None and last_err is not None:
            for k in range(copies):
                for mkey in models:
                    try:
                        dat=_try(_make_body(mkey, mid, 1))
                        ops=dat.get("operations",[]) if isinstance(dat,dict) else []
                        if ops:
                            nm=(ops[0].get("operation") or {}).get("name") or ops[0].get("name") or ""
                            if nm: 
                                job["operation_names"].append(nm)
                                job["op_index_map"][nm]=k
                                # Store metadata for batch check (sceneId and status from Google API)
                                # Always store metadata with at least the default status for Google API compatibility
                                scene_id = ops[0].get("sceneId", "")
                                status = ops[0].get("status", "MEDIA_GENERATION_STATUS_PENDING")
                                job["operation_metadata"][nm] = {"sceneId": scene_id, "status": status}
                                break
                    except Exception: continue
            return len(job.get("operation_names",[]))

        # 4) Batch success
        ops=data.get("operations",[]) if isinstance(data,dict) else []
        self._emit("operations_result", num_operations=len(ops), data_type=type(data).__name__, 
                   has_operations_key="operations" in (data if isinstance(data, dict) else {}))
        for ci,op in enumerate(ops):
            nm=(op.get("operation") or {}).get("name") or op.get("name") or ""
            if nm: 
                job["operation_names"].append(nm)
                job["op_index_map"][nm]=ci
                # Store metadata for batch check (sceneId and status from Google API)
                # Always store metadata with at least the default status for Google API compatibility
                scene_id = op.get("sceneId", "")
                status = op.get("status", "MEDIA_GENERATION_STATUS_PENDING")
                job["operation_metadata"][nm] = {"sceneId": scene_id, "status": status}
        if job.get("operation_names"): job["status"]="PENDING"
        
        final_count = len(job.get("operation_names",[]))
        self._emit("start_one_result", operation_count=final_count, requested_copies=copies)
        return final_count

    def _wrap_ops(self, op_names: List[str], metadata: Optional[Dict[str, Dict]] = None)->dict:
        """
        Wrap operation names into the payload format for batch check.
        
        Args:
            op_names: List of operation names
            metadata: Optional dict mapping operation name to metadata (sceneId, status)
        
        Returns:
            Payload dict with operations list
        """
        uniq=[]; seen=set()
        for s in op_names or []:
            if s and s not in seen: seen.add(s); uniq.append(s)
        
        # Build operations list with metadata if available
        operations = []
        for op_name in uniq:
            op_entry = {"operation": {"name": op_name}}
            # Include sceneId and status if available in metadata
            if metadata and op_name in metadata:
                meta = metadata[op_name]
                if meta.get("sceneId"):
                    op_entry["sceneId"] = meta["sceneId"]
                if meta.get("status"):
                    op_entry["status"] = meta["status"]
            operations.append(op_entry)
        
        return {"operations": operations}

    def batch_check_operations(self, op_names: List[str], metadata: Optional[Dict[str, Dict]] = None)->Dict[str,Dict]:
        """
        Check status of video generation operations.
        
        Args:
            op_names: List of operation names to check
            metadata: Optional dict mapping operation name to metadata (sceneId, status)
        
        Returns:
            Dict mapping operation name to status info
        """
        if not op_names: return {}
        data=self._post(BATCH_CHECK_URL, self._wrap_ops(op_names, metadata)) or {}
        out={}
        def _dedup(xs):
            seen=set(); r=[]
            for x in xs:
                if x not in seen: seen.add(x); r.append(x)
            return r
        for item in data.get("operations",[]):
            key=(item.get("operation") or {}).get("name") or item.get("name") or ""
            st=_normalize_status(item)
            urls=_collect_urls_any(item.get("response",{})) or _collect_urls_any(item)
            vurls=[u for u in urls if "/video/" in u]; iurls=[u for u in urls if "/image/" in u]
            out[key or "unknown"]={"status": ("COMPLETED" if st=="DONE" and vurls else ("DONE_NO_URL" if st=="DONE" else st)),
                                   "video_urls": _dedup(vurls), "image_urls": _dedup(iurls), "raw": item}
        return out

    def generate_videos_batch(self, prompt: str, num_videos: int = 1, model_key: str = "veo_3_1_t2v_fast_ultra", 
                              aspect_ratio: str = "VIDEO_ASPECT_RATIO_LANDSCAPE", 
                              project_id: Optional[str] = DEFAULT_PROJECT_ID) -> List[str]:
        """
        Generate multiple videos in one API call (PR#4: Batch video generation)
        Google Lab Flow supports up to 4 videos per request
        
        Args:
            prompt: Text prompt for video generation
            num_videos: Number of videos to generate (max 4)
            model_key: Video model to use
            aspect_ratio: Aspect ratio (e.g., VIDEO_ASPECT_RATIO_LANDSCAPE)
            project_id: Project ID for the request
            
        Returns:
            List of operation names for polling
        """
        if num_videos > 4:
            num_videos = 4

        # Build complete prompt with all fields
        prompt_text = _build_complete_prompt_text(prompt)

        # Build batch request with multiple copies
        requests_list = []
        for i in range(num_videos):
            seed = int(time.time() * 1000) + i
            item = {
                "aspectRatio": aspect_ratio,
                "seed": seed,
                "videoModelKey": model_key,
                "textInput": {"prompt": prompt_text}
            }
            requests_list.append(item)

        payload = {"requests": requests_list}
        if project_id:
            payload["clientContext"] = {"projectId": project_id}

        # Call T2V endpoint
        data = self._post(T2V_URL, payload) or {}

        # Extract operation names
        operations = data.get("operations", [])
        operation_names = []
        for op in operations:
            name = (op.get("operation") or {}).get("name") or op.get("name") or ""
            if name:
                operation_names.append(name)

        return operation_names
