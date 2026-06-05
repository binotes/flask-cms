import os as _os
from flask import Flask
from config import Config
import jinja2


class ThemeLoader(jinja2.BaseLoader):
    """Custom Jinja2 loader that dynamically adds active theme's template directory."""

    def __init__(self, app):
        self.app = app

    def get_source(self, environment, template):
        from cms.theme_system import get_active_theme
        theme = get_active_theme()
        base_sp = [_os.path.join(self.app.root_path, 'templates')]
        tmpl_dir = _os.path.join(theme['dir'], 'templates') if theme.get('dir') else None
        if tmpl_dir and _os.path.isdir(tmpl_dir):
            searchpath = [tmpl_dir] + base_sp
        else:
            searchpath = base_sp
        for sp in searchpath:
            filename = _os.path.join(sp, template)
            if _os.path.isfile(filename):
                with open(filename, 'rb') as f:
                    contents = f.read().decode('utf-8')
                mtime = _os.path.getmtime(filename)

                def uptodate():
                    try:
                        return _os.path.getmtime(filename) == mtime
                    except OSError:
                        return False
                return contents, filename, uptodate
        raise jinja2.TemplateNotFound(template)


def create_app(config_class=Config):
    app = Flask(__name__,
                static_folder='../static',
                static_url_path='/static')
    app.config.from_object(config_class)
    
    # Initialize extensions + theme + plugins
    from cms.extensions import db, login_manager, csrf, migrate
    from cms.hooks import do_action
    from cms.theme_system import theme_static_url, get_active_theme

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    # Override the Jinja2 loader AFTER all extensions have been initialized.
    # Extensions (csrf, migrate, etc.) rebuild app.jinja_env during init_app,
    # which would discard any loader we set before them.
    app.jinja_env.loader = ThemeLoader(app)
    # Disable template caching: set cache to None so every render_template
    # forces get_source() to be called, allowing real-time theme switching
    app.jinja_env.cache = None
    app.jinja_env.auto_reload = True

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

    # 注册 Markdown 渲染过滤器
    import markdown as _md
    @app.template_filter('markdown')
    def render_markdown(text):
        if not text:
            return ''
        return _md.markdown(text, extensions=['fenced_code', 'codehilite', 'tables', 'nl2br'])

    @app.template_filter('markdown_excerpt')
    def render_markdown_excerpt(text, length=200):
        if not text:
            return ''
        html = _md.markdown(text, extensions=['fenced_code', 'codehilite', 'tables', 'nl2br'])
        # 去掉 HTML 标签
        import re as _re
        plain = _re.sub(r'<[^>]+>', '', html).strip()
        if len(plain) > length:
            plain = plain[:length] + '...'
        return plain

    # 注入 CSRF token 到所有模板（使用 Flask-WTF 的 generate_csrf）
    @app.context_processor
    def inject_csrf_token():
        from flask_wtf.csrf import generate_csrf
        def _csrf_token():
            return generate_csrf()
        return {'csrf_token': _csrf_token}

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
        from cms.plugin_manager import load_all_active, discover_plugins
        loaded = load_all_active()
        if loaded:
            print(f'[CMS] Plugins loaded: {", ".join(loaded)}')
        # Auto-activate plugins that exist on disk but not yet in DB
        all_discovered = [p['name'] for p in discover_plugins()]
        if all_discovered:
            from cms.models import Setting
            current = Setting.get('active_plugins', '[]')
            import json
            try:
                active_list = json.loads(current)
            except json.JSONDecodeError:
                active_list = []
            changed = False
            for name in all_discovered:
                if name not in active_list:
                    from cms.plugin_manager import load_plugin
                    if load_plugin(name):
                        active_list.append(name)
                        print(f'[CMS] Plugin auto-activated: {name}')
                        changed = True
            if changed and not loaded:
                from cms.plugin_manager import save_active_plugins
                save_active_plugins(active_list)

    # Fire app_started hook so plugins can react
    with app.app_context():
        do_action('app_started')

    return app