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

def _trim_prompt_text(prompt_text: Any)->str:
    """
    Extract and build the actual text prompt for video generation from structured prompt data.
    
    For new format (with localization, key_action, character_details):
    - Extracts the actual scene description from key_action or localization.{lang}.prompt
    - Includes critical consistency information (character_details, hard_locks)
    - Builds a comprehensive text prompt suitable for video generation
    
    For old format (with Objective, Persona, Task_Instructions):
    - Falls back to legacy extraction logic
    
    For plain strings:
    - Returns as-is if under limit, otherwise intelligently truncates
    """
    # Handle string input
    if isinstance(prompt_text, str):
        s=prompt_text.strip()
        # If it's a reasonable length plain string, use it as-is
        if len(s)<=MAX_PLAIN_STRING_LENGTH: return s
        # Try to parse as JSON
        try:
            obj=json.loads(s)
        except Exception:
            # Not JSON, just a long string - truncate intelligently at sentence boundary
            if len(s) <= MAX_PROMPT_LENGTH:
                return s
            # Find last period before MAX_PLAIN_STRING_LENGTH chars
            truncate_at = s.rfind('.', 0, MAX_PLAIN_STRING_LENGTH)
            if truncate_at > 3000:
                return s[:truncate_at+1]
            return s[:MAX_PLAIN_STRING_LENGTH]
    else:
        obj=prompt_text
    
    # Handle dictionary/JSON input
    if isinstance(obj, dict):
        # NEW FORMAT: Check for modern schema with localization, key_action, character_details
        if "key_action" in obj or "localization" in obj or "character_details" in obj:
            parts = []
            
            # 1. Character consistency (CRITICAL for maintaining same character across scenes)
            if obj.get("character_details"):
                parts.append(str(obj["character_details"]))
            
            # 2. Location/setting consistency (CRITICAL for maintaining same location)
            hard_locks = obj.get("hard_locks", {})
            if isinstance(hard_locks, dict):
                location_lock = hard_locks.get("location")
                if location_lock:
                    parts.append(str(location_lock))
                # Add identity lock if not already in character_details
                identity_lock = hard_locks.get("identity")
                if identity_lock and "character_details" not in obj:
                    parts.append(str(identity_lock))
            
            # 3. Setting details
            if obj.get("setting_details"):
                parts.append(str(obj["setting_details"]))
            
            # 4. Main scene description - try localization first, then key_action
            scene_description = ""
            
            # Try to get localized prompt (preferred)
            localization = obj.get("localization", {})
            if isinstance(localization, dict):
                # Try to find the best language match
                # Priority: vi (Vietnamese) > en (English) > first available
                for lang in ["vi", "en"]:
                    if lang in localization:
                        lang_data = localization[lang]
                        if isinstance(lang_data, dict) and "prompt" in lang_data:
                            scene_description = str(lang_data["prompt"])
                            break
                
                # If still no description, use first available language
                if not scene_description:
                    for lang_data in localization.values():
                        if isinstance(lang_data, dict) and "prompt" in lang_data:
                            scene_description = str(lang_data["prompt"])
                            break
            
            # Fallback to key_action if no localized prompt found
            if not scene_description and obj.get("key_action"):
                scene_description = str(obj["key_action"])
            
            if scene_description:
                parts.append(scene_description)
            
            # 5. Camera direction hints (keep it brief)
            camera_dir = obj.get("camera_direction", [])
            if isinstance(camera_dir, list) and camera_dir:
                # Just include the first and last camera hints for brevity
                try:
                    first_shot = camera_dir[0].get("shot", "") if isinstance(camera_dir[0], dict) else ""
                    last_shot = camera_dir[-1].get("shot", "") if isinstance(camera_dir[-1], dict) else ""
                    if first_shot or last_shot:
                        parts.append(f"Camera: {first_shot}; End: {last_shot}")
                except (IndexError, AttributeError):
                    pass
            
            # Combine all parts
            text = "\n\n".join([p for p in parts if p])
            
            # If still too long (>MAX_PROMPT_LENGTH chars), prioritize scene description
            if len(text) > MAX_PROMPT_LENGTH:
                # Keep: character_details + location_lock + scene_description
                priority_parts = []
                if obj.get("character_details"):
                    # Truncate character_details if very long
                    char_details = str(obj["character_details"])
                    if len(char_details) > MAX_CHARACTER_DETAILS_LENGTH:
                        char_details = char_details[:MAX_CHARACTER_DETAILS_LENGTH] + "..."
                    priority_parts.append(char_details)
                
                if hard_locks and hard_locks.get("location"):
                    priority_parts.append(str(hard_locks["location"]))
                
                if scene_description:
                    # Preserve full scene description, truncate if needed
                    if len(scene_description) > MAX_SCENE_DESCRIPTION_LENGTH:
                        scene_description = scene_description[:MAX_SCENE_DESCRIPTION_LENGTH]
                    priority_parts.append(scene_description)
                
                text = "\n\n".join(priority_parts)
            
            return text
        
        # OLD FORMAT: Legacy extraction for backward compatibility
        parts=[]
        if obj.get("Objective"): parts.append(str(obj["Objective"]))
        per=obj.get("Persona") or {}
        if isinstance(per, dict):
            tone=per.get("Tone"); role=per.get("Role")
            if role or tone: parts.append(f"Role: {role or ''}; Tone: {tone or ''}")
        inst=obj.get("Task_Instructions") or []
        if isinstance(inst, list):
            parts+= [str(x) for x in inst][:6]
        cons=obj.get("Constraints") or []
        if isinstance(cons, list):
            parts+= [str(x) for x in cons][:4]
        text=" | ".join([p for p in parts if p])
        if text: return text
    
    # Fallback: convert to JSON string and return (with reasonable limit)
    try:
        result = json.dumps(obj, ensure_ascii=False)
        if len(result) <= MAX_PROMPT_LENGTH:
            return result
        # If too long, try to extract just the essential fields
        if isinstance(obj, dict):
            essential = {k: v for k, v in obj.items() if k in ["key_action", "character_details", "setting_details"]}
            if essential:
                return json.dumps(essential, ensure_ascii=False)
        return result[:MAX_PROMPT_LENGTH]
    except Exception:
        return str(obj)[:MAX_PROMPT_LENGTH]

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
        """Start a scene with robust fallbacks: delay-after-upload, model ladder (I2V vs T2V), reupload-on-400, per-copy fallback, prompt trimming."""
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

        # compose prompt text (trim if huge/complex)
        prompt=_trim_prompt_text(prompt_text)

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
        job.setdefault("operation_names",[]); job.setdefault("video_by_idx", [None]*copies); job.setdefault("thumb_by_idx", [None]*copies); job.setdefault("op_index_map", {}); job.setdefault("operation_metadata", {})
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

        # Trim prompt if too long
        prompt_text = _trim_prompt_text(prompt)

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
