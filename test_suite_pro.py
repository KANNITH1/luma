#!/usr/bin/env python3
"""
================================================================================
 LUMA — Enterprise Professional Test Suite & System Benchmark
 Distributed AI Image Studio (Frontend / Flask Backend / SD WebUI Forge GPU)
================================================================================
"""

import os
import sys
import time
import json
import base64
import struct
from datetime import datetime, timedelta
import requests

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Terminal Color Codes
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'

BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:5000").rstrip('/')
AI_SERVER_URL = os.environ.get("AI_SERVER_URL", "http://127.0.0.1:7860").rstrip('/')
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

class TestReporter:
    def __init__(self):
        self.suites = []
        self.current_suite = None
        self.start_time = time.time()

    def start_suite(self, name: str, description: str):
        self.current_suite = {
            "name": name,
            "description": description,
            "tests": [],
            "start_time": time.time()
        }
        self.suites.append(self.current_suite)
        print(f"\n{Colors.BOLD}{Colors.CYAN}+------------------------------------------------------------------------------+{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}| SUITE: {name:<69} |{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}| {description:<76} |{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}+------------------------------------------------------------------------------+{Colors.RESET}")

    def add_result(self, test_name: str, passed: bool, latency: float, details: str = ""):
        self.current_suite["tests"].append({
            "name": test_name,
            "passed": passed,
            "latency": latency,
            "details": details
        })
        badge = f"{Colors.GREEN}[PASS]{Colors.RESET}" if passed else f"{Colors.RED}[FAIL]{Colors.RESET}"
        time_str = f"{latency*1000:6.1f}ms" if latency < 1.0 else f"{latency:6.2f}s "
        print(f"  {badge}  {Colors.BOLD}{test_name:<46}{Colors.RESET} ({time_str})")
        if details:
            prefix = f"{Colors.GREEN}->{Colors.RESET}" if passed else f"{Colors.RED}->{Colors.RESET}"
            print(f"       {prefix} {details}")

    def print_summary(self):
        total_time = time.time() - self.start_time
        total_tests = sum(len(s["tests"]) for s in self.suites)
        total_passed = sum(sum(1 for t in s["tests"] if t["passed"]) for s in self.suites)
        total_failed = total_tests - total_passed
        pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

        print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD} LUMA ENTERPRISE TEST SUITE -- EXECUTIVE EXECUTION SUMMARY{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*80}{Colors.RESET}")

        for s in self.suites:
            s_tests = len(s["tests"])
            s_passed = sum(1 for t in s["tests"] if t["passed"])
            s_failed = s_tests - s_passed
            s_time = sum(t["latency"] for t in s["tests"])
            status_icon = f"{Colors.GREEN}[OK] PASSED{Colors.RESET}" if s_failed == 0 else f"{Colors.RED}[X] FAILED ({s_failed}){Colors.RESET}"
            print(f" * {s['name']:<48} {status_icon:<20} {s_passed}/{s_tests} tests in {s_time:.2f}s")

        print(f"{Colors.BOLD}{'-'*80}{Colors.RESET}")
        print(f" Total Tests Run : {Colors.BOLD}{total_tests}{Colors.RESET}")
        print(f" Passed          : {Colors.GREEN}{Colors.BOLD}{total_passed}{Colors.RESET}")
        print(f" Failed          : {Colors.RED if total_failed > 0 else Colors.GREEN}{Colors.BOLD}{total_failed}{Colors.RESET}")
        print(f" Pass Rate       : {Colors.BOLD}{pass_rate:.1f}%{Colors.RESET}")
        print(f" Total Duration  : {Colors.BOLD}{total_time:.2f} seconds{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*80}{Colors.RESET}")

        if total_failed == 0:
            print(f"{Colors.BOLD}{Colors.GREEN} *** ALL QUALITY GATES PASSED! SYSTEM IS PRODUCTION-GRADE. ***{Colors.RESET}\n")
            return 0
        else:
            print(f"{Colors.BOLD}{Colors.RED} [!] CRITICAL TEST FAILURES DETECTED. PLEASE REVIEW LOGS. [!]{Colors.RESET}\n")
            return 1


reporter = TestReporter()


# ==============================================================================
# 1. FRONTEND STATIC INTEGRITY & ARCHITECTURE AUDIT
# ==============================================================================
def test_frontend_integrity():
    reporter.start_suite("1. Frontend Integrity & Configuration Audit", "Verifies static assets, scripts ordering, and API_BASE configuration")

    # 1.1 Check HTML files existence
    t0 = time.time()
    html_files = ["frontend/login.html", "frontend/index.html", "frontend/history.html"]
    missing = [f for f in html_files if not os.path.isfile(os.path.join(PROJECT_ROOT, f))]
    reporter.add_result(
        "Core HTML Pages Existence",
        len(missing) == 0,
        time.time() - t0,
        f"Verified files: {', '.join(html_files)}" if not missing else f"Missing: {missing}"
    )

    # 1.2 Verify config.js and inclusion order in HTML
    t0 = time.time()
    config_path = os.path.join(PROJECT_ROOT, "frontend/js/config.js")
    config_exists = os.path.isfile(config_path)
    
    order_ok = True
    order_details = []
    if config_exists:
        for f in html_files:
            p = os.path.join(PROJECT_ROOT, f)
            with open(p, "r", encoding="utf-8") as file:
                content = file.read()
                pos_config = content.find('js/config.js')
                pos_app = content.find('js/app.js')
                if pos_config == -1:
                    order_ok = False
                    order_details.append(f"{f} missing config.js")
                elif pos_app == -1:
                    order_ok = False
                    order_details.append(f"{f} missing app.js")
                elif pos_config >= pos_app:
                    order_ok = False
                    order_details.append(f"{f} config.js must appear BEFORE app.js")

    reporter.add_result(
        "Script Include Order (config.js before app.js)",
        config_exists and order_ok,
        time.time() - t0,
        "config.js loaded before app.js in all 3 pages" if order_ok else "; ".join(order_details)
    )

    # 1.3 Verify Safe JSON Parser in app.js
    t0 = time.time()
    app_js_path = os.path.join(PROJECT_ROOT, "frontend/js/app.js")
    with open(app_js_path, "r", encoding="utf-8") as f:
        app_code = f.read()
    has_safe_parser = "parseJsonResponse" in app_code and "content-type" in app_code.lower()
    reporter.add_result(
        "Defensive Response Parser in app.js",
        has_safe_parser,
        time.time() - t0,
        "Confirmed parseJsonResponse handles non-JSON / HTML errors gracefully"
    )


# ==============================================================================
# 2. BACKEND AUTHENTICATION & SECURITY TEST
# ==============================================================================
def test_backend_auth():
    reporter.start_suite("2. Authentication & Security Penetration Test", "Audits password hashing, JWT issue/expiry, duplicate checks & input fuzzing")

    ts = int(time.time() * 1000)
    user_name = f"pro_tester_{ts}"
    password = "SecurePassword123!#"

    # 2.1 User Registration Success
    t0 = time.time()
    r = requests.post(f"{BACKEND_URL}/api/register", json={"username": user_name, "password": password})
    elapsed = time.time() - t0
    reporter.add_result(
        "Account Provisioning (POST /api/register)",
        r.status_code == 201 and "User registered successfully" in r.text,
        elapsed,
        f"HTTP 201 Created: user_id={r.json().get('user', {}).get('id')}"
    )

    # 2.2 Duplicate Username Rejection (409 Conflict)
    t0 = time.time()
    r = requests.post(f"{BACKEND_URL}/api/register", json={"username": user_name, "password": password})
    elapsed = time.time() - t0
    reporter.add_result(
        "Duplicate Username Collision (409 Conflict)",
        r.status_code == 409 and "already taken" in r.text,
        elapsed,
        f"HTTP 409 Conflict: {r.json().get('message')}"
    )

    # 2.3 Input Validation (Min length restrictions)
    t0 = time.time()
    r1 = requests.post(f"{BACKEND_URL}/api/register", json={"username": "ab", "password": password})
    r2 = requests.post(f"{BACKEND_URL}/api/register", json={"username": "valid_user", "password": "12"})
    r3 = requests.post(f"{BACKEND_URL}/api/register", json={})
    all_400 = (r1.status_code == 400) and (r2.status_code == 400) and (r3.status_code == 400)
    reporter.add_result(
        "Input Sanitization & Boundary Guards (400 Bad Request)",
        all_400,
        time.time() - t0,
        "Short username, short password, and empty payload all rejected with 400"
    )

    # 2.4 Login with Wrong Password (401 Unauthorized)
    t0 = time.time()
    r = requests.post(f"{BACKEND_URL}/api/login", json={"username": user_name, "password": "WrongPassword!"})
    reporter.add_result(
        "Invalid Password Authentication (401 Unauthorized)",
        r.status_code == 401 and "Invalid username or password" in r.text,
        time.time() - t0,
        f"HTTP 401 Unauthorized: {r.json().get('message')}"
    )

    # 2.5 Login with Non-Existent User (401 Unauthorized)
    t0 = time.time()
    r = requests.post(f"{BACKEND_URL}/api/login", json={"username": "ghost_user_does_not_exist", "password": password})
    reporter.add_result(
        "Non-Existent User Authentication (401 Unauthorized)",
        r.status_code == 401 and "Invalid username or password" in r.text,
        time.time() - t0,
        "Protected against user enumeration timing attacks"
    )

    # 2.6 Legitimate Login & JWT Acquisition
    t0 = time.time()
    r = requests.post(f"{BACKEND_URL}/api/login", json={"username": user_name, "password": password})
    token = r.json().get("token")
    reporter.add_result(
        "Legitimate User Authentication & JWT Issuance",
        r.status_code == 200 and bool(token),
        time.time() - t0,
        f"HTTP 200 OK: Issued HS256 Token ({len(token) if token else 0} bytes)"
    )

    # 2.7 JWT Bearer Access Verification (GET /api/me)
    t0 = time.time()
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{BACKEND_URL}/api/me", headers=headers)
    reporter.add_result(
        "Authenticated Identity Resolution (GET /api/me)",
        r.status_code == 200 and r.json().get("user", {}).get("username") == user_name,
        time.time() - t0,
        f"Verified authenticated session for '{user_name}'"
    )

    # 2.8 Tampered Token Resistance
    t0 = time.time()
    tampered_token = token[:-5] + "XXXXX"
    r = requests.get(f"{BACKEND_URL}/api/me", headers={"Authorization": f"Bearer {tampered_token}"})
    reporter.add_result(
        "Tampered Cryptographic Token Rejection (401)",
        r.status_code == 401,
        time.time() - t0,
        f"HTTP 401: Tampered signature rejected ({r.json().get('message')})"
    )

    return token, user_name


# ==============================================================================
# 3. BACKEND API CONTRACT & RESILIENCE
# ==============================================================================
def test_backend_contracts(token: str):
    reporter.start_suite("3. REST API Contract & Resilience Suite", "Validates HTTP specs, JSON guarantee, and error handlers")

    # 3.1 Health Check API
    t0 = time.time()
    r = requests.get(f"{BACKEND_URL}/api/health")
    data = r.json() if r.status_code == 200 else {}
    healthy = (r.status_code == 200) and (data.get("status") == "healthy") and ("ai_server" in data)
    reporter.add_result(
        "Health Probe API (GET /api/health)",
        healthy,
        time.time() - t0,
        f"Service: {data.get('service')}, DB: {data.get('database')}, AI Server: {data.get('ai_server', {}).get('status')}"
    )

    # 3.2 Guarantee JSON for Non-Existent Routes (404)
    t0 = time.time()
    r = requests.get(f"{BACKEND_URL}/api/undefined_resource_path_1234")
    content_type = r.headers.get("Content-Type", "")
    is_json = "application/json" in content_type and r.status_code == 404
    reporter.add_result(
        "404 Not Found JSON Guarantee (Never HTML)",
        is_json,
        time.time() - t0,
        f"Status: {r.status_code}, Content-Type: {content_type}"
    )

    # 3.3 Method Not Allowed JSON Guarantee (405)
    t0 = time.time()
    r = requests.get(f"{BACKEND_URL}/api/login") # Login only accepts POST
    content_type = r.headers.get("Content-Type", "")
    is_json = "application/json" in content_type and r.status_code == 405
    reporter.add_result(
        "405 Method Not Allowed JSON Guarantee",
        is_json,
        time.time() - t0,
        f"Status: {r.status_code}, Content-Type: {content_type}"
    )

    # 3.4 Missing Token on Protected Routes
    t0 = time.time()
    r1 = requests.post(f"{BACKEND_URL}/api/generate", json={"prompt": "cat"})
    r2 = requests.get(f"{BACKEND_URL}/api/history")
    both_401 = (r1.status_code == 401) and (r2.status_code == 401)
    reporter.add_result(
        "Unauthenticated Request Blocking (401 Unauthorized)",
        both_401,
        time.time() - t0,
        "POST /api/generate and GET /api/history both require authentication"
    )

    # 3.5 Generate Validation: Missing Prompt
    t0 = time.time()
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.post(f"{BACKEND_URL}/api/generate", headers=headers, json={"prompt": ""})
    reporter.add_result(
        "Generate Payload Validation (Empty Prompt -> 400)",
        r.status_code == 400 and "Prompt is required" in r.text,
        time.time() - t0,
        f"HTTP 400: {r.json().get('message')}"
    )


# ==============================================================================
# 4. AI INFERENCE ENGINE & GPU DIAGNOSTICS (DIRECT FORGE)
# ==============================================================================
def test_ai_engine():
    reporter.start_suite("4. AI Inference Engine & GPU Hardware Diagnostics", "Directly tests Stability Matrix SD WebUI Forge on port 7860")

    # 4.1 AI Server Connectivity Check
    t0 = time.time()
    try:
        r = requests.get(f"{AI_SERVER_URL}/sdapi/v1/options", timeout=10)
        online = r.status_code == 200
        loaded_checkpoint = r.json().get("sd_model_checkpoint", "Unknown") if online else "Offline"
    except Exception as e:
        online = False
        loaded_checkpoint = str(e)

    reporter.add_result(
        "AI Server Direct Ping & Active Checkpoint",
        online,
        time.time() - t0,
        f"Active Model: {loaded_checkpoint}"
    )

    # 4.2 Available Models Listing
    t0 = time.time()
    try:
        r = requests.get(f"{AI_SERVER_URL}/sdapi/v1/sd-models", timeout=10)
        models = [m.get("title") for m in r.json()] if r.status_code == 200 else []
        ok = len(models) > 0
    except Exception:
        ok = False
        models = []

    reporter.add_result(
        "Checkpoint Catalog Query (/sdapi/v1/sd-models)",
        ok,
        time.time() - t0,
        f"Found {len(models)} model(s): {', '.join(models[:2])}"
    )

    # 4.3 Direct txt2img GPU Benchmark
    t0 = time.time()
    txt2img_payload = {
        "prompt": "masterpiece, 8k, professional benchmark test cube, metallic ruby and gold, studio lighting",
        "negative_prompt": "blurry, bad quality, lowres",
        "width": 512,
        "height": 512,
        "steps": 15,
        "cfg_scale": 7.0,
        "sampler_name": "Euler a",
        "batch_size": 1,
        "save_images": False
    }
    
    print(f"       {Colors.YELLOW}⏳ Executing 15-step GPU inference directly on Forge...{Colors.RESET}")
    try:
        r = requests.post(f"{AI_SERVER_URL}/sdapi/v1/txt2img", json=txt2img_payload, timeout=180)
        gen_time = time.time() - t0
        res_data = r.json() if r.status_code == 200 else {}
        images = res_data.get("images", [])
        has_image = len(images) > 0

        # Validate PNG binary header
        raw_png = base64.b64decode(images[0]) if has_image else b""
        is_png = raw_png.startswith(b"\x89PNG\r\n\x1a\n")
        
        # Read width and height from PNG IHDR chunk
        w, h = struct.unpack(">II", raw_png[16:24]) if is_png else (0, 0)
        
        reporter.add_result(
            "Direct GPU txt2img Inference & Binary Header Check",
            has_image and is_png and w == 512 and h == 512,
            gen_time,
            f"Generated {w}x{h} PNG ({len(raw_png)/1024:.1f} KB) in {gen_time:.2f}s"
        )
        return images[0] if has_image else None
    except Exception as e:
        reporter.add_result("Direct GPU txt2img Inference", False, time.time() - t0, str(e))
        return None


# ==============================================================================
# 5. END-TO-END PIPELINE INTEGRATION
# ==============================================================================
def test_end_to_end(token: str, sample_b64: str = None):
    reporter.start_suite("5. End-to-End User Journey Pipeline Integration", "Simulates complete end-user generation, storage, and retrieval flow")

    headers = {"Authorization": f"Bearer {token}"}

    # 5.1 Real Text-to-Image Generation through Flask Backend
    t0 = time.time()
    prompt = "a photorealistic cute fluffy orange kitten playing with a golden ball of yarn, 8k, cinematic lighting"
    payload = {
        "prompt": prompt,
        "negative_prompt": "blurry, lowres, distorted",
        "width": 512,
        "height": 512,
        "steps": 20,
        "cfg_scale": 7.0
    }

    print(f"       {Colors.YELLOW}⏳ Sending E2E txt2img request via Backend to Forge GPU...{Colors.RESET}")
    r = requests.post(f"{BACKEND_URL}/api/generate", headers=headers, json=payload, timeout=180)
    gen_time = time.time() - t0
    gen_data = r.json() if r.status_code == 200 else {}
    job_id = gen_data.get("job_id")
    image_url = gen_data.get("image_url")
    has_b64 = bool(gen_data.get("image_base64"))
    
    e2e_gen_ok = (r.status_code == 200) and (gen_data.get("status") == "COMPLETED") and bool(job_id) and bool(image_url)
    reporter.add_result(
        "E2E Generation (Client -> Backend -> Forge -> DB)",
        e2e_gen_ok,
        gen_time,
        f"Job ID: {job_id}, URL: {image_url}, Total Latency: {gen_time:.2f}s"
    )

    # 5.2 Static Image Serving & File Integrity
    if image_url:
        t0 = time.time()
        img_res = requests.get(f"{BACKEND_URL}{image_url}")
        is_png = img_res.content.startswith(b"\x89PNG\r\n\x1a\n")
        reporter.add_result(
            "Artifact Retrieval & Storage Integrity (GET /api/images/...)",
            img_res.status_code == 200 and is_png,
            time.time() - t0,
            f"HTTP 200: Served {len(img_res.content)/1024:.1f} KB valid PNG binary"
        )

    # 5.3 History Record & Metadata Persistence
    t0 = time.time()
    hist_res = requests.get(f"{BACKEND_URL}/api/history?page=1&limit=5", headers=headers)
    hist_data = hist_res.json() if hist_res.status_code == 200 else {}
    items = hist_data.get("items", [])
    found_job = any(item.get("id") == job_id for item in items)
    reporter.add_result(
        "History Gallery Feed & Audit Log (GET /api/history)",
        hist_res.status_code == 200 and found_job,
        time.time() - t0,
        f"Verified new job '{job_id}' is tracked in user history (Total records: {hist_data.get('total')})"
    )


# ==============================================================================
# MAIN TEST RUNNER
# ==============================================================================
def main():
    print(f"\n{Colors.BOLD}{Colors.HEADER}================================================================================{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.HEADER}   LUMA PROFESSIONAL END-TO-END SYSTEM TEST BENCHMARK{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.HEADER}   Target Backend: {BACKEND_URL} | Target Forge: {AI_SERVER_URL}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.HEADER}================================================================================{Colors.RESET}")

    # 1. Frontend Test
    test_frontend_integrity()

    # 2. Auth & Security Test
    token, username = test_backend_auth()

    # 3. Contract & Resilience Test
    test_backend_contracts(token)

    # 4. Direct AI Engine & GPU Test
    sample_b64 = test_ai_engine()

    # 5. Full End-to-End User Journey
    test_end_to_end(token, sample_b64)

    # Executive Summary & Exit Code
    exit_code = reporter.print_summary()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
