import os, sys
os.chdir('/home/joyo/cms')
sys.path.insert(0, '/home/joyo/cms')

from cms import create_app
app = create_app()

print(f"cache_size: {app.jinja_env.cache_size}")

from cms.theme_system import set_active_theme, get_active_theme, _current_theme

with app.test_request_context('/'):
    # 1. Default
    tpl = app.jinja_env.get_template('public/home.html')
    print(f"Default template: {tpl.filename}")
    
    # 2. Switch to dark-reader
    set_active_theme('dark-reader')
    _current_theme = None
    theme = get_active_theme()
    
    sp = list(app.jinja_loader.searchpath)
    tmpl_dir = os.path.join(theme['dir'], 'templates') if theme.get('dir') else None
    if tmpl_dir and os.path.isdir(tmpl_dir):
        new_sp = [tmpl_dir] + [p for p in sp if p != tmpl_dir]
        app.jinja_loader.searchpath = new_sp
        print(f"Searchpath: {new_sp}")
    
    tpl2 = app.jinja_env.get_template('public/home.html')
    print(f"After switch: {tpl2.filename}")
    
    # Check the source
    loader = app.jinja_loader
    source, filename, uptodate = loader.get_source(app.jinja_env, 'public/home.html')
    print(f"Loader resolution: {filename}")
    print(f"Has style: {'<style>' in source[:500]}")
    
    # 3. Switch back to default
    set_active_theme('default')
    _current_theme = None
    theme2 = get_active_theme()
    
    sp2 = list(app.jinja_loader.searchpath)
    tmpl_dir2 = os.path.join(theme2['dir'], 'templates') if theme2.get('dir') else None
    if tmpl_dir2 and os.path.isdir(tmpl_dir2):
        new_sp2 = [tmpl_dir2] + [p for p in sp2 if p != tmpl_dir2]
        app.jinja_loader.searchpath = new_sp2
    else:
        new_sp2 = [p for p in sp2 if 'themes' not in p]
        app.jinja_loader.searchpath = new_sp2
    
    print(f"\nBack to default")
    print(f"Searchpath: {new_sp2}")
    
    tpl3 = app.jinja_env.get_template('public/home.html')
    print(f"Template: {tpl3.filename}")
    
    source3, filename3, _ = app.jinja_loader.get_source(app.jinja_env, 'public/home.html')
    print(f"Loader resolution: {filename3}")
    print(f"Has style: {'<style>' in source3[:500]}")