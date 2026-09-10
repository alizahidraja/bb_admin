# bb_admin hooks
app_name = "bb_admin"
app_title = "Manager"
app_publisher = "Entropic Technologies PK LTD"
app_description = "Icon/photo-led no-code facade for the Branch Tech Manager (menu, staff, sales, cash, setup)."
app_email = "support@entropictech.pk"
app_license = "MIT"

# Route the Branch Tech Manager straight to the facade; owner/admin land on the Desk.
role_home_page = {
    "Branch Tech Manager": "bb-admin",
}

# The manager role is granted NO doc-level permissions. The facade's api.py
# self-authorizes every call (see AUDIT_FINDINGS.md F1) and writes with
# ignore_permissions=True, so the Desk stays locked even if a manager reaches it.
app_include_js = []
app_include_css = []

doc_events = {}

fixtures = []
