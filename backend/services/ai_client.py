"""
AI Client Service
Handles HTTP communication with Stability Matrix AI Server (Forge / A1111 REST API)
Includes mock simulation support for offline/isolated development environments.
"""

import os
import io
import time
import base64
import logging
import requests
from typing import Dict, Any

logger = logging.getLogger('luma.ai_client')

class AIClient:
    def __init__(self):
        # AI Server IP / URL (Configured for node 3: 192.168.1.30:7860, or local dev: http://127.0.0.1:7860)
        self.server_url = os.environ.get('AI_SERVER_URL', 'http://127.0.0.1:7860').rstrip('/')
        self.mock_mode = os.environ.get('AI_MOCK_MODE', 'false').lower() in ('true', '1', 'yes')
        
        # Real AI Server generation timeout (120-180 seconds recommended for SDXL models on GPU)
        self.server_timeout = int(os.environ.get('AI_SERVER_TIMEOUT') or os.environ.get('AI_TIMEOUT_SECONDS') or '180')
        
        # Short connect timeout (seconds) to detect quickly if AI server is offline
        self.connect_timeout = int(os.environ.get('AI_CONNECT_TIMEOUT', '10'))
        
        # Whether to allow procedural mock fallback when AI server cannot be reached
        self.allow_fallback = os.environ.get('AI_ALLOW_FALLBACK_MOCK', 'true').lower() in ('true', '1', 'yes')
        
        logger.info(
            f"AIClient initialized. Server URL: {self.server_url}, Mock Mode: {self.mock_mode}, "
            f"Server Timeout: {self.server_timeout}s, Connect Timeout: {self.connect_timeout}s, Allow Fallback: {self.allow_fallback}"
        )

    def is_healthy(self) -> bool:
        """Check if AI Server is reachable"""
        if self.mock_mode:
            return True
        try:
            res = requests.get(f"{self.server_url}/sdapi/v1/options", timeout=self.connect_timeout)
            return res.status_code == 200
        except Exception as e:
            logger.warning(f"AI Server health check failed: {e}")
            return False

    def generate_txt2img(self, 
                          prompt: str, 
                          negative_prompt: str = "", 
                          width: int = 512, 
                          height: int = 512, 
                          steps: int = 20, 
                          cfg_scale: float = 7.0, 
                          seed: int = -1) -> Dict[str, Any]:
        """
        Generate image from text prompt via Stability Matrix (Forge/A1111 API)
        Endpoint: POST /sdapi/v1/txt2img
        """
        if self.mock_mode:
            logger.info(f"[MOCK MODE] Simulating txt2img generation for prompt: '{prompt}'")
            return self._generate_mock_result(prompt, width, height, steps, seed, mode="txt2img")

        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "steps": steps,
            "cfg_scale": cfg_scale,
            "width": width,
            "height": height,
            "seed": seed,
            "sampler_name": "Euler a",
            "batch_size": 1,
            "n_iter": 1,
            "save_images": False
        }

        endpoint = f"{self.server_url}/sdapi/v1/txt2img"
        logger.info(f"Calling AI Server txt2img endpoint: {endpoint} (Prompt: '{prompt[:60]}...', Timeout: {self.server_timeout}s)")

        start_time = time.time()
        try:
            response = requests.post(
                endpoint, 
                json=payload, 
                timeout=(self.connect_timeout, self.server_timeout)
            )

            # 1. Handle HTTP error codes from Forge
            if response.status_code != 200:
                err_detail = self._extract_error_detail(response)
                logger.error(f"Forge AI Server returned HTTP {response.status_code}: {err_detail}")
                raise RuntimeError(f"Forge AI Server error ({response.status_code}): {err_detail}")

            # 2. Parse response JSON safely
            try:
                data = response.json()
            except Exception as json_err:
                logger.error(f"Failed to parse Forge API response as JSON: {json_err}. Body: {response.text[:200]}")
                raise ValueError(f"AI Server returned non-JSON response: {json_err}")

            elapsed = time.time() - start_time
            logger.info(f"AI Server generation completed in {elapsed:.2f}s")

            images = data.get("images", [])
            if not images:
                raise ValueError("No images returned from AI Server")

            return {
                "image_base64": images[0],
                "seed": seed,
                "elapsed_seconds": round(elapsed, 2),
                "info": data.get("info", "")
            }

        except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError) as conn_err:
            logger.warning(f"[FALLBACK TRIGGERED] AI Server at {endpoint} is unreachable (connect timeout {self.connect_timeout}s): {conn_err}")
            if self.allow_fallback:
                logger.info(f"[FALLBACK ACTIVE] Generating simulated procedural image for prompt: '{prompt[:50]}...'")
                return self._generate_mock_result(prompt, width, height, steps, seed, mode="txt2img (fallback)")
            raise RuntimeError(f"Cannot connect to AI Server at {self.server_url}: {conn_err}")

        except requests.exceptions.ReadTimeout as timeout_err:
            logger.error(f"AI Server generation timed out after {self.server_timeout}s: {timeout_err}")
            raise TimeoutError(f"AI Server generation timed out after {self.server_timeout} seconds. Consider smaller dimensions or fewer steps.")

        except requests.exceptions.RequestException as req_err:
            logger.error(f"AI Server request failed: {req_err}")
            raise RuntimeError(f"AI Server request failed: {req_err}")

    def generate_img2img(self, 
                          init_image_base64: str, 
                          prompt: str, 
                          negative_prompt: str = "", 
                          width: int = 512, 
                          height: int = 512, 
                          steps: int = 20, 
                          cfg_scale: float = 7.0, 
                          denoising_strength: float = 0.75, 
                          seed: int = -1) -> Dict[str, Any]:
        """
        Generate image from existing image via Stability Matrix (Forge/A1111 API)
        Endpoint: POST /sdapi/v1/img2img
        """
        clean_base64 = self._strip_base64_header(init_image_base64)

        if self.mock_mode:
            logger.info(f"[MOCK MODE] Simulating img2img generation for prompt: '{prompt}'")
            return self._generate_mock_result(prompt, width, height, steps, seed, mode="img2img")

        payload = {
            "init_images": [clean_base64],
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "steps": steps,
            "cfg_scale": cfg_scale,
            "width": width,
            "height": height,
            "seed": seed,
            "denoising_strength": denoising_strength,
            "sampler_name": "Euler a",
            "batch_size": 1,
            "n_iter": 1,
            "save_images": False
        }

        endpoint = f"{self.server_url}/sdapi/v1/img2img"
        logger.info(f"Calling AI Server img2img endpoint: {endpoint} (Timeout: {self.server_timeout}s)")

        start_time = time.time()
        try:
            response = requests.post(
                endpoint, 
                json=payload, 
                timeout=(self.connect_timeout, self.server_timeout)
            )

            if response.status_code != 200:
                err_detail = self._extract_error_detail(response)
                logger.error(f"Forge AI Server returned HTTP {response.status_code}: {err_detail}")
                raise RuntimeError(f"Forge AI Server error ({response.status_code}): {err_detail}")

            try:
                data = response.json()
            except Exception as json_err:
                logger.error(f"Failed to parse Forge API response as JSON: {json_err}. Body: {response.text[:200]}")
                raise ValueError(f"AI Server returned non-JSON response: {json_err}")

            elapsed = time.time() - start_time
            logger.info(f"AI Server img2img completed in {elapsed:.2f}s")

            images = data.get("images", [])
            if not images:
                raise ValueError("No images returned from AI Server")

            return {
                "image_base64": images[0],
                "seed": seed,
                "elapsed_seconds": round(elapsed, 2),
                "info": data.get("info", "")
            }

        except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError) as conn_err:
            logger.warning(f"[FALLBACK TRIGGERED] AI Server at {endpoint} is unreachable: {conn_err}")
            if self.allow_fallback:
                logger.info("[FALLBACK ACTIVE] Generating simulated procedural image for img2img")
                return self._generate_mock_result(prompt, width, height, steps, seed, mode="img2img (fallback)")
            raise RuntimeError(f"Cannot connect to AI Server at {self.server_url}: {conn_err}")

        except requests.exceptions.ReadTimeout as timeout_err:
            logger.error(f"AI Server img2img timed out after {self.server_timeout}s: {timeout_err}")
            raise TimeoutError(f"AI Server generation timed out after {self.server_timeout} seconds.")

        except requests.exceptions.RequestException as req_err:
            logger.error(f"AI Server request failed: {req_err}")
            raise RuntimeError(f"AI Server request failed: {req_err}")

    def _extract_error_detail(self, response: requests.Response) -> str:
        """Helper to extract meaningful error message from Forge response"""
        try:
            data = response.json()
            if isinstance(data, dict):
                return data.get('error') or data.get('detail') or data.get('message') or str(data)
        except Exception:
            pass
        return response.text[:300] or f"HTTP {response.status_code}"

    def _strip_base64_header(self, data_url: str) -> str:
        """Helper to extract pure base64 string from data URI"""
        if ',' in data_url:
            return data_url.split(',', 1)[1]
        return data_url

    def _generate_mock_result(self, prompt: str, width: int, height: int, steps: int, seed: int, mode: str) -> Dict[str, Any]:
        """
        Generates an aesthetic procedural image for development and testing
        when AI Server is offline or being developed on a separate machine.
        """
        time.sleep(1.2)
        
        try:
            # pyrefly: ignore [missing-import]
            from PIL import Image, ImageDraw
            img = Image.new('RGB', (width, height), color=(15, 23, 42))
            draw = ImageDraw.Draw(img)

            colors = [
                (99, 102, 241),   # Indigo
                (168, 85, 247),  # Purple
                (236, 72, 153),  # Pink
                (59, 130, 246)   # Blue
            ]
            for i in range(5):
                r = int(min(width, height) * (0.35 + i * 0.1))
                cx = int(width * (0.3 + (i * 0.12) % 0.4))
                cy = int(height * (0.3 + (i * 0.15) % 0.4))
                c = colors[i % len(colors)]
                draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=c, width=3)

            banner_height = 80
            draw.rectangle([0, height - banner_height, width, height], fill=(10, 13, 20))
            
            title_text = f"LUMA AI STUDIO - {mode.upper()}"
            draw.text((20, height - banner_height + 15), title_text, fill=(248, 250, 252))
            
            prompt_snip = (prompt[:50] + '...') if len(prompt) > 50 else prompt
            draw.text((20, height - banner_height + 42), f"Prompt: {prompt_snip}", fill=(148, 163, 184))

            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            img_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        except ImportError:
            img_b64 = (
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
                "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
            )

        return {
            "image_base64": img_b64,
            "seed": seed if seed != -1 else 4289102,
            "elapsed_seconds": 1.25,
            "info": f"Simulated LUMA generation ({mode})"
        }

# Global singleton client instance
ai_client = AIClient()
