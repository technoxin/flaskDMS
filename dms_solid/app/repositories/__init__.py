"""
Repository pattern implementation for data access.
Follows Single Responsibility and Dependency Inversion Principles.
"""
from datetime import datetime
from sqlalchemy import and_, or_
from app.models import db, User, Role, File, Tag, Project


class BaseRepository:
    """Base repository with common CRUD operations."""
    
    def __init__(self, model):
        self.model = model
    
    def get_by_id(self, id):
        return self.model.query.get(id)
    
    def get_all(self):
        return self.model.query.all()
    
    def create(self, **kwargs):
        instance = self.model(**kwargs)
        db.session.add(instance)
        db.session.commit()
        return instance
    
    def update(self, instance, **kwargs):
        for key, value in kwargs.items():
            setattr(instance, key, value)
        db.session.commit()
        return instance
    
    def delete(self, instance):
        db.session.delete(instance)
        db.session.commit()


class UserRepository(BaseRepository):
    """Repository for User operations."""
    
    def __init__(self):
        super().__init__(User)
    
    def get_by_username(self, username):
        return User.query.filter_by(username=username).first()
    
    def get_by_email(self, email):
        return User.query.filter_by(email=email).first()
    
    def get_active_users(self):
        return User.query.filter_by(is_active=True).all()
    
    def search_users(self, query_str, page=1, per_page=15):
        """Search users by username, email, or full name."""
        search = f"%{query_str}%"
        return User.query.filter(
            or_(
                User.username.ilike(search),
                User.email.ilike(search),
                User.full_name.ilike(search)
            )
        ).paginate(page=page, per_page=per_page, error_out=False)
    
    def create_user(self, username, email, password, full_name, role_id):
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            role_id=role_id
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user
    
    def deactivate_user(self, user):
        user.is_active = False
        db.session.commit()
        return user


class RoleRepository(BaseRepository):
    """Repository for Role operations."""
    
    def __init__(self):
        super().__init__(Role)
    
    def get_by_name(self, name):
        return Role.query.filter_by(name=name).first()
    
    def get_all_roles(self):
        return Role.query.order_by(Role.name).all()
    
    def create_role(self, name, description='', is_admin=False):
        role = Role(name=name, description=description, is_admin=is_admin)
        db.session.add(role)
        db.session.commit()
        return role


class ProjectRepository(BaseRepository):
    """Repository for Project operations."""
    
    def __init__(self):
        super().__init__(Project)
    
    def get_by_name(self, name):
        return Project.query.filter_by(name=name).first()
    
    def get_active_projects(self):
        return Project.query.filter_by(is_active=True).order_by(Project.name).all()
    
    def search_projects(self, query_str):
        search = f"%{query_str}%"
        return Project.query.filter(
            or_(
                Project.name.ilike(search),
                Project.description.ilike(search)
            )
        ).all()
    
    def create_project(self, name, description=''):
        project = Project(name=name, description=description)
        db.session.add(project)
        db.session.commit()
        return project


class TagRepository(BaseRepository):
    """Repository for Tag operations."""
    
    def __init__(self):
        super().__init__(Tag)
    
    def get_by_name(self, name):
        return Tag.query.filter_by(name=name).first()
    
    def get_all_tags(self):
        return Tag.query.order_by(Tag.name).all()
    
    def create_tag(self, name, color='#6c757d'):
        tag = Tag(name=name, color=color)
        db.session.add(tag)
        db.session.commit()
        return tag
    
    def get_or_create_tag(self, name, color='#6c757d'):
        tag = self.get_by_name(name)
        if not tag:
            tag = self.create_tag(name, color)
        return tag


class FileRepository(BaseRepository):
    """Repository for File operations with advanced search."""
    
    def __init__(self):
        super().__init__(File)
    
    def get_by_filename(self, filename):
        return File.query.filter_by(filename=filename).first()
    
    def get_files_for_user(self, user, page=1, per_page=20):
        """Get files that user has access to based on roles."""
        if user.role.is_admin:
            query = File.query
        else:
            # Join with file_roles to filter by allowed roles
            query = File.query.join(File.allowed_roles).filter(Role.id == user.role.id)
        
        return query.order_by(File.uploaded_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
    
    def advanced_search(
        self,
        filename=None,
        tags=None,
        project_name=None,
        date_from=None,
        date_to=None,
        page=1,
        per_page=20
    ):
        """
        Advanced search with multiple filters.
        Follows Open/Closed Principle - easy to extend without modification.
        """
        query = File.query
        
        # Filter by filename
        if filename:
            query = query.filter(File.original_filename.ilike(f"%{filename}%"))
        
        # Filter by tags (ALL tags must match)
        if tags:
            tag_ids = []
            for tag_name in tags:
                tag = Tag.query.filter_by(name=tag_name.strip()).first()
                if tag:
                    tag_ids.append(tag.id)
            
            if tag_ids:
                # Files must have ALL specified tags
                for tag_id in tag_ids:
                    query = query.join(File.tags).filter(Tag.id == tag_id)
        
        # Filter by project
        if project_name:
            project = Project.query.filter_by(name=project_name).first()
            if project:
                query = query.filter(File.project_id == project.id)
            else:
                # No project found, return empty result
                return File.query.filter(False).paginate(page=page, per_page=per_page, error_out=False)
        
        # Filter by date range
        if date_from:
            query = query.filter(File.uploaded_at >= date_from)
        if date_to:
            # Include the entire end date
            date_to_end = datetime.combine(date_to, datetime.max.time())
            query = query.filter(File.uploaded_at <= date_to_end)
        
        return query.order_by(File.uploaded_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
    
    def search_in_ocr_text(self, search_term, page=1, per_page=20):
        """Search within OCR-extracted text."""
        return File.query.filter(
            File.ocr_text.ilike(f"%{search_term}%")
        ).order_by(File.uploaded_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
    
    def increment_download_count(self, file):
        file.download_count += 1
        db.session.commit()
        return file
