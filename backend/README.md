# LUMA Backend Service

Flask REST API สำหรับระบบ LUMA — ให้บริการ Authentication, จัดการคิว Generation, บันทึกประวัติ และเชื่อมต่อไปยัง Stability Matrix AI Server บน Node 3 พร้อมระบบ Smart Fallback

---

## 1. การติดตั้งและเริ่มต้นใช้งาน

### 1.1 ติดตั้ง Dependencies
```bash
pip install -r requirements.txt
```

### 1.2 กำหนดค่า Environment Variables (.env)
คัดลอกไฟล์ตัวอย่างและแก้ไขตามสภาพแวดล้อม:
```bash
cp .env.example .env
```

ตัวแปรสำคัญที่เกี่ยวข้องกับ AI Server และ Fallback:
| ตัวแปร | ค่ามาตรฐาน | คำอธิบาย |
|---|---|---|
| `PORT` | `5000` | พอร์ตของ Flask Backend |
| `DATABASE_URI` | `sqlite:///luma.db` | ที่อยู่ฐานข้อมูล SQLite |
| `AI_SERVER_URL` | `http://192.168.1.30:7860` | URL ชี้ไปยัง Stability Matrix AI Server |
| `AI_TIMEOUT_SECONDS`| `15` | Timeout การเชื่อมต่อและอ่านผลลัพธ์ (ปรับลดจาก 120s เพื่อ fallback เร็วขึ้น) |
| `AI_ALLOW_FALLBACK_MOCK` | `true` | อนุญาตให้สลับไปใช้ Procedural Mock Image เมื่อ AI Server ไม่พร้อม |
| `AI_MOCK_MODE` | `false` | บังคับใช้ Mock Mode ตลอดเวลาโดยไม่ต้องต่อ GPU |

### 1.3 รัน Backend Server
```bash
python app.py
```

---

## 2. การทดสอบ Endpoints อัตโนมัติ (Automated Test Suite)

ระบบมีสคริปต์ทดสอบครบทุก Endpoint ทั้งกรณีปกติและกรณีเกิดข้อผิดพลาด (Edge/Error Cases) อยู่ในไฟล์ `test_endpoints.py`

### วิธีรันการทดสอบ:
```bash
python test_endpoints.py
```

---

## 3. สรุปผลการทดสอบ Endpoints (Manual & Automated Test Checklist)

สรุปผลการทดสอบครอบคลุมทุก Route และ Authentication Guard:

| # | Endpoint | Method | กรณีทดสอบ (Scenario) | Expected Code | Status | รายละเอียดข้อความตอบกลับ |
|---|---|:---:|---|:---:|:---:|---|
| 1 | `/api/register` | POST | สมัครสมาชิกด้วย Username ใหม่ | **201 Created** | ✅ PASS | `User registered successfully` |
| 2 | `/api/register` | POST | สมัครด้วย Username ที่มีอยู่แล้ว (Duplicate) | **409 Conflict** | ✅ PASS | `Username '<username>' is already taken` |
| 3 | `/api/register` | POST | ข้อมูลไม่ครบ / Username สั้นกว่า 3 ตัวอักษร | **400 Bad Request** | ✅ PASS | `Username must be at least 3 characters` |
| 4 | `/api/login` | POST | ล็อกอินด้วย Password ที่ถูกต้อง | **200 OK** | ✅ PASS | `Login successful` + คืน JWT Token |
| 5 | `/api/login` | POST | ล็อกอินด้วย Password ที่ผิด | **401 Unauthorized** | ✅ PASS | `Invalid username or password` |
| 6 | `/api/login` | POST | ล็อกอินด้วย Username ที่ไม่มีในระบบ | **401 Unauthorized** | ✅ PASS | `Invalid username or password` |
| 7 | `/api/me` | GET | เรียกโดยไม่มี Token ใน Header | **401 Unauthorized** | ✅ PASS | `Missing authentication token` |
| 8 | `/api/me` | GET | Token รูปแบบผิด หรือเซ็นไม่ถูกต้อง | **401 Unauthorized** | ✅ PASS | `Invalid token: ...` |
| 9 | `/api/me` | GET | Token หมดอายุ (Expired Token) | **401 Unauthorized** | ✅ PASS | `Token has expired, please log in again` |
| 10 | `/api/me` | GET | แนบ Bearer Token ที่ถูกต้อง | **200 OK** | ✅ PASS | คืนข้อมูล user profile |
| 11 | `/api/generate` | POST | เรียกโดยไม่มี Token | **401 Unauthorized** | ✅ PASS | `Missing authentication token` |
| 12 | `/api/generate` | POST | ข้อมูล prompt ว่างเปล่า | **400 Bad Request** | ✅ PASS | `Prompt is required` |
| 13 | `/api/generate` | POST | AI Server ออฟไลน์ (Smart Fallback Mode) | **200 OK** | ✅ PASS | สลับใช้ Procedural Mock Image อัตโนมัติใน ~6s พร้อมบันทึกลงฐานข้อมูล |
| 14 | `/api/history` | GET | ดึงประวัติแบบแบ่งหน้า (Pagination) | **200 OK** | ✅ PASS | คืนรายการ Generation ที่เสร็จสมบูรณ์ |
| 15 | `/api/images/<file>`| GET | เรียกดูไฟล์รูปภาพที่เซฟไว้บนเซิร์ฟเวอร์ | **200 OK** | ✅ PASS | ส่งข้อมูล Image binary กลับถูกต้อง |

---

## 4. กลไก Smart Fallback & Timeout Optimization

- **Connect Timeout:** 5 วินาที สำหรับตรวจจับการเชื่อมต่อไปยัง IP ของ AI Server
- **Read/Execution Timeout:** ปรับค่าเริ่มต้นเป็น 15 วินาที (จากเดิม 120 วินาที)
- **Fallback Logging:** เมื่อไม่สามารถติดต่อ AI Server ได้ ระบบจะบันทึก Log ระดับ `WARNING` และ `INFO` ชัดเจน:
  - `[FALLBACK TRIGGERED] AI Server at ... unreachable or timed out (15s)`
  - `[FALLBACK ACTIVE] Generating simulated procedural image for prompt: ...`
- หน้าเว็บจะได้รับการตอบกลับภายใน 5–7 วินาทีโดยไม่ค้าง และผู้ใช้จะได้รับภาพจำลองที่มีคุณภาพเพื่อทดสอบระบบต่อไปได้อย่างราบรื่น
