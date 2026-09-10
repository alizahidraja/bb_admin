"""Public menu page for customer ordering (V1 WhatsApp-click).
Served at /menu. Guest-accessible — no login."""
import frappe


def get_context(context):
    context.no_cache = 1
    context.whatsapp_number = "03110177077"
    context.restaurant_name = "BunBites"

    restaurant = frappe.get_all(
        "URY Restaurant", fields=["name", "active_menu"], limit_page_length=1
    )
    items = []
    if restaurant and restaurant[0].active_menu:
        menu = restaurant[0].active_menu
        items = frappe.get_all(
            "URY Menu Item",
            filters={"parent": menu, "disabled": 0},
            fields=["item", "item_name", "rate", "course"],
            order_by="course, item_name",
        )
        for i in items:
            i["image"] = frappe.db.get_value("Item", i["item"], "image")

    # group by course, preserving order
    courses = []
    seen = {}
    for i in items:
        c = i.get("course") or "Menu"
        if c not in seen:
            seen[c] = {"name": c, "items": []}
            courses.append(seen[c])
        seen[c]["items"].append(i)

    context.courses = courses
    context.item_count = len(items)
    return context
