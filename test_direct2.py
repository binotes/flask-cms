import os, sys, json
os.chdir('/home/joyo/cms')
sys.path.insert(0, '/home/joyo/cms')

from cms import create_app
app = create_app()

with app.test_request_context('/'):
    from flask import render_template
    from cms.theme_system import get_active_theme, set_active_theme, _current_theme
    
    print("=== BEFORE any theme set ===")
    theme = get_active_theme()
    print(f"  get_active_theme() = {theme.get('name')}")
    print(f"  _current_theme = {_current_theme.get('name') if _current_theme else 'None'}")
    print(f"  searchpath = {app.jinja_loader.searchpath}")
    
    # Render a template
    loader = app.jinja_loader
    src, fname, _ = loader.get_source(app.jinja_env, 'public/home.html')
    print(f"  loader gets: {fname}")
    
    # Now set theme and simulate before_request
    set_active_theme('dark-reader')
    _current_theme = None
    
    print("\n=== AFTER set_active_theme('dark-reader') ===")
    theme = get_active_theme()
    print(f"  get_active_theme() = {theme.get('name')}")
    print(f"  dir = {theme.get('dir')}")
    
    tmpl_dir = os.path.join(theme['dir'], 'templates') if theme.get('dir') else None
    sp = list(app.jinja_loader.searchpath)
    new_sp = [tmpl_dir] + [p for p in sp if p != tmpl_dir]
    app.jinja_loader.searchpath = new_sp
    print(f"  searchpath = {app.jinja_loader.searchpath}")
    
    src2, fname2, _ = app.jinja_loader.get_source(app.jinja_env, 'public/home.html')
    print(f"  loader gets: {fname2}")
    
    # Compare with DispatchingJinjaLoader
    dj = app.jinja_env.loader
    src3, fname3, _ = dj.get_source(app.jinja_env, 'public/home.html')
    print(f"  DispatchingJinjaLoader gets: {fname3}")
    
    # Get template
    tpl = app.jinja_env.get_template('public/home.html')
    print(f"  environment.get_template() filename: {tpl.filename}")
    print(f"  environment.cache_size: {app.jinja_env.cache_size}")
    
    # ALSO check: does _current_theme change between calls?
    _current_theme2 = get_active_theme()
    print(f"\n  Second call _current_theme: {_current_theme2.get('name')}")