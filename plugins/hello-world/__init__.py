"""Hello World 示例插件"""

from cms.hooks import add_filter, add_action


def register():
    """插件入口：注册 hooks"""
    add_filter('post_content', add_copyright, priority=99)
    add_action('app_started', on_start)


def add_copyright(content, post_id=None):
    """在文章内容后追加版权信息"""
    from cms.models import Setting
    site_name = Setting.get('site_name', 'My CMS')
    return content + f'\\n\\n<hr>\\n<p class="plugin-copyright">© {site_name}. Powered by Flask CMS Plugin System.</p>'


def on_start():
    print("[HelloWorld Plugin] Plugin loaded successfully!")
