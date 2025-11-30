translations = {
    # ==================== 通用变量 ====================
    "common":{
        # 语言设置
        "this_language": "中文",
        "this_language_code": "zh",
        "this_language_select_text": "选择语言",

        # 翻译缺失时的错误消息
        "this_error_missing_common": "[{lang}] 翻译缺失：common['{key}']",
        "this_error_missing_section": "[{lang}] 翻译缺失：sections['{section}']['?']['{key}']",
        "this_error_invalid_section": "[{lang}] 无效模块：sections['{section}'] 不是字典",
        "this_error_missing_main": "[{lang}] 翻译缺失：main['{section}']['{key}']",
        "this_error_missing_main_section": "[{lang}] 部分缺失：main['{section}'] 不存在",
        "this_error_invalid_key": "[{lang}] 无效键：'{key}'（期望 section_key 或 section_file_key）"
    },

    # ==================== 主要模板变量（templates 文件夹中的文件） ====================

    "main":{
        # ==================== 主要布局 ====================
        "layout":{
            "default_title": "启动器", # 项目名称，表示汽车零件（翻译时在目标语言中寻找等价物）
            "system_info": "系统信息",
            "logout_button": "退出",
            "logout_error": "退出错误",
            "unauthorized_access": "未经授权的访问。请重新登录。",
            "network_error": "网络错误。请检查您的连接。"
        },

        # ==================== 页脚 ====================
        "footer":{
            "copyright": "© 2025 MyIDon.SITE. 保留所有权利。"
        },

        # ==================== 认证 ====================
        "login":{
            "username_label": "用户名",
            "password_label": "密码",
            "submit_button": "登录",
            "network_error": "网络错误。请检查您的连接。",
            "error_occurred": "发生错误",
            "missing_credentials": "需要用户名和密码",
            "invalid_credentials": "无效凭据",
            "auth_not_configured": "认证系统未配置"
        },

        # ==================== 语言更改 ====================

        "changeLanguage":{
            "selector_label": "语言选择",
            "no_languages": "没有可用语言",
            "network_error": "网络错误。请检查您的连接。",
            "change_failed": "更改语言失败",
            "unknown_error": "发生未知错误",
            "language_changed": "语言更改成功",
            "invalid_language": "无效语言",
        },

        # ==================== 主要控制面板 ====================
        "controlPanel":{
            "loading": "加载中...",
            "action_error": "操作执行错误",
            "section_error": "模块加载错误",
            "parse_error": "数据解析错误",
            "status": "状态",
            "error": "错误",
        }
    },

    # ==================== 部分变量（templates/sections 文件夹中的文件） ====================

    "sections":{

        # ==================== DASHBOARD ====================
        'dashboard': {
            # 基本模块设置
            "basic":{
                # 在控制面板中显示
                "title":"系统",
                "description": "主要信息仪表盘"
            },

            'index': {
                "dashboard": "信息仪表盘",
                "system_info": "系统信息",
                "system": "系统",
                "hostname": "主机名",
                "os": "操作系统",
                "os_version": "操作系统版本",
                "python_version": "Python 版本",
                "implementation": "实现",
                "current_time": "当前时间",
                "uptime": "运行时间",
                "system_uptime": "系统运行时间",
                "version": "版本",
                "refresh": "刷新",
                "username": "用户名",
                "disk": "磁盘",
                "total": "总计",
                "used": "已用",
                "free": "可用",
                "docker_info": "Docker 信息",
                "docker_status": "Docker 状态",
                "docker_compose_status": "Docker Compose 状态",
                "installed": "已安装",
                "not_installed": "未安装",
                "registry_auth": "注册表认证",
                "authenticated": "已认证",
                "not_authenticated": "未认证",
                "registry_url": "注册表 URL",
                "network_info": "网络信息",
                "no_ips_found": "未找到 IP 地址",
                'corporate': '企业',
                'other': '其他',
                'disabled': '已禁用',
                'active': '活跃',
                'inactive': '不活跃',
                'ip_address': 'IP 地址',
                'netmask': '子网掩码',
                'mac_address': 'MAC 地址',
                'status': '状态',
                'external': '外部',
                'default_gateway': '默认网关',
                'no_network_interfaces': '未找到网络接口',
                "cpu": "处理器",
                "processor": "型号",
                "cores": "核心",
                "logical": "线程",
                "usage": "使用率",
                "memory": "内存",
                "total": "总计",
                "used": "已用",
                "available": "可用",
                "install": "安装",
                "package_installation": "软件包安装",
                "close": "关闭",
                "loading": "加载",
                "preparing_installation": "准备安装",
                "installation_logs": "安装日志",
                "finish": "完成",
                "download_logs": "下载日志",
                "confirm_install_package": "确认软件包安装",
                "starting_installation": "开始安装",
                "installation_completed_success": "安装成功完成！",
                "installation_failed": "安装失败",
                "log_request_failed": "获取日志失败",
                "start_install_failed": "开始安装失败",
                "request_failed": "请求失败",
                "compiler":"编译器",
                'install_docker_from_dashboard': '从仪表盘安装 Docker',
                'go_to_dashboard': '转到仪表盘',
                'install_from_dashboard': '从仪表盘安装'
            }
        },

        # ==================== DOCKER ====================
        'docker':{

            "basic": {
                "title": "Docker",
                "description": "容器管理"
            },

            'info': {
                "docker_info": "Docker 信息",
                "docker_status": "Docker 状态",
                "docker_compose_status": "Docker Compose 状态",
                "registry_auth": "注册表认证",
                "registry_url": "注册表 URL",
                "installed": "已安装",
                "not_installed": "未安装",
                "authenticated": "已认证",
                "not_authenticated": "未认证",
                "docker_restarted_successfully": "Docker 重启成功",
                "failed_to_restart_docker": "Docker 重启失败",
                "system_pruned_successfully": "Docker 系统清理成功",
                "failed_to_prune_system": "Docker 系统清理失败",
                "docker_dashboard": "Docker 仪表盘",
                "refresh": "刷新",
                "docker_version": "Docker 版本",
                "last_updated": "最后更新",
                "containers": "容器",
                "total": "总计",
                "running": "运行中",
                "stopped": "已停止",
                "images": "镜像",
                "total_images": "镜像总数",
                "disk_usage": "磁盘使用",
                "resources": "资源",
                "cpu_usage": "CPU 使用率",
                "memory_usage": "内存使用率",
                "docker_compose": "Docker Compose",
                "projects": "项目",
                "services": "服务",
                "quick_actions": "快速操作",
                "restart_docker": "重启 Docker",
                "prune_system": "清理系统",
                "confirm_restart_docker": "确定要重启 Docker 吗？这可能会停止所有正在运行的容器。",
                "confirm_prune_system": "确定要清理 Docker 系统吗？这将删除所有未使用的容器、网络、镜像和卷。",
                "request_failed": "请求失败",
                "install_docker": "安装 Docker",
                "confirm_install_docker": "这将在您的系统上安装 Docker。继续？",
                "installing": "安装中...",
                "docker_installed_success": "Docker 安装成功！重新启动会话。",
                "docker_install_failed": "Docker 安装失败。检查日志以获取详细信息。",
                "download_logs": "下载日志",
                "log_request_failed": "日志请求失败",
                "start_install_failed": "开始安装失败",
                "close": "关闭",
                "refresh": "刷新",
                "installation_started": "安装已开始",
                "docker_installation": "Docker 安装",
                "docker_not_installed": "Docker 未安装",
                "docker_installation_required": "需要 Docker 安装",
                "install_docker_guide": "Docker 安装指南",
                "docker_required_for_actions": "操作需要 Docker",
                "loading": "加载",
                "preparing_installation": "准备安装",
                "installation_logs": "安装日志",
                "finish": "完成",
                "starting_installation": "开始安装",
                "installation_completed_success": "安装成功完成！",
                "installation_completed_warning": "安装完成但有警告",
                "installation_failed": "安装失败",
                "start_project":"启动项目",
                # 项目启动模态框的新翻译
                "project_start_logs": "项目启动日志",
                "starting_project": "启动项目...",
                "startup_logs": "启动日志",
                "project_start_completed": "项目启动成功",
                "project_start_failed": "项目启动失败",
                "download_logs": "下载日志",
                "log_request_failed": "日志请求失败",
                "close": "关闭",
                "finish": "完成",
                "loading": "加载",
                "refresh": "刷新",
                # 历史表的新翻译
                "launch_history": "启动历史",
                "date_time": "日期和时间",
                "log_file": "日志文件",
                "duration": "持续时间",
                "status": "状态",
                "actions": "操作",
                "loading_history": "加载历史...",
                "no_launch_history": "没有启动历史",
                "view_logs": "查看日志",
                "download_logs": "下载日志",
                "status_success": "成功",
                "status_failed": "失败",
                "status_running": "运行中",
                "status_unknown": "未知",
                "seconds": "秒",
                "minutes": "分钟",
                "size": "大小",
                
                # 显示状态
                "completed": "已完成",
                "failed": "失败",
                "in_progress": "进行中",
                
                # 操作
                "open_logs": "打开日志",
                "copy_name": "复制名称",
                "delete_log": "删除日志",
                "confirm_delete_log": "确定要删除此日志文件吗？",
                "log_deleted_success": "日志文件删除成功",
                "log_deleted_error": "删除日志文件时出错",
                "open_logs": "打开日志",
                "copy_name": "复制名称",
                "delete_log": "删除日志",
                "view_logs": "查看日志",
                "download_logs": "下载日志",
                "log_content": "日志内容",
                "close": "关闭"
            },

            'containers': {
                "containers": "容器",
                "refresh": "刷新",
                "show_all": "显示全部",
                "name": "名称",
                "image": "镜像",
                "status": "状态",
                "ports": "端口",
                "running_for": "运行时间",
                "size": "大小",
                "actions": "操作",
                "stop": "停止",
                "restart": "重启",
                "start": "启动",
                "remove": "删除",
                "view_logs": "查看日志",
                "no_containers_found": "未找到容器",
                "confirm_remove_container": "确定要删除容器吗？",
                "request_failed": "请求失败",
                "docker_not_installed": "Docker 未安装",
                "docker_required_for_containers": "容器管理需要 Docker",
                "install_docker_guide": "Docker 安装指南"
            },

            'volumes': {
                "volumes": "卷",
                "refresh": "刷新",
                "name": "名称",
                "driver": "驱动",
                "scope": "范围",
                "mountpoint": "挂载点",
                "labels": "标签",
                "created": "创建时间",
                "no_volumes_found": "未找到卷"
            },

            'networks': {
                "networks": "网络",
                "refresh": "刷新",
                "name": "名称",
                "driver": "驱动",
                "scope": "范围",
                "ipv6": "IPv6",
                "internal": "内部",
                "created": "创建时间",
                "no_networks_found": "未找到网络"
            },

            'logs': {
                "logs": "日志",
                "select_container": "选择容器",
                "refresh": "刷新",
                "logs_for_container": "容器的日志",
                "select_container_to_view_logs": "选择容器以查看日志"
            },

            'images': {
                "images": "镜像",
                "refresh": "刷新",
                "repository": "仓库",
                "tag": "标签",
                "image_id": "镜像 ID",
                "created": "创建时间",
                "size": "大小",
                "actions": "操作",
                "remove": "删除",
                "no_images_found": "未找到镜像",
                "confirm_remove_image": "确定要删除此镜像吗？",
                "request_failed": "请求失败"
            }
        },

        # ==================== Port Knocking ====================
        'knocking':{

            'title':"Port Knocking",

            "index": {
                "knocking_title": "Port Knocking",
                "knocking_status": "状态",
                "knocking_ports": "端口序列", 
                "knocking_timeout": "超时",
                "knocking_description": "通过连接序列打开端口的方法",
                "knocking_how_it_works": "工作原理",
                "knocking_step1": "1. 配置端口序列",
                "knocking_step2": "2. 按顺序连接端口",
                "knocking_step3": "3. 所需端口自动打开",
                "active": "活跃",
                "inactive": "不活跃", 
                "seconds": "秒。",
                "refresh": "刷新",
                "start_service": "启动服务",
                "stop_service": "停止服务",
                "service_started": "服务已启动",
                "service_stopped": "服务已停止",
                "install":"安装",
                "knocking_not_installed": "Port Knocking 未安装",
                "knocking_install_instructions": "点击下方按钮安装 Port Knocking 服务",
                "knocking_already_installed": "Port Knocking 已安装",
                "knocking_install_success": "Port Knocking 安装成功",
                "knocking_install_failed": "安装 Port Knocking 失败",
                "knocking_install_error": "安装过程中出错",
            },

            "info": {
                "title": "Port Knocking 信息",
                "about": "关于技术",
                "what_is": "什么是？",
                "definition": "隐藏端口打开的安全技术",
                "benefits": "优势",
                "benefit1": "额外的安全层",
                "benefit2": "隐藏端口扫描器", 
                "benefit3": "动态访问管理",
                "limitations": "限制",
                "limit1": "需要客户端配置",
                "limit2": "可能的重放攻击",
                "limit3": "配置复杂性",
                "current_config": "当前设置",
                "configure_btn": "配置",
                "active_status": "活跃",
                "inactive_status": "已禁用"
            },

            "settings": {
                "title": "Port Knocking 设置",
                "configuration": "配置",
                "ports_label": "端口",
                "ports_help": "用逗号分隔（例如 1000,2000,3000）",
                "timeout_label": "超时（秒）",
                "timeout_help": "尝试间隔（1-10 秒）",
                "test_section": "测试",
                "test_description": "测试端口序列",
                "test_button": "测试",
                "min_ports": "至少需要 2 个端口",
                "invalid_timeout": "允许 1-10 秒",
                "save_btn": "保存",
                "save_success": "设置已保存",
                "save_error": "保存错误"
            }
        },

        # ==================== Logs ====================
        "logs": {
            "basic": {
                "title": "日志",
                "description": "查看和管理系统日志"
            },
            "index": {
                "logs_title": "系统日志",
                "refresh": "刷新",
                "logs_types": "日志类型",
                "logs_info": "日志信息",
                "logs_about": "关于系统日志",
                "logs_description": "在这里您可以查看和分析系统、应用程序和服务日志。",
                "logs_how_to_use": "如何使用：",
                "logs_step1": "从左侧列表中选择日志类型",
                "logs_step2": "选择特定的日志文件",
                "logs_step3": "使用过滤器搜索特定条目",
                "logs_types": "日志类型",
                "logs_info": "日志信息",
                "logs_about": "关于系统日志",
                "logs_description": "在这里您可以查看和分析系统、应用程序和服务日志。",
                "logs_how_to_use": "如何使用：",
                "logs_step1": "从左侧列表中选择日志类型",
                "logs_step2": "选择特定的日志文件",
                "logs_step3": "使用过滤器搜索特定条目"
            },
            "view": {
                "download": "下载",
                "logs_files": "日志文件",
                "logs_no_files": "没有可用的日志文件",
                "logs_filters": "日志过滤器",
                "logs_level": "日志级别",
                "all_levels": "所有级别",
                "log_levels": {
                    "DEBUG": "调试",
                    "INFO": "信息",
                    "WARNING": "警告",
                    "ERROR": "错误",
                    "CRITICAL": "严重"
                },
                "logs_source": "来源",
                "logs_source_placeholder": "模块或服务名称",
                "logs_search": "搜索",
                "logs_search_placeholder": "在日志中搜索文本",
                "apply_filters": "应用过滤器",
                "logs_no_file_selected": "未选择文件",
                "logs_top": "顶部",
                "logs_bottom": "底部",
                "logs_time": "时间",
                "logs_message": "消息",
                "logs_no_entries": "日志中没有条目",
                "logs_entries_shown": "显示条目",
                "refresh":"刷新"
            }
        },

        # ==================== NETWORK ====================
        'network': {
            'basic': {
                'title': '网络连接',
                'description': '网络接口管理'
            }
        },

        # ==================== VPN ====================
        'vpn': {
            'basic': {
                'title': 'VPN 连接和客户端',
                'description': 'VPN 管理'
            },

            "index": {
                "vpn_title": "VPN",
                "refresh": "刷新",
                "vpn_status": "VPN 状态",
                "details": "详情",
                "vpn_installed": "已安装",
                "yes": "是",
                "no": "否",
                "vpn_version": "版本",
                "vpn_connected": "已连接",
                "vpn_quick_actions": "快速操作",
                "vpn_disconnect": "断开连接",
                "vpn_connect": "连接",
                "vpn_restart": "重启",
                "vpn_not_installed": "SoftEther VPN 未安装",
                "vpn_install_instructions": "VPN 使用需要安装 SoftEther VPN 客户端",
                "vpn_download": "下载 SoftEther",
                "vpn_info_title": "VPN 信息",
                "vpn_technical_info": "技术信息",
                "vpn_os": "操作系统",
                "vpn_installation_details": "安装说明",
                "vpn_windows_instructions": "1. 下载并安装适用于 Windows 的 SoftEther VPN 客户端\n2. 启动程序并配置连接",
                "vpn_linux_instructions": "1. 通过您的包管理器安装 softether-vpnclient 包\n2. 在终端中配置连接",
                "vpn_mac_instructions": "1. 下载并安装适用于 macOS 的 SoftEther VPN 客户端\n2. 在程序中配置连接",
                "vpn_management": "VPN 管理",
                "vpn_configure": "配置",
                "vpn_uninstall": "卸载",
                "vpn_not_installed_instructions": "VPN 管理首先需要安装客户端"
            }
        },

        # ==================== UPDATES ====================
        'updates': {
            'basic': {
                'title': '更新',
                'description': '更新信息'
            },
            'index':{
                'updates_status_title': '更新状态',
                'check_updates': '检查更新',
                'update_status': '更新状态',
                'project': '项目',
                'last_update': '最后更新',
                'status': '状态',
                'actions': '操作',
                'never_updated': '从未更新',
                'update_now': '立即更新',
                'checking': '检查中...',
                'updating': '更新中...',
                'up_to_date': '最新',
                'recently_updated': '最近更新',
                'update_available': '有可用更新',
                'updates_check_success': '更新检查成功',
                'project_not_found': '未找到项目',
                'update_started': '更新已开始',
                'view_history': '历史',
                'no_projects_configured': '未配置项目',
                'configure_projects_in_config': '在配置中配置项目',
                'check_all_updates': '检查所有更新',
                'updates_check_started': '更新检查已开始'
            }
        },
    
        # ==================== SERVICE ====================
        'service': {
            'basic': {
                'title': "服务",
                "description": "服务和任务管理"
            },
            'index': {
                "service_title": "服务管理",
                "refresh": "刷新",
                "service_status": "服务状态",
                "details": "详情",
                "service_name": "服务名称",
                "service_installed": "服务已安装",
                "yes": "是",
                "no": "否",
                "service_running": "服务运行中",
                "service_autostart": "自动启动",
                "service_actions": "服务操作",
                "service_stop": "停止",
                "service_restart": "重启",
                "service_start": "启动",
                "service_disable_autostart": "禁用自动启动",
                "service_enable_autostart": "启用自动启动",
                "service_uninstall": "卸载服务",
                "service_install": "安装服务",
                "scheduled_tasks": "定时任务",
                "add_task": "添加任务",
                "task_name": "任务名称",
                "task_schedule": "计划",
                "task_command": "命令",
                "task_status": "任务状态",
                "actions": "操作",
                "no_tasks_configured": "未配置任务",
                "add_scheduled_task": "添加定时任务",
                "hourly": "每小时",
                "daily": "每日",
                "weekly": "每周",
                "monthly": "每月",
                "custom": "自定义",
                "custom_schedule": "自定义计划",
                "cron_format_help": "Cron 格式：分钟 小时 日 月 周几",
                "cancel": "取消",
                "save_task": "保存任务",
                "confirm_install_service": "确定要安装服务吗？",
                "service_installed_successfully": "服务安装成功",
                "service_installation_failed": "服务安装失败",
                "request_failed": "请求失败",
                "confirm_uninstall_service": "确定要卸载服务吗？",
                "service_uninstalled_successfully": "服务卸载成功",
                "service_uninstallation_failed": "服务卸载失败",
                "action_completed_successfully": "操作成功完成",
                "action_failed": "操作失败",
                "task_added_successfully": "任务添加成功",
                "task_addition_failed": "任务添加失败",
                "active": "活跃",
                "status": "状态",
                "service_diagnose": "诊断",
                "service_diagnosis": "服务诊断",
                "diagnosing_service": "诊断服务...",
                "diagnosis_results": "诊断结果",
                "diagnosis_completed": "诊断完成",
                "diagnosis_failed": "诊断失败",
                "problems_detected": "检测到问题",
                "detailed_status": "详细状态",
                "journal_logs": "日志",
                "service_configuration": "服务配置",
                "permissions": "权限",
                "paths": "路径",
                "errors": "错误",
                "copy_to_clipboard": "复制到剪贴板",
                "copied_to_clipboard": "已复制到剪贴板",
                "copy_failed": "复制失败",
                "installed": "已安装",
                "running":"运行中",
                "enabled":"已启用",
                "close": "关闭",
                "loading":"加载"
            }
        },

        # ==================== SETTINGS ====================
        'settings': {
            'basic': {
                'title': "设置",
                "description": "项目和 Docker 环境配置"
            },
            'index': {
                "settings_title": "项目设置",
                "refresh": "刷新",
                "project_settings": "项目参数",

                # project_path
                "project_path": "项目路径",
                "project_path_help": "指定项目目录的绝对路径",

                # docker_files
                "docker_files": "Docker 文件夹",
                "docker_files_help": "包含 .env 和 docker-compose.example.yml 的文件夹路径",
                "docker_env_file": "Docker 环境文件",

                # project_type
                "project_type": "项目类型",
                "environment": "环境",

                # actions
                "validate_paths": "验证路径",
                "save_settings": "保存设置",
                "generate_docker_compose": "生成 Docker Compose",

                # validation blocks
                "project_validation": "项目验证",
                "docker_validation": "Docker 文件验证",
                "validate_docker": "验证 Docker",
                "run_validation_to_see_results": "运行验证以查看结果",

                # statuses
                "settings_saved_successfully": "设置保存成功",
                "settings_save_failed": "设置保存失败",
                "docker_compose_generated_successfully": "docker-compose.yml 生成成功",
                "docker_compose_generation_failed": "docker-compose.yml 生成失败",
                "request_failed": "请求失败",
                "confirm_generate_docker_compose": "确定要生成 docker-compose.yml 吗？",

                # env editor
                "env_editor_title": "环境变量编辑器",
                "environment_variables": "环境变量",
                "variable_name": "变量名称",
                "variable_value": "变量值",
                "actions": "操作",
                "add_variable": "添加变量",
                "save_env": "保存 .env",
                "generate_docker_compose": "生成 Docker Compose",
                "env_saved_successfully": "文件 .env 保存成功",
                "env_save_failed": "保存 .env 文件时出错",
                "docker_env_editor": "Docker 环境变量编辑器"
            }
        }
    }
}