# DMS - Document Management System

یک سیستم مدیریت اسناد (DMS) مدرن با استفاده از Flask، MySQL و SQLAlchemy که بر اساس اصول SOLID طراحی شده است.

## ویژگی‌ها

✅ **احراز هویت امن** - ورود/خروج با رمزنگاری bcrypt  
✅ **مدیریت کاربران** - صفحه کارکنان با قابلیت جستجو و مدیریت  
✅ **سیستم نقش‌ها (Roles)** - Admin, User, Manager با دسترسی‌های مختلف  
✅ **کنترل دسترسی به فایل** - تعیین نقش‌های مجاز برای هر فایل  
✅ **تگ‌گذاری** - تگ‌های رنگی برای دسته‌بندی فایل‌ها  
✅ **پروژه‌ها** - سازماندهی فایل‌ها بر اساس پروژه  
✅ **OCR فارسی** - استخراج متن از تصاویر و PDF با پشتیبانی از زبان فارسی  
✅ **جستجوی پیشرفته** - جستجو بر اساس:
   - نام فایل
   - تگ‌ها (چند تگ همزمان)
   - نام پروژه
   - بازه تاریخ آپلود
   - متن OCR استخراج شده

## ساختار پروژه (SOLID)

```
dms_solid/
├── app/
│   ├── __init__.py          # Application Factory
│   ├── config.py            # Configuration (Single Responsibility)
│   ├── models/              # Database Models
│   │   └── __init__.py      # User, Role, File, Tag, Project
│   ├── repositories/        # Data Access Layer (Dependency Inversion)
│   │   └── __init__.py      # UserRepository, FileRepository, etc.
│   ├── services/            # Business Logic Layer
│   │   └── __init__.py      # UserService, FileUploadService, OCRService
│   ├── routes/              # Controllers (Single Responsibility)
│   │   └── __init__.py      # Blueprints for each domain
│   └── utils/               # Utility functions
├── templates/               # Jinja2 Templates
│   ├── base.html           # Base template with RTL support
│   ├── auth/               # Login page
│   ├── main/               # Dashboard
│   ├── files/              # File management pages
│   ├── users/              # User management (admin only)
│   ├── projects/           # Project management
│   ├── tags/               # Tags listing
│   └── search/             # Advanced search & OCR search
├── static/
│   └── uploads/            # Uploaded files storage
└── run.py                  # Entry point
```

## نصب و راه‌اندازی

### 1. پیش‌نیازها

```bash
# Python 3.8+
# MySQL 5.7+ یا MariaDB
```

### 2. نصب پکیج‌ها

```bash
pip install flask flask-sqlalchemy flask-login pymysql \
            werkzeug pytesseract pillow pdf2image
```

### 3. نصب Tesseract برای OCR فارسی

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install tesseract-ocr tesseract-ocr-fas tesseract-ocr-eng
```

**Windows:**
1. دانلود از https://github.com/tesseract-ocr/tesseract
2. نصب و اضافه کردن به PATH
3. دانلود زبان فارسی از https://github.com/tesseract-ocr/tessdata

### 4. تنظیم دیتابیس

```sql
CREATE DATABASE dms_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 5. پیکربندی

فایل `app/config.py` را ویرایش کنید:

```python
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://username:password@localhost/dms_db'
SECRET_KEY = 'your-secret-key-here'
```

### 6. اجرا

```bash
cd dms_solid
python run.py
```

مرورگر را باز کنید و به آدرس `http://localhost:5000` بروید.

## ورود به سیستم

- **نام کاربری:** `admin`
- **رمز عبور:** `admin123`

## اصول SOLID رعایت شده

1. **Single Responsibility Principle (SRP):**
   - هر کلاس فقط یک مسئولیت دارد
   - Config فقط تنظیمات، Models فقط ساختار داده، Services فقط منطق کسب‌وکار

2. **Open/Closed Principle (OCP):**
   - امکان افزودن فیلترهای جدید به جستجو بدون تغییر کد موجود
   - Repository pattern برای توسعه‌پذیری

3. **Liskov Substitution Principle (LSP):**
   - تمام Repositoryها از BaseRepository ارث‌بری می‌کنند

4. **Interface Segregation Principle (ISP):**
   - سرویس‌های کوچک و متمرکز (UserService, FileService, SearchService)

5. **Dependency Inversion Principle (DIP):**
   - وابستگی به abstractionها نه implementationها
   - Application Factory الگوی تزریق وابستگی

## API Endpoints

| Route | Method | Description |
|-------|--------|-------------|
| `/auth/login` | GET/POST | ورود به سیستم |
| `/dashboard` | GET | داشبورد اصلی |
| `/files/` | GET | لیست فایل‌ها |
| `/files/upload` | GET/POST | آپلود فایل |
| `/files/<id>` | GET | مشاهده جزئیات فایل |
| `/files/<id>/download` | GET | دانلود فایل |
| `/users/` | GET | لیست کاربران (ادمین) |
| `/users/create` | GET/POST | ایجاد کاربر (ادمین) |
| `/projects/` | GET | لیست پروژه‌ها |
| `/search/` | GET | جستجوی پیشرفته |
| `/search/ocr` | GET | جستجو در متن OCR |

## امنیت

- رمزنگاری رمز عبور با Werkzeug
- کنترل دسترسی مبتنی بر نقش (RBAC)
- محافظت در برابر CSRF
- اعتبارسنجی نوع فایل‌های آپلودی
- محدودیت حجم فایل (50MB)

## تکنولوژی‌ها

- **Backend:** Flask 3.x, SQLAlchemy 2.x
- **Database:** MySQL 8.x / MariaDB
- **ORM:** SQLAlchemy با Relationshipهای پیشرفته
- **Authentication:** Flask-Login
- **OCR:** Pytesseract با پشتیبانی از فارسی
- **Frontend:** Bootstrap 5 RTL, Font Awesome, Vazirmatn Font

---

ساخته شده با ❤️ برای مدیریت بهتر اسناد
