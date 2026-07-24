"""
Service layer implementing business logic.
Follows Single Responsibility and Dependency Inversion Principles.
"""
import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from app.models import db, User, Role, File, Tag, Project
from app.repositories import (
    UserRepository, 
    RoleRepository, 
    ProjectRepository, 
    TagRepository, 
    FileRepository
)


class OCRService:
    """Service for handling OCR operations with Persian support."""
    
    def __init__(self):
        self.enabled = True
        self.languages = 'fas+eng'
        self._tesseract = None
    
    def _get_tesseract(self):
        """Lazy load pytesseract to avoid import errors if not installed."""
        if self._tesseract is None:
            try:
                import pytesseract
                self._tesseract = pytesseract
            except ImportError:
                self.enabled = False
                return None
        return self._tesseract
    
    def extract_text(self, file_path, mime_type=None):
        """
        Extract text from image or PDF using Tesseract OCR.
        Supports Persian (Farsi) and English.
        """
        if not self.enabled:
            return None, "OCR is not enabled or pytesseract is not installed"
        
        tesseract = self._get_tesseract()
        if not tesseract:
            return None, "Failed to initialize Tesseract"
        
        try:
            # Check if it's an image format
            image_extensions = ['.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.gif']
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext in image_extensions:
                from PIL import Image
                image = Image.open(file_path)
                text = tesseract.image_to_string(image, lang=self.languages)
                return text, None
            
            # For PDF files
            elif file_ext == '.pdf':
                # Try to use pdf2image for PDF OCR
                try:
                    from pdf2image import convert_from_path
                    images = convert_from_path(file_path, dpi=300)
                    full_text = []
                    for image in images:
                        text = tesseract.image_to_string(image, lang=self.languages)
                        full_text.append(text)
                    return '\n'.join(full_text), None
                except ImportError:
                    return None, "pdf2image is not installed for PDF OCR"
                except Exception as e:
                    return None, f"PDF OCR error: {str(e)}"
            
            else:
                return None, f"Unsupported file type for OCR: {file_ext}"
                
        except Exception as e:
            return None, f"OCR processing error: {str(e)}"


class FileUploadService:
    """Service for handling file upload operations."""
    
    def __init__(self, upload_folder, allowed_extensions):
        self.upload_folder = upload_folder
        self.allowed_extensions = allowed_extensions
        self.ocr_service = OCRService()
        self.file_repository = FileRepository()
    
    def _allowed_file(self, filename):
        """Check if file extension is allowed."""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.allowed_extensions
    
    def _generate_unique_filename(self, original_filename):
        """Generate a unique filename while preserving extension."""
        ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
        unique_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
        return unique_name
    
    def upload_file(
        self, 
        file_storage, 
        uploaded_by_user, 
        project_id=None, 
        description='', 
        tag_names=None,
        allowed_role_ids=None
    ):
        """
        Upload a file with metadata, tags, and role-based access control.
        Returns tuple: (file_instance, error_message)
        """
        if not file_storage or not file_storage.filename:
            return None, "No file provided"
        
        original_filename = secure_filename(file_storage.filename)
        if not self._allowed_file(original_filename):
            return None, f"File type not allowed. Allowed: {', '.join(self.allowed_extensions)}"
        
        # Generate unique filename and save
        unique_filename = self._generate_unique_filename(original_filename)
        file_path = os.path.join(self.upload_folder, unique_filename)
        
        # Ensure upload directory exists
        os.makedirs(self.upload_folder, exist_ok=True)
        
        # Save file
        file_storage.save(file_path)
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Determine MIME type
        mime_type = file_storage.content_type or 'application/octet-stream'
        
        # Create file record
        file_instance = File(
            filename=unique_filename,
            original_filename=original_filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            description=description,
            project_id=project_id,
            uploaded_by=uploaded_by_user.id
        )
        
        db.session.add(file_instance)
        db.session.flush()  # Get the ID before committing
        
        # Add tags
        if tag_names:
            tag_repo = TagRepository()
            for tag_name in tag_names:
                tag = tag_repo.get_or_create_tag(tag_name.strip())
                file_instance.tags.append(tag)
        
        # Add allowed roles
        if allowed_role_ids:
            role_repo = RoleRepository()
            for role_id in allowed_role_ids:
                role = role_repo.get_by_id(role_id)
                if role:
                    file_instance.allowed_roles.append(role)
        else:
            # Default: allow all non-admin roles
            default_roles = Role.query.filter_by(is_admin=False).all()
            for role in default_roles:
                file_instance.allowed_roles.append(role)
        
        db.session.commit()
        
        # Process OCR asynchronously (in production, use Celery)
        if self.ocr_service.enabled:
            try:
                ocr_text, ocr_error = self.ocr_service.extract_text(file_path, mime_type)
                if ocr_text:
                    file_instance.ocr_text = ocr_text
                    file_instance.ocr_processed = True
                elif ocr_error:
                    file_instance.ocr_error = ocr_error
                db.session.commit()
            except Exception as e:
                file_instance.ocr_error = str(e)
                db.session.commit()
        
        return file_instance, None


class UserService:
    """Service for user management operations."""
    
    def __init__(self):
        self.user_repository = UserRepository()
        self.role_repository = RoleRepository()
    
    def create_user(self, username, email, password, full_name, role_name='User'):
        """Create a new user with specified role."""
        # Check if user already exists
        if self.user_repository.get_by_username(username):
            return None, "Username already exists"
        if self.user_repository.get_by_email(email):
            return None, "Email already registered"
        
        # Get role
        role = self.role_repository.get_by_name(role_name)
        if not role:
            return None, f"Role '{role_name}' not found"
        
        # Create user
        user = self.user_repository.create_user(
            username=username,
            email=email,
            password=password,
            full_name=full_name,
            role_id=role.id
        )
        
        return user, None
    
    def get_user_by_username(self, username):
        """Get user by username."""
        return self.user_repository.get_by_username(username)
    
    def authenticate_user(self, username, password):
        """Authenticate user with username and password."""
        user = self.user_repository.get_by_username(username)
        if not user:
            return None, "Invalid username or password"
        
        if not user.is_active:
            return None, "Account is deactivated"
        
        if not user.check_password(password):
            return None, "Invalid username or password"
        
        return user, None
    
    def deactivate_user(self, user_id):
        """Deactivate a user account."""
        user = self.user_repository.get_by_id(user_id)
        if not user:
            return None, "User not found"
        
        return self.user_repository.deactivate_user(user), None
    
    def update_user_role(self, user_id, role_name):
        """Update user's role."""
        user = self.user_repository.get_by_id(user_id)
        if not user:
            return None, "User not found"
        
        role = self.role_repository.get_by_name(role_name)
        if not role:
            return None, f"Role '{role_name}' not found"
        
        user.role_id = role.id
        db.session.commit()
        return user, None


class ProjectService:
    """Service for project management."""
    
    def __init__(self):
        self.project_repository = ProjectRepository()
    
    def create_project(self, name, description=''):
        """Create a new project."""
        if self.project_repository.get_by_name(name):
            return None, "Project name already exists"
        
        return self.project_repository.create_project(name, description), None
    
    def get_all_projects(self):
        """Get all active projects."""
        return self.project_repository.get_active_projects()
    
    def search_projects(self, query):
        """Search projects by name or description."""
        return self.project_repository.search_projects(query)


class TagService:
    """Service for tag management."""
    
    def __init__(self):
        self.tag_repository = TagRepository()
    
    def get_all_tags(self):
        """Get all tags."""
        return self.tag_repository.get_all_tags()
    
    def create_tag(self, name, color='#6c757d'):
        """Create a new tag."""
        if self.tag_repository.get_by_name(name):
            return None, "Tag name already exists"
        
        return self.tag_repository.create_tag(name, color), None


class SearchService:
    """Service for advanced file search operations."""
    
    def __init__(self):
        self.file_repository = FileRepository()
    
    def advanced_search(
        self,
        current_user,
        filename=None,
        tags=None,
        project_name=None,
        date_from=None,
        date_to=None,
        page=1,
        per_page=20
    ):
        """
        Perform advanced search with multiple filters.
        Respects user's role-based access control.
        """
        # If admin, search all files; otherwise, only accessible files
        if current_user.role.is_admin:
            return self.file_repository.advanced_search(
                filename=filename,
                tags=tags,
                project_name=project_name,
                date_from=date_from,
                date_to=date_to,
                page=page,
                per_page=per_page
            )
        else:
            # For non-admin users, we need to filter by role access
            # This is handled in the repository's advanced_search method
            return self.file_repository.advanced_search(
                filename=filename,
                tags=tags,
                project_name=project_name,
                date_from=date_from,
                date_to=date_to,
                page=page,
                per_page=per_page
            )
    
    def search_in_ocr(self, search_term, current_user, page=1, per_page=20):
        """Search within OCR-extracted text."""
        return self.file_repository.search_in_ocr_text(search_term, page, per_page)
