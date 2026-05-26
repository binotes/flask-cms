import os as _os
from flask import Flask
from config import Config


def create_app(config_class=Config):
    app = Flask(__name__,
                static_folder='../static',
                static_url_path='/static')
    app.config.from_object(config_class)

    # Disable Jinja2 template cache so theme switching takes effect immediately
    app.jinja_env.cache_size = 0

    # Initialize extensions + theme + plugins
    from cms.extensions import db, login_manager, csrf, migrate
    from cms.hooks import do_action
    from cms.theme_system import theme_static_url, get_active_theme

    # Dynamic theme template switching (runtime, no restart needed)
    @app.before_request
    def apply_theme_templates():
        from cms.theme_system import get_active_theme
        theme = get_active_theme()
        sp = list(app.jinja_loader.searchpath)
        tmpl_dir = _os.path.join(theme['dir'], 'templates') if theme and theme.get('dir') else None
        if tmpl_dir and _os.path.isdir(tmpl_dir):
            new_sp = [tmpl_dir] + [p for p in sp if p != tmpl_dir]
            app.jinja_loader.searchpath = new_sp
        else:
            app.jinja_loader.searchpath = [p for p in sp if 'themes' not in p]

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    from cms.public.views import public_bp
    from cms.auth.views import auth_bp
    from cms.admin.views import admin_bp
    from cms.api.views import api_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')

    # Exempt API from CSRF
    csrf.exempt(api_bp)

    # Context processors
    @app.context_processor
    def inject_settings():
        from cms.models import Setting, Category, Tag
        from cms.theme_system import get_active_theme, theme_static_url

        settings = {
            'site_name': Setting.get('site_name', 'My CMS'),
            'site_description': Setting.get('site_description', 'A Flask CMS'),
            'site_logo': Setting.get('site_logo', ''),
        }
        return {
            'settings': settings,
            'categories': Category.query.order_by(Category.name).all(),
            'tags': Tag.query.order_by(Tag.name).all(),
            'recent_posts': None,
            'active_theme': get_active_theme(),
            'theme_static_url': theme_static_url,
        }

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template('public/404.html'), 404

    # Media serving
    import os
    from flask import send_from_directory

    @app.route('/media/<path:filename>')
    def serve_media(filename):
        upload_dir = os.path.join(app.root_path, '..', 'media')
        return send_from_directory(os.path.abspath(upload_dir), filename)

    # Theme static files serving
    @app.route('/theme-static/<theme_name>/<path:filename>')
    def serve_theme_static(theme_name, filename):
        from cms.theme_system import get_themes_dir
        theme_dir = os.path.join(get_themes_dir(), theme_name, 'static')
        if os.path.isdir(theme_dir):
            return send_from_directory(theme_dir, filename)
        return '', 404

    # Create tables
    with app.app_context():
        from cms.models import User, Post, Page, Category, Tag, Comment, Media, Setting
        db.create_all()
        # Create default admin if not exists
        if not User.query.filter_by(role='admin').first():
            admin = User(
                username='admin',
                email='admin@example.com',
                role='admin',
                display_name='Administrator'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            # Default settings
            defaults = {
                'site_name': 'My CMS',
                'site_description': 'A powerful Flask CMS',
                'posts_per_page': '10',
                'default_category': '1',
                'comment_moderation': '1',
                'site_logo': '',
            }
            for k, v in defaults.items():
                Setting.set(k, v)
            db.session.commit()
            print('[CMS] Default admin created: admin / admin123')

    # Load active plugins from settings
    with app.app_context():
        from cms.plugin_manager import load_all_active
        loaded = load_all_active()
        if loaded:
            print(f'[CMS] Plugins loaded: {", ".join(loaded)}')

    # Fire app_started hook so plugins can react
    with app.app_context():
        do_action('app_started')

    return app