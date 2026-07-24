"""
Configuration settings for the DMS application.
Follows Single Responsibility Principle - only handles configuration.
"""
import os
from datetime import timedelta

class Config:
    """Base configuration class."""
    
    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
    
    # SQLAlchemy Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 
        'mysql+pymysql://root:password@localhost/dms_db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    # Upload Configuration
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'tiff', 'bmp', 'doc', 'docx', 'txt'}
    
    # OCR Configuration
    OCR_ENABLED = True
    OCR_LANGUAGES = 'fas+eng'  # Persian + English
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    
    # Pagination
    FILES_PER_PAGE = 20
    USERS_PER_PAGE = 15


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
