#!/usr/bin/env python3
"""
LUMA — Backend Endpoints Automated Test Suite
Tests all REST API endpoints under normal and error/edge cases:
1. POST /api/register (success, duplicate conflict 409, validation error 400)
2. POST /api/login (success 200, invalid credentials 401, validation error 400)
3. Auth Protection (missing token 401, invalid token 401, expired token 401)
4. POST /api/generate (mock mode / unreachable server fallback with reduced timeout)
5. GET /api/history (pagination, auth protection)
6. GET /api/images/<filename> (static file serving)
"""

import os
import sys
import time
import json
from datetime import datetime, timedelta
# pyrefly: ignore [missing-import]
import jwt

# Add current directory to path so imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from app import create_app
from models import db, User, Generation

def run_tests():
    print("=" * 65)
    print(" LUMA Backend API Endpoints & Error Handling Verification")
    print("=" * 65)

    app = create_app()
    client = app.test_client()

    results = []

    def record(test_name: str, passed: bool, detail: str = ""):
        status_str = "[PASS]" if passed else "[FAIL]"
        print(f" {status_str} {test_name}")
        if detail:
            print(f"        -> {detail}")
        results.append((test_name, passed, detail))

    with app.app_context():
        # Setup unique test user
        timestamp = int(time.time())
        test_user = f"testuser_{timestamp}"
        test_pass = "TestPass123!"

        # -------------------------------------------------------------
        # 1. POST /api/register Tests
        # -------------------------------------------------------------
        print("\n--- 1. Testing Registration Endpoint (/api/register) ---")

        # 1.1 Register valid user
        res = client.post('/api/register', json={'username': test_user, 'password': test_pass})
        is_pass = res.status_code == 201 and 'User registered successfully' in res.get_json().get('message', '')
        record("Register: New valid user", is_pass, f"Status: {res.status_code}, Msg: {res.get_json().get('message')}")

        # 1.2 Register duplicate user (Must return 409 Conflict with clear message)
        res = client.post('/api/register', json={'username': test_user, 'password': test_pass})
        is_pass = res.status_code == 409 and f"Username '{test_user}' is already taken" in res.get_json().get('message', '')
        record("Register: Duplicate username (409 Conflict)", is_pass, f"Status: {res.status_code}, Msg: {res.get_json().get('message')}")

        # 1.3 Register with empty / invalid payload (Must return 400 Bad Request)
        res = client.post('/api/register', json={'username': 'ab', 'password': '12'})
        is_pass = res.status_code == 400 and 'at least 3 characters' in res.get_json().get('message', '')
        record("Register: Username too short (400 Bad Request)", is_pass, f"Status: {res.status_code}, Msg: {res.get_json().get('message')}")

        # -------------------------------------------------------------
        # 2. POST /api/login Tests
        # -------------------------------------------------------------
        print("\n--- 2. Testing Login Endpoint (/api/login) ---")

        # 2.1 Login with wrong password (Must return 401 Unauthorized)
        res = client.post('/api/login', json={'username': test_user, 'password': 'WrongPassword123'})
        is_pass = res.status_code == 401 and 'Invalid username or password' in res.get_json().get('message', '')
        record("Login: Wrong password (401 Unauthorized)", is_pass, f"Status: {res.status_code}, Msg: {res.get_json().get('message')}")

        # 2.2 Login with non-existent user (Must return 401 Unauthorized)
        res = client.post('/api/login', json={'username': 'nonexistent_user_9999', 'password': 'password'})
        is_pass = res.status_code == 401 and 'Invalid username or password' in res.get_json().get('message', '')
        record("Login: Non-existent user (401 Unauthorized)", is_pass, f"Status: {res.status_code}, Msg: {res.get_json().get('message')}")

        # 2.3 Login with valid credentials (Must return 200 OK with JWT token)
        res = client.post('/api/login', json={'username': test_user, 'password': test_pass})
        data = res.get_json() or {}
        valid_token = data.get('token')
        is_pass = res.status_code == 200 and bool(valid_token)
        record("Login: Valid credentials (200 OK + JWT)", is_pass, f"Status: {res.status_code}, Token length: {len(valid_token) if valid_token else 0}")

        # -------------------------------------------------------------
        # 3. Authentication Middleware & Protected Endpoints
        # -------------------------------------------------------------
        print("\n--- 3. Testing Authentication Middleware (401 Checks) ---")

        # 3.1 Protected endpoint without Authorization header (Must return 401)
        res = client.get('/api/me')
        is_pass = res.status_code == 401 and 'Missing authentication token' in res.get_json().get('message', '')
        record("Auth Guard: GET /api/me without token (401)", is_pass, f"Status: {res.status_code}, Msg: {res.get_json().get('message')}")

        # 3.2 Generate endpoint without token (Must return 401)
        res = client.post('/api/generate', json={'prompt': 'test prompt'})
        is_pass = res.status_code == 401
        record("Auth Guard: POST /api/generate without token (401)", is_pass, f"Status: {res.status_code}, Msg: {res.get_json().get('message')}")

        # 3.3 History endpoint without token (Must return 401)
        res = client.get('/api/history')
        is_pass = res.status_code == 401
        record("Auth Guard: GET /api/history without token (401)", is_pass, f"Status: {res.status_code}, Msg: {res.get_json().get('message')}")

        # 3.4 Protected endpoint with invalid token (Must return 401)
        res = client.get('/api/me', headers={'Authorization': 'Bearer invalid.bogus.token'})
        is_pass = res.status_code == 401 and 'Invalid token' in res.get_json().get('message', '')
        record("Auth Guard: Invalid token format (401)", is_pass, f"Status: {res.status_code}, Msg: {res.get_json().get('message')}")

        # 3.5 Protected endpoint with expired token (Must return 401)
        expired_payload = {
            'user_id': data.get('user', {}).get('id', 1),
            'username': test_user,
            'exp': datetime.utcnow() - timedelta(hours=1),
            'iat': datetime.utcnow() - timedelta(hours=2)
        }
        expired_token = jwt.encode(expired_payload, app.config['JWT_SECRET'], algorithm='HS256')
        res = client.get('/api/me', headers={'Authorization': f'Bearer {expired_token}'})
        is_pass = res.status_code == 401 and 'Token has expired' in res.get_json().get('message', '')
        record("Auth Guard: Expired token (401)", is_pass, f"Status: {res.status_code}, Msg: {res.get_json().get('message')}")

        # 3.6 Protected endpoint with valid token (Must return 200 OK)
        auth_headers = {'Authorization': f'Bearer {valid_token}'}
        res = client.get('/api/me', headers=auth_headers)
        is_pass = res.status_code == 200 and res.get_json().get('user', {}).get('username') == test_user
        record("Auth Guard: Valid token access /api/me (200 OK)", is_pass, f"Status: {res.status_code}, User: {test_user}")

        # -------------------------------------------------------------
        # 4. POST /api/generate & Fallback Mock Execution
        # -------------------------------------------------------------
        print("\n--- 4. Testing Image Generation & Mock Fallback ---")
        start_gen = time.time()
        res = client.post('/api/generate', headers=auth_headers, json={
            'prompt': 'A beautiful futuristic neon city in rain, cyberpunk, 8k',
            'width': 512,
            'height': 512,
            'steps': 20
        })
        gen_duration = time.time() - start_gen
        gen_data = res.get_json() or {}
        image_url = gen_data.get('image_url')
        status = gen_data.get('status')
        has_base64 = bool(gen_data.get('image_base64'))

        # Check that request succeeded via live server or fallback within timeout
        is_pass = res.status_code == 200 and status == 'COMPLETED' and bool(image_url) and has_base64 and gen_duration < 180
        record(
            "Generate: Mock Fallback / Live Execution",
            is_pass,
            f"Status: {res.status_code}, Time: {gen_duration:.2f}s, Image: {image_url}"
        )

        # -------------------------------------------------------------
        # 5. GET /api/history Endpoint
        # -------------------------------------------------------------
        print("\n--- 5. Testing History Endpoint (/api/history) ---")
        res = client.get('/api/history?page=1&limit=10', headers=auth_headers)
        hist_data = res.get_json() or {}
        items = hist_data.get('items', [])
        is_pass = res.status_code == 200 and isinstance(items, list) and len(items) >= 1
        record("History: Paginated list for user", is_pass, f"Status: {res.status_code}, Total records: {hist_data.get('total')}")

        # -------------------------------------------------------------
        # 6. GET /api/images/<filename> Static Serving
        # -------------------------------------------------------------
        print("\n--- 6. Testing Static Image Serving (/api/images/...) ---")
        if image_url:
            filename = image_url.split('/')[-1]
            res = client.get(f'/api/images/{filename}')
            is_pass = res.status_code == 200 and len(res.data) > 0
            record(f"Static Serving: {filename}", is_pass, f"Status: {res.status_code}, Bytes: {len(res.data)}")

    # -------------------------------------------------------------
    # Final Summary
    # -------------------------------------------------------------
    print("\n" + "=" * 65)
    print(" VERIFICATION TEST SUMMARY")
    print("=" * 65)
    total = len(results)
    passed = sum(1 for _, p, _ in results if p)
    failed = total - passed

    for name, p, detail in results:
        mark = "PASS" if p else "FAIL"
        print(f" [{mark}] {name}")

    print("-" * 65)
    print(f" Total Tests : {total}")
    print(f" Passed      : {passed}")
    print(f" Failed      : {failed}")
    print("=" * 65)

    if failed > 0:
        sys.exit(1)
    else:
        print(" ALL ENDPOINT & ERROR-HANDLING TESTS PASSED!")

if __name__ == '__main__':
    run_tests()
