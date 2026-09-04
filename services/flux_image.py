"""
Vision AI v2.0 - Hugging Face Image Generator
==============================================
Multi-model image generation wrapper for Hugging Face Inference API.
Supports automatic fallback, queue waiting, and async execution.

Supported Models (Free):
- black-forest-labs/FLUX.1-dev          (Primary - Fast, detailed)
- stabilityai/stable-diffusion-3.5-large (Backup - High quality)
- black-forest-labs/FLUX.1-schnell       (Fallback - Very fast)
"""

import os
import base64
import asyncio
import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from dotenv import load_dotenv
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

load_dotenv()

# ==========================================================
# CONFIGURATION
# ==========================================================
HF_TOKEN = os.getenv("HF_TOKEN")
API_BASE = "https://api-inference.huggingface.co/models"
MAX_RETRIES = 3
TIMEOUT_SECONDS = 90

# Updated list of free models to try (using a tuple to prevent accidental modification)
MODELS = (
    "black-forest-labs/FLUX.1-dev",           # Primary (Fast, high quality)
    "stabilityai/stable-diffusion-3.5-large", # Backup (Excellent quality, free)
    "black-forest-labs/FLUX.1-schnell",       # Fallback (Very fast)
    "dreamshaper/XL-1-0",                     # Additional fallback
    "wavymulder/Analog-Diffusion",            # Artistic style fallback
)

# Setup logging
logger = logging.getLogger("vision-ai.image_gen")

# ==========================================================
# REQUEST HANDLER WITH RETRY LOGIC
# ==========================================================
def create_session_with_retries() -> requests.Session:
    """Create a requests session with retry logic."""
    session = requests.Session()
    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# ==========================================================
# IMAGE GENERATION
# ==========================================================
async def generate_image_hf(
    prompt: str, 
    model_index: int = 0,
    negative_prompt: Optional[str] = None,
    width: int = 1024,
    height: int = 1024,
    guidance_scale: float = 7.5,
    num_inference_steps: int = 25
) -> Dict[str, Any]:
    """
    Generate an image using the Hugging Face Inference API.
    Automatically rotates through free models and handles queues.

    Args:
        prompt (str): The text prompt for the image generation.
        model_index (int): Which model to try first (0 = primary).
        negative_prompt (str, optional): Negative prompt for better results.
        width (int): Image width (default: 1024).
        height (int): Image height (default: 1024).
        guidance_scale (float): Guidance scale (default: 7.5).
        num_inference_steps (int): Number of inference steps (default: 25).

    Returns:
        Dict[str, Any]: Success status, image_data (base64), or error message.
    """
    if not HF_TOKEN:
        logger.error("HF_TOKEN not configured in .env")
        return {
            "success": False, 
            "error": "HF_TOKEN not configured in .env. Please add your Hugging Face token to the .env file."
        }

    # Validate inputs
    if not prompt or len(prompt.strip()) < 3:
        return {
            "success": False,
            "error": "Prompt must be at least 3 characters long."
        }

    # Normalize dimensions
    width, height = validate_image_parameters(width, height)

    # Create payload with parameters
    payload = {
        "inputs": prompt,
        "parameters": {
            "width": width,
            "height": height,
            "guidance_scale": guidance_scale,
            "num_inference_steps": num_inference_steps,
        }
    }

    if negative_prompt:
        payload["parameters"]["negative_prompt"] = negative_prompt

    # Try each model in order
    attempted_models = []
    session = None

    try:
        for i in range(model_index, len(MODELS)):
            model_id = MODELS[i]
            url = f"{API_BASE}/{model_id}"
            headers = {
                "Authorization": f"Bearer {HF_TOKEN}",
                "Content-Type": "application/json",
            }
            attempted_models.append(model_id)

            try:
                logger.info(f"🖼️ Generating image with {model_id}...")
                
                session = create_session_with_retries()
                response = session.post(
                    url, 
                    headers=headers, 
                    json=payload, 
                    timeout=TIMEOUT_SECONDS
                )

                # Handle Hugging Face waiting queues (Status 503 means "Model is loading, wait")
                if response.status_code == 503:
                    wait_time = int(response.headers.get("X-Wait-Time", 5))
                    logger.info(f"⏳ {model_id} is loading. Waiting {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    
                    # Retry with the same model
                    response = session.post(
                        url, 
                        headers=headers, 
                        json=payload, 
                        timeout=TIMEOUT_SECONDS
                    )

                if response.status_code == 200:
                    # Check if response is actual image data or error JSON
                    content_type = response.headers.get("Content-Type", "")
                    if "application/json" in content_type:
                        error_data = response.json()
                        if "error" in error_data:
                            logger.warning(f"{model_id} returned error: {error_data['error']}")
                            continue

                    image_base64 = base64.b64encode(response.content).decode('utf-8')
                    logger.info(f"✅ Image generated successfully with {model_id}")
                    return {
                        "success": True,
                        "image_data": image_base64,
                        "provider": f"Hugging Face ({model_id})",
                        "model": model_id,
                        "width": width,
                        "height": height,
                    }
                else:
                    logger.warning(f"⚠️ {model_id} returned status {response.status_code}. Trying next model...")

            except requests.exceptions.Timeout:
                logger.warning(f"⏱️ {model_id} timed out after {TIMEOUT_SECONDS}s. Trying next model...")
            except requests.exceptions.ConnectionError:
                logger.warning(f"🔌 Connection error with {model_id}. Trying next model...")
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Request error with {model_id}: {e}. Trying next model...")
            except Exception as e:
                logger.error(f"❌ Unexpected error with {model_id}: {e}. Trying next model...")
            finally:
                if session:
                    session.close()
                    session = None

    finally:
        if session:
            session.close()

    # If all models fail
    logger.error("All Hugging Face models failed")
    return {
        "success": False,
        "error": "All Hugging Face models failed. Please try a simpler prompt, check your token, or try again later.",
        "attempted_models": attempted_models,
    }

async def generate_flux_image(prompt: str, **kwargs) -> Dict[str, Any]:
    """
    Legacy wrapper function to maintain backward compatibility.
    Supports all parameters from generate_image_hf via kwargs.
    """
    return await generate_image_hf(prompt, model_index=0, **kwargs)

async def generate_pollinations_image(prompt: str, width: int = 1024, height: int = 1024) -> Dict[str, Any]:
    """
    True no-key serverless image generation via public Pollinations endpoint.
    Free-tier friendly; best-effort only (no SLA).
    """
    import base64
    from urllib.parse import quote
    try:
        width, height = validate_image_parameters(width, height)
        url = (
            f"https://image.pollinations.ai/prompt/{quote(prompt[:400])}"
            f"?width={width}&height={height}&nologo=true"
        )
        session = create_session_with_retries()
        r = session.get(url, timeout=90)
        if r.status_code == 200 and r.headers.get("Content-Type", "").startswith("image"):
            return {
                "success": True,
                "image_data": base64.b64encode(r.content).decode("utf-8"),
                "provider": "Pollinations-Serverless",
                "model": "pollinations",
            }
        return {"success": False, "error": f"Pollinations HTTP {r.status_code}"}
    except Exception as e:
        logger.warning(f"Pollinations serverless failed: {e}")
        return {"success": False, "error": str(e)}


async def generate_image_with_fallback(
    prompt: str,
    preferred_model: str = "black-forest-labs/FLUX.1-dev",
    **kwargs
) -> Dict[str, Any]:
    """
    Generate image with a preferred model, with fallback to other models
    and finally to no-key Pollinations serverless.
    """
    # Try preferred model first
    if preferred_model in MODELS:
        try:
            model_index = MODELS.index(preferred_model)
            result = await generate_image_hf(prompt, model_index=model_index, **kwargs)
            if result.get("success"):
                return result
        except ValueError:
            logger.warning(f"Preferred model '{preferred_model}' not found in MODELS list.")

    # Default HF rotation
    result = await generate_image_hf(prompt, model_index=0, **kwargs)
    if result.get("success"):
        return result

    # Final free serverless (no key)
    width = kwargs.get("width", 1024)
    height = kwargs.get("height", 1024)
    return await generate_pollinations_image(prompt, width=width, height=height)

# ==========================================================
# UTILITY FUNCTIONS
# ==========================================================
def estimate_generation_time(model_id: str) -> int:
    """
    Estimate generation time based on model.
    
    Args:
        model_id (str): The model ID.
    
    Returns:
        int: Estimated time in seconds.
    """
    if "schnell" in model_id:
        return 10
    elif "dev" in model_id:
        return 20
    elif "large" in model_id:
        return 30
    else:
        return 15

def validate_image_parameters(width: int, height: int) -> Tuple[int, int]:
    """
    Validate and normalize image dimensions.
    
    Args:
        width (int): Desired width.
        height (int): Desired height.
    
    Returns:
        Tuple[int, int]: Normalized (width, height).
    """
    # Clamp values to valid range
    width = max(256, min(2048, width))
    height = max(256, min(2048, height))
    
    # Ensure dimensions are multiples of 8 (better performance)
    width = (width // 8) * 8
    height = (height // 8) * 8
    
    return width, height

# ==========================================================
# EXPORTS
# ==========================================================
__all__ = [
    "generate_image_hf",
    "generate_flux_image",
    "generate_image_with_fallback",
    "generate_pollinations_image",
    "estimate_generation_time",
    "validate_image_parameters",
]

logger.info("👁️ Vision AI Hugging Face Image Generator v2.0 - Ready")