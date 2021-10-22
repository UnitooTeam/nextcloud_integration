# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "nextcloud_integration"
app_title = "Nextcloud Integration"
app_publisher = "Frappe"
app_description = "Frappe App for NextCloud Backup"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "developers@frappe.io"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/nextcloud_integration/css/nextcloud_integration.css"
# app_include_js = "/assets/nextcloud_integration/js/nextcloud_integration.js"

# include js, css files in header of web template
# web_include_css = "/assets/nextcloud_integration/css/nextcloud_integration.css"
# web_include_js = "/assets/nextcloud_integration/js/nextcloud_integration.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "nextcloud_integration/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "nextcloud_integration.install.before_install"
# after_install = "nextcloud_integration.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "nextcloud_integration.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }
doc_events = {
    "Event": {
        "after_insert": "frappe.integrations.doctype.nextcloud_calendar.nextcloud_calendar.insert_event_in_nextcloud_calendar",
        "on_update": "frappe.integrations.doctype.nextcloud_calendar.nextcloud_calendar.update_event_in_nextcloud_calendar",
        "on_trash": "frappe.integrations.doctype.nextcloud_calendar.nextcloud_calendar.delete_event_from_nextcloud_calendar",
    },
}

# Scheduled Tasks
# ---------------

scheduler_events = {
    # 	"all": [
    # 		"nextcloud_integration.tasks.all"
    # 	],
    "daily": [
        "nextcloud_integration.nextcloud_integration.doctype.nextcloud_setting.nextcloud_setting.daily_backup",
        "frappe.integrations.doctype.google_contacts.google_contacts.sync",
    ],
    "hourly": [
        "frappe.integrations.doctype.nextcloud_calendar.nextcloud_calendar.sync",
    ],
    "weekly": [
        "nextcloud_integration.nextcloud_integration.doctype.nextcloud_setting.nextcloud_setting.weekly_backup"
    ],
    # 	"monthly": [
    # 		"nextcloud_integration.tasks.monthly"
    # 	]
}

# Testing
# -------

# before_tests = "nextcloud_integration.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "nextcloud_integration.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "nextcloud_integration.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]
