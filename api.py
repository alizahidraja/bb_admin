"""bb_admin API — whitelisted methods for the manager facade.

SECURITY MODEL (per AUDIT_FINDINGS.md F1): the "Branch Tech Manager" role is
granted NO doc-level permissions. Every method here self-authorizes
(_check_manager), resolves the caller's branch, validates inputs, and writes
with ignore_permissions=True. Whitelisted methods are reachable by any session
user, so the role check is mandatory — never rely on @frappe.whitelist as a gate.
"""
import frappe
from frappe import _
from frappe.utils.password import update_password

MANAGER_ROLES = ("Branch Tech Manager", "System Manager", "Administrator")


def _check_manager():
    roles = frappe.get_roles()
    if not any(r in MANAGER_ROLES for r in roles):
        frappe.throw(_("Not permitted"), frappe.PermissionError)


def _branch():
    """Resolve the current user's branch via the URY User child table."""
    rows = frappe.db.sql(
        "SELECT b.branch FROM `tabURY User` a INNER JOIN `tabBranch` b ON a.parent = b.name WHERE a.user = %s",
        frappe.session.user,
        as_dict=True,
    )
    if not rows:
        frappe.throw(_("No branch assigned to this user"), frappe.PermissionError)
    return rows[0].branch


def _active_menu():
    branch = _branch()
    restaurant = frappe.db.get_value("URY Restaurant", {"branch": branch}, "name")
    if not restaurant:
        frappe.throw(_("No restaurant configured for this branch"))
    menu = frappe.db.get_value("URY Restaurant", restaurant, "active_menu")
    if not menu:
        frappe.throw(_("No active menu set"))
    return menu, restaurant


@frappe.whitelist()
def get_home():
    _check_manager()
    branch = _branch()
    menu, restaurant = _active_menu()
    item86 = frappe.db.count("URY Menu Item", {"parent": menu, "disabled": 1})
    return {
        "branch": branch,
        "restaurant": restaurant,
        "menu": menu,
        "items_86": item86,
    }


@frappe.whitelist()
def get_menu():
    _check_manager()
    menu, _ = _active_menu()
    items = frappe.get_all(
        "URY Menu Item",
        filters={"parent": menu},
        fields=["item", "item_name", "rate", "course", "disabled", "special_dish"],
        order_by="course, item_name",
    )
    for i in items:
        i["image"] = frappe.db.get_value("Item", i["item"], "image")
    return {"menu": menu, "items": items}


@frappe.whitelist()
def set_availability(item, available):
    _check_manager()
    menu, _ = _active_menu()
    row = frappe.db.get_value("URY Menu Item", {"parent": menu, "item": item}, "name")
    if not row:
        frappe.throw(_("Item not in this menu"))
    frappe.db.set_value("URY Menu Item", row, "disabled", 0 if available else 1)
    return {"item": item, "available": bool(available)}


@frappe.whitelist()
def upsert_item(item, name=None, price=None):
    _check_manager()
    menu, _ = _active_menu()
    if not frappe.db.exists("Item", item):
        frappe.throw(_("Unknown item"))

    if name:
        frappe.db.set_value("Item", item, "item_name", name)

    row = frappe.db.get_value("URY Menu Item", {"parent": menu, "item": item}, "name")
    if row:
        updates = {}
        if name:
            updates["item_name"] = name
        if price is not None:
            updates["rate"] = float(price)
        if updates:
            frappe.db.set_value("URY Menu Item", row, updates)
    else:
        frappe.get_doc(
            {
                "doctype": "URY Menu Item",
                "parent": menu,
                "parenttype": "URY Menu",
                "parentfield": "items",
                "item": item,
                "item_name": name or frappe.db.get_value("Item", item, "item_name"),
                "rate": float(price) if price is not None else 0,
                "disabled": 0,
            }
        ).insert(ignore_permissions=True)

    return {"ok": 1, "item": item}


@frappe.whitelist()
def get_sales_pnl():
    _check_manager()
    branch = _branch()
    pnl = frappe.get_all(
        "URY Daily P and L",
        filters={"branch": branch},
        fields=["date", "gross_sales", "net_sales", "cogs", "total_direct_expenses", "gross_profit", "other_expenses"],
        order_by="date desc",
        limit_page_length=1,
    )
    return {"pnl": pnl[0] if pnl else None}


@frappe.whitelist()
def add_staff(name, role, pin=None):
    _check_manager()
    if role not in ("URY Cashier", "URY Captain", "URY Manager"):
        frappe.throw(_("Invalid role"))
    email = f"{name.lower().replace(' ', '.')}@bunbites.pk"
    if not frappe.db.exists("User", email):
        u = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": name,
                "send_welcome_email": 0,
                "enabled": 1,
                "roles": [{"role": role}],
            }
        )
        u.insert(ignore_permissions=True)
    if pin:
        update_password(email, pin)
    # link to branch + room
    branch = _branch()
    b = frappe.get_doc("Branch", branch)
    if not any(x.user == email for x in b.user):
        b.append("user", {"user": email, "room": "Main Dining"})
        b.save(ignore_permissions=True)
    return {"ok": 1, "email": email, "role": role}


@frappe.whitelist()
def reset_pin(email, pin=None):
    _check_manager()
    from frappe.utils import random_string

    pin = pin or random_string(4, "0123456789")
    update_password(email, pin)
    return {"email": email, "pin": pin}
