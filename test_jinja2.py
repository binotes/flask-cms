import os, sys
os.chdir('/home/joyo/cms')
sys.path.insert(0, '/home/joyo/cms')

from cms import create_app
app = create_app()

print(f"app.jinja_env.loader = {app.jinja_env.loader}")
print(f"type = {type(app.jinja_env.loader)}")
print(f"app.jinja_loader = {app.jinja_loader}")
print(f"type = {type(app.jinja_loader)}")

from cms.theme_system import set_active_theme, get_active_theme, _current_theme

with app.test_request_context('/'):
    set_active_theme('dark-reader')
    _current_theme = None
    theme = get_active_theme()
    
    sp = list(app.jinja_loader.searchpath)
    tmpl_dir = os.path.join(theme['dir'], 'templates') if theme.get('dir') else None
    if tmpl_dir and os.path.isdir(tmpl_dir):
        new_sp = [tmpl_dir] + [p for p in sp if p != tmpl_dir]
        app.jinja_loader.searchpath = new_sp
        print(f"\nsearchpath set to: {new_sp}")
    
    # Check that app.jinja_loader.searchpath was actually updated
    print(f"app.jinja_loader.searchpath = {app.jinja_loader.searchpath}")
    
    # Check using the env's loader (which is DispatchingJinjaLoader)
    env_loader = app.jinja_env.loader
    print(f"\nDispatchingJinjaLoader.get_source:")
    try:
        src, fname, up = env_loader.get_source(app.jinja_env, 'public/home.html')
        print(f"  filename via DispatchingJinjaLoader: {fname}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Now check app.jinja_loader directly
    print(f"\nFileSystemLoader.get_source:")
    try:
        src2, fname2, up2 = app.jinja_loader.get_source(app.jinja_env, 'public/home.html')
        print(f"  filename via FileSystemLoader: {fname2}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Check get_template
    tpl = app.jinja_env.get_template('public/home.html')
    print(f"\nget_template filename: {tpl.filename}")
    
    # The key question: is get_template using the same loader?
    print(f"\napp.jinja_env.loader is env_loader: {app.jinja_env.loader is env_loader}")
    print(f"app.jinja_loader is the same: {app.jinja_loader is app.jinja_loader}")