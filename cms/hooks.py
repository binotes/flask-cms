"""
CMS Hook/Filter System — WordPress 风格的 Actions 和 Filters

用法:
    from cms.hooks import add_action, do_action, add_filter, apply_filters

    def on_post_save(post_id):
        print(f"Post {post_id} saved")

    add_action('post_saved', on_post_save)
    do_action('post_saved', post_id=42)

    def content_filter(content, post_id=None):
        return content + "\n<!-- filtered -->"

    add_filter('post_content', content_filter)
    rendered = apply_filters('post_content', raw_content, post_id=post.id)
"""

import json

_HOOKS = {}  # {name: [(priority, callback), ...]}


def add_action(name, callback, priority=10):
    """注册一个 Action hook（无返回值）"""
    _HOOKS.setdefault('action_' + name, []).append((priority, callback))


def do_action(name, *args, **kwargs):
    """执行 Action hook"""
    key = 'action_' + name
    if key not in _HOOKS:
        return
    _HOOKS[key].sort(key=lambda x: x[0])  # 按 priority 排序
    for _, cb in _HOOKS[key]:
        cb(*args, **kwargs)


def add_filter(name, callback, priority=10):
    """注册一个 Filter hook（返回值会被传送到下一个 filter）"""
    _HOOKS.setdefault('filter_' + name, []).append((priority, callback))


def apply_filters(name, value, *args, **kwargs):
    """执行 Filter hook chain，value 依次经过每个回调"""
    key = 'filter_' + name
    if key not in _HOOKS:
        return value
    _HOOKS[key].sort(key=lambda x: x[0])
    for _, cb in _HOOKS[key]:
        value = cb(value, *args, **kwargs)
    return value


def remove_action(name, callback=None):
    """移除 Action hook"""
    _remove_hook('action_' + name, callback)


def remove_filter(name, callback=None):
    """移除 Filter hook"""
    _remove_hook('filter_' + name, callback)


def _remove_hook(key, callback=None):
    if key not in _HOOKS:
        return
    if callback is None:
        del _HOOKS[key]
    else:
        _HOOKS[key] = [(p, cb) for p, cb in _HOOKS[key] if cb != callback]
        if not _HOOKS[key]:
            del _HOOKS[key]


# 注册系统级默认 hooks
def _register_defaults():
    from cms.extensions import db
    from cms.models import Setting

    def auto_create_categories():
        if not Setting.get('default_category_created'):
            from cms.models import Category
            if not Category.query.first():
                default = Category(name='未分类', slug='uncategorized')
                db.session.add(default)
                db.session.commit()
                Setting.set('default_category_created', '1')

    add_action('app_started', auto_create_categories)


_register_defaults()
