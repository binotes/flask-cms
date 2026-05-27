"""
Tag Cloud Plugin — 标签云

在任意模板位置显示标签云，标签字体大小按文章数量自动缩放。
提供 Jinja2 函数和 HTML 两种输出方式。

用法:
    {{ get_tag_cloud() | safe }}        ← 渲染完整 HTML 标签云
    {{ get_tag_cloud_data() }}           ← 返回原始数据列表
"""
from cms.extensions import db
from cms.models import Tag, Post


def register():
    """注册上下文处理器，注入标签云函数"""
    from flask import current_app, url_for

    # 注入 get_tag_cloud() — 返回 HTML
    current_app.context_processor(_inject_tag_cloud)

    # 注入 get_tag_cloud_data() — 返回原始数据
    current_app.context_processor(_inject_tag_cloud_data)


def _compute_tag_cloud():
    """计算标签云数据，返回按文章数量排序的标签列表"""
    tags = Tag.query.all()
    if not tags:
        return []

    # 统计每个标签下的已发布文章数
    tag_data = []
    for tag in tags:
        count = tag.posts.filter(Post.status == 'publish').count()
        if count > 0:
            tag_data.append({
                'name': tag.name,
                'slug': tag.slug,
                'count': count,
            })

    if not tag_data:
        return []

    # 计算字体大小 (最小 ~ 最有用的标签)
    counts = [t['count'] for t in tag_data]
    min_count = min(counts)
    max_count = max(counts)
    range_count = max_count - min_count if max_count > min_count else 1

    for t in tag_data:
        # 字体大小: 10px ~ 22px，线性映射
        ratio = (t['count'] - min_count) / range_count
        t['font_size'] = round(10 + ratio * 12, 1)
        # CSS 颜色: 从 #999 渐变到 #2563eb
        r = int(0x66 + ratio * (0x1a - 0x66))
        g = int(0x66 + ratio * (0x73 - 0x66))
        b = int(0x66 + ratio * (0xe8 - 0x66))
        t['color'] = f'#{r:02x}{g:02x}{b:02x}'

    # 按名字字母排序
    tag_data.sort(key=lambda x: x['name'])
    return tag_data


def _render_tag_cloud_html(tag_data):
    """将标签云数据渲染为 HTML"""
    from flask import url_for
    if not tag_data:
        return '<p class="tag-cloud-empty">暂无标签</p>'

    parts = ['<div class="tag-cloud">']
    for t in tag_data:
        url = url_for('public.tag_archive', slug=t['slug'])
        parts.append(
            '<a href="%s" class="tag-cloud-item" '
            'style="font-size:%spx;color:%s;" '
            'title="%d 篇文章">%s</a>'
            % (url, t['font_size'], t['color'], t['count'], t['name'])
        )
    parts.append('</div>')
    return '\n'.join(parts)


def _inject_tag_cloud():
    """向模板注入 get_tag_cloud() HTML 渲染函数"""
    def get_tag_cloud():
        return _render_tag_cloud_html(_compute_tag_cloud())
    return dict(get_tag_cloud=get_tag_cloud)


def _inject_tag_cloud_data():
    """向模板注入 get_tag_cloud_data() 数据函数"""
    def get_tag_cloud_data():
        return _compute_tag_cloud()
    return dict(get_tag_cloud_data=get_tag_cloud_data)
