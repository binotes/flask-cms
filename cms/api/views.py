from flask import Blueprint, jsonify, request
from cms.models import Post, Page, Category, Tag
from cms.extensions import db

api_bp = Blueprint('api', __name__)


@api_bp.route('/posts')
def api_posts():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    posts = Post.query.filter_by(status='publish')\
        .order_by(Post.published_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'posts': [{
            'id': p.id,
            'title': p.title,
            'slug': p.slug,
            'excerpt': p.excerpt,
            'content': p.content,
            'featured_image': p.featured_image,
            'author': p.author.display_name if p.author else None,
            'category': p.category.name if p.category else None,
            'tags': [t.name for t in p.tags],
            'published_at': p.published_at.isoformat() if p.published_at else None,
            'created_at': p.created_at.isoformat() if p.created_at else None,
        } for p in posts.items],
        'total': posts.total,
        'page': posts.page,
        'per_page': posts.per_page,
        'pages': posts.pages,
    })


@api_bp.route('/categories')
def api_categories():
    categories = Category.query.order_by(Category.name).all()
    return jsonify({
        'categories': [{
            'id': c.id,
            'name': c.name,
            'slug': c.slug,
            'description': c.description,
            'post_count': c.posts.filter_by(status='publish').count(),
        } for c in categories]
    })


@api_bp.route('/categories/<int:id>')
def api_category_detail(id):
    category = Category.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    posts = Post.query.filter_by(category=category, status='publish')\
        .order_by(Post.published_at.desc())\
        .paginate(page=page, per_page=10, error_out=False)
    return jsonify({
        'category': {
            'id': category.id,
            'name': category.name,
            'slug': category.slug,
            'description': category.description,
            'post_count': posts.total,
        },
        'posts': [{
            'id': p.id,
            'title': p.title,
            'slug': p.slug,
            'excerpt': p.excerpt,
            'published_at': p.published_at.isoformat() if p.published_at else None,
        } for p in posts.items],
        'page': posts.page,
        'pages': posts.pages,
    })


@api_bp.route('/tags')
def api_tags():
    tags = Tag.query.order_by(Tag.name).all()
    return jsonify({
        'tags': [{
            'id': t.id,
            'name': t.name,
            'slug': t.slug,
        } for t in tags]
    })


@api_bp.route('/tags/<int:id>')
def api_tag_detail(id):
    tag = Tag.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    posts = tag.posts.filter_by(status='publish')\
        .order_by(Post.published_at.desc())\
        .paginate(page=page, per_page=10, error_out=False)
    return jsonify({
        'tag': {
            'id': tag.id,
            'name': tag.name,
            'slug': tag.slug,
        },
        'posts': [{
            'id': p.id,
            'title': p.title,
            'slug': p.slug,
            'excerpt': p.excerpt,
            'published_at': p.published_at.isoformat() if p.published_at else None,
        } for p in posts.items],
        'page': posts.page,
        'pages': posts.pages,
    })
