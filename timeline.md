# Flask CMS — 开发时间线

> 项目路径: `/home/joyo/cms`
> GitHub: [binotes/flask-cms](https://github.com/binotes/flask-cms)
> 起始日期: 2026-05-19

---

## 📅 时间线

| 日期 | 事件 | 详情 |
|------|------|------|
| 05-19 | 首次启动 CMS | 安装依赖，成功运行 Flask 应用 |
| 05-26 | GitHub 初始化 | `git init` → 推送到 `binotes/flask-cms`，创建 `push-to-github` skill |
| 05-29 | 功能规划 | 梳理 20+ 项可增加功能，选定"数据备份"优先实现 |
| 05-30 | backup_manager 插件 | 创建 → 修复 4 个 Bug（路由重复/模板函数/CSRF/url_for）→ 推送 |
| 06-01 | 移动端适配 | newspaper 主题响应式改造：汉堡菜单、触摸优化、三断点 |
| 06-03 | Feature Audit + RSS Feed | 全面审查已完成功能 + 实现 rss-feed 插件 + 推送 |

---

## 🏆 已完成功能

### 核心系统

| 模块 | 功能 |
|------|------|
| **用户认证** | 登录/注册/退出/个人资料，三级角色（admin/editor/author） |
| **文章管理** | 完整 CRUD、草稿/发布、分类、标签、特色图片、评论开关、Slug 自动生成 |
| **页面管理** | 完整 CRUD、父子层级、自定义模板、排序 |
| **分类管理** | 带层级，创建时自动创建默认「未分类」 |
| **标签管理** | 创建/删除 |
| **媒体库** | 上传/删除、图片尺寸检测、UUID 防重名、50MB 限制 |
| **评论系统** | 提交→审核→批准/垃圾/删除，支持审核开关 |
| **用户管理** | 管理员 CRUD，角色分配 |
| **系统设置** | 站点名称/描述、每页文章数、评论审核开关 |
| **API** | REST JSON 接口：`/api/posts`, `/api/categories`, `/api/tags` |
| **插件系统** | 自动发现、管理界面激活/停用、JSON 配置文件 |
| **主题系统** | 自动发现、管理界面切换、ThemeLoader 动态加载、静态文件服务 |
| **Hook 系统** | WordPress 风格 Actions + Filters，支持优先级排序 |
| **权限控制** | `editor_required` / `admin_required` 装饰器 |
| **错误处理** | 404 页面 |
| **手机适配** | 响应式 CSS、汉堡菜单、触摸目标优化（断点 768px / 480px） |

### 6 个插件

| 插件 | 版本 | 功能 |
|------|------|------|
| **related-posts** | 1.0.0 | 同分类+共享标签推荐算法，排序+去重 |
| **custom-fields** | 1.0.0 | PostMeta 模型，文章编辑页内联 CRUD，`get_meta()` / `get_meta_all()` 模板函数 |
| **tag-cloud** | 1.0.0 | 标签云，按文章数量缩放字体，可选 HTML 或原始数据输出 |
| **post-views** | 1.0.0 | 自动计阅读量，`before_request` 拦截，`get_post_views()` 模板函数 |
| **sitemap** | 1.0.0 | `/sitemap.xml` 自动生成（文章+页面） |
| **backup_manager** | 1.0.0 | 一键备份（DB+媒体+配置+主题+插件），列表/下载/删除/恢复，定时备份 |
| **rss-feed** | 1.0.0 | RSS 2.0 订阅源 `/feed.xml`，CDATA 支持中文，RFC 822 时间格式 |

### 7 个主题

- default（默认）
- minimal
- docs
- magazine
- dark-reader
- tech-blog
- newspaper（当前活跃主题，已做移动适配）

---

## 📋 待实现功能（按优先级）

### 🎯 高优先级
- [ ] **SEO 插件** — meta description、OG 标签、canonical URL、robots meta
- [ ] **批量操作** — 文章列表批量发布/删除/切换分类
- [ ] **Markdown 编辑** — 替换纯 textarea 为 Markdown 编辑器或支持渲染
- [ ] **阅读时间估算** — 「预计阅读 X 分钟」
- [ ] **热门文章 Widget** — 按阅读量排行的侧边栏
- [ ] **最近评论 Widget** — 显示最新评论

### 📈 中优先级
- [ ] **修订历史** — 文章版本管理和自动保存
- [ ] **定时发布** — 未来时间自动发布
- [ ] **Password 保护文章** — 访问密码
- [ ] **联系表单** — 公开联系页面 + 管理员邮件通知
- [ ] **短代码系统** — 类似 WordPress 的 `[gallery]` `[youtube]` 短代码
- [ ] **分类图片/图标** — 分类可视化增强
- [ ] **目录生成（TOC）** — 长文章自动生成锚点目录
- [ ] **嵌套回复** — 评论回复层级
- [ ] **社交分享按钮** — 微信/微博/Twitter 分享

### 🛠 低优先级
- [ ] PWA 支持
- [ ] WYSIWYG 编辑器
- [ ] 深色模式切换
- [ ] 反垃圾评论（Akismet）
- [ ] 导入/导出（WordPress XML, CSV）
- [ ] 自定义文章类型（CPT）
- [ ] 分析看板
- [ ] Webhook 支持
- [ ] 多语言/i18n

---

*最后更新: 2026-06-03*