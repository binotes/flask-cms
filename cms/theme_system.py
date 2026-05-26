"""
Theme System — 主题发现、模板覆盖、主题切换

主题目录结构:
    cms/themes/
        my-theme/
            theme.json   # {name, version, author, description, screenshot}
            templates/   # 覆盖 cms/templates/ 中同名文件
            static/      # 主题静态文件（CSS/JS等）
"""

import os
import json
from pathlib import Path


_current_theme = None


def get_themes_dir():
    return os.path.join(os.path.dirname(__file__), 'themes')


def discover_themes():
    """扫描 themes 目录，返回所有可用主题"""
    themes_dir = get_themes_dir()
    if not os.path.exists(themes_dir):
        return []
    result = []
    for entry in sorted(os.listdir(themes_dir)):
        theme_dir = os.path.join(themes_dir, entry)
        if not os.path.isdir(theme_dir):
            continue
        json_path = os.path.join(theme_dir, 'theme.json')
        if not os.path.isfile(json_path):
            continue
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                info = json.load(f)
            info['dir'] = theme_dir
            info['name'] = info.get('name', entry)
            info.setdefault('version', '1.0')
            info.setdefault('description', '')
            info.setdefault('author', '')
            result.append(info)
        except (json.JSONDecodeError, IOError):
            continue
    return result


def get_active_theme():
    global _current_theme
    if _current_theme:
        return _current_theme

    try:
        from cms.models import Setting
        theme_name = Setting.get('active_theme', 'default')
    except RuntimeError:
        theme_name = 'default'
    if theme_name == 'default':
        _current_theme = {'name': 'default', 'dir': None, 'version': '1.0'}
        return _current_theme

    for t in discover_themes():
        if t['name'] == theme_name:
            _current_theme = t
            return t
    _current_theme = {'name': 'default', 'dir': None, 'version': '1.0'}
    return _current_theme


def set_active_theme(name):
    """切换主题"""
    from cms.models import Setting
    Setting.set('active_theme', name)
    global _current_theme
    _current_theme = None


def theme_template_dirs():
    """返回主题模板目录（如果有的话）"""
    theme = get_active_theme()
    if theme and theme.get('dir'):
        tmpl_dir = os.path.join(theme['dir'], 'templates')
        if os.path.isdir(tmpl_dir):
            return [tmpl_dir]
    return []


def theme_static_dir():
    """返回主题的 static 目录路径"""
    theme = get_active_theme()
    if theme and theme.get('dir'):
        static_dir = os.path.join(theme['dir'], 'static')
        if os.path.isdir(static_dir):
            return static_dir
    return None


def theme_static_url():
    """返回主题静态文件的 URL 前缀"""
    theme = get_active_theme()
    if theme:
        return f'/theme-static/{theme["name"]}/'
    return '/static/'
