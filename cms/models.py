import uuid
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from slugify import slugify as make_slug
from cms.extensions import db, login_manager


# ─── Association Tables ────────────────────────────────────────
post_tags = db.Table('post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('post.id', ondelete='CASCADE'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id', ondelete='CASCADE'), primary_key=True)
)


# ─── User ──────────────────────────────────────────────────────
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='author')  # admin, editor, author
    display_name = db.Column(db.String(100), default='')
    bio = db.Column(db.Text, default='')
    avatar = db.Column(db.String(256), default='')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    posts = db.relationship('Post', backref='author', lazy='dynamic', foreign_keys='Post.author_id')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def is_editor(self):
        return self.role in ('admin', 'editor')

    def __repr__(self):
        return f'<User {self.username}>'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ─── Category ──────────────────────────────────────────────────
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, default='')
    parent_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    children = db.relationship('Category', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')
    posts = db.relationship('Post', backref='category', lazy='dynamic')

    def save(self):
        if not self.slug:
            self.slug = make_slug(self.name)
        db.session.add(self)
        db.session.commit()

    def __repr__(self):
        return f'<Category {self.name}>'


# ─── Tag ───────────────────────────────────────────────────────
class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def save(self):
        if not self.slug:
            self.slug = make_slug(self.name)
        db.session.add(self)
        db.session.commit()

    def __repr__(self):
        return f'<Tag {self.name}>'


# ─── Post ──────────────────────────────────────────────────────
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    excerpt = db.Column(db.Text, default='')
    featured_image = db.Column(db.String(256), default='')
    status = db.Column(db.String(20), nullable=False, default='draft')  # draft, publish
    comment_status = db.Column(db.String(20), default='open')  # open, closed
    author_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    published_at = db.Column(db.DateTime, nullable=True)

    tags = db.relationship('Tag', secondary=post_tags, backref=db.backref('posts', lazy='dynamic'), lazy='joined')
    comments = db.relationship('Comment', backref='post', lazy='dynamic',
                                foreign_keys='Comment.post_id',
                                order_by='Comment.created_at')

    def save(self):
        if not self.slug:
            base_slug = make_slug(self.title)
            slug = base_slug
            counter = 1
            while Post.query.filter_by(slug=slug).first():
                slug = f'{base_slug}-{counter}'
                counter += 1
            self.slug = slug
        if self.status == 'publish' and not self.published_at:
            self.published_at = datetime.now(timezone.utc)
        db.session.add(self)
        db.session.commit()

    @property
    def word_count(self):
        return len(self.content.split())

    def __repr__(self):
        return f'<Post {self.title}>'


# ─── Page ──────────────────────────────────────────────────────
class Page(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False, index=True)
    content = db.Column(db.Text, default='')
    status = db.Column(db.String(20), default='publish')  # draft, publish
    parent_id = db.Column(db.Integer, db.ForeignKey('page.id'), nullable=True)
    template = db.Column(db.String(100), default='')
    order = db.Column(db.Integer, default=0)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    children = db.relationship('Page', backref=db.backref('parent', remote_side=[id]), lazy='dynamic',
                                order_by='Page.order')

    def save(self):
        if not self.slug:
            self.slug = make_slug(self.title)
        db.session.add(self)
        db.session.commit()

    def __repr__(self):
        return f'<Page {self.title}>'


# ─── Comment ───────────────────────────────────────────────────
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    author_name = db.Column(db.String(100), default='')
    author_email = db.Column(db.String(120), default='')
    status = db.Column(db.String(20), default='pending')  # approved, pending, spam
    post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]),
                               lazy='dynamic', foreign_keys='Comment.parent_id')

    def save(self):
        db.session.add(self)
        db.session.commit()

    def __repr__(self):
        return f'<Comment {self.id} on Post {self.post_id}>'


# ─── Media ─────────────────────────────────────────────────────
class Media(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(500), nullable=False)
    original_name = db.Column(db.String(300), nullable=False)
    mime_type = db.Column(db.String(100), default='')
    size = db.Column(db.Integer, default=0)
    width = db.Column(db.Integer, default=0)
    height = db.Column(db.Integer, default=0)
    alt_text = db.Column(db.String(300), default='')
    description = db.Column(db.Text, default='')
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    uploader = db.relationship('User', backref='uploads')

    def save(self):
        db.session.add(self)
        db.session.commit()

    def __repr__(self):
        return f'<Media {self.original_name}>'

    @property
    def url(self):
        return f'/media/{self.filename}'

    @property
    def thumbnail_url(self):
        return f'/media/thumbs/{self.filename}'


# ─── Setting ───────────────────────────────────────────────────
class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, default='')

    @classmethod
    def get(cls, key, default=''):
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default

    @classmethod
    def set(cls, key, value):
        s = cls.query.filter_by(key=key).first()
        if s:
            s.value = value
        else:
            db.session.add(cls(key=key, value=value))
        db.session.commit()

    def __repr__(self):
        return f'<Setting {self.key}>'