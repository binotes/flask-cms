"""
Sitemap Generator Plugin

在插件加载时直接注册 /sitemap.xml 路由，
自动生成包含所有公开文章和页面的 XML Sitemap。
"""


def register():
    """插件注册入口 — 在插件加载时直接注册路由"""
    from flask import current_app
    current_app.add_url_rule('/sitemap.xml', 'sitemap', _generate_sitemap)


def _generate_sitemap():
    """生成 sitemap.xml 内容"""
    from flask import Response, url_for
    from cms.models import Post, Page

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]

    # 首页 — 最高优先级
    lines.append('  <url>')
    lines.append('    <loc>%s</loc>' % url_for('public.home', _external=True))
    lines.append('    <priority>1.0</priority>')
    lines.append('  </url>')

    # 所有已发布的文章
    posts = Post.query.filter_by(status='publish') \
        .order_by(Post.published_at.desc()).all()
    for post in posts:
        lines.append('  <url>')
        lines.append('    <loc>%s</loc>' % url_for('public.post_detail',
                     slug=post.slug, _external=True))
        if post.updated_at:
            lines.append('    <lastmod>%s</lastmod>' % post.updated_at.strftime('%Y-%m-%d'))
        lines.append('    <priority>0.8</priority>')
        lines.append('  </url>')

    # 所有已发布的页面
    pages = Page.query.filter_by(status='publish').all()
    for page in pages:
        lines.append('  <url>')
        lines.append('    <loc>%s</loc>' % url_for('public.page_detail',
                     slug=page.slug, _external=True))
        if page.updated_at:
            lines.append('    <lastmod>%s</lastmod>' % page.updated_at.strftime('%Y-%m-%d'))
        lines.append('    <priority>0.6</priority>')
        lines.append('  </url>')

    lines.append('</urlset>')
    return Response('\n'.join(lines), mimetype='application/xml')