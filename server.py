import json
import random
import time
import threading
import os

# -----------------------------
# Shared memory paths on VPS
# -----------------------------
PLAYER_ACTION_FILE = "/tmp/player_action"
GAME_STATE_FILE = "/tmp/game_state.json"

# -----------------------------
# Initial game state
# -----------------------------
game_state = {
    "player_x": 0,
    "player_y": -200,
    "bullets": [],       # [x, y, dy]
    "enemies": [],       # [x, y, last_shot_time]
    "river_left": -150,
    "river_right": 150
}

state_lock = threading.Lock()

# -----------------------------
# Settings
# -----------------------------
ENEMY_FIRE_INTERVAL = 3.0  # seconds
MAX_ENEMIES = 10           # limit number of enemies
MAX_BULLETS = 30           # limit number of bullets

# -----------------------------
# Game Logic Thread
# -----------------------------
def game_logic_thread():
    while True:
        # 1. Read player action
        if os.path.exists(PLAYER_ACTION_FILE):
            with open(PLAYER_ACTION_FILE, "r") as f:
                player_action = f.read().strip()
            # Reset action
            with open(PLAYER_ACTION_FILE, "w") as f:
                f.write("NONE")
        else:
            player_action = "NONE"

        with state_lock:
            # -------------------------
            # Update player
            # -------------------------
            if player_action == "LEFT":
                game_state["player_x"] -= 10
            elif player_action == "RIGHT":
                game_state["player_x"] += 10
            elif player_action == "UP":
                game_state["player_y"] += 10
            elif player_action == "DOWN":
                game_state["player_y"] -= 10
            elif player_action == "FIRE":
                game_state["bullets"].append([game_state["player_x"], game_state["player_y"] + 20, 15])

            # Keep player inside river
            game_state["player_x"] = max(game_state["river_left"] + 10,
                                         min(game_state["river_right"] - 10, game_state["player_x"]))
            game_state["player_y"] = max(-300, min(300, game_state["player_y"]))

            # -------------------------
            # Spawn enemies randomly (with limit)
            # -------------------------
            if len(game_state["enemies"]) < MAX_ENEMIES and random.random() < 0.03:
                game_state["enemies"].append([random.randint(-120, 120), 300, time.time()])

            # -------------------------
            # Move enemies and shoot
            # -------------------------
            now = time.time()
            for e in game_state["enemies"]:
                e[1] -= 5  # move down
                # Enemy shooting
                if now - e[2] > ENEMY_FIRE_INTERVAL:
                    game_state["bullets"].append([e[0], e[1] - 20, -15])
                    e[2] = now

            # Remove off-screen enemies
            game_state["enemies"] = [e for e in game_state["enemies"] if e[1] > -300]

            # -------------------------
            # Move bullets
            # -------------------------
            for b in game_state["bullets"]:
                b[1] += b[2]  # dy

            # Remove off-screen bullets
            game_state["bullets"] = [b for b in game_state["bullets"] if -300 < b[1] < 300]

            # Limit total bullets for performance
            game_state["bullets"] = game_state["bullets"][:MAX_BULLETS]

            # -------------------------
            # Collision: player bullets vs enemies
            # -------------------------
            new_bullets = []
            for b in game_state["bullets"]:
                hit = False
                if b[2] > 0:  # player bullet
                    for e in game_state["enemies"]:
                        if abs(b[0] - e[0]) < 15 and abs(b[1] - e[1]) < 15:
                            hit = True
                            game_state["enemies"].remove(e)
                            break
                if not hit:
                    new_bullets.append(b)
            game_state["bullets"] = new_bullets

            # -------------------------
            # Collision: enemy bullets vs player
            # -------------------------
            player_hit = False
            new_bullets = []
            for b in game_state["bullets"]:
                if b[2] < 0:  # enemy bullet
                    if abs(b[0] - game_state["player_x"]) < 15 and abs(b[1] - game_state["player_y"]) < 15:
                        player_hit = True
                        continue  # remove bullet
                new_bullets.append(b)
            game_state["bullets"] = new_bullets

            if player_hit:
                # Reset player to start
                game_state["player_x"] = 0
                game_state["player_y"] = -200

            # -------------------------
            # Write game state to file
            # -------------------------
            with open(GAME_STATE_FILE, "w") as f:
                json.dump(game_state, f)

        time.sleep(0.03)


# -----------------------------
# Start threads
# -----------------------------
t = threading.Thread(target=game_logic_thread, daemon=True)
t.start()

print("Server running...")

while True:
    time.sleep(1)