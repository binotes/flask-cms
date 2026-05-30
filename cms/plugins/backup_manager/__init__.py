"""
Backup Manager Plugin — 数据备份管理插件

功能：
    - 一键备份：数据库 + 媒体文件 + 配置 + 主题 + 插件
    - 备份列表：查看历史备份，支持下载、删除、恢复
    - 定时备份：支持每日/每周自动备份
    - 备份恢复：从备份文件恢复系统

目录结构：
    cms/plugins/backup-manager/
        __init__.py
        plugin.json
        templates/
            admin/
                backup.html          # 备份管理页面
                _backup_list.html    # 备份列表组件
        backups/                     # 备份文件存储目录（运行时创建）
"""

import os
import json
import shutil
import zipfile
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# ─── 插件配置 ──────────────────────────────────────────────────

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUPS_DIR = os.path.join(PLUGIN_DIR, 'backups')

# CMS 根目录（相对于插件目录）
CMS_ROOT = os.path.dirname(os.path.dirname(PLUGIN_DIR))
PROJECT_ROOT = os.path.dirname(CMS_ROOT)


def get_app():
    """获取当前 Flask app 实例"""
    from flask import current_app
    return current_app


def get_setting(key, default=None):
    """获取插件设置"""
    from cms.models import Setting
    val = Setting.get(f'backup_{key}', None)
    if val is not None:
        try:
            return json.loads(val)
        except:
            return val
    return default


def set_setting(key, value):
    """保存插件设置"""
    from cms.models import Setting
    if isinstance(value, (dict, list)):
        Setting.set(f'backup_{key}', json.dumps(value))
    else:
        Setting.set(f'backup_{key}', str(value))


def ensure_backups_dir():
    """确保备份目录存在"""
    os.makedirs(BACKUPS_DIR, exist_ok=True)
    return BACKUPS_DIR


# ─── 备份核心功能 ──────────────────────────────────────────────

def get_database_path():
    """获取数据库文件路径"""
    app = get_app()
    # 支持多种数据库类型
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    
    if db_uri.startswith('sqlite:'):
        # SQLite: sqlite:///path/to/db.db 或 sqlite:////absolute/path
        db_path = db_uri.replace('sqlite:///', '').replace('sqlite://', '')
        if not os.path.isabs(db_path):
            db_path = os.path.join(PROJECT_ROOT, db_path)
        return os.path.abspath(db_path)
    
    # 其他数据库（MySQL/PostgreSQL）需要导出 SQL
    return None


def backup_database(timestamp):
    """备份数据库"""
    db_path = get_database_path()
    
    if db_path and os.path.exists(db_path):
        # SQLite 直接复制
        backup_file = os.path.join(BACKUPS_DIR, f'database_{timestamp}.db')
        shutil.copy2(db_path, backup_file)
        return backup_file
    else:
        # 其他数据库：导出 SQL
        from cms.extensions import db
        backup_file = os.path.join(BACKUPS_DIR, f'database_{timestamp}.sql')
        
        # 使用 Flask-Migrate 导出
        try:
            from flask_migrate import export
            # 简化版：直接 dump 数据
            with app.app_context():
                from cms.models import User, Post, Page, Category, Tag, Comment, Media, Setting
                # 导出为 JSON（更通用）
                data = {
                    'users': [u.to_dict() if hasattr(u, 'to_dict') else {'id': u.id, 'username': u.username, 'email': u.email, 'role': u.role} for u in User.query.all()],
                    'categories': [c.to_dict() if hasattr(c, 'to_dict') else {'id': c.id, 'name': c.name, 'slug': c.slug} for c in Category.query.all()],
                    'tags': [t.to_dict() if hasattr(t, 'to_dict') else {'id': t.id, 'name': t.name, 'slug': t.slug} for t in Tag.query.all()],
                    'settings': [s.to_dict() if hasattr(s, 'to_dict') else {'key': s.key, 'value': s.value} for s in Setting.query.all()],
                }
                with open(backup_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                return backup_file
        except Exception as e:
            return None


def backup_media(timestamp):
    """备份媒体文件"""
    media_dir = os.path.join(PROJECT_ROOT, 'media')
    if not os.path.exists(media_dir):
        return None
    
    media_zip = os.path.join(BACKUPS_DIR, f'media_{timestamp}.zip')
    with zipfile.ZipFile(media_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(media_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, PROJECT_ROOT)
                zf.write(file_path, arcname)
    return media_zip


def backup_config(timestamp):
    """备份配置文件"""
    config_files = []
    
    # 配置文件
    config_path = os.path.join(PROJECT_ROOT, 'config.py')
    if os.path.exists(config_path):
        config_files.append(('config/config.py', config_path))
    
    # .env 文件
    env_path = os.path.join(PROJECT_ROOT, '.env')
    if os.path.exists(env_path):
        config_files.append(('config/.env', env_path))
    
    if not config_files:
        return None
    
    config_zip = os.path.join(BACKUPS_DIR, f'config_{timestamp}.zip')
    with zipfile.ZipFile(config_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for arcname, file_path in config_files:
            zf.write(file_path, arcname)
    return config_zip


def backup_themes(timestamp):
    """备份主题文件"""
    themes_dir = os.path.join(CMS_ROOT, 'themes')
    if not os.path.exists(themes_dir):
        return None
    
    themes_zip = os.path.join(BACKUPS_DIR, f'themes_{timestamp}.zip')
    with zipfile.ZipFile(themes_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(themes_dir):
            for file in files:
                if file.endswith('.pyc') or '__pycache__' in root:
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, PROJECT_ROOT)
                zf.write(file_path, arcname)
    return themes_zip


def backup_plugins(timestamp):
    """备份插件文件"""
    plugins_dir = os.path.join(CMS_ROOT, 'plugins')
    if not os.path.exists(plugins_dir):
        return None

    # 排除目录和文件
    EXCLUDE_DIRS = {
        'backups', '__pycache__', 'node_modules', '.git', '.svn',
        '__MACOSX', '.idea', '.vscode', 'venv', '.venv', 'env',
        '.pytest_cache', '.mypy_cache', '.ruff_cache',
    }
    EXCLUDE_FILES = {
        '.DS_Store', 'Thumbs.db', '*.pyc', '*.pyo', '*.log',
    }

    plugins_zip = os.path.join(BACKUPS_DIR, f'plugins_{timestamp}.zip')
    with zipfile.ZipFile(plugins_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(plugins_dir):
            # 过滤排除目录（原地修改 dirs 防止继续遍历）
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            # 跳过 __pycache__ 目录
            if '__pycache__' in root:
                continue
            for file in files:
                # 跳过排除文件
                if file.endswith('.pyc') or file.endswith('.pyo'):
                    continue
                if file in EXCLUDE_FILES:
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, PROJECT_ROOT)
                zf.write(file_path, arcname)
    return plugins_zip


def create_full_backup():
    """创建完整备份"""
    ensure_backups_dir()
    
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    backup_info = {
        'timestamp': timestamp,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'files': {},
        'size': 0,
        'status': 'creating',
    }
    
    # 备份信息文件
    info_file = os.path.join(BACKUPS_DIR, f'backup_{timestamp}.json')
    
    try:
        # 1. 备份数据库
        db_file = backup_database(timestamp)
        if db_file:
            backup_info['files']['database'] = os.path.basename(db_file)
            backup_info['size'] += os.path.getsize(db_file)
        
        # 2. 备份媒体文件
        media_file = backup_media(timestamp)
        if media_file:
            backup_info['files']['media'] = os.path.basename(media_file)
            backup_info['size'] += os.path.getsize(media_file)
        
        # 3. 备份配置
        config_file = backup_config(timestamp)
        if config_file:
            backup_info['files']['config'] = os.path.basename(config_file)
            backup_info['size'] += os.path.getsize(config_file)
        
        # 4. 备份主题
        themes_file = backup_themes(timestamp)
        if themes_file:
            backup_info['files']['themes'] = os.path.basename(themes_file)
            backup_info['size'] += os.path.getsize(themes_file)
        
        # 5. 备份插件
        plugins_file = backup_plugins(timestamp)
        if plugins_file:
            backup_info['files']['plugins'] = os.path.basename(plugins_file)
            backup_info['size'] += os.path.getsize(plugins_file)
        
        backup_info['status'] = 'success'
        
    except Exception as e:
        backup_info['status'] = f'error: {str(e)}'
    
    # 保存备份信息
    with open(info_file, 'w', encoding='utf-8') as f:
        json.dump(backup_info, f, ensure_ascii=False, indent=2)
    
    backup_info['info_file'] = info_file
    return backup_info


def list_backups():
    """列出所有备份"""
    ensure_backups_dir()
    backups = []
    
    for info_file in sorted(Path(BACKUPS_DIR).glob('backup_*.json'), reverse=True):
        try:
            with open(info_file, 'r', encoding='utf-8') as f:
                info = json.load(f)
            info['id'] = info['timestamp']
            backups.append(info)
        except:
            continue
    
    return backups


def get_backup(backup_id):
    """获取单个备份信息"""
    info_file = os.path.join(BACKUPS_DIR, f'backup_{backup_id}.json')
    if os.path.exists(info_file):
        with open(info_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def delete_backup(backup_id):
    """删除备份"""
    info = get_backup(backup_id)
    if not info:
        return False
    
    # 删除备份文件
    for file_type, filename in info.get('files', {}).items():
        file_path = os.path.join(BACKUPS_DIR, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
    
    # 删除信息文件
    info_file = os.path.join(BACKUPS_DIR, f'backup_{backup_id}.json')
    if os.path.exists(info_file):
        os.remove(info_file)
    
    return True


def restore_backup(backup_id):
    """恢复备份（仅支持 SQLite 数据库）"""
    info = get_backup(backup_id)
    if not info or info.get('status') != 'success':
        return False, '备份无效或创建失败'
    
    db_file = info.get('files', {}).get('database')
    if not db_file:
        return False, '备份中不包含数据库'
    
    db_path = get_database_path()
    if not db_path:
        return False, '无法确定数据库路径'
    
    # 备份当前数据库
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    backup_current = db_path + f'.pre_restore_{timestamp}.bak'
    shutil.copy2(db_path, backup_current)
    
    # 恢复数据库
    src = os.path.join(BACKUPS_DIR, db_file)
    try:
        shutil.copy2(src, db_path)
        return True, f'恢复成功，原数据库已备份为: {backup_current}'
    except Exception as e:
        return False, f'恢复失败: {str(e)}'


def cleanup_old_backups(max_count=10):
    """清理旧备份，保留最新 N 个"""
    backups = list_backups()
    if len(backups) <= max_count:
        return 0
    
    deleted = 0
    for backup in backups[max_count:]:
        if delete_backup(backup['id']):
            deleted += 1
    return deleted


# ─── Flask 路由注册 ────────────────────────────────────────────

def register():
    """注册插件：添加路由、上下文处理器、管理菜单"""
    from flask import current_app, render_template, redirect, url_for, flash, request, send_file, jsonify
    from cms.extensions import db
    from cms.hooks import do_action
    from flask_login import current_user
    import functools
    
    # ─── 权限检查装饰器 ───
    def admin_required(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            from flask_login import current_user
            if not current_user.is_authenticated:
                flash('请先登录', 'warning')
                return redirect('/admin/login')
            if not current_user.is_admin():
                flash('需要管理员权限', 'error')
                return redirect('/')
            return f(*args, **kwargs)
        return wrapped
    
    # ─── 路由处理函数 ───
    
    def _backup_index():
        """备份管理主页"""
        backups = list_backups()
        max_backups = get_setting('max_backups', 10)
        auto_enabled = get_setting('auto_backup_enabled', False)
        auto_schedule = get_setting('auto_backup_schedule', 'daily')
        auto_time = get_setting('auto_backup_time', '03:00')
        
        total_size = 0
        for backup in backups:
            for filename in backup.get('files', {}).values():
                fp = os.path.join(BACKUPS_DIR, filename)
                if os.path.exists(fp):
                    total_size += os.path.getsize(fp)
        
        return render_template('backup/backup.html',
                             backups=backups,
                             total_size=total_size,
                             max_backups=max_backups,
                             auto_enabled=auto_enabled,
                             auto_schedule=auto_schedule,
                             auto_time=auto_time)
    
    def _backup_create():
        """创建新备份"""
        backup_info = create_full_backup()
        
        if backup_info['status'] == 'success':
            flash(f'备份创建成功: {backup_info["timestamp"]}', 'success')
            max_backups = get_setting('max_backups', 10)
            cleanup_old_backups(max_backups)
        else:
            flash(f'备份创建失败: {backup_info["status"]}', 'error')
        
        return redirect(url_for('backup.index'))
    
    def _backup_delete(backup_id):
        """删除备份"""
        if delete_backup(backup_id):
            flash(f'备份 {backup_id} 已删除', 'success')
        else:
            flash('删除失败', 'error')
        return redirect(url_for('backup.index'))
    
    def _backup_restore(backup_id):
        """恢复备份"""
        success, message = restore_backup(backup_id)
        if success:
            flash(message, 'success')
            flash('请重启应用以完全恢复数据', 'warning')
        else:
            flash(message, 'error')
        return redirect(url_for('backup.index'))
    
    def _backup_download(backup_id, file_type):
        """下载备份文件"""
        info = get_backup(backup_id)
        if not info:
            flash('备份不存在', 'error')
            return redirect(url_for('backup.index'))
        
        filename = info.get('files', {}).get(file_type)
        if not filename:
            flash('文件不存在', 'error')
            return redirect(url_for('backup.index'))
        
        file_path = os.path.join(BACKUPS_DIR, filename)
        if not os.path.exists(file_path):
            flash('文件不存在', 'error')
            return redirect(url_for('backup.index'))
        
        return send_file(file_path, as_attachment=True)
    
    def _backup_settings():
        """备份设置"""
        if request.method == 'POST':
            set_setting('max_backups', int(request.form.get('max_backups', 10)))
            set_setting('auto_backup_enabled', request.form.get('auto_backup_enabled') == 'on')
            set_setting('auto_backup_schedule', request.form.get('auto_backup_schedule', 'daily'))
            set_setting('auto_backup_time', request.form.get('auto_backup_time', '03:00'))
            flash('设置已保存', 'success')
            return redirect(url_for('backup.settings'))
        
        return render_template('backup/settings.html',
                             max_backups=get_setting('max_backups', 10),
                             auto_enabled=get_setting('auto_backup_enabled', False),
                             auto_schedule=get_setting('auto_backup_schedule', 'daily'),
                             auto_time=get_setting('auto_backup_time', '03:00'))
    
    # ─── 注册路由 ───
    prefix = '/admin/backup'
    # 检查端点是否已存在，避免重复注册
    existing_endpoints = set(r.endpoint for r in current_app.url_map.iter_rules())
    
    if 'backup.index' not in existing_endpoints:
        current_app.add_url_rule(f'{prefix}/', 'backup.index', _backup_index)
    if 'backup.create' not in existing_endpoints:
        current_app.add_url_rule(f'{prefix}/create', 'backup.create', _backup_create, methods=['POST'])
    if 'backup.delete' not in existing_endpoints:
        current_app.add_url_rule(f'{prefix}/delete/<backup_id>', 'backup.delete', _backup_delete, methods=['POST'])
    if 'backup.restore' not in existing_endpoints:
        current_app.add_url_rule(f'{prefix}/restore/<backup_id>', 'backup.restore', _backup_restore, methods=['POST'])
    if 'backup.download' not in existing_endpoints:
        current_app.add_url_rule(f'{prefix}/download/<backup_id>/<file_type>', 'backup.download', _backup_download)
    if 'backup.settings' not in existing_endpoints:
        current_app.add_url_rule(f'{prefix}/settings', 'backup.settings', _backup_settings, methods=['GET', 'POST'])
    
    # ─── 注册 admin 菜单项 ───
    def render_backup_menu():
        return {'href': '/admin/backup/', 'label': '数据备份', 'icon': 'fa-database', 'order': 50}
    do_action('admin_menu_item', 'backup_manager', render_backup_menu)

    # ─── 注册内嵌模板 ───
    register_templates(current_app)
    
    # ─── 注册 dashboard widget ───
    def render_backup_widget():
        backups = list_backups()
        latest = backups[0] if backups else None
        from flask import render_template_string
        widget_tpl = '''<div class="card mb-3"><div class="card-header"><h5><i class="fa fa-database"></i> 备份状态</h5></div><div class="card-body"><p class="mb-1">总备份数: <strong>{{ count }}</strong></p>{% if latest %}<p class="mb-0">最近备份: <strong>{{ latest }}</strong></p>{% endif %}</div></div>'''
        return render_template_string(widget_tpl, count=len(backups), latest=latest.created_at[:19] if latest else None)
    do_action('admin_dashboard_widget', 'backup_manager', render_backup_widget)
    
    print('[Backup Manager] Plugin registered')


# ─── 模板 ──────────────────────────────────────────────────────

# 内嵌模板（避免文件依赖问题）

ADMIN_TEMPLATE = '''
{% extends "admin/base.html" %}
{% block title %}数据备份{% endblock %}
{% block content %}
<div class="card">
    <div class="card-header">
        <h2><i class="fa fa-database"></i> 数据备份管理</h2>
    </div>
    <div class="card-body">
        <!-- 操作按钮 -->
        <div class="mb-4">
            <form method="POST" action="{{ url_for('backup.create') }}" style="display:inline;">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
                <button type="submit" class="btn btn-primary">
                    <i class="fa fa-download"></i> 创建新备份
                </button>
            </form>
            <a href="{{ url_for('backup.settings') }}" class="btn btn-secondary">
                <i class="fa fa-cog"></i> 设置
            </a>
        </div>
        
        <!-- 备份统计 -->
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="stat-box">
                    <h3>{{ backups|length }}</h3>
                    <p>备份数量</p>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-box">
                    <h3>{{ "%.2f"|format(total_size / 1024 / 1024) }} MB</h3>
                    <p>总大小</p>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-box">
                    <h3>{{ max_backups }}</h3>
                    <p>最大保留数</p>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-box">
                    <h3>{% if auto_enabled %}已启用{% else %}未启用{% endif %}</h3>
                    <p>自动备份</p>
                </div>
            </div>
        </div>
        
        <!-- 备份列表 -->
        <table class="table table-hover">
            <thead>
                <tr>
                    <th>时间</th>
                    <th>包含内容</th>
                    <th>大小</th>
                    <th>状态</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>
                {% for backup in backups %}
                <tr>
                    <td>{{ backup.created_at[:19]|replace("T", " ") }}</td>
                    <td>
                        {% for type, file in backup.files.items() %}
                            <span class="badge bg-info">{{ type }}</span>
                        {% endfor %}
                    </td>
                    <td>{{ "%.2f"|format(backup.size / 1024 / 1024) }} MB</td>
                    <td>
                        {% if backup.status == 'success' %}
                            <span class="badge bg-success">成功</span>
                        {% elif backup.status == 'creating' %}
                            <span class="badge bg-warning">创建中</span>
                        {% else %}
                            <span class="badge bg-danger">失败</span>
                        {% endif %}
                    </td>
                    <td>
                        <div class="btn-group btn-group-sm">
                            {% for type, file in backup.files.items() %}
                            <a href="{{ url_for('backup.download', backup_id=backup.id, file_type=type) }}" 
                               class="btn btn-outline-primary" title="下载 {{ type }}">
                                <i class="fa fa-download"></i>
                            </a>
                            {% endfor %}
                            {% if 'database' in backup.files %}
                            <form method="POST" action="{{ url_for('backup.restore', backup_id=backup.id) }}" 
                                  style="display:inline;" onsubmit="return confirm('确定要恢复此备份吗？当前数据将被覆盖！');">
                                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
                                <button type="submit" class="btn btn-outline-warning">
                                    <i class="fa fa-undo"></i>
                                </button>
                            </form>
                            {% endif %}
                            <form method="POST" action="{{ url_for('backup.delete', backup_id=backup.id) }}" 
                                  style="display:inline;" onsubmit="return confirm('确定要删除此备份吗？');">
                                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
                                <button type="submit" class="btn btn-outline-danger">
                                    <i class="fa fa-trash"></i>
                                </button>
                            </form>
                        </div>
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="5" class="text-center text-muted">暂无备份</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
'''

SETTINGS_TEMPLATE = '''
{% extends "admin/base.html" %}
{% block title %}备份设置{% endblock %}
{% block content %}
<div class="card">
    <div class="card-header">
        <h2><i class="fa fa-cog"></i> 备份设置</h2>
    </div>
    <div class="card-body">
        <form method="POST">
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
            <div class="mb-3">
                <label class="form-label">最大保留备份数</label>
                <input type="number" name="max_backups" class="form-control" value="{{ max_backups }}" min="1" max="50">
                <small class="text-muted">超出数量后自动删除最旧的备份</small>
            </div>
            
            <div class="mb-3">
                <label class="form-label">
                    <input type="checkbox" name="auto_backup_enabled" {% if auto_enabled %}checked{% endif %}>
                    启用自动备份
                </label>
            </div>
            
            <div class="mb-3">
                <label class="form-label">备份频率</label>
                <select name="auto_backup_schedule" class="form-select">
                    <option value="daily" {% if auto_schedule == 'daily' %}selected{% endif %}>每日</option>
                    <option value="weekly" {% if auto_schedule == 'weekly' %}selected{% endif %}>每周</option>
                    <option value="monthly" {% if auto_schedule == 'monthly' %}selected{% endif %}>每月</option>
                </select>
            </div>
            
            <div class="mb-3">
                <label class="form-label">备份时间</label>
                <input type="time" name="auto_backup_time" class="form-control" value="{{ auto_time }}">
            </div>
            
            <button type="submit" class="btn btn-primary">保存设置</button>
            <a href="{{ url_for('backup.index') }}" class="btn btn-secondary">返回</a>
        </form>
    </div>
</div>
{% endblock %}
'''

DASHBOARD_WIDGET_TEMPLATE = '''
<div class="card mb-3">
    <div class="card-header">
        <h5><i class="fa fa-database"></i> 备份状态</h5>
    </div>
    <div class="card-body">
        <p class="mb-1">总备份数: <strong>{{ count }}</strong></p>
        {% if latest %}
        <p class="mb-0">最近备份: <strong>{{ latest.created_at[:19]|replace("T", " ") }}</strong></p>
        {% endif %}
    </div>
</div>
'''


def register_templates(app):
    """注册内嵌模板"""
    from flask import render_template_string
    app.add_template_filter(lambda *args, **kwargs: render_template_string(ADMIN_TEMPLATE, *args, **kwargs), 'render_backup_admin')
    app.add_template_filter(lambda *args, **kwargs: render_template_string(SETTINGS_TEMPLATE, *args, **kwargs), 'render_backup_settings')
    app.add_template_filter(lambda *args, **kwargs: render_template_string(DASHBOARD_WIDGET_TEMPLATE, *args, **kwargs), 'render_backup_dashboard_widget')
