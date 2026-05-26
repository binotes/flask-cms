import os
import uuid
from datetime import datetime, timezone
from functools import wraps
from slugify import slugify as make_slug

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from PIL import Image

from cms.models import User, Post, Page, Category, Tag, Comment, Media, Setting
from cms.forms import PostForm, PageForm, CategoryForm, TagForm, \
    CommentForm, SettingsForm, ProfileForm, RegisterForm, MediaUploadForm, UserForm
from cms.extensions import db

admin_bp = Blueprint('admin', __name__)


# ─── Decorators ─────────────────────────────────────────────

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin():
            flash('权限不足，需要管理员权限', 'error')
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated


def editor_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_editor():
            flash('权限不足，需要编辑或管理员权限', 'error')
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated


# ─── Dashboard ──────────────────────────────────────────────

@admin_bp.route('/')
@login_required
def dashboard():
    post_count = Post.query.count()
    page_count = Page.query.count()
    published_count = Post.query.filter_by(status='publish').count()
    draft_count = Post.query.filter_by(status='draft').count()
    comment_count = Comment.query.count()
    pending_comment_count = Comment.query.filter_by(status='pending').count()
    media_count = Media.query.count()
    category_count = Category.query.count()
    tag_count = Tag.query.count()
    recent_posts = Post.query.order_by(Post.created_at.desc()).limit(5).all()
    recent_comments = Comment.query.order_by(Comment.created_at.desc()).limit(5).all()
    return render_template('admin/dashboard.html', **locals())


# ─── Posts ──────────────────────────────────────────────────

@admin_bp.route('/posts')
@login_required
def posts_list():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    category_filter = request.args.get('category', 0, type=int)
    search_q = request.args.get('q', '').strip()

    query = Post.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if category_filter:
        query = query.filter_by(category_id=category_filter)
    if search_q:
        query = query.filter(Post.title.contains(search_q))
    if not current_user.is_admin():
        query = query.filter_by(author_id=current_user.id)

    posts = query.order_by(Post.created_at.desc())\
        .paginate(page=page, per_page=10, error_out=False)
    categories = Category.query.order_by(Category.name).all()
    return render_template('admin/posts.html', **locals())


@admin_bp.route('/posts/create', methods=['GET', 'POST'])
@editor_required
def post_create():
    form = PostForm()
    form.category_id.choices = [(0, '无分类')] + [
        (c.id, c.name) for c in Category.query.order_by(Category.name).all()
    ]
    if form.validate_on_submit():
        post = Post(
            title=form.title.data,
            content=form.content.data,
            excerpt=form.excerpt.data or '',
            status=form.status.data,
            featured_image=form.featured_image.data or '',
            comment_status=form.comment_status.data,
            author_id=current_user.id,
            category_id=form.category_id.data if form.category_id.data != 0 else None,
        )
        tag_names = [t.strip() for t in (form.tags.data or '').split(',') if t.strip()]
        for name in tag_names:
            tag = Tag.query.filter_by(name=name).first()
            if not tag:
                tag = Tag(name=name, slug=make_slug(name))
                db.session.add(tag)
            post.tags.append(tag)
        post.save()
        from cms.hooks import do_action, apply_filters
        do_action('post_saved', post_id=post.id, is_new=True)
        flash('文章已创建', 'success')
        return redirect(url_for('admin.posts_list'))
    return render_template('admin/post_form.html', form=form, post=None)


@admin_bp.route('/posts/<int:post_id>/edit', methods=['GET', 'POST'])
@editor_required
def post_edit(post_id):
    post = Post.query.get_or_404(post_id)
    if not current_user.is_admin() and post.author_id != current_user.id:
        flash('您无权编辑此文章', 'error')
        return redirect(url_for('admin.posts_list'))

    form = PostForm(obj=post)
    form.category_id.choices = [(0, '无分类')] + [
        (c.id, c.name) for c in Category.query.order_by(Category.name).all()
    ]
    if not form.is_submitted():
        form.category_id.data = post.category_id or 0
        form.tags.data = ', '.join(t.name for t in post.tags)
        form.featured_image.data = post.featured_image or ''

    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        post.excerpt = form.excerpt.data or ''
        post.status = form.status.data
        post.featured_image = form.featured_image.data or ''
        post.comment_status = form.comment_status.data
        post.category_id = form.category_id.data if form.category_id.data != 0 else None

        post.tags = []
        tag_names = [t.strip() for t in (form.tags.data or '').split(',') if t.strip()]
        for name in tag_names:
            tag = Tag.query.filter_by(name=name).first()
            if not tag:
                tag = Tag(name=name, slug=make_slug(name))
                db.session.add(tag)
            post.tags.append(tag)

        post.updated_at = datetime.now(timezone.utc)
        if post.status == 'publish' and not post.published_at:
            post.published_at = datetime.now(timezone.utc)
        db.session.commit()
        flash('文章已更新', 'success')
        return redirect(url_for('admin.posts_list'))
    return render_template('admin/post_form.html', form=form, post=post)


@admin_bp.route('/posts/<int:post_id>/delete', methods=['POST'])
@editor_required
def post_delete(post_id):
    post = Post.query.get_or_404(post_id)
    if not current_user.is_admin() and post.author_id != current_user.id:
        flash('您无权删除此文章', 'error')
        return redirect(url_for('admin.posts_list'))
    db.session.delete(post)
    db.session.commit()
    flash('文章已删除', 'success')
    return redirect(url_for('admin.posts_list'))


# ─── Pages ────────────────────────────────────────────────────────────────────

@admin_bp.route('/pages')
@login_required
def pages_list():
    pages = Page.query.order_by(Page.order, Page.title).all()
    return render_template('admin/pages.html', pages=pages)


@admin_bp.route('/pages/create', methods=['GET', 'POST'])
@editor_required
def page_create():
    form = PageForm()
    form.parent_id.choices = [(0, '无父页面')] + [
        (p.id, p.title) for p in Page.query.order_by(Page.title).all()
    ]
    if form.validate_on_submit():
        page = Page(
            title=form.title.data,
            content=form.content.data or '',
            status=form.status.data,
            parent_id=form.parent_id.data if form.parent_id.data != 0 else None,
            template=form.template.data or '',
            order=int(form.order.data or 0),
            author_id=current_user.id,
        )
        page.save()
        flash('页面已创建', 'success')
        return redirect(url_for('admin.pages_list'))
    return render_template('admin/page_form.html', form=form, page=None)


@admin_bp.route('/pages/<int:page_id>/edit', methods=['GET', 'POST'])
@editor_required
def page_edit(page_id):
    page = Page.query.get_or_404(page_id)
    form = PageForm(obj=page)
    form.parent_id.choices = [(0, '无父页面')] + [
        (p.id, p.title) for p in Page.query.order_by(Page.title).all()
        if p.id != page.id
    ]
    if not form.is_submitted():
        form.parent_id.data = page.parent_id or 0
        form.order.data = str(page.order or 0)
    if form.validate_on_submit():
        page.title = form.title.data
        page.content = form.content.data or ''
        page.status = form.status.data
        page.parent_id = form.parent_id.data if form.parent_id.data != 0 else None
        page.template = form.template.data or ''
        page.order = int(form.order.data or 0)
        page.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        flash('页面已更新', 'success')
        return redirect(url_for('admin.pages_list'))
    return render_template('admin/page_form.html', form=form, page=page)


@admin_bp.route('/pages/<int:page_id>/delete', methods=['POST'])
@editor_required
def page_delete(page_id):
    page = Page.query.get_or_404(page_id)
    db.session.delete(page)
    db.session.commit()
    flash('页面已删除', 'success')
    return redirect(url_for('admin.pages_list'))


# ─── Categories ─────────────────────────────────────────────

@admin_bp.route('/categories', methods=['GET', 'POST'])
@editor_required
def categories_mgmt():
    form = CategoryForm()
    form.parent_id.choices = [(0, '无父分类')] + [
        (c.id, c.name) for c in Category.query.order_by(Category.name).all()
    ]
    if form.validate_on_submit():
        if Category.query.filter_by(name=form.name.data).first():
            flash('分类名称已存在', 'error')
        else:
            cat = Category(
                name=form.name.data,
                description=form.description.data or '',
                parent_id=form.parent_id.data if form.parent_id.data != 0 else None,
            )
            cat.save()
            flash('分类已创建', 'success')
        return redirect(url_for('admin.categories_mgmt'))

    cats = Category.query.order_by(Category.name).all()
    return render_template('admin/categories.html', form=form, categories=cats)


@admin_bp.route('/categories/<int:cat_id>/edit', methods=['GET', 'POST'])
@editor_required
def category_edit(cat_id):
    cat = Category.query.get_or_404(cat_id)
    form = CategoryForm(obj=cat)
    form.parent_id.choices = [(0, '无父分类')] + [
        (c.id, c.name) for c in Category.query.order_by(Category.name).all()
        if c.id != cat_id
    ]
    if not form.is_submitted():
        form.parent_id.data = cat.parent_id or 0
    if form.validate_on_submit():
        if Category.query.filter(Category.name == form.name.data, Category.id != cat_id).first():
            flash('分类名称已存在', 'error')
        else:
            cat.name = form.name.data
            cat.description = form.description.data or ''
            cat.parent_id = form.parent_id.data if form.parent_id.data != 0 else None
            cat.slug = make_slug(cat.name)
            db.session.commit()
            flash('分类已更新', 'success')
        return redirect(url_for('admin.categories_mgmt'))
    cats = Category.query.order_by(Category.name).all()
    return render_template('admin/categories.html', form=form, categories=cats, editing=cat)


@admin_bp.route('/categories/<int:cat_id>/delete', methods=['POST'])
@editor_required
def category_delete(cat_id):
    cat = Category.query.get_or_404(cat_id)
    if cat.posts.count() > 0:
        flash('该分类下有文章，无法删除', 'error')
    else:
        db.session.delete(cat)
        db.session.commit()
        flash('分类已删除', 'success')
    return redirect(url_for('admin.categories_mgmt'))


# ─── Tags ───────────────────────────────────────────────────

@admin_bp.route('/tags', methods=['GET', 'POST'])
@editor_required
def tags_mgmt():
    form = TagForm()
    if form.validate_on_submit():
        if Tag.query.filter_by(name=form.name.data).first():
            flash('标签名称已存在', 'error')
        else:
            tag = Tag(name=form.name.data, slug=make_slug(form.name.data))
            db.session.add(tag)
            db.session.commit()
            flash('标签已创建', 'success')
        return redirect(url_for('admin.tags_mgmt'))

    all_tags = Tag.query.order_by(Tag.name).all()
    return render_template('admin/tags.html', form=form, tags=all_tags)


@admin_bp.route('/tags/<int:tag_id>/delete', methods=['POST'])
@editor_required
def tag_delete(tag_id):
    tag = Tag.query.get_or_404(tag_id)
    db.session.delete(tag)
    db.session.commit()
    flash('标签已删除', 'success')
    return redirect(url_for('admin.tags_mgmt'))


# ─── Media Library ──────────────────────────────────────────

@admin_bp.route('/media', methods=['GET', 'POST'])
@login_required
def media_library():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('请选择文件', 'error')
            return redirect(url_for('admin.media_library'))

        uploaded_file = request.files['file']
        if uploaded_file.filename == '':
            flash('请选择文件', 'error')
            return redirect(url_for('admin.media_library'))

        filename = secure_filename(uploaded_file.filename)
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        unique_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
        upload_dir = os.path.join(current_app.root_path, '..', 'media')
        os.makedirs(upload_dir, exist_ok=True)
        filepath = os.path.join(upload_dir, unique_name)
        uploaded_file.save(filepath)

        size = os.path.getsize(filepath)
        mime_type = uploaded_file.content_type or "application/octet-stream"
        width = height = 0
        if mime_type.startswith('image/'):
            try:
                with Image.open(filepath) as img:
                    width, height = img.size
            except Exception:
                pass

        media = Media(
            filename=unique_name,
            original_name=filename,
            mime_type=mime_type,
            size=size,
            width=width,
            height=height,
            alt_text=request.form.get('alt_text', ''),
            uploaded_by=current_user.id,
        )
        media.save()
        flash('文件上传成功', 'success')
        return redirect(url_for('admin.media_library'))

    page = request.args.get('page', 1, type=int)
    media_items = Media.query.order_by(Media.created_at.desc())\
        .paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/media.html', media_items=media_items)


@admin_bp.route('/media/<int:media_id>/delete', methods=['POST'])
@login_required
def media_delete(media_id):
    item = Media.query.get_or_404(media_id)
    filepath = os.path.join(current_app.root_path, '..', 'media', item.filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    db.session.delete(item)
    db.session.commit()
    flash('文件已删除', 'success')
    return redirect(url_for('admin.media_library'))


# ─── Comments ───────────────────────────────────────────────

@admin_bp.route('/comments')
@login_required
def comments_list():
    status_filter = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)
    query = Comment.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    comments = query.order_by(Comment.created_at.desc())\
        .paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/comments.html', comments=comments, status_filter=status_filter)


@admin_bp.route('/comments/<int:comment_id>/approve', methods=['POST'])
@editor_required
def comment_approve(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    comment.status = 'approved'
    db.session.commit()
    flash('评论已批准', 'success')
    return redirect(url_for('admin.comments_list'))


@admin_bp.route('/comments/<int:comment_id>/spam', methods=['POST'])
@editor_required
def comment_spam(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    comment.status = 'spam'
    db.session.commit()
    flash('评论已标记为垃圾', 'success')
    return redirect(url_for('admin.comments_list'))


@admin_bp.route('/comments/<int:comment_id>/delete', methods=['POST'])
@editor_required
def comment_delete(comment_id):
    comment = Comment.query.get_or_404(comment_id, 404)
    db.session.delete(comment)
    db.session.commit()
    flash('评论已删除', 'success')
    return redirect(url_for('admin.comments_list'))


@admin_bp.route('/users')
@admin_required
def users_list():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=all_users)


@admin_bp.route('/users/create', methods=['GET', 'POST'])
@admin_required
def user_create():
    form = UserForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('用户名已存在', 'error')
        elif User.query.filter_by(email=form.email.data).first():
            flash('邮箱已被使用', 'error')
        else:
            user = User(
                username=form.username.data,
                email=form.email.data,
                role=form.role.data,
                display_name=form.display_name.data or form.username.data,
            )
            if form.password.data:
                user.set_password(form.password.data)
            else:
                user.set_password('123456')
            if form.bio.data:
                user.bio = form.bio.data
            db.session.add(user)
            db.session.commit()
            flash(f'用户已创建（角色: {dict(form.role.choices)[form.role.data]}）', 'success')
            return redirect(url_for('admin.users_list'))
    return render_template('admin/user_form.html', form=form, user=None)


@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def user_edit(user_id):
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    if not form.is_submitted():
        form.role.data = user.role
    if form.validate_on_submit():
        user.display_name = form.display_name.data or user.username
        user.bio = form.bio.data or ''
        user.role = form.role.data
        if form.email.data and form.email.data != user.email:
            if User.query.filter(User.email == form.email.data, User.id != user_id).first():
                flash('邮箱已被使用', 'error')
                return render_template('admin/user_form.html', form=form, user=user)
            user.email = form.email.data
        if form.password.data:
            user.set_password(form.password.data)
        db.session.commit()
        flash(f'用户已更新（角色: {dict(form.role.choices)[form.role.data]}）', 'success')
        return redirect(url_for('admin.users_list'))
    return render_template('admin/user_form.html', form=form, user=user)


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def user_delete(user_id):
    if current_user.id == user_id:
        flash('不能删除自己', 'error')
        return redirect(url_for('admin.users_list'))
    user = User.query.get_or_404(user_id)
    Post.query.filter_by(author_id=user_id).update({'author_id': None})
    db.session.delete(user)
    db.session.commit()
    flash('用户已删除', 'success')
    return redirect(url_for('admin.users_list'))


# ─── Settings ───────────────────────────────────────────────

@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings_page():
    form = SettingsForm()
    if form.validate_on_submit():
        Setting.set('site_name', form.site_name.data or 'My CMS')
        Setting.set('site_description', form.site_description.data or '')
        Setting.set('posts_per_page', form.posts_per_page.data or '10')
        Setting.set('comment_moderation', '1' if form.comment_moderation.data == '1' else '0')
        flash('设置已保存', 'success')
        return redirect(url_for('admin.settings_page'))

    if not form.is_submitted():
        form.site_name.data = Setting.get('site_name', 'My CMS')
        form.site_description.data = Setting.get('site_description', '')
        form.posts_per_page.data = Setting.get('posts_per_page', '10')
        form.comment_moderation.data = Setting.get('comment_moderation', '1')

    return render_template('admin/settings.html', form=form)


# ─── Plugin Management ────────────────────────────────────

@admin_bp.route('/plugins')
@admin_required
def plugins_list():
    from cms.plugin_manager import discover_plugins, is_active, get_active_plugins
    available = discover_plugins()
    active_names = get_active_plugins()
    return render_template('admin/plugins.html',
                           plugins=available,
                           active_plugins=active_names)


@admin_bp.route('/plugins/<name>/activate', methods=['POST'])
@admin_required
def plugin_activate(name):
    from cms.plugin_manager import load_plugin, save_active_plugins, get_active_plugins
    if load_plugin(name):
        active = get_active_plugins()
        if name not in active:
            active.append(name)
        save_active_plugins(active)
        flash(f'插件 "{name}" 已激活', 'success')
    else:
        flash(f'插件 "{name}" 激活失败', 'error')
    return redirect(url_for('admin.plugins_list'))


@admin_bp.route('/plugins/<name>/deactivate', methods=['POST'])
@admin_required
def plugin_deactivate(name):
    from cms.plugin_manager import unload_plugin, save_active_plugins, get_active_plugins
    unload_plugin(name)
    active = [n for n in get_active_plugins() if n != name]
    save_active_plugins(active)
    flash(f'插件 "{name}" 已停用', 'success')
    return redirect(url_for('admin.plugins_list'))


# ─── Theme Management ─────────────────────────────────────

@admin_bp.route('/themes')
@admin_required
def themes_list():
    from cms.theme_system import discover_themes, get_active_theme
    themes = discover_themes()
    active = get_active_theme()
    return render_template('admin/themes.html',
                           themes=themes,
                           active_theme=active)


@admin_bp.route('/themes/<name>/activate', methods=['POST'])
@admin_required
def theme_activate(name):
    from cms.theme_system import set_active_theme
    set_active_theme(name)
    flash(f'主题 "{name}" 已启用', 'success')
    return redirect(url_for('admin.themes_list'))