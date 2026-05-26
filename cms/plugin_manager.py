"""
Plugin Manager — 插件发现、加载、管理

插件目录结构:
    cms/plugins/
        hello-world/
            plugin.json    # {name, version, description, author, hooks}
            __init__.py    # register() 函数，注册 hooks
"""

import os
import json
import importlib.util
from pathlib import Path


_plugins = {}  # name -> plugin_info


def get_plugins_dir():
    """返回插件目录路径"""
    return os.path.join(os.path.dirname(__file__), 'plugins')


def discover_plugins():
    """扫描插件目录，返回所有可用插件列表"""
    plugins_dir = get_plugins_dir()
    if not os.path.exists(plugins_dir):
        return []
    result = []
    for entry in sorted(os.listdir(plugins_dir)):
        plugin_dir = os.path.join(plugins_dir, entry)
        if not os.path.isdir(plugin_dir):
            continue
        info = _load_plugin_info(plugin_dir)
        if info:
            result.append(info)
    return result


def _load_plugin_info(plugin_dir):
    """加载插件的 plugin.json"""
    json_path = os.path.join(plugin_dir, 'plugin.json')
    if not os.path.isfile(json_path):
        return None
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            info = json.load(f)
        info['dir'] = plugin_dir
        info['name'] = info.get('name', os.path.basename(plugin_dir))
        info.setdefault('version', '0.1')
        info.setdefault('description', '')
        info.setdefault('author', '')
        info.setdefault('active', False)
        return info
    except (json.JSONDecodeError, IOError):
        return None


def load_plugin(name):
    """加载并激活一个插件（调用其 register() 函数）"""
    from cms.hooks import add_action

    plugin_dir = os.path.join(get_plugins_dir(), name)
    init_path = os.path.join(plugin_dir, '__init__.py')
    if not os.path.isfile(init_path):
        return False

    spec = importlib.util.spec_from_file_location(f'cms.plugins.{name}', init_path)
    if spec is None or spec.loader is None:
        return False

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if hasattr(module, 'register'):
        try:
            module.register()
            _plugins[name] = {'module': module, 'info': _load_plugin_info(plugin_dir)}
            return True
        except Exception:
            return False
    return False


def unload_plugin(name):
    """卸载插件"""
    if name in _plugins:
        del _plugins[name]
        return True
    return False


def get_active_plugins():
    """获取已激活的插件列表"""
    return list(_plugins.keys())


def is_active(name):
    return name in _plugins


def load_all_active():
    """从 Setting 中读取已激活插件列表，全部加载"""
    from cms.models import Setting
    raw = Setting.get('active_plugins', '[]')
    try:
        names = json.loads(raw)
    except json.JSONDecodeError:
        names = []
    loaded = []
    for name in names:
        if load_plugin(name):
            loaded.append(name)
    return loaded


def save_active_plugins(names):
    """保存激活的插件列表到 Setting"""
    from cms.models import Setting
    Setting.set('active_plugins', json.dumps(names))
