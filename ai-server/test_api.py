#!/usr/bin/env python3
"""
LUMA — AI Server API Test Script
Tests connectivity, text-to-image, and image-to-image endpoints
on Stability Matrix (Forge WebUI / Automatic1111 API)
"""

import os
import time
import base64
import argparse
import requests

DEFAULT_SERVER_URL = os.environ.get("AI_SERVER_URL", "http://192.168.1.30:7860").rstrip('/')

def check_health(server_url: str):
    """Test ping and fetch active checkpoint options"""
    print(f"\n[+] Checking AI Server connectivity at: {server_url} ...")
    try:
        start = time.time()
        res = requests.get(f"{server_url}/sdapi/v1/options", timeout=10)
        elapsed = time.time() - start
        
        if res.status_code == 200:
            data = res.json()
            model = data.get("sd_model_checkpoint", "Unknown Model")
            print(f"[SUCCESS] AI Server is ONLINE! (Response time: {elapsed:.2f}s)")
            print(f"    Active Model: {model}")
            return True
        else:
            print(f"[WARNING] Server responded with HTTP {res.status_code}: {res.text[:100]}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Could not connect to {server_url}.")
        print("    1. Is Stability Matrix running with '--api --listen' flags?")
        print("    2. Is Windows Firewall allowing inbound traffic on port 7860?")
        return False
    except Exception as e:
        print(f"[ERROR] Request failed: {e}")
        return False


def test_txt2img(server_url: str, prompt: str, negative_prompt: str, width: int, height: int, steps: int, cfg_scale: float, output_path: str):
    """Test Text-to-Image generation"""
    endpoint = f"{server_url}/sdapi/v1/txt2img"
    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "steps": steps,
        "cfg_scale": cfg_scale,
        "width": width,
        "height": height,
        "seed": -1,
        "sampler_name": "Euler a",
        "save_images": False
    }

    print("\n[+] Testing Text-to-Image generation...")
    print(f"    Endpoint: {endpoint}")
    print(f"    Prompt: '{prompt}'")
    print(f"    Resolution: {width}x{height}, Steps: {steps}, CFG: {cfg_scale}")

    start = time.time()
    try:
        response = requests.post(endpoint, json=payload, timeout=180)
        elapsed = time.time() - start

        if response.status_code != 200:
            print(f"[FAILED] HTTP {response.status_code}: {response.text}")
            return False

        data = response.json()
        images = data.get("images", [])
        if not images:
            print("[FAILED] Response received but 'images' list is empty.")
            return False

        # Save first image to disk
        image_bytes = base64.b64decode(images[0])
        with open(output_path, "wb") as f:
            f.write(image_bytes)

        print(f"[SUCCESS] Generated image successfully in {elapsed:.2f}s!")
        print(f"    Saved output to: {os.path.abspath(output_path)}")
        return True

    except Exception as e:
        print(f"[ERROR] Generation failed: {e}")
        return False


def test_img2img(server_url: str, input_image_path: str, prompt: str, denoising_strength: float, steps: int, output_path: str):
    """Test Image-to-Image generation"""
    endpoint = f"{server_url}/sdapi/v1/img2img"

    if not os.path.isfile(input_image_path):
        print(f"[ERROR] Input image file not found: {input_image_path}")
        return False

    with open(input_image_path, "rb") as f:
        init_image_b64 = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "init_images": [init_image_b64],
        "prompt": prompt,
        "negative_prompt": "blurry, bad quality",
        "steps": steps,
        "cfg_scale": 7.0,
        "denoising_strength": denoising_strength,
        "sampler_name": "Euler a",
        "save_images": False
    }

    print("\n[+] Testing Image-to-Image generation...")
    print(f"    Endpoint: {endpoint}")
    print(f"    Input image: {input_image_path}")
    print(f"    Prompt: '{prompt}'")
    print(f"    Denoising strength: {denoising_strength}")

    start = time.time()
    try:
        response = requests.post(endpoint, json=payload, timeout=180)
        elapsed = time.time() - start

        if response.status_code != 200:
            print(f"[FAILED] HTTP {response.status_code}: {response.text}")
            return False

        data = response.json()
        images = data.get("images", [])
        if not images:
            print("[FAILED] Response received but 'images' list is empty.")
            return False

        image_bytes = base64.b64decode(images[0])
        with open(output_path, "wb") as f:
            f.write(image_bytes)

        print(f"[SUCCESS] Image-to-Image completed in {elapsed:.2f}s!")
        print(f"    Saved output to: {os.path.abspath(output_path)}")
        return True

    except Exception as e:
        print(f"[ERROR] img2img failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="LUMA — Stability Matrix AI Server Test Tool")
    parser.add_argument("--url", default=DEFAULT_SERVER_URL, help=f"AI Server URL (default: {DEFAULT_SERVER_URL})")
    
    subparsers = parser.add_subparsers(dest="command", help="Commands to run")

    # Command: ping
    subparsers.add_parser("ping", help="Check server health and loaded model")

    # Command: txt2img
    txt_parser = subparsers.add_parser("txt2img", help="Test Text-to-Image")
    txt_parser.add_argument("-p", "--prompt", default="A magnificent crystal mountain glowing under a starry galaxy, 8k, cinematic lighting", help="Prompt text")
    txt_parser.add_argument("-n", "--negative", default="blurry, distorted, low quality", help="Negative prompt")
    txt_parser.add_argument("--width", type=int, default=512, help="Width in pixels")
    txt_parser.add_argument("--height", type=int, default=512, help="Height in pixels")
    txt_parser.add_argument("--steps", type=int, default=20, help="Sampling steps")
    txt_parser.add_argument("--cfg", type=float, default=7.0, help="CFG scale")
    txt_parser.add_argument("-o", "--output", default="test_txt2img_output.png", help="Output filename")

    # Command: img2img
    img_parser = subparsers.add_parser("img2img", help="Test Image-to-Image")
    img_parser.add_argument("-i", "--input", required=True, help="Input image file path")
    img_parser.add_argument("-p", "--prompt", default="oil painting style, vibrant colors", help="Prompt text")
    img_parser.add_argument("--denoise", type=float, default=0.7, help="Denoising strength (0.1 - 1.0)")
    img_parser.add_argument("--steps", type=int, default=20, help="Sampling steps")
    img_parser.add_argument("-o", "--output", default="test_img2img_output.png", help="Output filename")

    args = parser.parse_args()

    if not args.command:
        # Default run: ping check and guide
        check_health(args.url)
        print("\nUsage tips:")
        print("  python test_api.py ping                       # Check connection")
        print("  python test_api.py txt2img -p 'cyberpunk cat' # Generate test image")
        print("  python test_api.py img2img -i input.png -p 'anime style'")
        return

    if args.command == "ping":
        check_health(args.url)
    elif args.command == "txt2img":
        test_txt2img(args.url, args.prompt, args.negative, args.width, args.height, args.steps, args.cfg, args.output)
    elif args.command == "img2img":
        test_img2img(args.url, args.input, args.prompt, args.denoise, args.steps, args.output)

if __name__ == "__main__":
    main()
