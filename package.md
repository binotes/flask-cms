# CMS 项目打包分发说明

> 适用于将本机开发环境下的 Flask CMS 项目迁移到其他设备（Linux，Python 3.8+）

---

## 一、项目结构概览

```
cms/
├── cms/                  # 核心代码
│   ├── __init__.py       # Flask 应用工厂
│   ├── models.py         # 数据模型
│   ├── forms.py          # WTForms 表单
│   ├── extensions.py     # 扩展初始化
│   ├── hooks.py          # 插件钩子系统
│   ├── plugin_manager.py # 插件管理器
│   ├── theme_system.py   # 主题管理器
│   ├── admin/views.py    # 后台管理路由
│   ├── auth/views.py     # 认证路由
│   ├── public/views.py   # 前台路由
│   ├── api/views.py      # REST API 路由
│   ├── templates/        # Jinja2 模板
│   └── plugins/          # 插件目录
├── static/               # 静态文件（CSS/JS/图片）
├── themes/               # 主题目录
├── media/                # 上传文件目录
├── run.py                # 启动脚本
├── config.py             # 配置文件
├── requirements.txt      # Python 依赖清单
├── cms.db                # SQLite 数据库（开发数据）
└── venv/                 # 虚拟环境（本机路径，不可迁移）
```

---

## 二、标准分发步骤

### 2.1 打包要拷贝的文件

```bash
# 在项目根目录执行
tar -czf cms-dist.tar.gz \
    cms/ \
    static/ \
    themes/ \
    plugins/ \
    media/ \
    run.py \
    config.py \
    requirements.txt
```

**打包清单说明：**

| 打包项 | 是否必需 | 说明 |
|--------|---------|------|
| `cms/` | ✓ 必需 | 核心代码，含模板 |
| `static/` | ✓ 必需 | CSS/JS 等静态资源 |
| `themes/` | ✓ 必需 | 主题模板文件 |
| `run.py` | ✓ 必需 | 应用入口 |
| `config.py` | ✓ 必需 | 配置（密钥等） |
| `requirements.txt` | ✓ 必需 | 依赖清单 |
| `plugins/` | 非必需 | 如无插件可为空 |
| `media/` | 非必需 | 如无上传文件可为空 |
| `venv/` | **禁止打包** | 路径绑定本机，到新设备需重建 |
| `cms.db` | 可选 | SQLite 数据库，可拷也可重建 |

### 2.2 目标设备部署

```bash
# 1. 解压
tar -xzf cms-dist.tar.gz
cd cms

# 2. 创建虚拟环境
python3 -m venv venv

# 3. 安装依赖
source venv/bin/activate
pip install -r requirements.txt
pip install email_validator    # 如果 requirements.txt 未包含

# 4. （可选）删除旧数据库，让系统重建
rm -f cms.db

# 5. 启动
python3 run.py
```

### 2.3 验证部署

```bash
# 检查端口
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/
# 应返回 200

# 检查后台登录
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/auth/login
# 应返回 200

# 默认管理员：admin / admin123
```

---

## 三、生产环境部署（gunicorn）

### 3.1 systemd 服务

创建 `/etc/systemd/system/cms.service`：

```ini
[Unit]
Description=CMS Web Application
After=network.target

[Service]
User=joyo
WorkingDirectory=/home/joyo/cms
Environment="PATH=/home/joyo/cms/venv/bin"
ExecStart=/home/joyo/cms/venv/bin/gunicorn \
    -w 4 \
    -b 0.0.0.0:8000 \
    --access-logfile /var/log/cms/access.log \
    --error-logfile /var/log/cms/error.log \
    "run:app"

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable cms
sudo systemctl start cms
```

### 3.2 Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /static/ {
        alias /home/joyo/cms/static/;
        expires 30d;
    }

    location /media/ {
        alias /home/joyo/cms/media/;
        expires 30d;
    }
}
```

---

## 四、跨平台注意事项

### 4.1 Python 版本兼容

| 本机 | 目标设备 | 兼容性 |
|------|---------|--------|
| Python 3.8 | Python 3.8 | ✓ 完全兼容 |
| Python 3.8 | Python 3.9-3.11 | ✓ 基本兼容 |
| Python 3.8 | Python < 3.8 | ✗ 不兼容 |

### 4.2 操作系统

- **Linux → Linux**：完全兼容（推荐）
- **Linux → Windows**：部分兼容
  - `gunicorn` 在 Windows 不可用，改用 `waitress`
  - 路径分隔符差异需注意
  - 文件权限需重置
- **Linux → macOS**：基本兼容

### 4.3 Python 虚拟环境迁移

**不要直接拷贝 venv/ 目录！** venv 包含本机路径硬编码，到新设备必须重建：

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

这就够了，大约 30 秒完成。

### 4.4 数据库迁移

SQLite 数据库（`cms.db`）是单文件，可以跨机拷贝：

```bash
# 打包时包含
tar -czf cms-dist.tar.gz ... cms.db ...

# 到新设备直接用
# 注意：包含了旧设备上的测试数据
```

如果不想要旧数据，删除 `cms.db`，启动时系统会自动重建并创建默认管理员账号。

### 4.5 密钥和敏感信息

`config.py` 中的 SECRET_KEY：
- 开发环境默认密钥可分发
- 生产环境**必须更换**为随机密钥：
  ```bash
  python3 -c "import secrets; print(secrets.token_hex(32))"
  ```

---

## 五、快速部署脚本

创建 `deploy.sh` 放在项目根目录：

```bash
#!/bin/bash
# CMS 快速部署脚本
# 用法: 在目标设备上运行

set -e

echo "=== CMS 部署开始 ==="

# 检查 Python 版本
python3 --version || { echo "需要 Python 3.8+"; exit 1; }

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 安装依赖
echo "安装依赖..."
source venv/bin/activate
pip install -r requirements.txt

# 初始化数据库（删除旧库重建）
if [ ! -f "cms.db" ]; then
    echo "数据库将在首次启动时自动创建"
fi

echo "=== 部署完成 ==="
echo "启动: python3 run.py"
echo "访问: http://localhost:5000"
echo "管理员: admin / admin123"
```

```bash
chmod +x deploy.sh
# 到目标设备上：./deploy.sh && python3 run.py
```

---

## 六、常见问题

### Q: 报错 `ModuleNotFoundError: No module named 'email_validator'`
A: 运行 `pip install email_validator`，或在 requirements.txt 中添加。

### Q: 报错端口被占用
A: 修改 `run.py` 中的端口号，或先 `fuser -k 5000/tcp` 杀掉旧进程。

### Q: 启动后页面 500 错误
A: 检查数据库文件是否完整，尝试 `rm -f cms.db` 重建。

### Q: 主题切换不生效
A: 确认主题目录下包含 `templates/public/base.html`，重启服务器。

### Q: 上传图片 403/404
A: 确认 `media/` 目录存在且有写权限：`mkdir -p media && chmod 755 media`。

---

## 七、文件清单速查

```
需要分发的文件（7项）：
├── cms/                # 核心代码
├── static/             # 静态资源
├── themes/             # 主题
├── run.py              # 启动脚本
├── config.py           # 配置
├── requirements.txt    # 依赖
└── deploy.sh           # 部署脚本（可选）

目标设备上需要做的（3步）：
1. python3 -m venv venv
2. pip install -r requirements.txt
3. python3 run.py
```