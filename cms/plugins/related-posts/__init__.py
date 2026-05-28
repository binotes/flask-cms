"""
Related Posts Plugin — 相关文章推荐

在文章详情页底部自动显示与当前文章相关的文章。
推荐算法：
1. 同分类的文章优先
2. 共享标签越多的文章排名越高
3. 按发布时间倒序，取 top-N
"""
from collections import Counter


def register():
    """注册上下文处理器，注入 get_related_posts()"""
    from flask import current_app
    current_app.context_processor(inject_related_posts)


def get_related_posts(post, limit=5):
    """获取与指定文章相关的文章列表

    排序规则：
    - 同分类文章优先于非同分类
    - 共享标签数越多越靠前
    - 同条件下最新发布优先
    """
    from cms.extensions import db
    from cms.models import Post, post_tags

    tag_ids = [t.id for t in post.tags]
    category_id = post.category_id

    # 构建子查询：统计每篇文章与当前文章的共享标签数
    score_case = db.case(
        (post_tags.c.tag_id.in_(tag_ids), 1),
        else_=0
    )

    # 查询条件：已发布、不是当前文章
    filters = [Post.status == 'publish', Post.id != post.id]

    # 如果有关联的标签，按共享标签数排序
    if tag_ids:
        score = db.func.sum(score_case).label('relevance')
        query = db.session.query(Post, score) \
            .outerjoin(post_tags) \
            .filter(*filters) \
            .group_by(Post.id) \
            .order_by(score.desc(), Post.published_at.desc())
    else:
        # 没有标签时，只按分类 + 时间排序
        query = Post.query.filter(*filters) \
            .order_by(Post.published_at.desc())

    rows = query.limit(limit * 2).all()

    # 统一标准化：无论有无 score，都提取 Post 对象
    normalized = []
    for item in rows:
        # SQLAlchemy Row 对象支持数字索引，Post 对象不支持
        try:
            p = item[0]
        except (TypeError, IndexError):
            p = item
        normalized.append(p)

    # 如果有分类，同分类文章往前排
    if category_id:
        def sort_key(p):
            # 同分类得 1000 分（高权重），加上共享标签数
            same_cat = 1000 if p.category_id == category_id else 0
            tag_count = Counter()
            for t in post.tags:
                if t in p.tags:
                    tag_count[t.id] += 1
            return -(same_cat + len(tag_count))
        normalized.sort(key=sort_key)

    result = []
    seen = set()
    for p in normalized:
        if p.id not in seen:
            seen.add(p.id)
            result.append(p)
        if len(result) >= limit:
            break

    return result


def inject_related_posts():
    """向模板注入 get_related_posts(post) 函数"""
    return dict(get_related_posts=get_related_posts)
