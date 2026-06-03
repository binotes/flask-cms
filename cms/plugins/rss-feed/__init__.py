"""
RSS Feed Plugin — RSS 2.0 订阅源

在 /feed.xml 提供标准 RSS 2.0 XML 输出，
包含所有已发布文章的标题、链接、摘要、作者、分类、标签和发布时间。

订阅地址: /feed.xml
"""

from datetime import timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape


def register():
    """注册 /feed.xml 路由"""
    from flask import current_app
    current_app.add_url_rule('/feed.xml', 'rss_feed', _generate_feed)


def _generate_feed():
    """生成 RSS 2.0 XML"""
    from flask import Response, url_for
    from cms.models import Post, Setting

    site_name = escape(Setting.get('site_name', 'My CMS'))
    site_desc = escape(Setting.get('site_description', 'A Flask CMS'))
    site_url = url_for('public.home', _external=True)

    posts = Post.query.filter_by(status='publish') \
        .order_by(Post.published_at.desc()) \
        .limit(50).all()

    items = []
    for post in posts:
        post_url = url_for('public.post_detail', slug=post.slug, _external=True)
        pub_date = format_datetime(post.published_at) if post.published_at else ''

        title = escape(post.title)
        link = escape(post_url)
        guid = escape(post_url)

        # 摘要优先取 excerpt，否则取 content 前 500 字符
        excerpt_raw = post.excerpt or post.content[:500]
        description = escape(excerpt_raw)

        author = escape(post.author.display_name) if post.author else ''

        # 分类
        cat_name = escape(post.category.name) if post.category else ''

        # 标签
        tag_names = ''.join(
            f'      <category>{escape(t.name)}</category>\n'
            for t in post.tags
        )

        items.append(f"""  <item>
    <title>{title}</title>
    <link>{link}</link>
    <guid isPermaLink="true">{guid}</guid>
    <description><![CDATA[{excerpt_raw}]]></description>
    <pubDate>{pub_date}</pubDate>
    <author>{author}</author>
    <category>{cat_name}</category>
{tag_names}  </item>""")

    now_rfc822 = format_datetime(
        posts[0].published_at if posts else __import__('datetime').datetime.now(timezone.utc)
    )

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:content="http://purl.org/rss/1.0/modules/content/"
     xmlns:dc="http://purl.org/dc/elements/1.1/"
     xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{site_name}</title>
    <link>{escape(site_url)}</link>
    <description>{site_desc}</description>
    <language>zh-cn</language>
    <lastBuildDate>{now_rfc822}</lastBuildDate>
    <atom:link href="{escape(url_for('rss_feed', _external=True))}" rel="self" type="application/rss+xml"/>
    <generator>Flask CMS RSS Feed Plugin</generator>
{chr(10).join(items)}
  </channel>
</rss>"""

    return Response(xml, mimetype='application/rss+xml; charset=utf-8')