"""
Main entry point for the DMS application.
Run this file to start the server.
"""
import os

# Set environment variables for development
os.environ['FLASK_ENV'] = 'development'
os.environ['SECRET_KEY'] = 'dev-secret-key-change-in-production'
os.environ['DATABASE_URL'] = 'mysql+pymysql://root:password@localhost/dms_db'

from app import create_app

app = create_app()

if __name__ == '__main__':
    print("=" * 60)
    print("سیستم مدیریت اسناد (DMS)")
    print("=" * 60)
    print("\nراهنمای راه‌اندازی:")
    print("1. MySQL را نصب و دیتابیس dms_db را ایجاد کنید")
    print("2. فایل config.py را با اطلاعات دیتابیس خود ویرایش کنید")
    print("3. برای OCR فارسی، Tesseract را نصب کنید:")
    print("   - Ubuntu: sudo apt install tesseract-ocr tesseract-ocr-fas")
    print("   - Windows: دانلود از https://github.com/tesseract-ocr/tesseract")
    print("4. پکیج‌های لازم را نصب کنید:")
    print("   pip install flask flask-sqlalchemy flask-login pymysql pytesseract pillow pdf2image")
    print("\n" + "=" * 60)
    print("کاربر پیش‌فرض: admin")
    print("رمز عبور: admin123")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
