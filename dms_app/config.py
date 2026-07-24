import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-in-production'
    
    # MySQL Database Configuration
    MYSQL_HOST = os.environ.get('MYSQL_HOST') or 'localhost'
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT') or 3306)
    MYSQL_USER = os.environ.get('MYSQL_USER') or 'root'
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD') or 'your-password'
    MYSQL_DB = os.environ.get('MYSQL_DB') or 'dms_db'
    
    # SQLAlchemy Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload Configuration
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max file size
    
    # Allowed File Extensions
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'zip', 'rar'}
