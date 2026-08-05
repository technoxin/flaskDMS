"""
Database models following SOLID principles.
Each model has a single responsibility and uses proper relationships.
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Association tables for many-to-many relationships
file_tags = db.Table('file_tags',
    db.Column('file_id', db.Integer, db.ForeignKey('files.id', ondelete='CASCADE'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
)

file_roles = db.Table('file_roles',
    db.Column('file_id', db.Integer, db.ForeignKey('files.id', ondelete='CASCADE'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True)
)


class User(db.Model):
    """User model representing system users."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    role = db.relationship('Role', backref=db.backref('users', lazy='dynamic'))
    uploaded_files = db.relationship('File', backref='uploader', lazy='dynamic', foreign_keys='File.uploaded_by')
    
    def set_password(self, password):
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if the provided password matches the hash."""
        return check_password_hash(self.password_hash, password)
    
    def can_access_file(self, file):
        """Check if user can access a specific file based on roles."""
        if self.role.is_admin:
            return True
        return self.role in file.allowed_roles
    
    def __repr__(self):
        return f'<User {self.username}>'


class Role(db.Model):
    """Role model for access control."""
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with files (many-to-many)
    accessible_files = db.relationship('File', secondary=file_roles, 
                                      backref=db.backref('allowed_roles', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Role {self.name}>'


class Project(db.Model):
    """Project model for organizing files."""
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    files = db.relationship('File', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Project {self.name}>'


class Tag(db.Model):
    """Tag model for labeling files."""
    __tablename__ = 'tags'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    color = db.Column(db.String(7), default='#6c757d')  # Hex color code
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with files (many-to-many)
    files = db.relationship('File', secondary=file_tags, backref=db.backref('tags', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Tag {self.name}>'


class File(db.Model):
    """File model representing uploaded documents."""
    __tablename__ = 'files'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=False)
    mime_type = db.Column(db.String(100))
    
    # OCR extracted text
    ocr_text = db.Column(db.Text)
    ocr_processed = db.Column(db.Boolean, default=False)
    ocr_error = db.Column(db.String(500))
    
    # Metadata
    description = db.Column(db.Text)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    download_count = db.Column(db.Integer, default=0)
    
    # Indexes for search performance
    __table_args__ = (
        db.Index('idx_file_project', 'project_id'),
        db.Index('idx_file_uploader', 'uploaded_by'),
        db.Index('idx_file_uploaded_at', 'uploaded_at'),
    )
    
    def __repr__(self):
        return f'<File {self.original_filename}>'
