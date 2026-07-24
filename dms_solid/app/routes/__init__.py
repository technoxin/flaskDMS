"""
Route handlers for the DMS application.
Follows Single Responsibility Principle - each blueprint handles specific domain.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime
from app.models import db, User, Role, File, Tag, Project
from app.services import (
    UserService, 
    FileUploadService, 
    ProjectService, 
    TagService, 
    SearchService
)
from app.config import Config

# Create blueprints
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
main_bp = Blueprint('main', __name__)
files_bp = Blueprint('files', __name__, url_prefix='/files')
users_bp = Blueprint('users', __name__, url_prefix='/users')
projects_bp = Blueprint('projects', __name__, url_prefix='/projects')
tags_bp = Blueprint('tags', __name__, url_prefix='/tags')
search_bp = Blueprint('search', __name__, url_prefix='/search')

# Initialize services
user_service = UserService()
project_service = ProjectService()
tag_service = TagService()
search_service = SearchService()


def init_login_manager(app):
    """Initialize Flask-Login with the application."""
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    return login_manager


# ==================== AUTH ROUTES ====================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user, error = user_service.authenticate_user(username, password)
        if user:
            login_user(user, remember=True)
            next_page = request.args.get('next')
            flash('خوش آمدید!', 'success')
            return redirect(next_page or url_for('main.dashboard'))
        else:
            flash(error, 'danger')
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout."""
    logout_user()
    flash('با موفقیت خارج شدید.', 'info')
    return redirect(url_for('auth.login'))


# ==================== MAIN ROUTES ====================

@main_bp.route('/')
@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard showing recent files."""
    # Get recent files accessible to user
    from app.repositories import FileRepository
    file_repo = FileRepository()
    pagination = file_repo.get_files_for_user(current_user, page=1, per_page=10)
    
    # Get statistics
    total_files = len(pagination.items)
    total_projects = Project.query.count()
    total_tags = Tag.query.count()
    
    return render_template('main/dashboard.html', 
                         pagination=pagination,
                         total_files=total_files,
                         total_projects=total_projects,
                         total_tags=total_tags)


# ==================== FILE ROUTES ====================

@files_bp.route('/')
@login_required
def list_files():
    """List all files accessible to the user."""
    from app.repositories import FileRepository
    file_repo = FileRepository()
    
    page = request.args.get('page', 1, type=int)
    pagination = file_repo.get_files_for_user(current_user, page=page, per_page=Config.FILES_PER_PAGE)
    
    return render_template('files/list.html', pagination=pagination)


@files_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_file():
    """Handle file upload with metadata, tags, and role-based access."""
    if request.method == 'POST':
        file = request.files.get('file')
        description = request.form.get('description', '')
        project_id = request.form.get('project_id', type=int)
        tag_names = request.form.getlist('tags')
        allowed_role_ids = request.form.getlist('allowed_roles', type=int)
        
        # Initialize upload service
        upload_service = FileUploadService(Config.UPLOAD_FOLDER, Config.ALLOWED_EXTENSIONS)
        
        file_instance, error = upload_service.upload_file(
            file_storage=file,
            uploaded_by_user=current_user,
            project_id=project_id,
            description=description,
            tag_names=tag_names if tag_names else None,
            allowed_role_ids=allowed_role_ids if allowed_role_ids else None
        )
        
        if file_instance:
            flash('فایل با موفقیت آپلود شد.', 'success')
            return redirect(url_for('files.view_file', file_id=file_instance.id))
        else:
            flash(f'خطا در آپلود فایل: {error}', 'danger')
    
    # GET request - show upload form
    projects = project_service.get_all_projects()
    tags = tag_service.get_all_tags()
    roles = Role.query.filter_by(is_admin=False).all()
    
    return render_template('files/upload.html', 
                         projects=projects, 
                         tags=tags, 
                         roles=roles)


@files_bp.route('/<int:file_id>')
@login_required
def view_file(file_id):
    """View file details."""
    from app.repositories import FileRepository
    file_repo = FileRepository()
    
    file = file_repo.get_by_id(file_id)
    if not file:
        flash('فایل یافت نشد.', 'danger')
        return redirect(url_for('files.list_files'))
    
    # Check access permission
    if not current_user.can_access_file(file):
        flash('شما دسترسی به این فایل را ندارید.', 'warning')
        return redirect(url_for('files.list_files'))
    
    return render_template('files/view.html', file=file)


@files_bp.route('/<int:file_id>/download')
@login_required
def download_file(file_id):
    """Download a file."""
    from app.repositories import FileRepository
    file_repo = FileRepository()
    
    file = file_repo.get_by_id(file_id)
    if not file:
        flash('فایل یافت نشد.', 'danger')
        return redirect(url_for('files.list_files'))
    
    # Check access permission
    if not current_user.can_access_file(file):
        flash('شما دسترسی به این فایل را ندارید.', 'warning')
        return redirect(url_for('files.list_files'))
    
    # Increment download count
    file_repo.increment_download_count(file)
    
    # Send file
    directory = os.path.dirname(file.file_path)
    filename = os.path.basename(file.file_path)
    return send_from_directory(directory, filename, 
                              as_attachment=True, 
                              download_name=file.original_filename)


@files_bp.route('/<int:file_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_file(file_id):
    """Edit file metadata, tags, and permissions."""
    from app.repositories import FileRepository
    file_repo = FileRepository()
    
    file = file_repo.get_by_id(file_id)
    if not file:
        flash('فایل یافت نشد.', 'danger')
        return redirect(url_for('files.list_files'))
    
    # Check access permission (admin or uploader)
    if not current_user.role.is_admin and file.uploaded_by != current_user.id:
        flash('شما مجاز به ویرایش این فایل نیستید.', 'warning')
        return redirect(url_for('files.view_file', file_id=file.id))
    
    if request.method == 'POST':
        file.description = request.form.get('description', '')
        file.project_id = request.form.get('project_id', type=int)
        
        # Update tags
        tag_names = request.form.getlist('tags')
        file.tags = []
        if tag_names:
            tag_repo = TagRepository()
            for tag_name in tag_names:
                tag = tag_repo.get_or_create_tag(tag_name.strip())
                file.tags.append(tag)
        
        # Update allowed roles
        allowed_role_ids = request.form.getlist('allowed_roles', type=int)
        file.allowed_roles = []
        if allowed_role_ids:
            role_repo = RoleRepository()
            for role_id in allowed_role_ids:
                role = role_repo.get_by_id(role_id)
                if role:
                    file.allowed_roles.append(role)
        else:
            # Default: allow all non-admin roles
            default_roles = Role.query.filter_by(is_admin=False).all()
            for role in default_roles:
                file.allowed_roles.append(role)
        
        db.session.commit()
        flash('اطلاعات فایل با موفقیت به‌روزرسانی شد.', 'success')
        return redirect(url_for('files.view_file', file_id=file.id))
    
    # GET request
    projects = project_service.get_all_projects()
    tags = tag_service.get_all_tags()
    roles = Role.query.filter_by(is_admin=False).all()
    
    return render_template('files/edit.html', 
                         file=file, 
                         projects=projects, 
                         tags=tags, 
                         roles=roles)


@files_bp.route('/<int:file_id>/delete', methods=['POST'])
@login_required
def delete_file(file_id):
    """Delete a file."""
    from app.repositories import FileRepository
    import os
    
    file_repo = FileRepository()
    file = file_repo.get_by_id(file_id)
    
    if not file:
        flash('فایل یافت نشد.', 'danger')
        return redirect(url_for('files.list_files'))
    
    # Check permission (admin only)
    if not current_user.role.is_admin:
        flash('فقط مدیران می‌توانند فایل حذف کنند.', 'warning')
        return redirect(url_for('files.list_files'))
    
    # Delete physical file
    try:
        if os.path.exists(file.file_path):
            os.remove(file.file_path)
    except Exception as e:
        flash(f'خطا در حذف فایل فیزیکی: {str(e)}', 'warning')
    
    # Delete database record
    file_repo.delete(file)
    flash('فایل با موفقیت حذف شد.', 'success')
    return redirect(url_for('files.list_files'))


# ==================== USER ROUTES (ADMIN ONLY) ====================

@users_bp.route('/')
@login_required
def list_users():
    """List all users (admin only)."""
    if not current_user.role.is_admin:
        flash('شما دسترسی به این صفحه را ندارید.', 'warning')
        return redirect(url_for('main.dashboard'))
    
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '')
    
    if search_query:
        pagination = user_service.user_repository.search_users(search_query, page, Config.USERS_PER_PAGE)
    else:
        from app.repositories import UserRepository
        user_repo = UserRepository()
        users = user_repo.get_active_users()
        # Simple pagination for now
        per_page = Config.USERS_PER_PAGE
        total = len(users)
        pages = (total + per_page - 1) // per_page
        start = (page - 1) * per_page
        end = start + per_page
        pagination = type('Pagination', (), {
            'items': users[start:end],
            'page': page,
            'per_page': per_page,
            'pages': pages,
            'total': total,
            'has_next': page < pages,
            'has_prev': page > 1,
            'next_num': page + 1 if page < pages else None,
            'prev_num': page - 1 if page > 1 else None
        })()
    
    roles = Role.query.all()
    return render_template('users/list.html', pagination=pagination, roles=roles, search_query=search_query)


@users_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_user():
    """Create a new user (admin only)."""
    if not current_user.role.is_admin:
        flash('شما دسترسی به این صفحه را ندارید.', 'warning')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        role_name = request.form.get('role_name', 'User')
        
        user, error = user_service.create_user(
            username=username,
            email=email,
            password=password,
            full_name=full_name,
            role_name=role_name
        )
        
        if user:
            flash('کاربر با موفقیت ایجاد شد.', 'success')
            return redirect(url_for('users.list_users'))
        else:
            flash(error, 'danger')
    
    roles = Role.query.all()
    return render_template('users/create.html', roles=roles)


@users_bp.route('/<int:user_id>/deactivate', methods=['POST'])
@login_required
def deactivate_user(user_id):
    """Deactivate a user (admin only)."""
    if not current_user.role.is_admin:
        flash('شما دسترسی به این عملیات را ندارید.', 'warning')
        return redirect(url_for('main.dashboard'))
    
    user, error = user_service.deactivate_user(user_id)
    if user:
        flash('حساب کاربر غیرفعال شد.', 'success')
    else:
        flash(error, 'danger')
    
    return redirect(url_for('users.list_users'))


# ==================== PROJECT ROUTES ====================

@projects_bp.route('/')
@login_required
def list_projects():
    """List all projects."""
    projects = project_service.get_all_projects()
    return render_template('projects/list.html', projects=projects)


@projects_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_project():
    """Create a new project."""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        
        project, error = project_service.create_project(name, description)
        if project:
            flash('پروژه با موفقیت ایجاد شد.', 'success')
            return redirect(url_for('projects.list_projects'))
        else:
            flash(error, 'danger')
    
    return render_template('projects/create.html')


# ==================== TAG ROUTES ====================

@tags_bp.route('/')
@login_required
def list_tags():
    """List all tags."""
    tags = tag_service.get_all_tags()
    return render_template('tags/list.html', tags=tags)


# ==================== SEARCH ROUTES ====================

@search_bp.route('/')
@login_required
def advanced_search():
    """Advanced search with multiple filters."""
    # Get search parameters
    filename = request.args.get('filename', '')
    tag_names = request.args.getlist('tags')
    project_name = request.args.get('project', '')
    date_from_str = request.args.get('date_from', '')
    date_to_str = request.args.get('date_to', '')
    
    # Parse dates
    date_from = None
    date_to = None
    if date_from_str:
        try:
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
        except ValueError:
            pass
    if date_to_str:
        try:
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d')
        except ValueError:
            pass
    
    page = request.args.get('page', 1, type=int)
    
    # Perform search if any filter is provided
    results = None
    if any([filename, tag_names, project_name, date_from, date_to]):
        pagination = search_service.advanced_search(
            current_user=current_user,
            filename=filename if filename else None,
            tags=tag_names if tag_names else None,
            project_name=project_name if project_name else None,
            date_from=date_from,
            date_to=date_to,
            page=page,
            per_page=Config.FILES_PER_PAGE
        )
        results = pagination
    
    # Get all projects and tags for filters
    all_projects = project_service.get_all_projects()
    all_tags = tag_service.get_all_tags()
    
    return render_template('search/advanced.html',
                         results=results,
                         all_projects=all_projects,
                         all_tags=all_tags,
                         filename=filename,
                         selected_tags=tag_names,
                         project_name=project_name,
                         date_from=date_from_str,
                         date_to=date_to_str)


@search_bp.route('/ocr')
@login_required
def search_ocr():
    """Search within OCR-extracted text."""
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    
    results = None
    if query:
        pagination = search_service.search_in_ocr(query, current_user, page, Config.FILES_PER_PAGE)
        results = pagination
    
    return render_template('search/ocr.html', results=results, query=query)
