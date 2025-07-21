# inventory.py (converted for Application API)

from storage import database as db

def use_item(user_id, item_name):
    inventory = db.get_inventory(user_id)

    if item_name not in inventory:
        return "❌ You don’t have that item."

    if db.is_item_on_cooldown(user_id, item_name):
        return "⏳ That item is still cooling down. Try again later."

    response = "🌀 Nothing happens. Maybe it’s a fake?"

    # 🧠 Effects for Known Items
    if item_name == "truth_crystal":
        all_roles = db.reveal_all_roles()
        response = "🔍 *Truth Revealed:*\n" + "\n".join(all_roles)

    elif item_name == "shadow_ring":
        db.grant_immunity(user_id)
        response = "🕳 You are now immune to death for one night."

    elif item_name == "goat_scroll":
        db.trigger_goat_prophecy()
        response = "🐐 A ghostly goat bellows... destiny shifts."

    elif item_name == "core_key":
        if db.check_nexus_control(user_id):
            db.set_nexus_winner(user_id)
            response = "⚙️ You activated the Core Key. Nexus Guild wins!"
        else:
            response = "The Core is not aligned. The key does nothing..."

    # 🕒 Set Cooldown and Remove Item
    db.set_item_cooldown(user_id, item_name, duration=120)  # 2 minutes cooldown
    db.remove_item(user_id, item_name)

    return response

def describe_item(item_name):
    descriptions = {
        "relic": "🪙 A mysterious fragment of Aether. Required for certain wins.",
        "truth_crystal": "🔍 Reveals all roles when used.",
        "shadow_ring": "🕳 Grants temporary death immunity.",
        "goat_scroll": "🐐 Calls the Goat Prophecy...",
        "core_key": "⚙️ Nexus Guild can use this to trigger victory."
    }
    return descriptions.get(item_name, "❓ An unknown item.")
