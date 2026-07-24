from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()
login_manager = LoginManager()

# Association table for many-to-many relationship between files and tags
file_tags = db.Table('file_tags',
    db.Column('file_id', db.Integer, db.ForeignKey('file.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

# Association table for role-file permissions
role_file_permissions = db.Table('role_file_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True),
    db.Column('file_id', db.Integer, db.ForeignKey('file.id'), primary_key=True)
)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to role
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    role = db.relationship('Role', backref=db.backref('users', lazy=True))
    
    # Relationship to uploaded files
    uploaded_files = db.relationship('File', backref='uploader', lazy=True, foreign_keys='File.uploader_id')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def can_view_file(self, file):
        """Check if user can view a file based on role permissions"""
        if self.is_admin:
            return True
        # Check if user's role has permission to view the file
        return self.role in file.allowed_roles


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Many-to-many relationship with files (which roles can view this file)
    allowed_files = db.relationship('File', secondary=role_file_permissions, 
                                   backref=db.backref('allowed_roles', lazy='dynamic'))


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    creator = db.relationship('User', backref=db.backref('created_projects', lazy=True), foreign_keys=[created_by])
    
    # Relationship to files
    files = db.relationship('File', backref='project', lazy=True)


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    color = db.Column(db.String(7), default='#3498db')  # Hex color code
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Many-to-many relationship with files
    files = db.relationship('File', secondary=file_tags, backref=db.backref('tags', lazy='dynamic'))


class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(256), nullable=False)  # Original filename
    stored_filename = db.Column(db.String(256), nullable=False)  # Unique stored filename
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.BigInteger)
    mime_type = db.Column(db.String(100))
    description = db.Column(db.Text)
    
    # Upload metadata
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Project relationship
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    
    # Many-to-many relationship with tags
    # (defined through file_tags association table)
    
    def get_extension(self):
        return self.filename.rsplit('.', 1)[1].lower() if '.' in self.filename else ''
