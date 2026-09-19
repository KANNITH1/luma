# ✨ LUMA — Distributed AI Image Generation Studio

**LUMA** เป็นระบบสร้างภาพด้วยปัญญาประดิษฐ์ (AI Image Generation) สถาปัตยกรรมแบบกระจายศูนย์ (Distributed System) ที่ออกแบบให้ทำงานแยกเครื่องประมวลผล 3 เครื่องในวงเครือข่าย LAN เพื่อประสิทธิภาพสูงสุดในการใช้ทรัพยากร GPU และการรองรับผู้ใช้งานพร้อมกัน

---

## 🏛️ โครงสร้างสถาปัตยกรรมระบบ (System Architecture)

```
                       [ ผู้ใช้งาน (Browser) ]
                                  │
                                  ▼
                   ┌──────────────────────────────┐
                   │  Node 1: Frontend + Nginx    │ (IP: 192.168.1.10)
                   │  - Nginx Reverse Proxy (:80) │
                   │  - Static Web UI (HTML/CSS)  │
                   └──────────────┬───────────────┘
                                  │ proxy_pass /api/
                                  ▼
                   ┌──────────────────────────────┐
                   │  Node 2: Backend + Database  │ (IP: 192.168.1.20)
                   │  - Flask REST API (:5000)    │
                   │  - SQLite / SQLAlchemy       │
                   │  - JWT Auth & Job Manager    │
                   └──────────────┬───────────────┘
                                  │ HTTP POST /sdapi/v1/...
                                  ▼
                   ┌──────────────────────────────┐
                   │  Node 3: AI Inference Server │ (IP: 192.168.1.30)
                   │  - Stability Matrix (:7860)  │
                   │  - SD WebUI Forge / ComfyUI  │
                   │  - NVIDIA CUDA GPU           │
                   └──────────────────────────────┘
```

---

## 📁 โครงสร้างไฟล์ใน Monorepo

```
/luma
├── .gitignore                   # ตัวกรองไฟล์ครอบคลุม Python, Node, Database, Secrets, Outputs
├── README.md                    # เอกสารคู่มือระบบและการติดตั้งทั้ง 3 เครื่อง
├── frontend/                    # ส่วนที่ 1: หน้าบ้าน Web Application (Node 1)
│   ├── index.html               # หน้าหลักสำหรับสร้างภาพ (Text-to-Image & Image-to-Image)
│   ├── login.html               # หน้าเข้าสู่ระบบและสมัครสมาชิก (JWT Auth)
│   ├── history.html             # หน้าประวัติการ generate ภาพ พร้อม Pagination & Modal
│   ├── css/
│   │   └── style.css            # ธีม Dark/Glassmorphism ดีไซน์ทันสมัย
│   └── js/
│       └── app.js               # Logic ฝั่ง Client, JWT Storage, API Calls
├── backend/                     # ส่วนที่ 2: REST API & ฐานข้อมูล (Node 2)
│   ├── app.py                   # Application Factory, CORS, Logging, Error Handlers
│   ├── models.py                # Database Models (User, Generation) ผ่าน SQLAlchemy
│   ├── requirements.txt         # รายการ Python dependencies
│   ├── .env.example             # เทมเพลต Environment Variables
│   ├── routes/
│   │   ├── auth.py              # Endpoints: /api/register, /api/login, /api/me
│   │   └── generate.py          # Endpoints: /api/generate, /api/history, /api/status/<id>
│   ├── services/
│   │   └── ai_client.py         # Service เชื่อมต่อ Stability Matrix Forge API (+ Mock Mode)
│   ├── outputs/                 # ที่จัดเก็บไฟล์ภาพที่ generate แล้ว
│   └── logs/                    # ที่จัดเก็บ Rotating File Logs
├── ai-server/                   # ส่วนที่ 3: สคริปต์และคู่มือ AI Server (Node 3)
│   ├── API_SPEC.md              # ข้อกำหนด REST API และคู่มือตั้งค่า Stability Matrix
│   └── test_api.py              # CLI Tool ทดสอบ Ping, txt2img, และ img2img
└── nginx/                       # การตั้งค่า Reverse Proxy (Node 1)
    └── nginx.conf               # กำหนดเส้นทาง / -> Frontend และ /api/ -> Backend
```

---

## ⚙️ Environment Variables ที่สำคัญ

กำหนดค่าเหล่านี้ในไฟล์ `backend/.env`:

| ตัวแปร | ค่าตัวอย่าง | คำอธิบาย |
|---|---|---|
| `PORT` | `5000` | พอร์ตที่ Flask Backend เปิดให้บริการ |
| `HOST` | `0.0.0.0` | IP Address ที่เซิร์ฟเวอร์ผูกไว้ (0.0.0.0 เพื่อรับ LAN) |
| `JWT_SECRET` | `luma-jwt-super-secret-key-2026` | Secret Key สำหรับการเข้ารหัส JWT Token |
| `DATABASE_URI` | `sqlite:///luma.db` | ที่อยู่ฐานข้อมูล SQLite |
| `AI_SERVER_URL` | `http://192.168.1.30:7860` | URL ของ Stability Matrix AI Server |
| `AI_TIMEOUT_SECONDS`| `120` | เวลา Timeout สูงสุดในการรอ AI Generate ภาพ (วินาที) |
| `AI_MOCK_MODE` | `false` | ตั้งเป็น `true` เมื่อต้องการทดสอบระบบโดยไม่ต้องเปิด GPU Server |
| `AI_ALLOW_FALLBACK_MOCK` | `true` | อนุญาตให้สลับเป็น Mock ชั่วคราวหาก AI Server ดับ |

---

## 🚀 คู่มือการ Deploy ระบบแยก 3 เครื่อง (Multi-Node Deployment)

### 🖥️ เครื่องที่ 3: AI Server (Stability Matrix) — `192.168.1.30`

1. **ติดตั้ง Stability Matrix**:
   - ดาวน์โหลดและแตกไฟล์จาก [Stability Matrix Releases](https://github.com/LykosAI/StabilityMatrix/releases)
   - เปิดโปรแกรมแล้วติดตั้งแพ็กเกจ **Stable Diffusion WebUI Forge**
2. **เปิดโหมด API และอนุญาต LAN Access**:
   - ในการตั้งค่าแพ็กเกจ (Settings) ให้เพิ่ม **Extra Launch Arguments**:
     ```bash
     --api --listen --port 7860 --cors-allow-origins=* --enable-insecure-extension-access
     ```
3. **เปิดพอร์ตใน Firewall (Windows Defender)**:
   - รันใน PowerShell (Admin):
     ```powershell
     New-NetFirewallRule -DisplayName "LUMA AI Server" -Direction Inbound -LocalPort 7860 -Protocol TCP -Action Allow
     ```
4. **เริ่มการทำงาน**:
   - กดปุ่ม **Launch** ใน Stability Matrix แล้วตรวจสอบว่าเข้า `http://192.168.1.30:7860/sdapi/v1/options` ได้

---

### 🖥️ เครื่องที่ 2: Backend + Database — `192.168.1.20`

1. **เตรียม Environment**:
   ```bash
   cd backend
   python -m venv venv
   # สำหรับ Windows:
   venv\Scripts\activate
   # สำหรับ Linux:
   source venv/bin/activate
   ```
2. **ติดตั้ง Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **กำหนดค่า `.env`**:
   ```bash
   cp .env.example .env
   ```
   แก้ไขไฟล์ `.env` ให้ชี้ไปยัง AI Server:
   ```ini
   AI_SERVER_URL=http://192.168.1.30:7860
   PORT=5000
   ```
4. **เริ่มการทำงานของเซิร์ฟเวอร์**:
   ```bash
   python app.py
   ```
   *(หรือใช้ Gunicorn สำหรับ Production: `gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()" --timeout 180`)*

---

### 🖥️ เครื่องที่ 1: Frontend + Nginx — `192.168.1.10`

1. **คัดลอกไฟล์ Frontend**:
   - นำไฟล์ในโฟลเดอร์ `frontend/` ไปวางที่ `/var/www/luma/frontend/` (หรือไดเรกทอรีที่กำหนด)
2. **ติดตั้ง Nginx Configuration**:
   - คัดลอก `nginx/nginx.conf` ไปยัง `/etc/nginx/nginx.conf` (หรือ `/etc/nginx/conf.d/luma.conf`)
   - ตรวจสอบว่าในไฟล์ Nginx ชี้ `upstream luma_backend` ไปที่ `192.168.1.20:5000`
3. **ทดสอบและเปิดใช้งาน Nginx**:
   ```bash
   sudo nginx -t
   sudo systemctl reload nginx
   ```
4. **เข้าใช้งาน**:
   - เปิด Browser แล้วไปที่ `http://192.168.1.10`

---

## 💻 การทดสอบและรันบนเครื่องเดียวสำหรับขั้นตอนพัฒนา (Local Dev Mode)

คุณสามารถทดสอบการทำงานของทั้งระบบบนเครื่องเดียว (Localhost) ได้อย่างสมบูรณ์:

1. **รัน Backend ใน Mock Mode** (ไม่ต้องเปิด AI Server):
   ```bash
   cd backend
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   # กำหนดให้รัน mock mode
   set AI_MOCK_MODE=true
   python app.py
   ```
2. **เปิดหน้า Frontend**:
   - เปิดไฟล์ `frontend/login.html` หรือ `frontend/index.html` บน Browser (หรือใช้ Live Server / `python -m http.server 8080 -d frontend`)
   - ทดลองสมัครสมาชิก เข้าสู่ระบบ และกด Generate ภาพ จะได้รับภาพทดสอบและประวัติจะถูกบันทึกลงฐานข้อมูล SQLite ทันที!
3. **ทดสอบสคริปต์ AI Server**:
   ```bash
   python ai-server/test_api.py --help
   ```

---

## 📝 รายการ REST API Endpoints

### การยืนยันตัวตน (Authentication)
- `POST /api/register` — สมัครสมาชิกใหม่ (`username`, `password`)
- `POST /api/login` — เข้าสู่ระบบ รับ JWT Token (`username`, `password`)
- `GET /api/me` — ข้อมูลผู้ใช้งานปัจจุบัน (ต้องแนบ JWT Bearer Token)

### การสร้างภาพและประวัติ (Generation & Gallery)
- `POST /api/generate` — สร้างภาพใหม่ รองรับทั้ง Text-to-Image และ Image-to-Image
- `GET /api/history?page=1&limit=12` — ดึงประวัติภาพที่เคยสร้างของผู้ใช้ (Pagination)
- `GET /api/status/<job_id>` — ตรวจสอบสถานะงาน (PENDING, PROCESSING, COMPLETED, FAILED)
- `GET /api/images/<filename>` — ดึงไฟล์ภาพผลลัพธ์
- `GET /api/health` — ตรวจสอบสถานะการเชื่อมต่อของ Backend และ AI Server

---

## 🔒 การรักษาความปลอดภัย (Security)
- รหัสผ่านของผู้ใช้งานถูกแฮชด้วยอัลกอริทึม Scrypt (ผ่าน `werkzeug.security`) ปลอดภัยจากการรั่วไหล
- การเข้าถึง API ที่สำคัญได้รับการคุ้มครองด้วย JWT Token ตรวจสอบสิทธิ์ทุกคำขอ
- Nginx มีการจำกัดขนาด Request Payload (`client_max_body_size 25M`) เพื่อป้องกัน DoS
- มี `.gitignore` ป้องกันไม่ให้ Git ติดตามไฟล์รหัสผ่าน, Database จริง, และ Model Weights
