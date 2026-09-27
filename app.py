# -*- coding: utf-8 -*-
"""
E-Book Store Mini Project Database
Backend: Python Native HTTP Server + SQLite3 (No external dependencies)
Database: 3NF Relational Architecture (ebookstore.db)
"""

import http.server
import socketserver
import sqlite3
import json
import os
import re
import urllib.parse
from datetime import datetime

PORT = 8000
DB_FILE = os.path.join(os.path.dirname(__file__), 'ebookstore.db')
STATIC_DIR = os.path.dirname(__file__)

# ==============================================================================
# DATABASE INITIALIZATION & 3NF SCHEMA
# ==============================================================================

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    # 1. roles
    cur.execute("""
    CREATE TABLE IF NOT EXISTS roles (
        role_id INTEGER PRIMARY KEY AUTOINCREMENT,
        role_name TEXT NOT NULL UNIQUE
    )
    """)

    # 2. users
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        phone TEXT,
        role_id INTEGER NOT NULL DEFAULT 2,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (role_id) REFERENCES roles(role_id)
    )
    """)

    # 3. categories
    cur.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        category_id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_name TEXT NOT NULL UNIQUE
    )
    """)

    # 4. authors
    cur.execute("""
    CREATE TABLE IF NOT EXISTS authors (
        author_id INTEGER PRIMARY KEY AUTOINCREMENT,
        author_name TEXT NOT NULL,
        bio TEXT
    )
    """)

    # 5. ebooks
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ebooks (
        ebook_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL CHECK (price >= 0),
        cover_image_url TEXT,
        is_active INTEGER NOT NULL DEFAULT 1,
        category_id INTEGER NOT NULL,
        author_id INTEGER NOT NULL,
        FOREIGN KEY (category_id) REFERENCES categories(category_id),
        FOREIGN KEY (author_id) REFERENCES authors(author_id)
    )
    """)

    # 6. carts & cart_items
    cur.execute("""
    CREATE TABLE IF NOT EXISTS carts (
        cart_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS cart_items (
        cart_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        cart_id INTEGER NOT NULL,
        ebook_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
        FOREIGN KEY (cart_id) REFERENCES carts(cart_id) ON DELETE CASCADE,
        FOREIGN KEY (ebook_id) REFERENCES ebooks(ebook_id) ON DELETE CASCADE,
        UNIQUE(cart_id, ebook_id)
    )
    """)

    # 7. orders & order_items
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_code TEXT NOT NULL UNIQUE,
        user_id INTEGER NOT NULL,
        order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        total_amount REAL NOT NULL CHECK (total_amount >= 0),
        status TEXT NOT NULL CHECK (status IN ('pending', 'paid', 'confirmed', 'cancelled')),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        ebook_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
        unit_price REAL NOT NULL CHECK (unit_price >= 0),
        FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
        FOREIGN KEY (ebook_id) REFERENCES ebooks(ebook_id)
    )
    """)

    # 8. payments
    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL UNIQUE,
        payment_method TEXT NOT NULL,
        proof_image TEXT,
        status TEXT NOT NULL DEFAULT 'pending_review',
        paid_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
    )
    """)

    # 9. download_links
    cur.execute("""
    CREATE TABLE IF NOT EXISTS download_links (
        download_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        ebook_id INTEGER NOT NULL,
        file_name TEXT NOT NULL,
        file_size TEXT NOT NULL,
        download_url TEXT NOT NULL,
        expires_at DATETIME,
        FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
        FOREIGN KEY (ebook_id) REFERENCES ebooks(ebook_id),
        UNIQUE(order_id, ebook_id)
    )
    """)

    conn.commit()

    # Seed Default Data (Roles, Users, Categories, Authors, Ebooks ONLY - NO mock orders)
    cur.execute("SELECT COUNT(*) FROM roles")
    if cur.fetchone()[0] == 0:
        seed_mock_data(conn)

    conn.close()

def seed_mock_data(conn):
    cur = conn.cursor()
    # 1. Roles
    cur.executemany("INSERT INTO roles (role_id, role_name) VALUES (?, ?)", [
        (1, 'admin'),
        (2, 'customer')
    ])

    # 2. Users (Admin + Customer Accounts)
    cur.executemany("""
    INSERT INTO users (user_id, email, password_hash, full_name, phone, role_id, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [
        (1, 'admin@vintagebooks.com', 'admin123', 'บรรณารักษ์ ผู้ดูแลร้าน (Admin)', '081-999-8888', 1, '2026-01-01 09:00:00'),
        (2, 'somchai@reader.com', 'pass123', 'สมชาย รักการอ่าน', '089-111-2222', 2, '2026-01-05 10:15:00'),
        (3, 'kanya.dev@outlook.com', 'pass123', 'กัญญา พัฒนซอฟต์แวร์', '086-333-4444', 2, '2026-01-10 14:20:00'),
        (4, 'thanawat.biz@yahoo.com', 'pass123', 'ธนวัฒน์ นักลงทุน', '085-555-6666', 2, '2026-01-15 11:00:00')
    ])

    # 3. Categories
    cur.executemany("INSERT INTO categories (category_id, category_name) VALUES (?, ?)", [
        (1, 'วรรณกรรมและประวัติศาสตร์ (Literature & History)'),
        (2, 'เทคโนโลยีและการเขียนโปรแกรม (Technology & IT)'),
        (3, 'ปรัชญาและการพัฒนาตนเอง (Philosophy & Self Growth)'),
        (4, 'ธุรกิจและการลงทุน (Business & Economics)'),
        (5, 'วิทยาศาสตร์ธรรมชาติ (Natural Sciences)')
    ])

    # 4. Authors
    cur.executemany("INSERT INTO authors (author_id, author_name, bio) VALUES (?, ?, ?)", [
        (1, 'ศ.ดร. นิทัศน์ รัตนมนตรี', 'นักประวัติศาสตร์วรรณกรรมและผู้แปลงานคลาสสิกตะวันตก'),
        (2, 'ดร. อนุสรณ์ พัฒนซอฟต์แวร์', 'สถาปนิกซอฟต์แวร์และผู้เชี่ยวชาญด้าน Database Architecture'),
        (3, 'พิมพา รุ่งอรุณ', 'นักเขียนและนักจิตวิทยา ผู้ถ่ายทอดแนวคิด Stoicism สู่ชีวิตสมัยใหม่'),
        (4, 'กิตติศักดิ์ ชัยชนะเศรษฐ์', 'นักวิเคราะห์เศรษฐกิจและการลงทุนเน้นคุณค่า (Value Investor)'),
        (5, 'รศ.ดร. นิรันดร์ ปรีชาวิทยา', 'นักฟิสิกส์ดาราศาสตร์และผู้เขียนหนังสือวิทยาศาสตร์ยอดนิยม')
    ])

    # 5. Ebooks
    cur.executemany("""
    INSERT INTO ebooks (ebook_id, title, description, price, cover_image_url, is_active, category_id, author_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        (1, 'บันทึกประวัติศาสตร์วรรณกรรมโบราณ (Chronicles of Classical Prose)', 'สำรวจรากเหง้าแห่งวรรณศิลป์ยุคคลาสสิก ปรัชญา และบันทึกอันทรงคุณค่าในอดีต', 350.00, 'https://images.unsplash.com/photo-1544947950-fa07a98d237f?auto=format&fit=crop&w=600&q=80', 1, 1, 1),
        (2, 'Mastering Database Design (3NF & SQL Architecture)', 'คู่มือออกแบบฐานข้อมูลเชิงสัมพันธ์ตั้งแต่ 1NF-3NF การทำ Normalization และการเขียน Complex Query', 390.00, 'https://images.unsplash.com/photo-1544383835-bda2bc66a55d?auto=format&fit=crop&w=600&q=80', 1, 2, 2),
        (3, 'Modern Web Architecture & Native Python', 'เจาะลึกการพัฒนา Web Application ด้วย Clean Architecture โดยไม่พึ่งพา Framework ขนาดใหญ่', 420.00, 'https://images.unsplash.com/photo-1555066931-4365d14bab8c?auto=format&fit=crop&w=600&q=80', 1, 2, 2),
        (4, 'ปรัชญาสโตอิกสำหรับชีวิตร่วมสมัย (The Stoic Compass)', 'แนวคิดความสงบทางใจ การยอมรับธรรมชาติ และการสร้างภูมิคุ้มกันทางอารมณ์', 280.00, 'https://images.unsplash.com/photo-1499750310107-5fef28a66643?auto=format&fit=crop&w=600&q=80', 1, 3, 3),
        (5, 'ศิลปะแห่งการเจรจาและการโน้มน้าวใจ (Persuasion Mastery)', 'เทคนิคจิตวิทยาเพื่อการสื่อสารที่สร้างความร่วมมือและความเข้าใจอันลึกซึ้ง', 290.00, 'https://images.unsplash.com/photo-1551836022-d5d88e9218df?auto=format&fit=crop&w=600&q=80', 1, 3, 3),
        (6, 'กลยุทธ์การลงทุนเน้นคุณค่าในยุคดิจิทัล (Value Investing Paradigm)', 'วิธีประเมินมูลค่ากิจการ อ่านงบการเงินอย่างรอบคอบ และวิเคราะห์คูเมืองธุรกิจ', 320.00, 'https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?auto=format&fit=crop&w=600&q=80', 1, 4, 4),
        (7, 'อิสรภาพทางการเงินด้วย Passive Cash Flow', 'คู่มือวางแผนทางการเงิน การสร้างกระแสเงินสดต่อเนื่อง และการบริหารความเสี่ยง', 260.00, 'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=600&q=80', 1, 4, 4),
        (8, 'ความลับแห่งจักรวาลควอนตัม (Quantum Reality)', 'ท่องโลกฟิสิกส์ควอนตัม ทฤษฎีสัมพัทธภาพ และความลึกลับของเอกภพ', 340.00, 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=600&q=80', 1, 5, 5),
        (9, 'กำเนิดสิ่งมีชีวิตและวิวัฒนาการธรรมชาติ (The Web of Nature)', 'เรื่องราวของความหลากหลายทางชีวภาพและระบบนิเวศบนผืนพิภพ', 270.00, 'https://images.unsplash.com/photo-1509198397868-475647b2a1e5?auto=format&fit=crop&w=600&q=80', 1, 5, 5),
        (10, 'มหากาพย์ตำนานกรีกและโรมโบราณ (Classical Mythos)', 'เรื่องเล่าเทววิทยา วีรบุรุษ และปรัมปราคติที่เป็นรากฐานของอารยธรรม', 310.00, 'https://images.unsplash.com/photo-1512820790803-83ca734da794?auto=format&fit=crop&w=600&q=80', 1, 1, 1),
        (11, 'จดหมายเหตุเมนเฟรมโบราณ (ฉบับพักการพิมพ์)', 'เอกสารประวัติศาสตร์ระบบคอมพิวเตอร์ยุคแรก (ปิดการจำหน่ายชั่วคราว)', 199.00, 'https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=600&q=80', 0, 2, 2)
    ])

    # Note: 0 Mock orders are seeded by default as requested.
    conn.commit()

# ==============================================================================
# NATIVE HTTP REQUEST HANDLER & REST API
# ==============================================================================

class AppRequestHandler(http.server.SimpleHTTPRequestHandler):
    def send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-User-Id")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def send_error_response(self, message, status=400):
        self.send_json_response({"error": message, "success": False}, status=status)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-User-Id")
        self.end_headers()

    def get_request_body(self):
        content_len = int(self.headers.get('Content-Length', 0))
        if content_len == 0:
            return {}
        raw = self.rfile.read(content_len).decode('utf-8')
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def get_current_user_id(self):
        user_id_hdr = self.headers.get('X-User-Id')
        if user_id_hdr and user_id_hdr.isdigit():
            return int(user_id_hdr)
        return None

    def is_current_user_admin(self, conn):
        user_id = self.get_current_user_id()
        if not user_id:
            return False
        cur = conn.cursor()
        cur.execute("SELECT role_id FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        return bool(row and row['role_id'] == 1)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # Serve Frontend
        if path == '/' or path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            with open(os.path.join(STATIC_DIR, 'index.html'), 'rb') as f:
                self.wfile.write(f.read())
            return

        # ----------------- API Endpoints -----------------
        conn = get_db()
        cur = conn.cursor()

        try:
            # Current Session Info (Auth Me)
            if path == '/api/auth/me':
                user_id = self.get_current_user_id()
                if not user_id:
                    self.send_json_response({"user": None, "success": True})
                    return
                cur.execute("SELECT u.user_id, u.email, u.full_name, u.phone, u.role_id, u.created_at, r.role_name FROM users u JOIN roles r ON u.role_id = r.role_id WHERE u.user_id = ?", (user_id,))
                user = cur.fetchone()
                if user:
                    self.send_json_response({"user": dict(user), "success": True})
                else:
                    self.send_json_response({"user": None, "success": True})
                return

            # 1. Categories
            if path == '/api/categories':
                cur.execute("SELECT category_id, category_name FROM categories ORDER BY category_id ASC")
                cats = [dict(r) for r in cur.fetchall()]
                self.send_json_response({"categories": cats, "success": True})
                return

            # 2. Authors
            if path == '/api/authors':
                cur.execute("SELECT author_id, author_name, bio FROM authors ORDER BY author_id ASC")
                authors = [dict(r) for r in cur.fetchall()]
                self.send_json_response({"authors": authors, "success": True})
                return

            # 3. E-Books (Catalog with search & filter)
            if path == '/api/ebooks':
                search_term = query.get('search', [''])[0].strip()
                cat_id = query.get('category', [''])[0].strip()

                sql = """
                SELECT e.ebook_id, e.title, e.description, e.price, e.cover_image_url, 
                       e.is_active, e.category_id, e.author_id,
                       c.category_name, a.author_name, a.bio as author_bio
                FROM ebooks e
                JOIN categories c ON e.category_id = c.category_id
                JOIN authors a ON e.author_id = a.author_id
                WHERE 1=1
                """
                params = []

                if search_term:
                    sql += " AND (e.title LIKE ? OR a.author_name LIKE ? OR e.description LIKE ?)"
                    p = f"%{search_term}%"
                    params.extend([p, p, p])

                if cat_id and cat_id.isdigit():
                    sql += " AND e.category_id = ?"
                    params.append(int(cat_id))

                sql += " ORDER BY e.ebook_id ASC"
                cur.execute(sql, params)
                books = [dict(r) for r in cur.fetchall()]
                self.send_json_response({"ebooks": books, "success": True})
                return

            # 4. Active User Cart
            if path == '/api/cart':
                user_id = self.get_current_user_id()
                if not user_id:
                    self.send_json_response({"items": [], "total": 0, "success": True})
                    return

                cur.execute("SELECT cart_id FROM carts WHERE user_id = ?", (user_id,))
                cart = cur.fetchone()
                if not cart:
                    self.send_json_response({"items": [], "total": 0, "success": True})
                    return

                cart_id = cart['cart_id']
                cur.execute("""
                SELECT ci.cart_item_id, ci.cart_id, ci.ebook_id, ci.quantity,
                       e.title, e.price, e.cover_image_url, e.is_active,
                       a.author_name, c.category_name,
                       (ci.quantity * e.price) AS subtotal
                FROM cart_items ci
                JOIN ebooks e ON ci.ebook_id = e.ebook_id
                JOIN authors a ON e.author_id = a.author_id
                JOIN categories c ON e.category_id = c.category_id
                WHERE ci.cart_id = ?
                ORDER BY ci.cart_item_id ASC
                """, (cart_id,))
                items = [dict(r) for r in cur.fetchall()]
                total = sum(i['subtotal'] for i in items)
                self.send_json_response({"items": items, "total": total, "cart_id": cart_id, "success": True})
                return

            # 5. Customer's Orders
            if path == '/api/orders/my':
                user_id = self.get_current_user_id()
                if not user_id:
                    self.send_error_response("กรุณาเข้าสู่ระบบก่อนดูคำสั่งซื้อ", status=401)
                    return

                cur.execute("""
                SELECT o.order_id, o.order_code, o.order_date, o.total_amount, o.status,
                       p.payment_method, p.proof_image, p.status as payment_status
                FROM orders o
                LEFT JOIN payments p ON o.order_id = p.order_id
                WHERE o.user_id = ?
                ORDER BY o.order_id DESC
                """, (user_id,))
                orders = [dict(r) for r in cur.fetchall()]

                # Fetch items & download links for each order
                for ord_entry in orders:
                    o_id = ord_entry['order_id']
                    cur.execute("""
                    SELECT oi.order_item_id, oi.ebook_id, oi.quantity, oi.unit_price,
                           e.title, e.cover_image_url
                    FROM order_items oi
                    JOIN ebooks e ON oi.ebook_id = e.ebook_id
                    WHERE oi.order_id = ?
                    """, (o_id,))
                    ord_entry['items'] = [dict(r) for r in cur.fetchall()]

                    # Strict Download guardrail: Only fetch download link if order is confirmed
                    if ord_entry['status'] == 'confirmed':
                        cur.execute("""
                        SELECT download_id, ebook_id, file_name, file_size, download_url
                        FROM download_links
                        WHERE order_id = ?
                        """, (o_id,))
                        ord_entry['downloads'] = [dict(r) for r in cur.fetchall()]
                    else:
                        ord_entry['downloads'] = []

                self.send_json_response({"orders": orders, "success": True})
                return

            # 6. Admin All Orders (RBAC Protected: Admin Only)
            if path == '/api/orders/all':
                if not self.is_current_user_admin(conn):
                    self.send_error_response("สิทธิ์การใช้งานถูกปฏิเสธ: เฉพาะ Admin เท่านั้นที่เข้าถึงข้อมูลนี้ได้", status=403)
                    return

                search_q = query.get('search', [''])[0].strip()
                status_filter = query.get('status', [''])[0].strip()

                sql = """
                SELECT o.order_id, o.order_code, o.order_date, o.total_amount, o.status,
                       u.user_id, u.full_name, u.email, u.phone,
                       p.payment_method, p.proof_image, p.status as payment_status, p.paid_at
                FROM orders o
                JOIN users u ON o.user_id = u.user_id
                LEFT JOIN payments p ON o.order_id = p.order_id
                WHERE 1=1
                """
                params = []

                if search_q:
                    sql += " AND (o.order_code LIKE ? OR u.full_name LIKE ? OR u.email LIKE ? OR u.phone LIKE ?)"
                    p = f"%{search_q}%"
                    params.extend([p, p, p, p])

                if status_filter and status_filter in ('pending', 'paid', 'confirmed', 'cancelled'):
                    sql += " AND o.status = ?"
                    params.append(status_filter)

                sql += " ORDER BY o.order_id DESC"

                cur.execute(sql, params)
                orders = [dict(r) for r in cur.fetchall()]

                for ord_entry in orders:
                    cur.execute("""
                    SELECT oi.order_item_id, oi.ebook_id, oi.quantity, oi.unit_price, e.title
                    FROM order_items oi
                    JOIN ebooks e ON oi.ebook_id = e.ebook_id
                    WHERE oi.order_id = ?
                    """, (ord_entry['order_id'],))
                    ord_entry['items'] = [dict(r) for r in cur.fetchall()]

                self.send_json_response({"orders": orders, "success": True})
                return

            # 7. Admin All Users (RBAC Protected)
            if path == '/api/users':
                if not self.is_current_user_admin(conn):
                    self.send_error_response("สิทธิ์การใช้งานถูกปฏิเสธ: เฉพาะ Admin เท่านั้นที่เข้าถึงข้อมูลนี้ได้", status=403)
                    return

                cur.execute("""
                SELECT u.user_id, u.email, u.full_name, u.phone, u.role_id, u.created_at,
                       r.role_name,
                       COUNT(o.order_id) as total_orders,
                       COALESCE(SUM(CASE WHEN o.status = 'confirmed' THEN o.total_amount ELSE 0 END), 0) as total_spent
                FROM users u
                JOIN roles r ON u.role_id = r.role_id
                LEFT JOIN orders o ON u.user_id = o.user_id
                GROUP BY u.user_id, u.email, u.full_name, u.phone, u.role_id, u.created_at, r.role_name
                ORDER BY u.user_id ASC
                """)
                users = [dict(r) for r in cur.fetchall()]
                self.send_json_response({"users": users, "success": True})
                return

            # 8. Analytical SQL Reports (Section 4 in Specification)
            if path.startswith('/api/reports/'):
                report_id = path.replace('/api/reports/', '').strip()

                # Report 1: Sales Over Time
                if report_id == '1':
                    cur.execute("""
                    SELECT 
                        strftime('%Y-%m', order_date) AS month,
                        COUNT(order_id) AS total_orders,
                        COALESCE(ROUND(SUM(total_amount), 2), 0) AS total_revenue,
                        COALESCE(ROUND(AVG(total_amount), 2), 0) AS avg_order_value
                    FROM orders
                    WHERE status = 'confirmed'
                    GROUP BY strftime('%Y-%m', order_date)
                    ORDER BY month ASC
                    """)
                    rows = [dict(r) for r in cur.fetchall()]
                    self.send_json_response({
                        "report_id": 1,
                        "title": "ยอดขายตามช่วงเวลา (Sales Over Time)",
                        "description": "ยอดขายรวม, จำนวนคำสั่งซื้อ, และค่าเฉลี่ยต่อคำสั่งซื้อ ตามรายเดือน (เฉพาะคำสั่งซื้อที่ได้รับการอนุมัติ confirmed)",
                        "sql_used": "JOIN, GROUP BY, SUM(), COUNT(), AVG(), Date Filters",
                        "data": rows,
                        "success": True
                    })
                    return

                # Report 2: Best Selling E-Books (Top 5)
                if report_id == '2':
                    cur.execute("""
                    SELECT 
                        e.ebook_id,
                        e.title,
                        c.category_name,
                        a.author_name,
                        COALESCE(SUM(oi.quantity), 0) AS total_units_sold,
                        COALESCE(ROUND(SUM(oi.quantity * oi.unit_price), 2), 0) AS total_revenue
                    FROM order_items oi
                    JOIN orders o ON oi.order_id = o.order_id
                    JOIN ebooks e ON oi.ebook_id = e.ebook_id
                    JOIN categories c ON e.category_id = c.category_id
                    JOIN authors a ON e.author_id = a.author_id
                    WHERE o.status = 'confirmed'
                    GROUP BY e.ebook_id, e.title, c.category_name, a.author_name
                    ORDER BY total_units_sold DESC, total_revenue DESC
                    LIMIT 5
                    """)
                    rows = [dict(r) for r in cur.fetchall()]
                    self.send_json_response({
                        "report_id": 2,
                        "title": "E-Book ขายดีที่สุด (Top 5 Best-Sellers)",
                        "description": "หนังสือที่ขายได้จำนวนเล่มและสร้างยอดขายได้มากที่สุด 5 อันดับแรก",
                        "sql_used": "JOIN, GROUP BY, SUM(), LIMIT",
                        "data": rows,
                        "success": True
                    })
                    return

                # Report 3: Sales by Category
                if report_id == '3':
                    cur.execute("""
                    SELECT 
                        c.category_id,
                        c.category_name,
                        COUNT(DISTINCT o.order_id) AS order_count,
                        COALESCE(SUM(oi.quantity), 0) AS total_books_sold,
                        COALESCE(ROUND(SUM(oi.quantity * oi.unit_price), 2), 0) AS total_category_revenue
                    FROM categories c
                    LEFT JOIN ebooks e ON c.category_id = e.category_id
                    LEFT JOIN order_items oi ON e.ebook_id = oi.ebook_id
                    LEFT JOIN orders o ON oi.order_id = o.order_id AND o.status = 'confirmed'
                    GROUP BY c.category_id, c.category_name
                    ORDER BY total_category_revenue DESC
                    """)
                    rows = [dict(r) for r in cur.fetchall()]
                    self.send_json_response({
                        "report_id": 3,
                        "title": "ยอดขายตามหมวดหมู่ (Sales by Category)",
                        "description": "หมวดหมู่ที่สร้างรายได้และมีจำนวนเล่มจำหน่ายสูงสุด",
                        "sql_used": "Multi-table JOIN, GROUP BY, SUM()",
                        "data": rows,
                        "success": True
                    })
                    return

                # Report 4: Customer Spending & Behavior
                if report_id == '4':
                    cur.execute("""
                    SELECT 
                        u.user_id,
                        u.full_name,
                        u.email,
                        COUNT(o.order_id) AS total_orders,
                        COALESCE(ROUND(SUM(CASE WHEN o.status = 'confirmed' THEN o.total_amount ELSE 0 END), 2), 0) AS confirmed_spending,
                        SUM(CASE WHEN o.status = 'confirmed' THEN 1 ELSE 0 END) AS confirmed_orders,
                        SUM(CASE WHEN o.status = 'pending' THEN 1 ELSE 0 END) AS pending_orders,
                        SUM(CASE WHEN o.status = 'paid' THEN 1 ELSE 0 END) AS paid_orders,
                        SUM(CASE WHEN o.status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled_orders
                    FROM users u
                    LEFT JOIN orders o ON u.user_id = o.user_id
                    WHERE u.role_id = 2
                    GROUP BY u.user_id, u.full_name, u.email
                    ORDER BY confirmed_spending DESC
                    """)
                    rows = [dict(r) for r in cur.fetchall()]
                    self.send_json_response({
                        "report_id": 4,
                        "title": "พฤติกรรมลูกค้า & ยอดซื้อสะสม (Customer Analytics)",
                        "description": "จำแนกพฤติกรรมลูกค้าและยอดใช้จ่ายสะสม",
                        "sql_used": "JOIN, GROUP BY, HAVING, COUNT(), SUM()",
                        "data": rows,
                        "success": True
                    })
                    return

            # 9. Strict Digital Download Guardrail
            m_dl = re.match(r'^/api/download/(\d+)/(\d+)$', path)
            if m_dl:
                order_id = int(m_dl.group(1))
                ebook_id = int(m_dl.group(2))
                user_id = self.get_current_user_id()

                if not user_id:
                    self.send_error_response("กรุณาเข้าสู่ระบบก่อนดาวน์โหลด", status=401)
                    return

                # Verify order status in DB
                cur.execute("SELECT order_id, user_id, status FROM orders WHERE order_id = ?", (order_id,))
                order = cur.fetchone()
                if not order:
                    self.send_error_response("ไม่พบคำสั่งซื้อนี้ในระบบ", status=404)
                    return

                # Verify ownership (Customer must own the order, Admin can download any)
                is_admin = self.is_current_user_admin(conn)
                if not is_admin and order['user_id'] != user_id:
                    self.send_error_response("🔒 การเข้าถึงถูกปฏิเสธ: คุณไม่ใช่เจ้าของคำสั่งซื้อนี้", status=403)
                    return

                # STRICT RULE: Status MUST be 'confirmed'
                if order['status'] != 'confirmed':
                    self.send_error_response(
                        f"🔒 การเข้าถึงถูกปฏิเสธ: คำสั่งซื้ออยู่ในสถานะ '{order['status']}' จะดาวน์โหลดได้เมื่อผู้ดูแลยืนยันคำสั่งซื้อแล้วเท่านั้น",
                        status=403
                    )
                    return

                cur.execute("SELECT * FROM download_links WHERE order_id = ? AND ebook_id = ?", (order_id, ebook_id))
                dl = cur.fetchone()
                if not dl:
                    self.send_error_response("ไม่พบไฟล์ดาวน์โหลดสำหรับรายการนี้", status=404)
                    return

                # Return Mock PDF Content Stream
                self.send_response(200)
                self.send_header('Content-Type', 'application/pdf')
                self.send_header('Content-Disposition', f'attachment; filename="{dl["file_name"]}"')
                self.end_headers()
                sample_pdf_text = f"%PDF-1.4\n1 0 obj << /Title ({dl['file_name']}) >> endobj\ntrailer << /Root 1 0 R >>\n%%EOF"
                self.wfile.write(sample_pdf_text.encode('utf-8'))
                return

            self.send_error_response(f"Endpoint not found: {path}", status=404)

        except Exception as e:
            self.send_error_response(f"Internal Server Error: {str(e)}", status=500)
        finally:
            conn.close()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self.get_request_body()

        conn = get_db()
        cur = conn.cursor()

        try:
            # 1. Register
            if path == '/api/auth/register':
                email = body.get('email', '').strip().lower()
                full_name = body.get('full_name', '').strip()
                phone = body.get('phone', '').strip()
                password = body.get('password', '').strip()

                if not email or not full_name or not password:
                    self.send_error_response("กรุณากรอกอีเมล, รหัสผ่าน, และชื่อ-นามสกุลให้ครบถ้วน", status=400)
                    return

                # Check unique email constraint
                cur.execute("SELECT user_id FROM users WHERE email = ?", (email,))
                if cur.fetchone():
                    self.send_error_response(f"อีเมล '{email}' มีผู้ใช้งานในระบบแล้ว (UNIQUE Constraint)", status=400)
                    return

                cur.execute("""
                INSERT INTO users (email, password_hash, full_name, phone, role_id)
                VALUES (?, ?, ?, ?, 2)
                """, (email, password, full_name, phone))
                conn.commit()

                user_id = cur.lastrowid
                cur.execute("SELECT u.user_id, u.email, u.full_name, u.phone, u.role_id, u.created_at, r.role_name FROM users u JOIN roles r ON u.role_id = r.role_id WHERE u.user_id = ?", (user_id,))
                user = dict(cur.fetchone())
                self.send_json_response({"user": user, "message": "สมัครสมาชิกสำเร็จ", "success": True})
                return

            # 2. Login
            if path == '/api/auth/login':
                email = body.get('email', '').strip().lower()
                password = body.get('password', '').strip()

                if not email or not password:
                    self.send_error_response("กรุณากรอกอีเมลและรหัสผ่าน", status=400)
                    return

                cur.execute("SELECT u.user_id, u.email, u.full_name, u.phone, u.role_id, u.created_at, r.role_name, u.password_hash FROM users u JOIN roles r ON u.role_id = r.role_id WHERE u.email = ?", (email,))
                user = cur.fetchone()
                if not user or user['password_hash'] != password:
                    self.send_error_response("อีเมลหรือรหัสผ่านไม่ถูกต้อง", status=401)
                    return

                user_dict = dict(user)
                del user_dict['password_hash']
                self.send_json_response({"user": user_dict, "message": "เข้าสู่ระบบสำเร็จ", "success": True})
                return

            # 3. Add to Cart
            if path == '/api/cart/add':
                user_id = self.get_current_user_id()
                if not user_id:
                    self.send_error_response("กรุณาเข้าสู่ระบบก่อนเพิ่มสินค้าลงตะกร้า", status=401)
                    return

                ebook_id = body.get('ebook_id')
                if not ebook_id:
                    self.send_error_response("กรุณาระบุรหัส E-Book", status=400)
                    return

                # Check ebook active status
                cur.execute("SELECT ebook_id, title, is_active FROM ebooks WHERE ebook_id = ?", (ebook_id,))
                ebook = cur.fetchone()
                if not ebook:
                    self.send_error_response("ไม่พบหนังสือเล่มนี้ในระบบ", status=404)
                    return
                if not ebook['is_active']:
                    self.send_error_response(f"หนังสือ '{ebook['title']}' ปิดการจำหน่ายชั่วคราว ไม่สามารถเพิ่มลงตะกร้าได้", status=400)
                    return

                # Get or create cart
                cur.execute("SELECT cart_id FROM carts WHERE user_id = ?", (user_id,))
                cart = cur.fetchone()
                if not cart:
                    cur.execute("INSERT INTO carts (user_id) VALUES (?)", (user_id,))
                    conn.commit()
                    cart_id = cur.lastrowid
                else:
                    cart_id = cart['cart_id']

                # Prevent duplicate addition if already in cart
                cur.execute("SELECT cart_item_id, quantity FROM cart_items WHERE cart_id = ? AND ebook_id = ?", (cart_id, ebook_id))
                item = cur.fetchone()
                if item:
                    self.send_error_response("หนังสือเล่มนี้อยู่ในตะกร้าสินค้าของคุณแล้ว", status=400)
                    return

                cur.execute("INSERT INTO cart_items (cart_id, ebook_id, quantity) VALUES (?, ?, 1)", (cart_id, ebook_id))
                conn.commit()

                self.send_json_response({"message": f"เพิ่ม '{ebook['title']}' ลงในตะกร้าสำเร็จ", "success": True})
                return

            # 4. Checkout & Mock Payment
            if path == '/api/checkout':
                user_id = self.get_current_user_id()
                if not user_id:
                    self.send_error_response("กรุณาเข้าสู่ระบบก่อนสั่งซื้อ", status=401)
                    return

                payment_method = body.get('payment_method', 'PromptPay QR Transfer')
                proof_image = body.get('proof_image', 'https://images.unsplash.com/photo-1559526324-4b87b5e36e44?auto=format&fit=crop&w=400&q=80')

                # Get cart items
                cur.execute("SELECT cart_id FROM carts WHERE user_id = ?", (user_id,))
                cart = cur.fetchone()
                if not cart:
                    self.send_error_response("ตะกร้าสินค้าว่างเปล่า", status=400)
                    return

                cart_id = cart['cart_id']
                cur.execute("""
                SELECT ci.ebook_id, ci.quantity, e.price, e.title, e.is_active
                FROM cart_items ci
                JOIN ebooks e ON ci.ebook_id = e.ebook_id
                WHERE ci.cart_id = ?
                """, (cart_id,))
                cart_items = [dict(r) for r in cur.fetchall()]

                if not cart_items:
                    self.send_error_response("ไม่มีรายการสินค้าในตะกร้า", status=400)
                    return

                # Verify all are active
                for item in cart_items:
                    if not item['is_active']:
                        self.send_error_response(f"ไม่สามารถสั่งซื้อได้เนื่องจาก '{item['title']}' ปิดการขายอยู่", status=400)
                        return

                total_amount = sum(i['price'] * i['quantity'] for i in cart_items)
                now_str = datetime.now().strftime('%Y%m%d')
                order_code = f"ORD-{now_str}-{int(datetime.now().timestamp() * 1000) % 10000:04d}"

                # Create Order (Initial status pending)
                cur.execute("""
                INSERT INTO orders (order_code, user_id, total_amount, status)
                VALUES (?, ?, ?, 'pending')
                """, (order_code, user_id, total_amount))
                order_id = cur.lastrowid

                # Create Order Items
                for item in cart_items:
                    cur.execute("""
                    INSERT INTO order_items (order_id, ebook_id, quantity, unit_price)
                    VALUES (?, ?, ?, ?)
                    """, (order_id, item['ebook_id'], item['quantity'], item['price']))

                # Create Mock Payment record
                cur.execute("""
                INSERT INTO payments (order_id, payment_method, proof_image, status)
                VALUES (?, ?, ?, 'pending_review')
                """, (order_id, payment_method, proof_image))

                # Clear Cart
                cur.execute("DELETE FROM cart_items WHERE cart_id = ?", (cart_id,))
                conn.commit()

                self.send_json_response({
                    "order_id": order_id,
                    "order_code": order_code,
                    "total_amount": total_amount,
                    "status": "pending",
                    "message": "สร้างคำสั่งซื้อและบันทึกสลิปจำลองเรียบร้อยแล้ว (รอผู้ดูแลตรวจสอบและอนุมัติ)",
                    "success": True
                })
                return

            # 5. Admin Add E-Book (RBAC Protected)
            if path == '/api/ebooks':
                if not self.is_current_user_admin(conn):
                    self.send_error_response("สิทธิ์การใช้งานถูกปฏิเสธ: เฉพาะ Admin เท่านั้นที่เพิ่มหนังสือได้", status=403)
                    return

                title = body.get('title', '').strip()
                description = body.get('description', '').strip()
                price = float(body.get('price', 0))
                cover_image_url = body.get('cover_image_url', '').strip()
                category_id = int(body.get('category_id', 1))
                author_id = int(body.get('author_id', 1))
                is_active = int(body.get('is_active', 1))

                if not title:
                    self.send_error_response("กรุณากรอกชื่อหนังสือ (NOT NULL)", status=400)
                    return
                if price < 0:
                    self.send_error_response("ราคาต้องไม่ติดลบ (CHECK price >= 0)", status=400)
                    return

                cur.execute("""
                INSERT INTO ebooks (title, description, price, cover_image_url, is_active, category_id, author_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (title, description, price, cover_image_url, is_active, category_id, author_id))
                conn.commit()

                self.send_json_response({"ebook_id": cur.lastrowid, "message": "เพิ่ม E-Book สำเร็จ", "success": True})
                return

            # 6. Admin Add Category (RBAC Protected)
            if path == '/api/categories':
                if not self.is_current_user_admin(conn):
                    self.send_error_response("สิทธิ์การใช้งานถูกปฏิเสธ: เฉพาะ Admin เท่านั้นที่เพิ่มหมวดหมู่ได้", status=403)
                    return

                category_name = body.get('category_name', '').strip()
                if not category_name:
                    self.send_error_response("กรุณาระบุชื่อหมวดหมู่", status=400)
                    return

                cur.execute("INSERT INTO categories (category_name) VALUES (?)", (category_name,))
                conn.commit()
                self.send_json_response({"category_id": cur.lastrowid, "message": "เพิ่มหมวดหมู่สำเร็จ", "success": True})
                return

            # 7. Reset DB to Default Seed
            if path == '/api/db/reset':
                if not self.is_current_user_admin(conn):
                    self.send_error_response("สิทธิ์การใช้งานถูกปฏิเสธ: เฉพาะ Admin เท่านั้น", status=403)
                    return

                cur.execute("DELETE FROM download_links")
                cur.execute("DELETE FROM payments")
                cur.execute("DELETE FROM order_items")
                cur.execute("DELETE FROM orders")
                cur.execute("DELETE FROM cart_items")
                cur.execute("DELETE FROM carts")
                cur.execute("DELETE FROM ebooks")
                cur.execute("DELETE FROM authors")
                cur.execute("DELETE FROM categories")
                cur.execute("DELETE FROM users")
                cur.execute("DELETE FROM roles")
                conn.commit()
                seed_mock_data(conn)
                self.send_json_response({"message": "รีเซ็ตฐานข้อมูลเรียบร้อยแล้ว (ออเดอร์เริ่มต้น 0 รายการ)", "success": True})
                return

            self.send_error_response(f"Endpoint not found: {path}", status=404)

        except Exception as e:
            self.send_error_response(f"Request Error: {str(e)}", status=400)
        finally:
            conn.close()

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self.get_request_body()

        conn = get_db()
        cur = conn.cursor()

        try:
            # 1. Update Profile (User edits their own profile)
            if path == '/api/auth/profile':
                user_id = self.get_current_user_id()
                if not user_id:
                    self.send_error_response("กรุณาเข้าสู่ระบบก่อนแก้ไขข้อมูล", status=401)
                    return

                full_name = body.get('full_name', '').strip()
                phone = body.get('phone', '').strip()

                if not full_name:
                    self.send_error_response("กรุณากรอกชื่อ-นามสกุล", status=400)
                    return

                cur.execute("UPDATE users SET full_name = ?, phone = ? WHERE user_id = ?", (full_name, phone, user_id))
                conn.commit()

                cur.execute("SELECT u.user_id, u.email, u.full_name, u.phone, u.role_id, u.created_at, r.role_name FROM users u JOIN roles r ON u.role_id = r.role_id WHERE u.user_id = ?", (user_id,))
                user = dict(cur.fetchone())
                self.send_json_response({"user": user, "message": "อัปเดตข้อมูลส่วนตัวสำเร็จ", "success": True})
                return

            # 2. Update Cart Item Qty
            m_cart = re.match(r'^/api/cart/item/(\d+)$', path)
            if m_cart:
                cart_item_id = int(m_cart.group(1))
                qty = int(body.get('quantity', 1))

                if qty <= 0:
                    cur.execute("DELETE FROM cart_items WHERE cart_item_id = ?", (cart_item_id,))
                else:
                    cur.execute("UPDATE cart_items SET quantity = ? WHERE cart_item_id = ?", (qty, cart_item_id))
                conn.commit()
                self.send_json_response({"message": "อัปเดตตะกร้าสินค้าสำเร็จ", "success": True})
                return

            self.send_error_response(f"Endpoint not found: {path}", status=404)

        except Exception as e:
            self.send_error_response(str(e), status=400)
        finally:
            conn.close()

    def do_PATCH(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self.get_request_body()

        conn = get_db()
        cur = conn.cursor()

        try:
            # 1. Admin Change Order Status (RBAC Protected: Admin Only)
            m_ord = re.match(r'^/api/orders/(\d+)/status$', path)
            if m_ord:
                if not self.is_current_user_admin(conn):
                    self.send_error_response("สิทธิ์การใช้งานถูกปฏิเสธ: เฉพาะ Admin เท่านั้นที่เปลี่ยนสถานะคำสั่งซื้อได้", status=403)
                    return

                order_id = int(m_ord.group(1))
                new_status = body.get('status', '').strip()

                if new_status not in ('pending', 'paid', 'confirmed', 'cancelled'):
                    self.send_error_response("สถานะไม่ถูกต้อง (ต้องเป็น pending, paid, confirmed, cancelled)", status=400)
                    return

                cur.execute("UPDATE orders SET status = ? WHERE order_id = ?", (new_status, order_id))

                # If status becomes 'confirmed': automatically generate download links and mark payment verified
                if new_status == 'confirmed':
                    cur.execute("UPDATE payments SET status = 'verified' WHERE order_id = ?", (order_id,))
                    cur.execute("SELECT ebook_id FROM order_items WHERE order_id = ?", (order_id,))
                    items = cur.fetchall()

                    for item in items:
                        eb_id = item['ebook_id']
                        cur.execute("SELECT title FROM ebooks WHERE ebook_id = ?", (eb_id,))
                        ebook = cur.fetchone()
                        fname = f"{ebook['title'].lower().replace(' ', '_')[:25]}.pdf"

                        cur.execute("""
                        INSERT OR IGNORE INTO download_links (order_id, ebook_id, file_name, file_size, download_url, expires_at)
                        VALUES (?, ?, ?, '14.2 MB', ?, '2026-12-31 23:59:59')
                        """, (order_id, eb_id, fname, f"/api/download/{order_id}/{eb_id}"))
                else:
                    # If reverted from confirmed to pending/paid/cancelled: remove download links to prevent unauthorized downloads
                    cur.execute("DELETE FROM download_links WHERE order_id = ?", (order_id,))
                    if new_status == 'cancelled':
                        cur.execute("UPDATE payments SET status = 'rejected' WHERE order_id = ?", (order_id,))
                    elif new_status == 'pending':
                        cur.execute("UPDATE payments SET status = 'pending' WHERE order_id = ?", (order_id,))
                    elif new_status == 'paid':
                        cur.execute("UPDATE payments SET status = 'pending_review' WHERE order_id = ?", (order_id,))

                conn.commit()
                status_labels = {
                    'pending': 'รอชำระเงิน (Pending)',
                    'paid': 'รอตรวจสอบสลิป (Paid)',
                    'confirmed': 'อนุมัติ / ยืนยันแล้ว (Confirmed)',
                    'cancelled': 'ยกเลิกคำสั่งซื้อ (Cancelled)'
                }
                self.send_json_response({
                    "message": f"เปลี่ยนสถานะคำสั่งซื้อ #{order_id} เป็น '{status_labels.get(new_status, new_status)}' สำเร็จ",
                    "status": new_status,
                    "success": True
                })
                return

            # 2. Admin Toggle E-Book is_active (RBAC Protected: Admin Only)
            m_eb = re.match(r'^/api/ebooks/(\d+)/toggle$', path)
            if m_eb:
                if not self.is_current_user_admin(conn):
                    self.send_error_response("สิทธิ์การใช้งานถูกปฏิเสธ: เฉพาะ Admin เท่านั้น", status=403)
                    return

                ebook_id = int(m_eb.group(1))
                cur.execute("SELECT is_active FROM ebooks WHERE ebook_id = ?", (ebook_id,))
                eb = cur.fetchone()
                if not eb:
                    self.send_error_response("ไม่พบหนังสือเล่มนี้", status=404)
                    return

                new_val = 0 if eb['is_active'] == 1 else 1
                cur.execute("UPDATE ebooks SET is_active = ? WHERE ebook_id = ?", (new_val, ebook_id))
                conn.commit()

                status_label = "เปิดจำหน่าย" if new_val == 1 else "ปิดการขายชั่วคราว"
                self.send_json_response({"is_active": new_val, "message": f"เปลี่ยนสถานะหนังสือเป็น '{status_label}'", "success": True})
                return

            self.send_error_response(f"Endpoint not found: {path}", status=404)

        except Exception as e:
            self.send_error_response(str(e), status=400)
        finally:
            conn.close()

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        conn = get_db()
        cur = conn.cursor()

        try:
            m_cart = re.match(r'^/api/cart/item/(\d+)$', path)
            if m_cart:
                cart_item_id = int(m_cart.group(1))
                cur.execute("DELETE FROM cart_items WHERE cart_item_id = ?", (cart_item_id,))
                conn.commit()
                self.send_json_response({"message": "ลบรายการออกจากตะกร้าสำเร็จ", "success": True})
                return

            self.send_error_response(f"Endpoint not found: {path}", status=404)

        except Exception as e:
            self.send_error_response(str(e), status=400)
        finally:
            conn.close()

# ==============================================================================
# SERVER RUNNER
# ==============================================================================

def run_server():
    init_db()
    print("=" * 70)
    print("E-Book Store Server (Classic Vintage Paper Edition) Started!")
    print(f"URL: http://localhost:{PORT}")
    print(f"Database: {DB_FILE} (SQLite 3NF Schema)")
    print("=" * 70)

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), AppRequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer shutting down gracefully...")
            httpd.server_close()

if __name__ == '__main__':
    run_server()
