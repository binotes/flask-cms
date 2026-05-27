#!/usr/bin/env python3
"""
网易新闻头条导入工具
从 m.163.com 抓取 top 新闻并导入 Flask CMS。
用法: venv/bin/python3 scripts/import_news.py [数量]
  默认抓取 10 篇，可指定: venv/bin/python3 scripts/import_news.py 5
"""
import sys, os, re, html as html_mod, urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cms import create_app
from cms.extensions import db
from cms.models import Post, Category, Tag, User
from datetime import datetime, timezone

# 配置
NETEASE_URL = "https://m.163.com/"
UA = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
CATEGORY_NAME = "网易新闻"
TAG_NAME = "网易"
DEFAULT_COUNT = 10


def fetch_article_list(limit=10):
    """获取网易新闻头条文章链接列表"""
    req = urllib.request.Request(NETEASE_URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    articles = re.findall(
        r'<a href="(/news/article/[^"]+)"[^>]*><article><section class="[^"]*"><h4>(.*?)</h4>',
        html,
    )
    result = []
    for url, title in articles[:limit]:
        clean_title = html_mod.unescape(title).replace("&quot;", '"')
        full_url = "https://m.163.com" + url
        result.append((full_url, clean_title))
    return result


def fetch_article(url):
    """提取单篇文章的标题和正文"""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read().decode("utf-8", errors="replace")

    # 标题
    title_match = re.search(r"<title>(.*?)</title>", data, re.DOTALL)
    title = html_mod.unescape(title_match.group(1).strip()) if title_match else ""
    title = re.sub(r"[_-]\s*手机网易网$", "", title).strip()

    # 正文 — 多种模式容错
    body = ""

    # 模式1: content div
    match = re.search(
        r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>\s*(?:<div[^>]*class="[^"]*(?:article-info|share|tags)|<footer)',
        data,
        re.DOTALL | re.IGNORECASE,
    )
    # 模式2: article div
    if not match:
        match = re.search(
            r'<div[^>]*class="[^"]*article[^"]*"[^>]*>(.*?)</div>\s*(?:<div[^>]*class="[^"]*(?:article-info|share|tags)|<footer)',
            data,
            re.DOTALL | re.IGNORECASE,
        )
    # 模式3: <p> 段落聚合
    if not match:
        all_ps = re.findall(r"<p[^>]*>(.*?)</p>", data, re.DOTALL)
        substantial = [
            p for p in all_ps if len(re.sub(r"<[^>]+>", "", p).strip()) > 20
        ]
        if substantial:
            body = "\n\n".join(substantial[:20])

    if match:
        raw = match.group(1)
        raw = re.sub(r"<script[^>]*>.*?</script>", "", raw, flags=re.DOTALL)
        raw = re.sub(r"<style[^>]*>.*?</style>", "", raw, flags=re.DOTALL)
        raw = re.sub(r"<br\s*/?>", "\n", raw)
        paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", raw, re.DOTALL)
        body = "\n\n".join(paragraphs) if paragraphs else re.sub(r"<[^>]+>", "", raw)

    body = html_mod.unescape(body)
    body = re.sub(r"&nbsp;", " ", body)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()

    return title, body


def import_news(count=DEFAULT_COUNT):
    """抓取并导入网易新闻"""
    print(f"正在获取网易新闻头条...")
    articles = fetch_article_list(limit=count)
    print(f"获取到 {len(articles)} 篇文章\n")

    app = create_app()
    with app.app_context():
        admin = User.query.filter_by(role="admin").first()
        if not admin:
            print("错误: 未找到管理员用户")
            return

        cat = Category.query.filter_by(name=CATEGORY_NAME).first()
        if not cat:
            cat = Category(name=CATEGORY_NAME, slug="netease-news")
            db.session.add(cat)
            db.session.commit()
            print(f"创建分类: {CATEGORY_NAME}")

        tag = Tag.query.filter_by(name=TAG_NAME).first()
        if not tag:
            tag = Tag(name=TAG_NAME, slug="netease")
            db.session.add(tag)
            db.session.commit()

        created = 0
        for url, list_title in articles:
            article_id = url.rstrip(".html").split("/")[-1]
            slug = f"netEase-{article_id}"

            print(f"  [{article_id}] {list_title[:55]}")

            if Post.query.filter_by(slug=slug).first():
                print(f"    跳过: 已存在")
                continue

            title, body = fetch_article(url)

            # 视频文章补偿
            if len(body) < 50:
                body = list_title

            post = Post(
                title=title or list_title,
                slug=slug,
                content=body or list_title,
                excerpt=(body[:200] if len(body) > 200 else body) or list_title[:200],
                status="publish",
                comment_status="closed",
                author_id=admin.id,
                category_id=cat.id,
                published_at=datetime.now(timezone.utc),
            )
            post.tags.append(tag)
            db.session.add(post)
            db.session.commit()
            created += 1
            print(f"    导入成功 ➜ Post #{post.id} ({len(body)} 字)")

        print(f"\n完成: 新增 {created} 篇，分类 {CATEGORY_NAME} 共 {len(cat.posts.all())} 篇")


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_COUNT
    import_news(count)
