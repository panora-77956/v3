# -*- coding: utf-8 -*-
"""
Parallel Worker - Multi-account parallel processing for Labs Flow API
Distributes jobs across multiple Google accounts using round-robin
"""
import threading
import time
from queue import Queue
from typing import List, Tuple

from PyQt5.QtCore import QObject, pyqtSignal


class ParallelSeqWorker(QObject):
    """
    Parallel worker that distributes jobs across multiple Google Labs accounts
    Each account processes its batch sequentially in a separate thread
    """

    # Signals
    log = pyqtSignal(str, str)          # Log level, message
    progress = pyqtSignal(int, str)     # Progress value, progress text
    row_update = pyqtSignal(int, dict)  # Row index, job data
    started = pyqtSignal()              # Worker started
    finished = pyqtSignal(int)          # Worker finished with count

    def __init__(self, account_mgr, jobs, model, aspect, copies, project_id=None):
        """
        Initialize parallel worker
        
        Args:
            account_mgr: AccountManager instance with multiple accounts
            jobs: List of job dictionaries to process
            model: Model to use for generation
            aspect: Aspect ratio
            copies: Number of copies per scene
            project_id: (Deprecated) Google Labs project ID - now uses account-specific IDs
        """
        super().__init__()
        self.account_mgr = account_mgr
        self.jobs = jobs
        self.model = model
        self.aspect = aspect
        self.copies = copies
        self.project_id = project_id  # Kept for backward compatibility, not used

        # Thread coordination
        self.results_queue = Queue()
        self.should_stop = False
        self._lock = threading.Lock()

        # Progress tracking
        self.total_jobs = len(jobs)
        self.completed_jobs = 0

    def run(self):
        """Execute jobs in parallel across multiple accounts"""
        try:
            self.started.emit()

            # Check if multi-account is enabled
            if not self.account_mgr.is_multi_account_enabled():
                self.log.emit("INFO", "Multi-account disabled, falling back to sequential mode")
                self._run_sequential()
                return

            # Get enabled accounts
            accounts = self.account_mgr.get_enabled_accounts()
            num_accounts = len(accounts)

            self.log.emit("INFO", f"🚀 Parallel mode: {num_accounts} accounts, {self.total_jobs} jobs")

            # Distribute jobs across accounts using round-robin
            batches = self._distribute_jobs(self.jobs, num_accounts)

            # Create and start threads (one per account)
            threads = []
            for i, (account, batch) in enumerate(zip(accounts, batches)):
                if not batch:  # Skip empty batches
                    continue

                thread = threading.Thread(
                    target=self._process_batch,
                    args=(account, batch, i),
                    daemon=True,
                    name=f"Worker-{account.name}"
                )
                threads.append(thread)
                self.log.emit("INFO", f"Thread {i+1}: {len(batch)} jobs → {account.name}")
                thread.start()

            # Monitor progress from all threads
            self._monitor_progress(threads)

            # All threads completed
            self.progress.emit(100, "Hoàn tất gửi song song")
            self.finished.emit(1)

        except Exception as e:
            self.log.emit("ERR", f"Parallel worker error: {e}")
            self.finished.emit(0)

    def _distribute_jobs(self, jobs: List[dict], num_accounts: int) -> List[List[Tuple[int, dict]]]:
        """
        Distribute jobs across accounts using round-robin
        
        Args:
            jobs: List of job dictionaries
            num_accounts: Number of accounts to distribute across
            
        Returns:
            List of batches, where each batch is a list of (job_index, job) tuples
        """
        batches = [[] for _ in range(num_accounts)]

        for idx, job in enumerate(jobs):
            account_idx = idx % num_accounts
            batches[account_idx].append((idx, job))

        return batches

    def _process_batch(self, account, batch: List[Tuple[int, dict]], thread_id: int):
        """
        Process a batch of jobs sequentially for one account
        Runs in a separate thread
        
        Args:
            account: LabsAccount object with tokens and project_id
            batch: List of (job_index, job_dict) tuples
            thread_id: Thread identifier for logging
        """
        try:
            # Import here to avoid circular imports
            from services.google.labs_flow_client import LabsFlowClient

            # Create client for this account
            client = LabsFlowClient(account.tokens, on_event=None)

            # Use account-specific project_id instead of global one
            account_project_id = account.project_id

            thread_name = f"T{thread_id+1}"

            # Process each job in batch sequentially
            for job_idx, job in batch:
                if self.should_stop:
                    self.log.emit("WARN", f"{thread_name}: Stopped by user")
                    break

                try:
                    # Upload image if needed
                    if job.get("image_path") and not job.get("media_id"):
                        self.log.emit("INFO", f"{thread_name}: Uploading image for job {job_idx+1}")

                        try:
                            media_id = client.upload_image_file(job["image_path"])
                            job["media_id"] = media_id
                            self.log.emit("HTTP", f"{thread_name}: Upload OK mediaId={media_id}")
                        except Exception as e:
                            self.log.emit("ERR", f"{thread_name}: Upload failed: {e}")
                            job["status"] = "UPLOAD_FAILED"
                            self._queue_update(job_idx, job)
                            continue

                    # Start generation
                    self.log.emit("INFO", f"{thread_name}: Starting generation for job {job_idx+1}")

                    rc = client.start_one(
                        job, 
                        self.model, 
                        self.aspect, 
                        job.get("prompt", ""),
                        copies=self.copies,
                        project_id=account_project_id
                    )

                    # CRITICAL FIX: Store account name so CheckWorker can use correct client
                    # Each operation must be checked with the same account that created it
                    job["account_name"] = account.name

                    self.log.emit("HTTP", f"{thread_name}: START OK -> {rc} ref(s)")

                    # Queue update
                    self._queue_update(job_idx, job)

                    # Rate limiting: small delay between jobs in same thread
                    time.sleep(0.5)

                except Exception as e:
                    self.log.emit("ERR", f"{thread_name}: Job {job_idx+1} failed: {e}")
                    self._queue_update(job_idx, job)

            self.log.emit("INFO", f"{thread_name}: Batch complete ({len(batch)} jobs)")

        except Exception as e:
            self.log.emit("ERR", f"Thread {thread_id+1} error: {e}")

    def _queue_update(self, job_idx: int, job: dict):
        """
        Queue a job update for the main thread
        Thread-safe method to update progress
        """
        self.results_queue.put(("update", job_idx, job))

    def _monitor_progress(self, threads: List[threading.Thread]):
        """
        Monitor progress from all threads
        Processes updates from the queue and waits for threads to complete
        
        Args:
            threads: List of worker threads
        """
        while True:
            # Check if all threads are done
            all_done = all(not t.is_alive() for t in threads)

            # Process queued updates
            updates_processed = 0
            while not self.results_queue.empty():
                try:
                    msg_type, job_idx, job = self.results_queue.get_nowait()

                    if msg_type == "update":
                        # Emit update to main thread
                        self.row_update.emit(job_idx, job)

                        # Update progress
                        with self._lock:
                            self.completed_jobs += 1
                            progress_pct = int(self.completed_jobs * 100 / self.total_jobs)
                            self.progress.emit(
                                progress_pct,
                                f"Đã gửi {self.completed_jobs}/{self.total_jobs} cảnh"
                            )

                        updates_processed += 1

                except Exception as e:
                    self.log.emit("ERR", f"Monitor error: {e}")
                    break

            # If all threads done and queue empty, we're finished
            if all_done and self.results_queue.empty():
                break

            # Small sleep to avoid busy-waiting
            time.sleep(0.1)

    def _run_sequential(self):
        """
        Fallback to sequential processing with primary account
        Used when multi-account is not enabled
        """
        try:
            from services.google.labs_flow_client import LabsFlowClient

            # Get primary account
            account = self.account_mgr.get_primary_account()
            if not account:
                self.log.emit("ERR", "No accounts available")
                self.finished.emit(0)
                return

            # Create client
            client = LabsFlowClient(account.tokens, on_event=None)

            # Use account-specific project_id
            account_project_id = account.project_id

            # Process jobs sequentially
            total = max(1, len(self.jobs))
            done = 0

            for i, job in enumerate(self.jobs):
                if self.should_stop:
                    break

                # Upload image if needed
                if job.get("image_path"):
                    self.log.emit("INFO", f"[{i+1}/{len(self.jobs)}] Upload ảnh…")
                    self.progress.emit(int(done * 100 / total), f"Cảnh {i+1}/{len(self.jobs)}: upload…")

                    if not job.get("media_id"):
                        try:
                            mid = client.upload_image_file(job["image_path"])
                            job["media_id"] = mid
                            self.log.emit("HTTP", f"UPLOAD OK mediaId={mid}")
                        except Exception as e:
                            self.log.emit("ERR", f"Upload lỗi: {e}")
                            job["status"] = "UPLOAD_FAILED"
                            self.row_update.emit(i, job)
                            continue

                # Start generation
                self.log.emit("INFO", f"[{i+1}/{len(self.jobs)}] Start generate…")
                try:
                    self.progress.emit(int(done * 100 / total), f"Cảnh {i+1}/{len(self.jobs)}: start…")
                    rc = client.start_one(
                        job, self.model, self.aspect, job.get("prompt", ""), 
                        copies=self.copies, project_id=account_project_id
                    )
                    self.log.emit("HTTP", f"START OK -> {rc} ref(s).")
                except Exception as e:
                    self.log.emit("ERR", f"Start thất bại: {e}")

                self.row_update.emit(i, job)
                done += 1
                self.progress.emit(int(done * 100 / total), f"Đã gửi {done}/{len(self.jobs)} cảnh")
                time.sleep(1.2)

            self.progress.emit(100, "Hoàn tất gửi tuần tự")
            self.finished.emit(1)

        except Exception as e:
            self.log.emit("ERR", f"Sequential fallback error: {e}")
            self.finished.emit(0)

    def stop(self):
        """Signal the worker to stop processing"""
        self.should_stop = True
        self.log.emit("WARN", "Stop signal received")
