"""
Main application factory following SOLID principles.
Implements Dependency Inversion by creating all dependencies centrally.
"""
import os
from flask import Flask
from app.config import DevelopmentConfig, ProductionConfig


def create_app(config_class=DevelopmentConfig):
    """Application factory for creating the Flask app."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize extensions
    from app.models import db
    db.init_app(app)
    
    # Create tables
    with app.app_context():
        db.create_all()
        
        # Create default roles if they don't exist
        from app.models import Role
        if not Role.query.first():
            admin_role = Role(name='Admin', description='System Administrator', is_admin=True)
            user_role = Role(name='User', description='Regular User', is_admin=False)
            manager_role = Role(name='Manager', description='Project Manager', is_admin=False)
            db.session.add_all([admin_role, user_role, manager_role])
            db.session.commit()
            
            # Create default admin user
            from app.models import User
            admin_user = User(
                username='admin',
                email='admin@dms.local',
                full_name='مدیر سیستم',
                role_id=admin_role.id
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
    
    # Register blueprints
    from app.routes import (
        auth_bp, 
        main_bp, 
        files_bp, 
        users_bp, 
        projects_bp, 
        tags_bp, 
        search_bp,
        init_login_manager
    )
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(tags_bp)
    app.register_blueprint(search_bp)
    
    # Initialize login manager
    init_login_manager(app)
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    return app
