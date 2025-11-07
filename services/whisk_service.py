# -*- coding: utf-8 -*-
"""
Whisk Service - Complete implementation with correct API flow
Based on real curl analysis from labs.google
"""
import requests
import base64
import time
import uuid
from typing import Optional, Callable


class WhiskError(Exception):
    """Whisk API error"""
    pass


def get_session_cookies() -> str:
    """
    Get session cookies from config
    Returns cookie string for requests
    """
    from services.core.key_manager import get_all_keys
    session_tokens = get_all_keys('session')
    if not session_tokens:
        raise WhiskError("No Whisk session token configured")

    # Session token format: __Secure-next-auth.session-token=...
    return f"__Secure-next-auth.session-token={session_tokens[0]}"


def get_bearer_token() -> str:
    """
    Get bearer token (OAuth token) from config for Whisk API
    """
    from services.core.key_manager import get_all_keys
    
    # Try to get labs tokens (bearer tokens for aisandbox API)
    labs_tokens = get_all_keys('labs')
    if labs_tokens:
        return labs_tokens[0]
    
    # Fall back to google keys if no labs tokens
    google_keys = get_all_keys('google')
    if google_keys:
        return google_keys[0]
    
    raise WhiskError("No Bearer token (labs/google API key) configured for Whisk")


def caption_image(image_path: str, log_callback: Optional[Callable] = None) -> Optional[str]:
    """
    Step 1: Caption image using backbone.captionImage
    
    Args:
        image_path: Path to image file
        log_callback: Optional logging callback
        
    Returns:
        Caption text or None
    """
    def log(msg):
        if log_callback:
            log_callback(msg)

    try:
        # Read and encode image
        with open(image_path, 'rb') as f:
            image_data = f.read()

        b64_image = base64.b64encode(image_data).decode('utf-8')
        data_uri = f"data:image/png;base64,{b64_image}"

        # Generate IDs
        workflow_id = str(uuid.uuid4())
        session_id = f";{int(time.time() * 1000)}"

        url = "https://labs.google/fx/api/trpc/backbone.captionImage"

        cookies = get_session_cookies()

        headers = {
            "Accept": "*/*",
            "Content-Type": "application/json",
            "Cookie": cookies,
            "Origin": "https://labs.google",
            "Referer": f"https://labs.google/fx/tools/whisk/project/{workflow_id}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        payload = {
            "json": {
                "clientContext": {
                    "sessionId": session_id,
                    "workflowId": workflow_id
                },
                "captionInput": {
                    "candidatesCount": 1,
                    "mediaInput": {
                        "mediaCategory": "MEDIA_CATEGORY_SUBJECT",
                        "rawBytes": data_uri
                    }
                }
            }
        }

        log(f"[INFO] Whisk: Captioning image...")

        response = requests.post(url, json=payload, headers=headers, timeout=60)

        if response.status_code != 200:
            log(f"[ERROR] Caption failed with status {response.status_code}")
            return None

        data = response.json()

        # Parse caption from response
        try:
            result = data['result']['data']['json']
            if 'candidates' in result and result['candidates']:
                caption = result['candidates'][0].get('caption', '')
                log(f"[INFO] Whisk: Got caption ({len(caption)} chars)")
                return caption
        except (KeyError, TypeError, IndexError):
            log(f"[ERROR] Could not parse caption from response")
            return None

    except Exception as e:
        log(f"[ERROR] Caption error: {str(e)[:100]}")
        return None


def upload_image_whisk(image_path: str, workflow_id: str, session_id: str, log_callback: Optional[Callable] = None) -> Optional[str]:
    """
    Step 2: Upload image to Whisk
    
    FIXED: Parse correct nested structure from response
    
    Args:
        image_path: Path to image file
        workflow_id: Workflow UUID
        session_id: Session ID
        log_callback: Optional callback for logging
        
    Returns:
        mediaGenerationId or None if failed
    """
    def log(msg):
        if log_callback:
            log_callback(msg)

    try:
        # Read and encode image
        with open(image_path, 'rb') as f:
            image_data = f.read()

        b64_image = base64.b64encode(image_data).decode('utf-8')
        data_uri = f"data:image/png;base64,{b64_image}"

        url = "https://labs.google/fx/api/trpc/backbone.uploadImage"

        cookies = get_session_cookies()

        headers = {
            "Accept": "*/*",
            "Content-Type": "application/json",
            "Cookie": cookies,
            "Origin": "https://labs.google",
            "Referer": f"https://labs.google/fx/tools/whisk/project/{workflow_id}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        payload = {
            "json": {
                "clientContext": {
                    "workflowId": workflow_id,
                    "sessionId": session_id
                },
                "uploadMediaInput": {
                    "mediaCategory": "MEDIA_CATEGORY_SUBJECT",
                    "rawBytes": data_uri
                }
            }
        }

        log(f"[INFO] Whisk: Uploading {image_path.split('/')[-1]}...")

        response = requests.post(url, json=payload, headers=headers, timeout=60)
        log(f"[INFO] Whisk: Upload response status {response.status_code}")

        if response.status_code != 200:
            log(f"[ERROR] Whisk upload failed with status {response.status_code}")
            return None

        data = response.json()

        # CRITICAL FIX: Parse correct nested structure
        # Response: {"result": {"data": {"json": {"result": {"uploadMediaGenerationId": "..."}}}}}
        try:
            media_id = data['result']['data']['json']['result']['uploadMediaGenerationId']
            log(f"[INFO] Whisk: Got mediaGenerationId: {media_id[:30]}...")
            return media_id
        except (KeyError, TypeError) as e:
            log(f"[ERROR] No mediaGenerationId in upload response")
            log(f"[DEBUG] Response structure: {str(data)[:200]}")
            return None

    except FileNotFoundError:
        log(f"[ERROR] Image file not found: {image_path}")
        return None
    except Exception as e:
        log(f"[ERROR] Whisk upload exception: {str(e)[:100]}")
        return None


def run_image_recipe(
    prompt: str,
    recipe_media_inputs: list,
    workflow_id: str,
    session_id: str,
    log_callback: Optional[Callable] = None
) -> Optional[bytes]:
    """
    Step 3: Run image recipe with Whisk API
    
    Args:
        prompt: Text prompt for generation
        recipe_media_inputs: List of uploaded media inputs
        workflow_id: Workflow UUID
        session_id: Session ID
        log_callback: Optional logging callback
        
    Returns:
        Generated image bytes or None if failed
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
    
    try:
        # Get bearer token for API authentication
        bearer_token = get_bearer_token()
        
        url = "https://aisandbox-pa.googleapis.com/v1/whisk:runImageRecipe"
        
        headers = {
            "authorization": f"Bearer {bearer_token}",
            "content-type": "application/json; charset=utf-8",
            "origin": "https://labs.google",
            "referer": "https://labs.google/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        payload = {
            "imageRecipeInput": {
                "prompt": prompt,
                "recipeMediaInputs": recipe_media_inputs,
                "aspectRatio": "ASPECT_RATIO_SQUARE"
            },
            "clientContext": {
                "workflowId": workflow_id,
                "sessionId": session_id
            }
        }
        
        log("[INFO] Whisk: Running image recipe...")
        
        response = requests.post(url, json=payload, headers=headers, timeout=120)
        
        if response.status_code != 200:
            log(f"[ERROR] Whisk recipe failed with status {response.status_code}")
            log(f"[DEBUG] Response: {response.text[:200]}")
            return None
        
        data = response.json()
        
        # Parse the response to get generation ID or result
        # Response structure may vary, typical patterns:
        # 1. Immediate result with image data
        # 2. Generation ID for polling
        
        try:
            # Try to extract image data if available immediately
            if 'imageRecipeResult' in data:
                result = data['imageRecipeResult']
                
                # Check for direct image data
                if 'generatedImage' in result:
                    img_data = result['generatedImage']
                    if 'rawBytes' in img_data:
                        # Base64 encoded image
                        b64_data = img_data['rawBytes']
                        if b64_data.startswith('data:'):
                            # Extract base64 part from data URI
                            b64_data = b64_data.split(',', 1)[1]
                        return base64.b64decode(b64_data)
                    elif 'signedUrl' in img_data or 'downloadUrl' in img_data:
                        # Download from URL
                        download_url = img_data.get('signedUrl') or img_data.get('downloadUrl')
                        log(f"[INFO] Whisk: Downloading image from URL...")
                        img_response = requests.get(download_url, timeout=60)
                        if img_response.status_code == 200:
                            return img_response.content
                
                # Check for generation ID for polling
                if 'generationId' in result or 'mediaGenerationId' in result:
                    gen_id = result.get('generationId') or result.get('mediaGenerationId')
                    log(f"[INFO] Whisk: Got generation ID: {gen_id[:30]}...")
                    # NOTE: Async generation polling not yet implemented
                    # Whisk API returns generation ID for async requests that need to be polled
                    # This is a known limitation - immediate results only
                    log(f"[LIMITATION] Whisk: Async polling not implemented - only immediate results supported")
                    return None
            
            log(f"[ERROR] Whisk: Unexpected response structure")
            log(f"[DEBUG] Response keys: {list(data.keys())}")
            return None
            
        except (KeyError, TypeError, IndexError) as e:
            log(f"[ERROR] Whisk: Failed to parse response - {str(e)}")
            log(f"[DEBUG] Response: {str(data)[:300]}")
            return None
            
    except Exception as e:
        log(f"[ERROR] Whisk: runImageRecipe failed - {str(e)[:100]}")
        return None


def generate_image(prompt: str, model_image: Optional[str] = None, product_image: Optional[str] = None, 
                   debug_callback: Optional[Callable] = None) -> Optional[bytes]:
    """
    Generate image using Whisk with reference images
    
    Complete flow:
    1. Caption images
    2. Upload images
    3. Run image recipe
    
    Args:
        prompt: Text prompt
        model_image: Path to model/character reference image
        product_image: Path to product reference image
        debug_callback: Callback for debug logging
        
    Returns:
        Generated image as bytes or None if failed
    """
    def log(msg):
        if debug_callback:
            debug_callback(msg)

    try:
        log("[INFO] Whisk: Starting generation...")

        # Generate IDs
        workflow_id = str(uuid.uuid4())
        session_id = f";{int(time.time() * 1000)}"

        # Prepare reference images
        images_to_process = []
        if model_image:
            images_to_process.append(model_image)
        if product_image:
            images_to_process.append(product_image)

        if not images_to_process:
            raise WhiskError("No reference images provided")

        log(f"[INFO] Whisk: Processing {len(images_to_process)} reference images...")

        # Step 1 & 2: Caption and upload each image
        recipe_media_inputs = []

        for idx, img_path in enumerate(images_to_process, 1):
            log(f"[INFO] Whisk: Processing image {idx}/{len(images_to_process)}...")

            # Caption
            caption = caption_image(img_path, log)
            if not caption:
                log(f"[WARN] No caption for image {idx}, using default")
                caption = "Reference image"

            # Upload
            media_id = upload_image_whisk(img_path, workflow_id, session_id, log)

            if media_id:
                recipe_media_inputs.append({
                    "caption": caption,
                    "mediaInput": {
                        "mediaCategory": "MEDIA_CATEGORY_SUBJECT",
                        "mediaGenerationId": media_id
                    }
                })
            else:
                log(f"[ERROR] Failed to upload image {idx}")

        if not recipe_media_inputs:
            log("[ERROR] Whisk: No images uploaded successfully")
            raise WhiskError("No images uploaded")

        log(f"[INFO] Whisk: Uploaded {len(recipe_media_inputs)} images successfully")

        # Step 3: Run image recipe with OAuth
        log("[INFO] Whisk: Running image recipe with Bearer token...")
        
        result_image = run_image_recipe(
            prompt=prompt,
            recipe_media_inputs=recipe_media_inputs,
            workflow_id=workflow_id,
            session_id=session_id,
            log_callback=log
        )
        
        if result_image:
            log("[INFO] Whisk: Image generation complete!")
            return result_image
        else:
            log("[WARN] Whisk: Image generation returned no data")
            return None

    except WhiskError as e:
        log(f"[ERROR] Whisk: {str(e)}")
        return None
    except Exception as e:
        log(f"[ERROR] Whisk: Unexpected error - {str(e)[:100]}")
        return None