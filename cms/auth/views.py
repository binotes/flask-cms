from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from cms.models import User
from cms.forms import LoginForm, RegisterForm, ProfileForm
from cms.extensions import db

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('用户名或密码错误', 'error')
            return render_template('auth/login.html', form=form)

        login_user(user, remember=form.remember.data)
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('admin.dashboard')
        flash('登录成功', 'success')
        return redirect(next_page)

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('已退出登录', 'info')
    return redirect(url_for('public.home'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))

    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('用户名已存在', 'error')
            return render_template('auth/register.html', form=form)
        if User.query.filter_by(email=form.email.data).first():
            flash('邮箱已被注册', 'error')
            return render_template('auth/register.html', form=form)

        user = User(
            username=form.username.data,
            email=form.email.data,
            role='author',
            display_name=form.username.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash('注册成功，请登录', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.display_name = form.display_name.data or current_user.username
        current_user.bio = form.bio.data or ''
        if form.email.data and form.email.data != current_user.email:
            existing = User.query.filter(
                User.email == form.email.data,
                User.id != current_user.id
            ).first()
            if existing:
                flash('邮箱已被使用', 'error')
                return render_template('auth/profile.html', form=form)
            current_user.email = form.email.data
        db.session.commit()
        flash('个人资料已更新', 'success')
        return redirect(url_for('auth.profile'))

    return render_template('auth/profile.html', form=form)
