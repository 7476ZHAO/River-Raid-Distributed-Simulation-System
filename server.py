import json
import random
import time
import threading
import os
import sys
import fcntl
from typing import Dict, Tuple, Optional

# -----------------------------
# Shared memory paths on VPS
# -----------------------------
PLAYER_ACTION_FILE = "/tmp/player_action"
GAME_STATE_FILE = "/tmp/game_state.json"
GAME_STATE_TMP_FILE = f"{GAME_STATE_FILE}.tmp"

# -----------------------------
# Gameplay constants
# -----------------------------
RIVER_LEFT = -175
RIVER_RIGHT = 175
PLAYER_MIN_X = -150
PLAYER_MAX_X = 150
PLAYER_SPEED = 8
BULLET_SPEED = 15
MAX_ENEMIES = 8
ENEMY_SPAWN_CHANCE = 0.02  # evaluated every 50 ms

ENEMY_PROPERTIES: Dict[str, Dict[str, float]] = {
    "H": {"speed": 85.0, "score": 100, "radius": 25},  # Helicopter
    "J": {"speed": 110.0, "score": 150, "radius": 25},  # Jet
    "B": {"speed": 60.0, "score": 125, "radius": 40},  # Boat
}

# -----------------------------
# Global state
# -----------------------------
state: Dict[str, object] = {
    "player": {"x": 0.0, "y": -250.0},
    "enemies": [],
    "bullets": [],
    "score": 0,
    "game_over": False,
}

state_lock = threading.Lock()
stop_event = threading.Event()
last_action_nonce = -1


# -----------------------------
# File helpers
# -----------------------------
def ensure_shared_files() -> None:
    """Create shared-memory files and ensure correct permissions."""
    # create main state file
    if not os.path.exists(GAME_STATE_FILE):
        with open(GAME_STATE_FILE, "w", encoding="utf-8") as f:
            f.write(json.dumps(state))
        os.chmod(GAME_STATE_FILE, 0o666)

    # create tmp file ALWAYS
    with open(GAME_STATE_TMP_FILE, "w", encoding="utf-8") as f:
        f.write(json.dumps(state))
    os.chmod(GAME_STATE_TMP_FILE, 0o666)

    # create action file (empty)
    if not os.path.exists(PLAYER_ACTION_FILE):
        with open(PLAYER_ACTION_FILE, "w", encoding="utf-8") as f:
            f.write("")
        os.chmod(PLAYER_ACTION_FILE, 0o666)

def save_state() -> None:
    """Thread-safe and safe against race conditions."""
    with state_lock:
        snapshot = json.dumps(state)

        # ALWAYS create tmp file before replace
        with open(GAME_STATE_TMP_FILE, "w", encoding="utf-8") as tmp:
            tmp.write(snapshot)
        os.chmod(GAME_STATE_TMP_FILE, 0o666)

        # replace atomically (never missing)
        try:
            os.replace(GAME_STATE_TMP_FILE, GAME_STATE_FILE)
        except FileNotFoundError:
            # recreate tmp then replace again
            with open(GAME_STATE_TMP_FILE, "w", encoding="utf-8") as tmp:
                tmp.write(snapshot)
            os.replace(GAME_STATE_TMP_FILE, GAME_STATE_FILE)

        # ensure permissions
        os.chmod(GAME_STATE_FILE, 0o666)



# -----------------------------
# Enemy helpers
# -----------------------------
def spawn_enemy(now: float) -> Dict[str, float]:
    """Create a new enemy at the left edge of the river."""
    enemy_type = random.choice(list(ENEMY_PROPERTIES.keys()))
    return {
        "type": enemy_type,
        "x": float(RIVER_LEFT + 1),
        "y": random.uniform(-200.0, 280.0),
        "spawn_time": now,
        "last_move_time": now,
    }


def move_enemies(now: float) -> None:
    """Advance all enemies horizontally and drop any that exit right side."""
    for enemy in state["enemies"][:]:
        props = ENEMY_PROPERTIES[enemy["type"]]
        last_time = enemy.get("last_move_time", now)
        delta = max(0.0, now - last_time)
        enemy["x"] += props["speed"] * delta
        enemy["last_move_time"] = now

        if enemy["x"] >= RIVER_RIGHT - 2:
            state["enemies"].remove(enemy)


# -----------------------------
# Bullet helpers
# -----------------------------
def move_bullets() -> None:
    """Move bullets upward and discard those off-screen."""
    for bullet in state["bullets"][:]:
        bullet["y"] += BULLET_SPEED
        if bullet["y"] > 320:
            state["bullets"].remove(bullet)


def check_collision(bullet: Dict[str, float], enemy: Dict[str, float]) -> bool:
    props = ENEMY_PROPERTIES[enemy["type"]]
    dx = bullet["x"] - enemy["x"]
    dy = bullet["y"] - enemy["y"]
    return (dx * dx + dy * dy) ** 0.5 <= props["radius"]


# -----------------------------
# Threads
# -----------------------------
def enemy_thread() -> None:
    while not stop_event.is_set():
        now = time.time()
        with state_lock:
            move_enemies(now)
            if len(state["enemies"]) < MAX_ENEMIES and random.random() < ENEMY_SPAWN_CHANCE:
                state["enemies"].append(spawn_enemy(now))
        save_state()
        time.sleep(0.05)


def bullet_thread() -> None:
    while not stop_event.is_set():
        with state_lock:
            move_bullets()
            for bullet in state["bullets"][:]:
                for enemy in state["enemies"][:]:
                    if check_collision(bullet, enemy):
                        state["score"] += ENEMY_PROPERTIES[enemy["type"]]["score"]
                        state["bullets"].remove(bullet)
                        state["enemies"].remove(enemy)
                        break
        save_state()
        time.sleep(0.03)


def read_action_file() -> Tuple[Optional[str], Optional[int]]:
    if not os.path.exists(PLAYER_ACTION_FILE):
        return None, None

    try:
        with open(PLAYER_ACTION_FILE, "r", encoding="utf-8") as action_file:
            try:
                fcntl.flock(action_file, fcntl.LOCK_SH | fcntl.LOCK_NB)
            except BlockingIOError:
                return None, None
            payload = action_file.read().strip()
            fcntl.flock(action_file, fcntl.LOCK_UN)
    except Exception as exc:  # noqa: BLE001 - log and continue
        print(f"Failed to read action file: {exc}")
        return None, None

    if not payload:
        return None, None

    try:
        message = json.loads(payload)
        return message.get("action"), message.get("nonce")
    except json.JSONDecodeError:
        return payload, None


def player_thread() -> None:
    global last_action_nonce

    while not stop_event.is_set():
        action, nonce = read_action_file()
        if not action:
            time.sleep(0.02)
            continue

        action = action.upper()
        if nonce is not None:
            if nonce == last_action_nonce:
                time.sleep(0.02)
                continue
            last_action_nonce = nonce
        else:
            last_action_nonce += 1

        with state_lock:
            if action == "LEFT":
                state["player"]["x"] = max(PLAYER_MIN_X, state["player"]["x"] - PLAYER_SPEED)
            elif action == "RIGHT":
                state["player"]["x"] = min(PLAYER_MAX_X, state["player"]["x"] + PLAYER_SPEED)
            elif action == "FIRE":
                state["bullets"].append({
                    "x": state["player"]["x"],
                    "y": state["player"]["y"] + 20,
                })
        save_state()
        time.sleep(0.02)


# -----------------------------
# Entrypoint
# -----------------------------
def main() -> None:
    print("River Raid server starting...")
    ensure_shared_files()

    with state_lock:
        state["enemies"] = [spawn_enemy(time.time()) for _ in range(3)]
        state["bullets"] = []
        state["score"] = 0
        state["player"] = {"x": 0.0, "y": -250.0}
    save_state()

    threads = [
        threading.Thread(target=enemy_thread, daemon=True),
        threading.Thread(target=player_thread, daemon=True),
        threading.Thread(target=bullet_thread, daemon=True),
    ]

    for thread in threads:
        thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nServer shutting down...")
        stop_event.set()
        time.sleep(0.2)
        sys.exit(0)


if __name__ == "__main__":
    main()
