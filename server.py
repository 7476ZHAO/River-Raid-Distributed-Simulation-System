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
    "ai_x": 0,
    "ai_y": 150,
    "bullets": [],
    "enemies": [],
    "river_left": -150,
    "river_right": 150
}

player_lock = threading.Lock()


# -----------------------------
# AI random action thread
# -----------------------------
def ai_action_thread():
    while True:
        game_state["ai_move"] = random.choice(["H", "J", "B", "NONE"])
        time.sleep(0.15)


# -----------------------------
# Game Logic Thread
# -----------------------------
def game_logic_thread():
    while True:
        # -------------------------
        # 1. Read player action from file
        # -------------------------
        if os.path.exists(PLAYER_ACTION_FILE):
            with open(PLAYER_ACTION_FILE, "r") as f:
                player_action = f.read().strip()
        else:
            player_action = "NONE"

        # -------------------------
        # 2. Update player
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
            game_state["bullets"].append([game_state["player_x"], game_state["player_y"] + 20])

        # -------------------------
        # 3. Update AI
        # -------------------------
        ai_move = game_state.get("ai_move", "NONE")

        if ai_move == "H":  # left
            game_state["ai_x"] -= 10
        elif ai_move == "J":  # right
            game_state["ai_x"] += 10
        elif ai_move == "B":  # fire
            game_state["bullets"].append([game_state["ai_x"], game_state["ai_y"] - 20])

        # -------------------------
        # 4. Move bullets
        # -------------------------
        for b in game_state["bullets"]:
            b[1] += 15
        game_state["bullets"] = [b for b in game_state["bullets"] if b[1] < 300]

        # -------------------------
        # 5. Random enemies
        # -------------------------
        if random.random() < 0.03:
            game_state["enemies"].append([random.randint(-120, 120), 300])

        for e in game_state["enemies"]:
            e[1] -= 5
        game_state["enemies"] = [e for e in game_state["enemies"] if e[1] > -300]

        # -------------------------
        # 6. Write game_state.json
        # -------------------------
        with open(GAME_STATE_FILE, "w") as f:
            json.dump(game_state, f)

        time.sleep(0.03)


# -----------------------------
# Start threads
# -----------------------------
print("Server running with AI thread + Game logic thread")

t1 = threading.Thread(target=ai_action_thread, daemon=True)
t2 = threading.Thread(target=game_logic_thread, daemon=True)

t1.start()
t2.start()

# Keep server alive
while True:
    time.sleep(1)
