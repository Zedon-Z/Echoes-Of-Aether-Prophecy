# win.py (converted for Application API)

from storage import database as db

def check_for_winner(chat_id):
    players = db.get_alive_players(chat_id)

    if not players:
        return "💀 Everyone perished. The void claims Aether."

    factions = [db.get_player_faction(pid) for pid in players]
    roles = {pid: db.get_user_role(pid) for pid in players}
    unique_factions = set(factions)

    # 🟣 1. GOAT WIN — Survive till final 3
    for pid in players:
        if roles[pid] == "Goat" and len(players) <= 3:
            return f"🐐 @{db.get_username(pid)} (Goat) wins by surviving until the Final 3!"

    # 🟡 2. ARCHIVIST RELIC WIN
    for pid in players:
        if roles[pid] == "Archivist" and db.get_relic_count(pid) >= 3:
            return f"📚 @{db.get_username(pid)} (Archivist) wins by collecting 3 relics!"

    # 🧵 3. PUPPETMASTER THREAD WIN
    for pid in players:
        if roles[pid] == "Puppetmaster" and db.used_thread(pid):
            return f"🧵 @{db.get_username(pid)} (Puppetmaster) wins via total mind control!"

    # ⚙️ 4. NEXUS WIN CONDITION
    for pid in players:
        if roles[pid] == "Ascended" and db.check_nexus_control(pid):
            db.set_nexus_winner(pid)
            return f"⚙️ Nexus Manipulation! @{db.get_username(pid)} (Ascended) triggers Core Hijack Victory!"

    # 🏆 5. FACTIONAL WIN
    if len(unique_factions) == 1:
        faction = unique_factions.pop()
        return f"🏆 {faction} claims the world of Aether. All others perished!"

    # 🌌 6. FINAL ECHO OUTCOME
    if db.is_final_echo_active(chat_id):
        dominant_echo = db.get_dominant_echo_vote(chat_id)

        if dominant_echo == "destroy_the_core":
            top_betrayer = db.get_top_betrayer(chat_id)
            if top_betrayer:
                return f"💥 Chaos wins! @{db.get_username(top_betrayer)} becomes the *True Echo of Destruction*."
            return "💥 Chaos reigns. The world is destroyed. No victors remain."

        elif dominant_echo == "save_the_core":
            return "🕊️ Hope prevails. The Core survives and the Luminae ascend!"

        elif dominant_echo == "escape_the_core":
            escapers = db.get_escapees(chat_id)
            if escapers:
                names = ", ".join(f"@{db.get_username(uid)}" for uid in escapers)
                return f"🚀 Escapees: {names} survived the collapse!"
            return "🚀 A few managed to escape. Aether's future is... unknown."

    # ❌ 7. No Winner Yet
    return None
