#!/usr/bin/env python3
"""自动备份脚本 - 由 cron 调用"""
import os
import sys
import json

# 添加 CMS 目录到路径
sys.path.insert(0, '/home/joyo/cms')

os.chdir('/home/joyo/cms')

# 初始化 Flask app
from cms import create_app
from cms.plugin_manager import load_plugin
from cms.models import Setting

app = create_app()

with app.app_context():
    # 加载 backup_manager 插件
    load_plugin('backup_manager')
    
    # 检查是否启用自动备份
    auto_enabled = Setting.get('backup_auto_backup_enabled', 'false')
    if auto_enabled.lower() != 'true':
        print("自动备份未启用，跳过")
        sys.exit(0)
    
    # 执行备份
    from cms.plugins.backup_manager import create_full_backup, cleanup_old_backups, get_setting
    
    backup_info = create_full_backup()
    
    if backup_info['status'] == 'success':
        print(f"自动备份成功: {backup_info['timestamp']}")
        # 清理旧备份
        max_backups = get_setting('max_backups', 10)
        deleted = cleanup_old_backups(max_backups)
        if deleted:
            print(f"清理了 {deleted} 个旧备份")
    else:
        print(f"自动备份失败: {backup_info['status']}")
        sys.exit(1)
