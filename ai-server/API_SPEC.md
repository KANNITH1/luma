# Stability Matrix AI Server — API Specification & Setup Guide

เอกสารคู่มือทางเทคนิคสำหรับติดตั้ง กำหนดค่า และเชื่อมต่อ AI Server ด้วย **Stability Matrix** บน Node 3 (`192.168.1.30`) สำหรับระบบ LUMA

---

## สารบัญ
1. [ภาพรวมสถาปัตยกรรม AI Server](#1-ภาพรวมสถาปัตยกรรม-ai-server)
2. [ขั้นตอนการติดตั้ง Stability Matrix](#2-ขั้นตอนการติดตั้ง-stability-matrix)
3. [การเปิดโหมด API และการอนุญาต LAN Access](#3-การเปิดโหมด-api-และการอนุญาต-lan-access)
4. [ข้อกำหนด API (API Specification)](#4-ข้อกำหนด-api-api-specification)
5. [การจัดการคิวงานและ Concurrent Requests (Queue Management)](#5-การจัดการคิวงานและ-concurrent-requests-queue-management)
6. [การทดสอบการเชื่อมต่อ](#6-การทดสอบการเชื่อมต่อ)

---

## 1. ภาพรวมสถาปัตยกรรม AI Server

ในสถาปัตยกรรม Distributed ของ LUMA:
- **Node 3 (AI Server)**: มี IP Address `192.168.1.30` มีการติดตั้ง GPU (NVIDIA CUDA) ทำหน้าที่ประมวลผลโมเดล Stable Diffusion / Flux
- **แพ็กเกจหลัก**: **Stable Diffusion WebUI Forge** (หรือ Automatic1111) หรือ **ComfyUI** ภายใต้ Stability Matrix
- **Backend (Node 2: 192.168.1.20)** จะส่ง HTTP POST request ข้ามเครือข่าย LAN มายังพอร์ต `7860` ของ AI Server เพื่อรับผลลัพธ์ภาพ Base64 กลับไปจัดเก็บ

---

## 2. ขั้นตอนการติดตั้ง Stability Matrix

Stability Matrix เป็น Package Manager แบบ All-in-One สำหรับ Stable Diffusion ที่แยก Python virtual environment ในตัว:

1. **ดาวน์โหลดตัวติดตั้ง**:
   - ไปที่ [Stability Matrix Releases](https://github.com/LykosAI/StabilityMatrix/releases)
   - ดาวน์โหลด `StabilityMatrix-win-x64.zip`
   - แตกไฟล์ไว้ในไดรฟ์ที่มีพื้นที่ว่างสำหรับ Checkpoints/LoRAs (เช่น `D:\StabilityMatrix`)

2. **ติดตั้ง Package (แนะนำ: Stable Diffusion WebUI Forge)**:
   - เปิดโปรแกรม Stability Matrix
   - ไปที่แท็บ **Packages** ด้านซ้าย
   - คลิก **Add Package**
   - เลือก **Stable Diffusion WebUI Forge** (ประสิทธิภาพ VRAM ดีเยี่ยม และมี REST API ที่เสถียร)
   - กดปุ่ม **Install**

3. **ดาวน์โหลดโมเดล Checkpoint**:
   - ไปที่แท็บ **Model Browser**
   - ดาวน์โหลดโมเดลที่ต้องการ เช่น `SDXL 1.0`, `Juggernaut XL`, หรือ `DreamShaper`

---

## 3. การเปิดโหมด API และการอนุญาต LAN Access

ตามค่าเริ่มต้น WebUI จะรันเฉพาะบน `localhost` (127.0.0.1) และปิดโหมด API เอาไว้ ดังนั้นจึงต้องเปิดการตั้งค่าเพื่อให้ Backend (192.168.1.20) เรียกเข้ามาได้:

### 3.1 ตั้งค่า Launch Arguments ใน Stability Matrix
1. ใน Stability Matrix คลิกไอคอน **ฟันเฟือง (Settings)** ข้างแพ็กเกจ WebUI Forge
2. ในช่อง **Extra Launch Arguments** ให้ใส่ข้อความต่อไปนี้:
   ```bash
   --api --listen --port 7860 --cors-allow-origins=* --enable-insecure-extension-access
   ```
   **ความหมายของแต่ละ Flag:**
   - `--api`: เปิดการทำงานของ REST API endpoint (`/sdapi/v1/...`)
   - `--listen`: สั่งให้เซิร์ฟเวอร์ผูกกับ `0.0.0.0` แทน `127.0.0.1` เพื่อให้เครื่องใน LAN เรียกเข้าได้
   - `--port 7860`: กำหนดพอร์ตบริการเป็น 7860
   - `--cors-allow-origins=*`: อนุญาต CORS headers ข้ามโฮสต์

3. บันทึกและกดปุ่ม **Launch** เพื่อเปิดเซิร์ฟเวอร์

### 3.2 เปิด Port ใน Windows Defender Firewall (Node 3)
เพื่อให้เครื่อง Backend (`192.168.1.20`) ส่ง request เข้ามาได้ ให้เปิดพอร์ต 7860 ใน Windows Firewall:

1. เปิด **PowerShell** ในสิทธิ์ Administrator บนเครื่อง AI Server (192.168.1.30)
2. รันคำสั่งเพิ่ม Inbound Rule:
   ```powershell
   New-NetFirewallRule -DisplayName "LUMA AI Server (Port 7860)" `
     -Direction Inbound `
     -LocalPort 7860 `
     -Protocol TCP `
     -Action Allow
   ```

---

## 4. ข้อกำหนด API (API Specification)

Base URL ของ AI Server: `http://192.168.1.30:7860`

### 4.1 Health Check & Options
- **Endpoint:** `GET /sdapi/v1/options`
- **คำอธิบาย:** ตรวจสอบว่าเซิร์ฟเวอร์พร้อมทำงาน และโมเดลที่โหลดอยู่คืออะไร
- **Response:**
  ```json
  {
    "sd_model_checkpoint": "v1-5-pruned-emaonly.safetensors",
    "samples_save": true
  }
  ```

---

### 4.2 Text-to-Image (สร้างภาพจากข้อความ)
- **Endpoint:** `POST /sdapi/v1/txt2img`
- **Content-Type:** `application/json`

#### Request Payload Parameters:
| พารามิเตอร์ | ชนิด | ตัวอย่างค่า | คำอธิบาย |
|---|---|---|---|
| `prompt` | string | `"cyberpunk cat, neon city, 8k"` | ข้อความอธิบายภาพที่ต้องการ (รองรับ LoRA syntax: `<lora:name:0.8>`) |
| `negative_prompt` | string | `"blurry, bad quality"` | สิ่งที่ไม่ต้องการให้ปรากฏในภาพ |
| `steps` | integer | `20` | จำนวนรอบ sampling (15-30) |
| `cfg_scale` | float | `7.0` | ระดับการยึดตาม prompt (1.0 - 15.0) |
| `width` | integer | `512` | ความกว้างของภาพ (พิกเซล) |
| `height` | integer | `512` | ความสูงของภาพ (พิกเซล) |
| `seed` | integer | `-1` | ค่า seed (-1 หมายถึงสุ่ม) |
| `sampler_name` | string | `"Euler a"` | อัลกอริทึม Sampling (เช่น `"Euler a"`, `"DPM++ 2M Karras"`) |
| `batch_size` | integer | `1` | จำนวนภาพที่ generate ต่อรอบ |
| `save_images` | boolean | `false` | ตั้งเป็น `false` เพื่อไม่ให้เซฟซ้ำซ้อนใน AI Server |

#### ตัวอย่าง Request:
```json
{
  "prompt": "masterpiece, best quality, a stunning futuristic cityscape with flying cars, octane render, 8k",
  "negative_prompt": "blurry, lowres, bad anatomy, deformed, watermark",
  "steps": 25,
  "cfg_scale": 7.5,
  "width": 768,
  "height": 512,
  "seed": -1,
  "sampler_name": "Euler a",
  "batch_size": 1,
  "save_images": false
}
```

#### ตัวอย่าง Response:
```json
{
  "images": [
    "iVBORw0KGgoAAAANSUhEUgAAA... (base64 string)"
  ],
  "parameters": {
    "prompt": "masterpiece, best quality...",
    "steps": 25,
    "cfg_scale": 7.5
  },
  "info": "{\"seed\": 392810928, \"sampler_name\": \"Euler a\"}"
}
```

---

### 4.3 Image-to-Image (แปลงภาพจากภาพต้นฉบับ)
- **Endpoint:** `POST /sdapi/v1/img2img`
- **Content-Type:** `application/json`

#### Request Payload Parameters:
| พารามิเตอร์ | ชนิด | ตัวอย่างค่า | คำอธิบาย |
|---|---|---|---|
| `init_images` | list[string] | `["iVBORw0KGgo..."]` | รายการภาพต้นฉบับในรูปแบบ Base64 string |
| `denoising_strength`| float | `0.75` | ระดับการเปลี่ยนแปลงภาพเดิม (0.1 = คล้ายเดิมมาก, 1.0 = เปลี่ยนใหม่หมด) |
| `prompt` | string | `"anime style, watercolor"` | คำสั่งสำหรับตกแต่งหรือเปลี่ยนสไตล์ |
| `negative_prompt` | string | `"photorealistic, lowres"` | สิ่งที่ไม่ต้องการ |
| `steps` | integer | `20` | จำนวน sampling steps |
| `cfg_scale` | float | `7.0` | ระดับการยึดตาม prompt |
| `width` | integer | `512` | ความกว้างของภาพผลลัพธ์ |
| `height` | integer | `512` | ความสูงของภาพผลลัพธ์ |
| `seed` | integer | `-1` | Seed (-1 สำหรับสุ่ม) |

#### ตัวอย่าง Response:
```json
{
  "images": [
    "iVBORw0KGgoAAAANSUhEUgAAA... (base64 string)"
  ],
  "parameters": {
    "denoising_strength": 0.75
  },
  "info": "{\"seed\": 10928374}"
}
```

---

### 4.4 ตรวจสอบความคืบหน้า (Progress Polling)
- **Endpoint:** `GET /sdapi/v1/progress`
- **Response:**
  ```json
  {
    "progress": 0.65,
    "eta_relative": 3.2,
    "state": {
      "skipped": false,
      "interrupted": false,
      "job": "txt2img",
      "job_count": 1
    },
    "current_image": "base64 preview if enabled"
  }
  ```

---

## 5. การจัดการคิวงานและ Concurrent Requests (Queue Management)

### ธรรมชาติของ GPU Inference
การคำนวณของ AI Image Generation ใช้ทรัพยากร VRAM สูงมาก หากส่ง request เข้ามาพร้อมกันโดยตรงหลายงาน อาจทำให้เกิดปัญหา **CUDA Out of Memory (OOM)** หรือเซิร์ฟเวอร์ค้าง

### แนวทางการจัดการที่แนะนำใน LUMA:
1. **Forge WebUI Internal Queue Lock:**
   - โดยพื้นฐานแล้ว Forge WebUI มี Threading Lock ภายในที่จะประมวลผลงานทีละ 1 งานอยู่แล้ว งานถัดไปจะรออยู่ในคิว HTTP connection
2. **Backend Concurrency Limiter (Semaphore):**
   - ใน Flask Backend (`ai_client.py`) สามารถใช้ `threading.Semaphore(1)` หรือ `threading.BoundedSemaphore(max_concurrent=1)`
   - จำกัดให้มีเพียง 1 งานที่กำลังประมวลผลบน GPU ในเวลาใดเวลาหนึ่ง
   - หากมีผู้ใช้งานส่งเข้ามาพร้อมกัน งานที่ 2 จะรอจนกว่างานแรกจะเสร็จสิ้น
3. **HTTP Timeout:**
   - ตั้งค่า Timeout ของ Backend และ Nginx ไว้อย่างน้อย 120-180 วินาที เพื่อให้มีเวลารองรับงานที่รอคิว

---

## 6. การทดสอบการเชื่อมต่อ

ตรวจสอบว่าเครื่อง Backend สามารถ Ping และเรียก HTTP endpoint ของ AI Server ได้หรือไม่:

```bash
# ทดสอบ ping จากเครื่อง Backend
ping 192.168.1.30

# ทดสอบเรียก options endpoint
curl -X GET http://192.168.1.30:7860/sdapi/v1/options
```
