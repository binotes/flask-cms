from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, PasswordField, SelectField, \
    SelectMultipleField, FileField, BooleanField, HiddenField
from wtforms.validators import DataRequired, Email, Length, Optional, EqualTo


class LoginForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired()])
    password = PasswordField('密码', validators=[DataRequired()])
    remember = BooleanField('记住我')


class RegisterForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(3, 80)])
    email = StringField('邮箱', validators=[DataRequired(), Email()])
    password = PasswordField('密码', validators=[DataRequired(), Length(6, 128)])
    confirm = PasswordField('确认密码', validators=[
        DataRequired(), EqualTo('password', message='两次密码不一致')
    ])
    display_name = StringField('显示名称', validators=[Optional(), Length(0, 100)])
    bio = TextAreaField('简介', validators=[Optional()])
    role = SelectField('角色', choices=[
        ('author', '作者'),
        ('editor', '编辑'),
        ('admin', '管理员')
    ], default='author')


class PostForm(FlaskForm):
    title = StringField('标题', validators=[DataRequired(), Length(1, 200)])
    content = TextAreaField('内容', validators=[DataRequired()])
    excerpt = TextAreaField('摘要', validators=[Optional()])
    status = SelectField('状态', choices=[
        ('draft', '草稿'),
        ('publish', '发布')
    ], default='draft')
    category_id = SelectField('分类', coerce=int, default=0)
    tags = StringField('标签（逗号分隔）', validators=[Optional()])
    featured_image = HiddenField('特色图片')
    comment_status = SelectField('评论', choices=[
        ('open', '开放'),
        ('closed', '关闭')
    ], default='open')


class PageForm(FlaskForm):
    title = StringField('标题', validators=[DataRequired(), Length(1, 200)])
    content = TextAreaField('内容', validators=[Optional()])
    status = SelectField('状态', choices=[
        ('draft', '草稿'),
        ('publish', '发布')
    ], default='publish')
    parent_id = SelectField('父页面', coerce=int, default=0)
    template = SelectField('模板', choices=[('', '默认模板')], default='')
    order = StringField('排序', default='0')


class CategoryForm(FlaskForm):
    name = StringField('名称', validators=[DataRequired(), Length(1, 100)])
    description = TextAreaField('描述', validators=[Optional()])
    parent_id = SelectField('父分类', coerce=int, default=0)


class TagForm(FlaskForm):
    name = StringField('名称', validators=[DataRequired(), Length(1, 80)])


class CommentForm(FlaskForm):
    content = TextAreaField('评论内容', validators=[DataRequired()])
    author_name = StringField('称呼', validators=[Optional(), Length(1, 100)])
    author_email = StringField('邮箱', validators=[Optional(), Email()])


class SettingsForm(FlaskForm):
    site_name = StringField('站点名称', validators=[Optional(), Length(1, 200)])
    site_description = TextAreaField('站点描述', validators=[Optional()])
    posts_per_page = StringField('每页文章数', default='10')
    comment_moderation = SelectField('评论审核', choices=[
        ('1', '开启'),
        ('0', '关闭')
    ], default='1')


class ProfileForm(FlaskForm):
    display_name = StringField('显示名称', validators=[Optional(), Length(1, 100)])
    bio = TextAreaField('个人简介', validators=[Optional()])
    email = StringField('邮箱', validators=[Optional(), Email()])


class MediaUploadForm(FlaskForm):
    file = FileField('选择文件', validators=[DataRequired()])
    alt_text = StringField('替代文本', validators=[Optional()])


class UserForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(3, 80)])
    email = StringField('邮箱', validators=[DataRequired(), Email()])
    password = PasswordField('密码', validators=[Optional(), Length(6, 128)])
    confirm = PasswordField('确认密码', validators=[Optional(), EqualTo('password', message='两次密码不一致')])
    display_name = StringField('显示名称', validators=[Optional(), Length(0, 100)])
    bio = TextAreaField('简介', validators=[Optional()])
    role = SelectField('角色', choices=[
        ('author', '作者'),
        ('editor', '编辑'),
        ('admin', '管理员')
    ], default='author')