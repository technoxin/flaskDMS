from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import uuid
import mimetypes

from config import Config
from models import db, login_manager, User, Role, Project, Tag, File


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    
    # Configure upload folder
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    @login_manager.unauthorized_handler
    def unauthorized():
        return redirect(url_for('login'))
    
    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
    
    # Routes
    @app.route('/')
    @login_required
    def index():
        # Show files user has permission to view
        if current_user.is_admin:
            files = File.query.order_by(File.uploaded_at.desc()).all()
        else:
            files = []
            all_files = File.query.all()
            for file in all_files:
                if current_user.can_view_file(file):
                    files.append(file)
        
        projects = Project.query.all()
        tags = Tag.query.all()
        return render_template('index.html', files=files, projects=projects, tags=tags)
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password):
                login_user(user)
                next_page = request.args.get('next')
                return redirect(next_page or url_for('index'))
            else:
                flash('Invalid username or password', 'error')
        
        return render_template('login.html')
    
    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login'))
    
    @app.route('/users')
    @login_required
    def users():
        if not current_user.is_admin:
            flash('Access denied. Admin only.', 'error')
            return redirect(url_for('index'))
        
        users = User.query.all()
        roles = Role.query.all()
        return render_template('users.html', users=users, roles=roles)
    
    @app.route('/users/add', methods=['POST'])
    @login_required
    def add_user():
        if not current_user.is_admin:
            flash('Access denied. Admin only.', 'error')
            return redirect(url_for('index'))
        
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role_id = request.form.get('role_id')
        is_admin = request.form.get('is_admin') == 'on'
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('users'))
        
        user = User(username=username, email=email, role_id=role_id, is_admin=is_admin)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('User added successfully', 'success')
        return redirect(url_for('users'))
    
    @app.route('/roles')
    @login_required
    def roles():
        if not current_user.is_admin:
            flash('Access denied. Admin only.', 'error')
            return redirect(url_for('index'))
        
        roles = Role.query.all()
        return render_template('roles.html', roles=roles)
    
    @app.route('/roles/add', methods=['POST'])
    @login_required
    def add_role():
        if not current_user.is_admin:
            flash('Access denied. Admin only.', 'error')
            return redirect(url_for('index'))
        
        name = request.form.get('name')
        description = request.form.get('description')
        
        if Role.query.filter_by(name=name).first():
            flash('Role already exists', 'error')
            return redirect(url_for('roles'))
        
        role = Role(name=name, description=description)
        db.session.add(role)
        db.session.commit()
        
        flash('Role added successfully', 'success')
        return redirect(url_for('roles'))
    
    @app.route('/projects')
    @login_required
    def projects():
        projects = Project.query.all()
        return render_template('projects.html', projects=projects)
    
    @app.route('/projects/add', methods=['POST'])
    @login_required
    def add_project():
        name = request.form.get('name')
        description = request.form.get('description')
        
        project = Project(name=name, description=description, created_by=current_user.id)
        db.session.add(project)
        db.session.commit()
        
        flash('Project added successfully', 'success')
        return redirect(url_for('projects'))
    
    @app.route('/tags')
    @login_required
    def tags():
        tags = Tag.query.all()
        return render_template('tags.html', tags=tags)
    
    @app.route('/tags/add', methods=['POST'])
    @login_required
    def add_tag():
        name = request.form.get('name')
        color = request.form.get('color', '#3498db')
        
        if Tag.query.filter_by(name=name).first():
            flash('Tag already exists', 'error')
            return redirect(url_for('tags'))
        
        tag = Tag(name=name, color=color)
        db.session.add(tag)
        db.session.commit()
        
        flash('Tag added successfully', 'success')
        return redirect(url_for('tags'))
    
    @app.route('/upload', methods=['GET', 'POST'])
    @login_required
    def upload_file():
        if request.method == 'POST':
            if 'file' not in request.files:
                flash('No file selected', 'error')
                return redirect(request.url)
            
            file = request.files['file']
            
            if file.filename == '':
                flash('No file selected', 'error')
                return redirect(request.url)
            
            if file and allowed_file(file.filename):
                # Generate unique filename
                original_filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
                
                # Save file
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                
                # Get file size
                file_size = os.path.getsize(file_path)
                
                # Get MIME type
                mime_type, _ = mimetypes.guess_type(original_filename)
                
                # Create database record
                new_file = File(
                    filename=original_filename,
                    stored_filename=unique_filename,
                    file_path=file_path,
                    file_size=file_size,
                    mime_type=mime_type,
                    description=request.form.get('description'),
                    uploader_id=current_user.id,
                    project_id=request.form.get('project_id') or None
                )
                
                db.session.add(new_file)
                db.session.commit()
                
                # Add tags
                tag_ids = request.form.getlist('tags')
                for tag_id in tag_ids:
                    tag = Tag.query.get(int(tag_id))
                    if tag:
                        new_file.tags.append(tag)
                
                # Add role permissions
                role_ids = request.form.getlist('allowed_roles')
                for role_id in role_ids:
                    role = Role.query.get(int(role_id))
                    if role:
                        new_file.allowed_roles.append(role)
                
                db.session.commit()
                
                flash('File uploaded successfully', 'success')
                return redirect(url_for('index'))
            else:
                flash('File type not allowed', 'error')
                return redirect(request.url)
        
        projects = Project.query.all()
        tags = Tag.query.all()
        roles = Role.query.all()
        return render_template('upload.html', projects=projects, tags=tags, roles=roles)
    
    @app.route('/file/<int:file_id>')
    @login_required
    def view_file(file_id):
        file = File.query.get_or_404(file_id)
        
        # Check permission
        if not current_user.can_view_file(file):
            flash('You do not have permission to view this file', 'error')
            return redirect(url_for('index'))
        
        return send_from_directory(app.config['UPLOAD_FOLDER'], file.stored_filename, 
                                  download_name=file.filename)
    
    @app.route('/file/<int:file_id>/details')
    @login_required
    def file_details(file_id):
        file = File.query.get_or_404(file_id)
        
        # Check permission
        if not current_user.can_view_file(file):
            flash('You do not have permission to view this file', 'error')
            return redirect(url_for('index'))
        
        projects = Project.query.all()
        tags = Tag.query.all()
        roles = Role.query.all()
        
        return render_template('file_details.html', file=file, projects=projects, tags=tags, roles=roles)
    
    @app.route('/file/<int:file_id>/edit', methods=['POST'])
    @login_required
    def edit_file(file_id):
        file = File.query.get_or_404(file_id)
        
        # Check permission (admin or uploader)
        if not current_user.is_admin and file.uploader_id != current_user.id:
            flash('You do not have permission to edit this file', 'error')
            return redirect(url_for('index'))
        
        # Update description
        file.description = request.form.get('description')
        
        # Update project
        project_id = request.form.get('project_id')
        file.project_id = int(project_id) if project_id else None
        
        # Update tags
        file.tags = []
        tag_ids = request.form.getlist('tags')
        for tag_id in tag_ids:
            tag = Tag.query.get(int(tag_id))
            if tag:
                file.tags.append(tag)
        
        # Update role permissions
        if current_user.is_admin:
            file.allowed_roles = []
            role_ids = request.form.getlist('allowed_roles')
            for role_id in role_ids:
                role = Role.query.get(int(role_id))
                if role:
                    file.allowed_roles.append(role)
        
        db.session.commit()
        
        flash('File updated successfully', 'success')
        return redirect(url_for('file_details', file_id=file.id))
    
    @app.route('/search')
    @login_required
    def search():
        query = request.args.get('q', '')
        tag_names = request.args.getlist('tags')
        project_name = request.args.get('project', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        
        # Start with base query based on user permissions
        if current_user.is_admin:
            base_query = File.query
        else:
            # Get files user has permission to view
            user_files = []
            all_files = File.query.all()
            for f in all_files:
                if current_user.can_view_file(f):
                    user_files.append(f.id)
            base_query = File.query.filter(File.id.in_(user_files)) if user_files else File.query.filter(File.id == -1)
        
        # Apply filters
        if query:
            base_query = base_query.filter(File.filename.like(f'%{query}%'))
        
        if tag_names:
            base_query = base_query.join(File.tags).filter(Tag.name.in_(tag_names))
        
        if project_name:
            base_query = base_query.join(File.project).filter(Project.name.like(f'%{project_name}%'))
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                base_query = base_query.filter(File.uploaded_at >= date_from_obj)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
                base_query = base_query.filter(File.uploaded_at <= date_to_obj)
            except ValueError:
                pass
        
        files = base_query.order_by(File.uploaded_at.desc()).all()
        
        projects = Project.query.all()
        tags = Tag.query.all()
        
        return render_template('search.html', files=files, query=query, 
                             selected_tags=tag_names, project_name=project_name,
                             date_from=date_from, date_to=date_to,
                             projects=projects, tags=tags)
    
    @app.route('/api/files')
    @login_required
    def api_files():
        """API endpoint for getting files (useful for AJAX)"""
        if current_user.is_admin:
            files = File.query.all()
        else:
            files = [f for f in File.query.all() if current_user.can_view_file(f)]
        
        result = []
        for file in files:
            result.append({
                'id': file.id,
                'filename': file.filename,
                'uploaded_at': file.uploaded_at.isoformat(),
                'project': file.project.name if file.project else None,
                'tags': [tag.name for tag in file.tags],
                'uploader': file.uploader.username
            })
        
        return jsonify(result)
    
    # Create tables
    with app.app_context():
        db.create_all()
        
        # Create default admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin_role = Role.query.filter_by(name='Admin').first()
            if not admin_role:
                admin_role = Role(name='Admin', description='System Administrator')
                db.session.add(admin_role)
                db.session.commit()
            
            admin = User(username='admin', email='admin@example.com', 
                        role_id=admin_role.id, is_admin=True)
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Default admin user created: admin / admin123")
        
        # Create default roles if not exist
        if not Role.query.filter_by(name='User').first():
            user_role = Role(name='User', description='Regular User')
            db.session.add(user_role)
            db.session.commit()
        
        if not Role.query.filter_by(name='Manager').first():
            manager_role = Role(name='Manager', description='Project Manager')
            db.session.add(manager_role)
            db.session.commit()
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
