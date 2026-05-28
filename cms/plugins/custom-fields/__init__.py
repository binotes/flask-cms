"""
Custom Fields Plugin — WordPress 风格自定义字段 (Post Meta)

为文章和页面添加任意键值对元数据。
功能：
- 在文章编辑页添加自定义字段 Metabox
- 支持添加、编辑、删除自定义字段
- 前台模板注入 get_meta() / get_meta_all()
- 数据持久化到 post_meta 表
"""
from datetime import datetime, timezone
from flask import jsonify, request, redirect, url_for, flash


# ─── PostMeta Model ──────────────────────────────────────────────

_meta_model_defined = False
_meta_model_class = None


def _get_meta_model():
    """动态定义 PostMeta 模型（避免循环导入）"""
    global _meta_model_defined
    global _meta_model_class
    if _meta_model_defined and _meta_model_class is not None:
        return _meta_model_class

    from cms.extensions import db

    class PostMeta(db.Model):
        __tablename__ = 'post_meta'

        id = db.Column(db.Integer, primary_key=True)
        post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete='CASCADE'),
                            nullable=False, index=True)
        meta_key = db.Column(db.String(255), nullable=False, index=True)
        meta_value = db.Column(db.Text, default='')
        created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

        post = db.relationship('Post', backref=db.backref('meta_list', lazy='dynamic',
                                                           cascade='all, delete-orphan'))

        def __repr__(self):
            return f'<PostMeta {self.meta_key}={self.meta_value[:30]}>'

    _meta_model_defined = True
    _meta_model_class = PostMeta
    return PostMeta


# ─── Public Template Functions ──────────────────────────────────

def get_meta(post, key, default=None):
    """获取单条自定义字段值（第一个匹配）"""
    PostMeta = _get_meta_model()
    meta = PostMeta.query.filter_by(post_id=post.id, meta_key=key).first()
    return meta.meta_value if meta else default


def get_meta_all(post, prefix=None):
    """获取所有自定义字段，返回 {key: [value1, value2, ...]} 或 {key: value}
    若 prefix 指定，则只返回键以 prefix 开头的字段
    """
    PostMeta = _get_meta_model()
    query = PostMeta.query.filter_by(post_id=post.id)
    if prefix:
        query = query.filter(PostMeta.meta_key.startswith(prefix))
    metas = query.all()
    result = {}
    for m in metas:
        if m.meta_key in result:
            if not isinstance(result[m.meta_key], list):
                result[m.meta_key] = [result[m.meta_key]]
            result[m.meta_key].append(m.meta_value)
        else:
            result[m.meta_key] = m.meta_value
    return result


# ─── Admin Editor UI ────────────────────────────────────────────

META_EDITOR_HTML = r"""
<div class="card custom-fields-card">
    <div class="card-header">
        <h3>📋 自定义字段</h3>
    </div>
    <div class="card-body">
        <p class="field-desc">为当前文章添加自定义键值对元数据。</p>

        <table class="custom-fields-table" id="customFieldsTable">
            <thead>
                <tr>
                    <th class="cf-key-col">键名 (Key)</th>
                    <th class="cf-value-col">值 (Value)</th>
                    <th class="cf-actions-col">操作</th>
                </tr>
            </thead>
            <tbody id="cfBody">
                {% for meta in metas %}
                <tr data-meta-id="{{ meta.id }}">
                    <td class="cf-key">{{ meta.meta_key }}</td>
                    <td class="cf-value">
                        <span class="cf-value-text">{{ meta.meta_value }}</span>
                        <input type="text" class="cf-edit-input" value="{{ meta.meta_value }}"
                               style="display:none;" data-original="{{ meta.meta_value }}">
                    </td>
                    <td class="cf-actions">
                        <button type="button" class="btn btn-sm btn-edit"
                                onclick="toggleEdit(this, {{ meta.id }})">编辑</button>
                        <button type="button" class="btn btn-sm btn-danger"
                                onclick="deleteMeta({{ meta.id }})">删除</button>
                        <button type="button" class="btn btn-sm btn-success"
                                style="display:none;" onclick="saveEdit(this, {{ meta.id }})">保存</button>
                        <button type="button" class="btn btn-sm btn-secondary"
                                style="display:none;" onclick="cancelEdit(this)">取消</button>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <div class="cf-add-row">
            <h4>添加新字段</h4>
            <div class="cf-add-form">
                <input type="text" id="cfNewKey" class="form-control" placeholder="键名 (如: subtitle, author_name)" style="width:200px;">
                <input type="text" id="cfNewValue" class="form-control" placeholder="字段值" style="width:300px;">
                <button type="button" class="btn btn-primary btn-sm" onclick="addMeta()">添加</button>
            </div>
        </div>
    </div>
</div>

<script>
var CSRF_TOKEN = document.querySelector('input[name="csrf_token"]')?.value || '';

function addMeta() {
    var key = document.getElementById('cfNewKey').value.trim();
    var val = document.getElementById('cfNewValue').value.trim();
    if (!key) { alert('请输入键名'); return; }
    fetch('/admin/plugins/custom-fields/{{ post_id }}/add', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN},
        body: JSON.stringify({meta_key: key, meta_value: val})
    }).then(r => r.json()).then(data => {
        if (data.success) {
            location.reload();
        } else {
            alert('添加失败: ' + (data.error || '未知错误'));
        }
    });
}

function deleteMeta(metaId) {
    if (!confirm('确定删除此自定义字段？')) return;
    fetch('/admin/plugins/custom-fields/{{ post_id }}/delete/' + metaId, {
        method: 'POST',
        headers: {'X-CSRFToken': CSRF_TOKEN}
    }).then(r => r.json()).then(data => {
        if (data.success) {
            var row = document.querySelector('tr[data-meta-id="' + metaId + '"]');
            if (row) row.remove();
        } else {
            alert('删除失败: ' + (data.error || '未知错误'));
        }
    });
}

function toggleEdit(btn, metaId) {
    var row = btn.closest('tr');
    var textSpan = row.querySelector('.cf-value-text');
    var editInput = row.querySelector('.cf-edit-input');
    var editBtn = row.querySelector('.btn-edit');
    var delBtn = row.querySelector('.btn-danger');
    var saveBtn = row.querySelector('.btn-success');
    var cancelBtn = row.querySelector('.btn-secondary');

    // 保持简洁: 直接开启内联编辑
    textSpan.style.display = 'none';
    editInput.style.display = 'inline-block';
    editInput.value = textSpan.textContent.trim();
    editBtn.style.display = 'none';
    delBtn.style.display = 'none';
    saveBtn.style.display = 'inline-block';
    cancelBtn.style.display = 'inline-block';
    editInput.focus();
}

function saveEdit(btn, metaId) {
    var row = btn.closest('tr');
    var editInput = row.querySelector('.cf-edit-input');
    var newVal = editInput.value.trim();

    fetch('/admin/plugins/custom-fields/{{ post_id }}/edit/' + metaId, {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN},
        body: JSON.stringify({meta_value: newVal})
    }).then(r => r.json()).then(data => {
        if (data.success) {
            location.reload();
        } else {
            alert('编辑失败: ' + (data.error || '未知错误'));
        }
    });
}

function cancelEdit(btn) {
    var row = btn.closest('tr');
    var textSpan = row.querySelector('.cf-value-text');
    var editInput = row.querySelector('.cf-edit-input');
    var editBtn = row.querySelector('.btn-edit');
    var delBtn = row.querySelector('.btn-danger');
    var saveBtn = row.querySelector('.btn-success');
    var cancelBtn = row.querySelector('.btn-secondary');

    textSpan.style.display = 'inline';
    editInput.style.display = 'none';
    editInput.value = editInput.dataset.original || '';
    editBtn.style.display = 'inline-block';
    delBtn.style.display = 'inline-block';
    saveBtn.style.display = 'none';
    cancelBtn.style.display = 'none';
}
</script>
"""


def _render_cf_editor(post_id):
    """渲染自定义字段编辑器 HTML"""
    from flask import render_template_string
    from jinja2 import Template
    PostMeta = _get_meta_model()
    metas = PostMeta.query.filter_by(post_id=post_id).order_by(PostMeta.id).all()
    tpl = Template(META_EDITOR_HTML)
    return tpl.render(post_id=post_id, metas=metas)


# ─── API Handlers ────────────────────────────────────────────────

def _api_list(post_id):
    """JSON: 获取指定文章的所有自定义字段"""
    PostMeta = _get_meta_model()
    metas = PostMeta.query.filter_by(post_id=post_id).order_by(PostMeta.id).all()
    return jsonify([{
        'id': m.id, 'meta_key': m.meta_key,
        'meta_value': m.meta_value, 'created_at': m.created_at.isoformat()
    } for m in metas])


def _api_add(post_id):
    """JSON: 添加自定义字段"""
    PostMeta = _get_meta_model()
    from cms.extensions import db
    data = request.get_json(silent=True) or {}
    meta_key = (data.get('meta_key') or '').strip()
    meta_value = (data.get('meta_value') or '').strip()
    if not meta_key:
        return jsonify({'success': False, 'error': '键名不能为空'}), 400
    meta = PostMeta(post_id=post_id, meta_key=meta_key, meta_value=meta_value)
    db.session.add(meta)
    db.session.commit()
    return jsonify({'success': True, 'id': meta.id})


def _api_edit(post_id, meta_id):
    """JSON: 编辑自定义字段值"""
    PostMeta = _get_meta_model()
    from cms.extensions import db
    meta = PostMeta.query.get_or_404(meta_id)
    if meta.post_id != post_id:
        return jsonify({'success': False, 'error': '字段不属于该文章'}), 403
    data = request.get_json(silent=True) or {}
    new_value = (data.get('meta_value') or '').strip()
    meta.meta_value = new_value
    db.session.commit()
    return jsonify({'success': True})


def _api_delete(post_id, meta_id):
    """JSON: 删除自定义字段"""
    PostMeta = _get_meta_model()
    from cms.extensions import db
    meta = PostMeta.query.get_or_404(meta_id)
    if meta.post_id != post_id:
        return jsonify({'success': False, 'error': '字段不属于该文章'}), 403
    db.session.delete(meta)
    db.session.commit()
    return jsonify({'success': True})


# ─── Plugin Registration ────────────────────────────────────────

def register():
    """注册插件：创建表、注册路由、注入上下文处理器"""
    from flask import current_app
    from cms.extensions import db

    # 1. 创建 PostMeta 表
    PostMeta = _get_meta_model()
    with current_app.app_context():
        try:
            db.create_all()
        except Exception:
            # 表可能已存在，忽略
            pass

    # 2. 注册 API 路由
    prefix = '/admin/plugins/custom-fields'
    current_app.add_url_rule(f'{prefix}/<int:post_id>/list',
                             'cf_list', _api_list)
    current_app.add_url_rule(f'{prefix}/<int:post_id>/add',
                             'cf_add', _api_add, methods=['POST'])
    current_app.add_url_rule(f'{prefix}/<int:post_id>/edit/<int:meta_id>',
                             'cf_edit', _api_edit, methods=['POST'])
    current_app.add_url_rule(f'{prefix}/<int:post_id>/delete/<int:meta_id>',
                             'cf_delete', _api_delete, methods=['POST'])

    # 3. 注册公共模板函数
    current_app.context_processor(_inject_public_functions)

    # 4. 注册管理编辑器函数
    current_app.context_processor(_inject_admin_editor)


def _inject_public_functions():
    """向公共模板注入 get_meta() 和 get_meta_all()"""
    return dict(get_meta=get_meta, get_meta_all=get_meta_all)


def _inject_admin_editor():
    """向管理模板注入 custom_fields_editor()"""
    def editor(post=None, post_id=None):
        pid = post_id or (post.id if post else None)
        if pid is None:
            return ''
        return _render_cf_editor(pid)
    return dict(custom_fields_editor=editor)
