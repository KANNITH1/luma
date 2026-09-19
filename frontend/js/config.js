/**
 * LUMA - Local Development Configuration
 * 
 * NOTE: ไฟล์นี้ใช้เฉพาะสำหรับการพัฒนาและทดสอบบน Local Development เท่านั้น (เช่น Live Server / standalone test)
 * เพื่อชี้ API_BASE ไปยัง Flask backend ที่รันบน port 5000 โดยตรง
 * 
 * สำหรับการ Deploy จริงบน Production ผ่าน Nginx Reverse Proxy:
 * - ให้ลบไฟล์นี้ หรือไม่ต้อง include ไฟล์นี้ใน HTML
 * - เพื่อให้ app.js fallback ไปใช้ relative path '/api' ซึ่ง Nginx จะทำ reverse proxy ไปยัง backend อัตโนมัติ
 */

window.LUMA_API_URL = 'http://localhost:5000/api';
