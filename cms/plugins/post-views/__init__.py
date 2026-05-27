"""
Post Views Counter Plugin

自动记录每篇文章的浏览次数，并在文章中显示。
使用独立数据表存储，不影响核心 Post 模型。
"""

from cms.extensions import db


class PostView(db.Model):
    """文章浏览记录"""
    __tablename__ = 'plugin_post_views'

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, nullable=False, index=True)
    views = db.Column(db.Integer, default=0, nullable=False)

    @classmethod
    def get_count(cls, post_id):
        """获取指定文章的阅读量"""
        record = cls.query.filter_by(post_id=post_id).first()
        return record.views if record else 0

    @classmethod
    def increment(cls, post_id):
        """增加阅读量"""
        record = cls.query.filter_by(post_id=post_id).first()
        if record:
            record.views += 1
        else:
            record = cls(post_id=post_id, views=1)
            db.session.add(record)
        db.session.commit()


def register():
    """插件注册入口"""
    from flask import current_app

    # 创建插件专属的数据表
    with current_app.app_context():
        db.create_all()

    # 注册请求拦截 — 在文章详情页增加阅读量
    current_app.before_request(_count_view)

    # 注册上下文处理器 — 在模板中注入阅读量
    current_app.context_processor(_inject_view_count)


def _count_view():
    """在文章详情页请求中增加阅读量"""
    from flask import request
    if request.endpoint != 'public.post_detail':
        return

    # 从 URL 中提取 slug
    slug = request.view_args.get('slug') if request.view_args else None
    if not slug:
        return

    # 查询文章 ID
    from cms.models import Post
    post = Post.query.filter_by(slug=slug).first()
    if not post:
        return

    # 增加阅读量
    PostView.increment(post.id)


def _inject_view_count():
    """向所有模板注入 get_post_views 函数"""
    def get_post_views(post_id):
        return PostView.get_count(post_id)

    return dict(get_post_views=get_post_views)
