translations = {
    # ==================== COMMON VARIABLES ====================
    "common":{
        # Language settings
        "this_language": "English",
        "this_language_code": "en",
        "this_language_select_text": "Select language",

        # Error messages when translations are missing
        "this_error_missing_common": "[{lang}] Translation missing: common['{key}']",
        "this_error_missing_section": "[{lang}] Translation missing: sections['{section}']['?']['{key}']",
        "this_error_invalid_section": "[{lang}] Invalid module: sections['{section}'] is not a dictionary",
        "this_error_missing_main": "[{lang}] Translation missing: main['{section}']['{key}']",
        "this_error_missing_main_section": "[{lang}] Section missing: main['{section}'] does not exist",
        "this_error_invalid_key": "[{lang}] Invalid key: '{key}' (expected section_key or section_file_key)"
    },

    # ==================== MAIN TEMPLATE VARIABLES (Files in templates folder) ====================

    "main":{
        # ==================== MAIN LAYOUT ====================
        "layout":{
            "default_title": "Starter", # Project name denoting a car part (find equivalent in target language when translating)
            "system_info": "System Information",
            "logout_button": "Logout",
            "logout_error": "Logout error",
            "unauthorized_access": "Unauthorized access. Please log in again.",
            "network_error": "Network error. Please check your connection."
        },

        # ==================== FOOTER ====================
        "footer":{
            "copyright": "© 2025 MyIDon.SITE. All rights reserved."
        },

        # ==================== AUTHENTICATION ====================
        "login":{
            "username_label": "Username",
            "password_label": "Password",
            "submit_button": "Login",
            "network_error": "Network error. Please check your connection.",
            "error_occurred": "An error occurred",
            "missing_credentials": "Username and password are required",
            "invalid_credentials": "Invalid credentials",
            "auth_not_configured": "Authentication system not configured"
        },

        # ==================== LANGUAGE CHANGE ====================

        "changeLanguage":{
            "selector_label": "Language selection",
            "no_languages": "No languages available",
            "network_error": "Network error. Please check your connection.",
            "change_failed": "Failed to change language",
            "unknown_error": "An unknown error occurred",
            "language_changed": "Language changed successfully",
            "invalid_language": "Invalid language",
        },

        # ==================== MAIN CONTROL PANEL ====================
        "controlPanel":{
            "loading": "Loading...",
            "action_error": "Action execution error",
            "section_error": "Module loading error",
            "parse_error": "Data parsing error",
            "status": "Status",
            "error": "Error",
        }
    },

    # ==================== SECTION VARIABLES (Files in templates/sections folder) ====================

    "sections":{

        # ==================== DASHBOARD ====================
        'dashboard': {
            # Basic module settings
            "basic":{
                # Displayed in control panel
                "title":"System",
                "description": "Main information dashboard"
            },

            'index': {
                "dashboard": "Information dashboards",
                "system_info": "System information",
                "system": "System",
                "hostname": "Hostname",
                "os": "Operating system",
                "os_version": "OS version",
                "python_version": "Python version",
                "implementation": "Implementation",
                "current_time": "Current time",
                "uptime": "Uptime",
                "system_uptime": "System uptime",
                "version": "Version",
                "refresh": "Refresh",
                "username": "Username",
                "disk": "Disk",
                "total": "Total",
                "used": "Used",
                "free": "Free",
                "docker_info": "Docker information",
                "docker_status": "Docker status",
                "docker_compose_status": "Docker Compose status",
                "installed": "Installed",
                "not_installed": "Not installed",
                "registry_auth": "Registry authentication",
                "authenticated": "Authenticated",
                "not_authenticated": "Not authenticated",
                "registry_url": "Registry URL",
                "network_info": "Network information",
                "no_ips_found": "No IP addresses found",
                'corporate': 'Corporate',
                'other': 'Other',
                'disabled': 'Disabled',
                'active': 'Active',
                'inactive': 'Inactive',
                'ip_address': 'IP address',
                'netmask': 'Netmask',
                'mac_address': 'MAC address',
                'status': 'Status',
                'external': 'External',
                'default_gateway': 'Default gateway',
                'no_network_interfaces': 'No network interfaces found',
                'domain_setup': 'Domain setup',
                'use_domain': 'Use domain name',
                'domain_name': 'Domain name',
                'domain_name_placeholder': 'Enter your domain name (e.g., example.com)',
                'domain_saved': 'Domain name saved',
                'domain_error': 'Error saving domain name',
                'domain_access_setup': 'Domain access setup',
                'domain_access_success': 'Domain access successfully configured',
                'domain_access_error': 'Error configuring domain access',
                "cpu": "Processor",
                "processor": "Model",
                "cores": "cores",
                "logical": "threads",
                "usage": "Usage",
                "memory": "Memory",
                "total": "Total",
                "used": "Used",
                "available": "Available",
                "install": "Install",
                "package_installation": "Package installation",
                "close": "Close",
                "loading": "Loading",
                "preparing_installation": "Preparing installation",
                "installation_logs": "Installation logs",
                "finish": "Finish",
                "download_logs": "Download logs",
                "confirm_install_package": "Confirm package installation",
                "starting_installation": "Starting installation",
                "installation_completed_success": "Installation completed successfully!",
                "installation_failed": "Installation failed",
                "log_request_failed": "Failed to retrieve logs",
                "start_install_failed": "Failed to start installation",
                "request_failed": "Request failed",
                "compiler":"Compiler",
                'install_docker_from_dashboard': 'Install Docker from Dashboard',
                'go_to_dashboard': 'Go to Dashboard',
                'install_from_dashboard': 'Install from Dashboard'
            }
        },

        # ==================== DOCKER ====================
        'docker':{

            "basic": {
                "title": "Docker",
                "description": "Container management"
            },

            'info': {
                "docker_info": "Docker information",
                "docker_status": "Docker status",
                "docker_compose_status": "Docker Compose status",
                "registry_auth": "Registry authentication",
                "registry_url": "Registry URL",
                "installed": "Installed",
                "not_installed": "Not installed",
                "authenticated": "Authenticated",
                "not_authenticated": "Not authenticated",
                "docker_restarted_successfully": "Docker restarted successfully",
                "failed_to_restart_docker": "Failed to restart Docker",
                "system_pruned_successfully": "Docker system pruned successfully",
                "failed_to_prune_system": "Failed to prune Docker system",
                "docker_dashboard": "Docker Dashboard",
                "refresh": "Refresh",
                "docker_version": "Docker version",
                "last_updated": "Last updated",
                "containers": "Containers",
                "total": "Total",
                "running": "Running",
                "stopped": "Stopped",
                "images": "Images",
                "total_images": "Total images",
                "disk_usage": "Disk usage",
                "resources": "Resources",
                "cpu_usage": "CPU usage",
                "memory_usage": "Memory usage",
                "docker_compose": "Docker Compose",
                "projects": "Projects",
                "services": "Services",
                "quick_actions": "Quick actions",
                "restart_docker": "Restart Docker",
                "prune_system": "Prune system",
                "confirm_restart_docker": "Are you sure you want to restart Docker? This may stop all running containers.",
                "confirm_prune_system": "Are you sure you want to prune the Docker system? This will remove all unused containers, networks, images, and volumes.",
                "request_failed": "Request failed",
                "install_docker": "Install Docker",
                "confirm_install_docker": "This will install Docker on your system. Continue?",
                "installing": "Installing...",
                "docker_installed_success": "Docker installed successfully! Restart the session.",
                "docker_install_failed": "Docker installation failed. Check logs for details.",
                "download_logs": "Download logs",
                "log_request_failed": "Log request failed",
                "start_install_failed": "Start install failed",
                "close": "Close",
                "refresh": "Refresh",
                "installation_started": "Installation started",
                "docker_installation": "Docker installation",
                "docker_not_installed": "Docker not installed",
                "docker_installation_required": "Docker installation required",
                "install_docker_guide": "Docker installation guide",
                "docker_required_for_actions": "Docker required for actions",
                "loading": "Loading",
                "preparing_installation": "Preparing installation",
                "installation_logs": "Installation logs",
                "finish": "Finish",
                "starting_installation": "Starting installation",
                "installation_completed_success": "Installation completed successfully!",
                "installation_completed_warning": "Installation completed with warnings",
                "installation_failed": "Installation failed",
                "start_project":"Start project",
                # New translations for project start modal
                "project_start_logs": "Project start logs",
                "starting_project": "Starting project...",
                "startup_logs": "Startup logs",
                "project_start_completed": "Project started successfully",
                "project_start_failed": "Project start failed",
                "download_logs": "Download logs",
                "log_request_failed": "Log request failed",
                "close": "Close",
                "finish": "Finish",
                "loading": "Loading",
                "refresh": "Refresh",
                # New translations for history table
                "launch_history": "Launch history",
                "date_time": "Date and time",
                "log_file": "Log file",
                "duration": "Duration",
                "status": "Status",
                "actions": "Actions",
                "loading_history": "Loading history...",
                "no_launch_history": "No launch history",
                "view_logs": "View logs",
                "download_logs": "Download logs",
                "status_success": "Success",
                "status_failed": "Failed",
                "status_running": "Running",
                "status_unknown": "Unknown",
                "seconds": "sec",
                "minutes": "min",
                "size": "Size",
                
                # Statuses for display
                "completed": "Completed",
                "failed": "Failed",
                "in_progress": "In progress",
                
                # Actions
                "open_logs": "Open logs",
                "copy_name": "Copy name",
                "delete_log": "Delete log",
                "confirm_delete_log": "Are you sure you want to delete this log file?",
                "log_deleted_success": "Log file deleted successfully",
                "log_deleted_error": "Error deleting log file",
                "open_logs": "Open logs",
                "copy_name": "Copy name",
                "delete_log": "Delete log",
                "view_logs": "View logs",
                "download_logs": "Download logs",
                "log_content": "Log content",
                "close": "Close"
            },

            'containers': {
                "containers": "Containers",
                "refresh": "Refresh",
                "show_all": "Show all",
                "name": "Name",
                "image": "Image",
                "status": "Status",
                "ports": "Ports",
                "running_for": "Running for",
                "size": "Size",
                "actions": "Actions",
                "stop": "Stop",
                "restart": "Restart",
                "start": "Start",
                "remove": "Remove",
                "view_logs": "View logs",
                "no_containers_found": "No containers found",
                "confirm_remove_container": "Are you sure you want to remove the container?",
                "request_failed": "Request failed",
                "docker_not_installed": "Docker not installed",
                "docker_required_for_containers": "Docker required for container management",
                "install_docker_guide": "Docker installation guide"
            },

            'volumes': {
                "volumes": "Volumes",
                "refresh": "Refresh",
                "name": "Name",
                "driver": "Driver",
                "scope": "Scope",
                "mountpoint": "Mount point",
                "labels": "Labels",
                "created": "Created",
                "no_volumes_found": "No volumes found"
            },

            'networks': {
                "networks": "Networks",
                "refresh": "Refresh",
                "name": "Name",
                "driver": "Driver",
                "scope": "Scope",
                "ipv6": "IPv6",
                "internal": "Internal",
                "created": "Created",
                "no_networks_found": "No networks found"
            },

            'logs': {
                "logs": "Logs",
                "select_container": "Select container",
                "refresh": "Refresh",
                "logs_for_container": "Logs for container",
                "select_container_to_view_logs": "Select a container to view logs"
            },

            'images': {
                "images": "Images",
                "refresh": "Refresh",
                "repository": "Repository",
                "tag": "Tag",
                "image_id": "Image ID",
                "created": "Created",
                "size": "Size",
                "actions": "Actions",
                "remove": "Remove",
                "no_images_found": "No images found",
                "confirm_remove_image": "Are you sure you want to remove this image?",
                "request_failed": "Request failed"
            }
        },

        # ==================== Port Knocking ====================
        'knocking':{

            'title':"Port Knocking",

            "index": {
                "knocking_title": "Port Knocking",
                "knocking_status": "Status",
                "knocking_ports": "Port sequence", 
                "knocking_timeout": "Timeout",
                "knocking_description": "Method to open ports through a sequence of connections",
                "knocking_how_it_works": "How it works",
                "knocking_step1": "1. Configure port sequence",
                "knocking_step2": "2. Connect to ports in sequence",
                "knocking_step3": "3. The required port opens automatically",
                "active": "Active",
                "inactive": "Inactive", 
                "seconds": "sec.",
                "refresh": "Refresh",
                "start_service": "Start service",
                "stop_service": "Stop service",
                "service_started": "Service started",
                "service_stopped": "Service stopped",
                "install":"Install",
                "knocking_not_installed": "Port Knocking not installed",
                "knocking_install_instructions": "Click the button below to install the Port Knocking service",
                "knocking_already_installed": "Port Knocking already installed",
                "knocking_install_success": "Port Knocking installed successfully",
                "knocking_install_failed": "Failed to install Port Knocking",
                "knocking_install_error": "Error during installation",
            },

            "info": {
                "title": "Port Knocking Information",
                "about": "About the technology",
                "what_is": "What is it?",
                "definition": "Security technique for hiding port opening",
                "benefits": "Benefits",
                "benefit1": "Additional security layer",
                "benefit2": "Hiding from port scanners", 
                "benefit3": "Dynamic access management",
                "limitations": "Limitations",
                "limit1": "Requires client configuration",
                "limit2": "Possible replay attacks",
                "limit3": "Configuration complexity",
                "current_config": "Current settings",
                "configure_btn": "Configure",
                "active_status": "Active",
                "inactive_status": "Disabled"
            },

            "settings": {
                "title": "Port Knocking Settings",
                "configuration": "Configuration",
                "ports_label": "Ports",
                "ports_help": "Comma-separated (e.g. 1000,2000,3000)",
                "timeout_label": "Timeout (sec)",
                "timeout_help": "Interval between attempts (1-10 sec)",
                "test_section": "Testing",
                "test_description": "Testing port sequence",
                "test_button": "Test",
                "min_ports": "Need at least 2 ports",
                "invalid_timeout": "Allowed 1-10 seconds",
                "save_btn": "Save",
                "save_success": "Settings saved",
                "save_error": "Save error"
            }
        },

        # ==================== Logs ====================
        "logs": {
            "basic": {
                "title": "Logs",
                "description": "View and manage system logs"
            },
            "index": {
                "logs_title": "System logs",
                "refresh": "Refresh",
                "logs_types": "Log types",
                "logs_info": "Log information",
                "logs_about": "About system logs",
                "logs_description": "Here you can view and analyze system, application, and service logs.",
                "logs_how_to_use": "How to use:",
                "logs_step1": "Select log type from the list on the left",
                "logs_step2": "Select specific log file",
                "logs_step3": "Use filters to search for specific entries",
                "logs_types": "Log types",
                "logs_info": "Log information",
                "logs_about": "About system logs",
                "logs_description": "Here you can view and analyze system, application, and service logs.",
                "logs_how_to_use": "How to use:",
                "logs_step1": "Select log type from the list on the left",
                "logs_step2": "Select specific log file",
                "logs_step3": "Use filters to search for specific entries"
            },
            "view": {
                "download": "Download",
                "logs_files": "Log files",
                "logs_no_files": "No log files available",
                "logs_filters": "Log filters",
                "logs_level": "Log level",
                "all_levels": "All levels",
                "log_levels": {
                    "DEBUG": "Debug",
                    "INFO": "Information",
                    "WARNING": "Warning",
                    "ERROR": "Error",
                    "CRITICAL": "Critical"
                },
                "logs_source": "Source",
                "logs_source_placeholder": "Module or service name",
                "logs_search": "Search",
                "logs_search_placeholder": "Text to search in logs",
                "apply_filters": "Apply filters",
                "logs_no_file_selected": "No file selected",
                "logs_top": "Top",
                "logs_bottom": "Bottom",
                "logs_time": "Time",
                "logs_message": "Message",
                "logs_no_entries": "No log entries",
                "logs_entries_shown": "entries shown",
                "refresh":"Refresh"
            }
        },

        # ==================== NETWORK ====================
        'network': {
            'basic': {
                'title': 'Network connections',
                'description': 'Network interface management'
            }
        },

        # ==================== VPN ====================
        'vpn': {
            'basic': {
                'title': 'VPN connections and clients',
                'description': 'VPN management'
            },

            "index": {
                "vpn_title": "VPN",
                "refresh": "Refresh",
                "vpn_status": "VPN status",
                "details": "Details",
                "vpn_installed": "Installed",
                "yes": "Yes",
                "no": "No",
                "vpn_version": "Version",
                "vpn_connected": "Connected",
                "vpn_quick_actions": "Quick actions",
                "vpn_disconnect": "Disconnect",
                "vpn_connect": "Connect",
                "vpn_restart": "Restart",
                "vpn_not_installed": "SoftEther VPN not installed",
                "vpn_install_instructions": "VPN usage requires SoftEther VPN Client installation",
                "vpn_download": "Download SoftEther",
                "vpn_info_title": "VPN information",
                "vpn_technical_info": "Technical information",
                "vpn_os": "Operating system",
                "vpn_installation_details": "Installation instructions",
                "vpn_windows_instructions": "1. Download and install SoftEther VPN Client for Windows\n2. Launch the program and configure the connection",
                "vpn_linux_instructions": "1. Install softether-vpnclient package via your package manager\n2. Configure connection in terminal",
                "vpn_mac_instructions": "1. Download and install SoftEther VPN Client for macOS\n2. Configure connection in the program",
                "vpn_management": "VPN management",
                "vpn_configure": "Configure",
                "vpn_uninstall": "Uninstall",
                "vpn_not_installed_instructions": "VPN management requires client installation first"
            }
        },

        # ==================== UPDATES ====================
        'updates': {
            'basic': {
                'title': 'Updates',
                'description': 'Update information'
            },
            'index':{
                'updates_status_title': 'Update status',
                'check_updates': 'Check for updates',
                'update_status': 'Update status',
                'project': 'Project',
                'last_update': 'Last update',
                'status': 'Status',
                'actions': 'Actions',
                'never_updated': 'Never updated',
                'update_now': 'Update now',
                'checking': 'Checking...',
                'updating': 'Updating...',
                'up_to_date': 'Up to date',
                'recently_updated': 'Recently updated',
                'update_available': 'Update available',
                'updates_check_success': 'Updates checked successfully',
                'project_not_found': 'Project not found',
                'update_started': 'Update started',
                'view_history': 'History',
                'no_projects_configured': 'No projects configured',
                'configure_projects_in_config': 'Configure projects in configuration',
                'check_all_updates': 'Check all updates',
                'updates_check_started': 'Updates check started'
            }
        },
    
        # ==================== SERVICE ====================
        'service': {
            'basic': {
                'title': "Service",
                "description": "Service and task management"
            },
            'index': {
                "service_title": "Service management",
                "refresh": "Refresh",
                "service_status": "Service status",
                "details": "Details",
                "service_name": "Service name",
                "service_installed": "Service installed",
                "yes": "Yes",
                "no": "No",
                "service_running": "Service running",
                "service_autostart": "Autostart",
                "service_actions": "Service actions",
                "service_stop": "Stop",
                "service_restart": "Restart",
                "service_start": "Start",
                "service_disable_autostart": "Disable autostart",
                "service_enable_autostart": "Enable autostart",
                "service_uninstall": "Uninstall service",
                "service_install": "Install service",
                "scheduled_tasks": "Scheduled tasks",
                "add_task": "Add task",
                "task_name": "Task name",
                "task_schedule": "Schedule",
                "task_command": "Command",
                "task_status": "Task status",
                "actions": "Actions",
                "no_tasks_configured": "No tasks configured",
                "add_scheduled_task": "Add scheduled task",
                "hourly": "Hourly",
                "daily": "Daily",
                "weekly": "Weekly",
                "monthly": "Monthly",
                "custom": "Custom",
                "custom_schedule": "Custom schedule",
                "cron_format_help": "Cron format: minute hour day month day_of_week",
                "cancel": "Cancel",
                "save_task": "Save task",
                "confirm_install_service": "Are you sure you want to install the service?",
                "service_installed_successfully": "Service installed successfully",
                "service_installation_failed": "Service installation failed",
                "request_failed": "Request failed",
                "confirm_uninstall_service": "Are you sure you want to uninstall the service?",
                "service_uninstalled_successfully": "Service uninstalled successfully",
                "service_uninstallation_failed": "Service uninstallation failed",
                "action_completed_successfully": "Action completed successfully",
                "action_failed": "Action failed",
                "task_added_successfully": "Task added successfully",
                "task_addition_failed": "Task addition failed",
                "active": "Active",
                "status": "Status",
                "service_diagnose": "Diagnose",
                "service_diagnosis": "Service diagnosis",
                "diagnosing_service": "Diagnosing service...",
                "diagnosis_results": "Diagnosis results",
                "diagnosis_completed": "Diagnosis completed",
                "diagnosis_failed": "Diagnosis failed",
                "problems_detected": "Problems detected",
                "detailed_status": "Detailed status",
                "journal_logs": "Journal logs",
                "service_configuration": "Service configuration",
                "permissions": "Permissions",
                "paths": "Paths",
                "errors": "Errors",
                "copy_to_clipboard": "Copy to clipboard",
                "copied_to_clipboard": "Copied to clipboard",
                "copy_failed": "Copy failed",
                "installed": "Installed",
                "running":"Running",
                "enabled":"Enabled",
                "close": "Close",
                "loading":"Loading"
            }
        },

        # ==================== SETTINGS ====================
        'settings': {
            'basic': {
                'title': "Settings",
                "description": "Project and Docker environment configuration"
            },
            'index': {
                "settings_title": "Project settings",
                "refresh": "Refresh",
                "project_settings": "Project parameters",

                # project_path
                "project_path": "Project path",
                "project_path_help": "Specify absolute path to project directory",

                # docker_files
                "docker_files": "Docker folder",
                "docker_files_help": "Path to folder with .env and docker-compose.example.yml",
                "docker_env_file": "Docker environment file",

                # project_type
                "project_type": "Project type",
                "environment": "Environment",

                # actions
                "validate_paths": "Validate paths",
                "save_settings": "Save settings",
                "generate_docker_compose": "Generate Docker Compose",

                # validation blocks
                "project_validation": "Project validation",
                "docker_validation": "Docker files validation",
                "validate_docker": "Validate Docker",
                "run_validation_to_see_results": "Run validation to see results",

                # statuses
                "settings_saved_successfully": "Settings saved successfully",
                "settings_save_failed": "Settings save failed",
                "docker_compose_generated_successfully": "docker-compose.yml generated successfully",
                "docker_compose_generation_failed": "docker-compose.yml generation failed",
                "request_failed": "Request failed",
                "confirm_generate_docker_compose": "Are you sure you want to generate docker-compose.yml?",

                # env editor
                "env_editor_title": "Environment variables editor",
                "environment_variables": "Environment variables",
                "variable_name": "Variable name",
                "variable_value": "Variable value",
                "actions": "Actions",
                "add_variable": "Add variable",
                "save_env": "Save .env",
                "generate_docker_compose": "Generate Docker Compose",
                "env_saved_successfully": "File .env saved successfully",
                "env_save_failed": "Error saving .env file",
                "docker_env_editor": "Docker Environment Editor"
            }
        }
    }
}