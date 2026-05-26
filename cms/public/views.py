from flask import Blueprint, render_template, request, redirect, url_for, abort, flash
from flask_login import current_user
from cms.models import Post, Page, Category, Tag, Comment
from cms.forms import CommentForm
from cms.extensions import db

public_bp = Blueprint('public', __name__, template_folder='../templates')


@public_bp.route('/')
def home():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    posts = Post.query.filter_by(status='publish')\
        .order_by(Post.published_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    return render_template('public/home.html', posts=posts)


@public_bp.route('/post/<slug>')
def post_detail(slug):
    post = Post.query.filter_by(slug=slug, status='publish').first_or_404()
    form = CommentForm()
    return render_template('public/post.html', post=post, form=form)


@public_bp.route('/page/<slug>')
def page_detail(slug):
    page = Page.query.filter_by(slug=slug, status='publish').first_or_404()
    return render_template('public/page.html', page=page)


@public_bp.route('/category/<slug>')
def category_archive(slug):
    category = Category.query.filter_by(slug=slug).first_or_404()
    page = request.args.get('page', 1, type=int)
    posts = Post.query.filter_by(category=category, status='publish')\
        .order_by(Post.published_at.desc())\
        .paginate(page=page, per_page=10, error_out=False)
    return render_template('public/category.html', category=category, posts=posts)


@public_bp.route('/tag/<slug>')
def tag_archive(slug):
    tag = Tag.query.filter_by(slug=slug).first_or_404()
    page = request.args.get('page', 1, type=int)
    posts = tag.posts.filter_by(status='publish')\
        .order_by(Post.published_at.desc())\
        .paginate(page=page, per_page=10, error_out=False)
    return render_template('public/tag.html', tag=tag, posts=posts)


@public_bp.route('/search')
def search():
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    results = []
    if query:
        results = Post.query.filter(
            Post.status == 'publish',
            Post.title.contains(query) | Post.content.contains(query)
        ).order_by(Post.published_at.desc())\
         .paginate(page=page, per_page=10, error_out=False)
    return render_template('public/search.html', query=query, results=results)


@public_bp.route('/comment/<int:post_id>', methods=['POST'])
def submit_comment(post_id):
    post = Post.query.get_or_404(post_id)
    if post.comment_status == 'closed':
        flash('Comments are closed on this post.', 'error')
        return redirect(url_for('public.post_detail', slug=post.slug))

    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(
            content=form.content.data,
            author_name=form.author_name.data or (current_user.display_name if current_user.is_authenticated else ''),
            author_email=form.author_email.data or (current_user.email if current_user.is_authenticated else ''),
            post_id=post.id,
            user_id=current_user.id if current_user.is_authenticated else None
        )
        db.session.add(comment)
        db.session.commit()
        flash('Comment submitted for review.', 'success')
    else:
        for errors in form.errors.values():
            for error in errors:
                flash(error, 'error')

    return redirect(url_for('public.post_detail', slug=post.slug))
