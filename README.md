# 📖 E-Book Store Mini Project Database (Classic Vintage Paper Edition)

เว็บแอปพลิเคชันระบบร้านขาย E-Book และระบบบริหารจัดการฐานข้อมูลเชิงสัมพันธ์แบบ **3NF (Third Normal Form)** ด้วย **Python (Native HTTP Server + SQLite3)** และหน้าบ้านแบบ **Single File (HTML5 + Tailwind CSS + Vanilla JS)** ตามข้อกำหนดใน [e_book_store_technical_specification.md](file:///d:/E-Book%20%28Mini%20Project%20Database%29/e_book_store_technical_specification.md)

---

## 🎨 ธีมและสไตล์การออกแบบ (UX/UI Design Concept)
- **ธีม Classic Vintage Paper:** สไตล์ร้านหนังสือคลาสสิก อารมณ์ห้องสมุดยุโรปโบราณ ผสมผสานความ Clean & Responsive ใช้งานง่าย
- **โทนสี (Color Palette):**
  - Background หลัก: สีกระดาษถนอมสายตา/กระดาษสาโบราณ (`#F4EFEA`)
  - Container / Card: สีกระดาษขาวนวลธรรมชาติ (`#FDFBF7`) ตัดขอบสีน้ำตาลสันหนังสือ (`#E3DCD3`)
  - Typography: ตัวอักษรสีหมึกพิมพ์ดำอมน้ำตาล (`#2C2523`) ฟอนต์ Google Fonts: `'Playfair Display'` (หัวข้อ Serif คลาสสิก) และ `'Sarabun'` (ภาษาไทย)
  - Accent หนังโบราณ: `#8C5336` (hover: `#72422A`)
  - ปุ่มอนุมัติ/ดาวน์โหลด: สีเขียวใบชาแห้ง (`#2D4739` hover: `#203328`)

---

## 🌟 ฟีเจอร์หลักของระบบ (Key Features)

### 1. ฝั่งลูกค้า (Customer Facing)
- **ระบบสมาชิกและโปรไฟล์:** สมัครสมาชิก (ดักจับ `UNIQUE` Email), เข้าสู่ระบบ, สลับบัญชีทดสอบ, และแก้ไขข้อมูลส่วนตัวบันทึกลงตาราง `users`
- **ค้นหาและคัดกรอง:** ค้นหา Real-time ตามชื่อเรื่อง/ผู้แต่ง และกรองตามหมวดหมู่จากตาราง `categories`
- **การ์ดหนังสือ E-Book:** แสดงภาพปก, ชื่อเรื่อง, ผู้แต่ง, หมวดหมู่, ราคา (฿), และป้ายสถานะ "พร้อมขาย" / "ปิดการขายชั่วคราว"
- **ตะกร้าสินค้า (Cart):** เพิ่มลงตะกร้าพร้อมดักจับสินค้าซ้ำ และป้องกันการเพิ่มสินค้าที่ปิดการขาย (`is_active = 0`)
- **สั่งซื้อและชำระเงินจำลอง (Mock Checkout):** สแกน QR Code พร้อมเพย์จำลอง และแนบลิงก์สลิปจำลองบันทึกลงตาราง `payments`
- **ระบบดาวน์โหลดดิจิทัล (Strict Security Guardrail):** 
  - หากออเดอร์อยู่ในสถานะ `pending` หรือ `cancelled` ปุ่มดาวน์โหลดจะถูกล็อก `🔒 ลิงก์ถูกระงับ (รอการอนุมัติ)` และ Backend API จะบล็อกไม่ส่งไฟล์
  - เฉพาะออเดอร์ที่ Admin อนุมัติ (`confirmed`) ปุ่มจะเปลี่ยนเป็นสีเขียว `⬇ ดาวน์โหลด E-Book` และเปิดดาวน์โหลดไฟล์จำลองได้ทันที

### 2. ฝั่งผู้ดูแลระบบ (Admin Backoffice)
- **จัดการคำสั่งซื้อ (Orders Management):** ดูสลิปจำลอง, ปุ่มกดยืนยัน (`confirmed`) หรือยกเลิก (`cancelled`)
- **จัดการ E-Book:** เพิ่มหนังสือใหม่ (ดักจับราคาติดลบ) และปุ่มกดสลับเปิด/ปิดการขาย (`is_active`) แบบ Toggle
- **จัดการหมวดหมู่:** ฟอร์มเพิ่มหมวดหมู่ใหม่
- **จัดการผู้ใช้:** ดูรายชื่อผู้ใช้งาน บทบาท ยอดสั่งซื้อสะสม
- **รายงานวิเคราะห์ 4 เรื่อง (SQL Reports Dashboard):**
  1. ยอดขายตามช่วงเวลารายเดือน (Sales Over Time)
  2. E-Book ขายดีที่สุด Top 5 (Best-Selling E-Books)
  3. ยอดขายตามหมวดหมู่ (Sales by Category)
  4. พฤติกรรมลูกค้า & ยอดซื้อสะสม (Customer Analytics)

---

## 🗄️ โครงสร้างฐานข้อมูล SQLite 3NF Schema (11 Tables)
1. `roles` (role_id, role_name)
2. `users` (user_id, email, password_hash, full_name, phone, role_id, created_at)
3. `categories` (category_id, category_name)
4. `authors` (author_id, author_name, bio)
5. `ebooks` (ebook_id, title, description, price, cover_image_url, is_active, category_id, author_id)
6. `carts` (cart_id, user_id, updated_at)
7. `cart_items` (cart_item_id, cart_id, ebook_id, quantity)
8. `orders` (order_id, order_code, user_id, order_date, total_amount, status)
9. `order_items` (order_item_id, order_id, ebook_id, quantity, unit_price)
10. `payments` (payment_id, order_id, payment_method, proof_image, status, paid_at)
11. `download_links` (download_id, order_id, ebook_id, file_name, file_size, download_url, expires_at)

---

## 🚀 วิธีการรันโปรเจกต์ (How to Run)

ไม่ต้องติดตั้ง Third-party Packages เพิ่มเติม สามารถรันได้ทันทีด้วย Python:

```bash
# เริ่มต้นเซิร์ฟเวอร์ Backend & Database
python app.py
```

เข้าใช้งานผ่านเว็บเบราว์เซอร์: **`http://localhost:8000/`**
