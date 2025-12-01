import time
import threading
from multiprocessing import shared_memory
import json
import os

# -------------------------
# Shared Memory Definition
# -------------------------
def init_shared_memory():
    # JSON game state
    initial_state = {
        "player_x": 50,
        "player_y": 90,
        "H_enemy": 10,
        "J_enemy": 30,
        "B_enemy": 70,
        "action": "NONE"
    }

    data = json.dumps(initial_state).encode("utf-8")
    shm = shared_memory.SharedMemory(create=True, size=4096, name="game_state")

    shm.buf[:len(data)] = data
    return shm

def read_shared_memory(shm):
    raw = bytes(shm.buf[:4096]).rstrip(b"\x00")
    return json.loads(raw)

def write_shared_memory(shm, obj):
    data = json.dumps(obj).encode("utf-8")
    shm.buf[:4096] = b"\x00" * 4096
    shm.buf[:len(data)] = data

# -------------------------
# Enemy Thread Behaviors
# -------------------------
def enemy_H(shm):
    while True:
        state = read_shared_memory(shm)
        state["H_enemy"] += 1
        write_shared_memory(shm, state)
        time.sleep(1)

def enemy_J(shm):
    while True:
        state = read_shared_memory(shm)
        state["J_enemy"] -= 1
        write_shared_memory(shm, state)
        time.sleep(1.2)

def enemy_B(shm):
    while True:
        state = read_shared_memory(shm)
        state["B_enemy"] += 2
        write_shared_memory(shm, state)
        time.sleep(0.8)

# -------------------------
# Read Client Action
# -------------------------
def read_client_action():
    if not os.path.exists("/tmp/player_action"):
        return None

    with open("/tmp/player_action", "r") as f:
        return f.read().strip()

# -------------------------
# Apply Player Action
# -------------------------
def apply_player_action(shm):
    while True:
        action = read_client_action()
        if action:
            state = read_shared_memory(shm)

            if action == "LEFT":
                state["player_x"] -= 2
            elif action == "RIGHT":
                state["player_x"] += 2
            elif action == "UP":
                state["player_y"] -= 2
            elif action == "DOWN":
                state["player_y"] += 2
            elif action == "FIRE":
                print("Player fires!")

            state["action"] = action
            write_shared_memory(shm, state)

        time.sleep(0.2)

# -------------------------
# MAIN SERVER PROGRAM
# -------------------------
def main():
    shm = init_shared_memory()
    print("Shared memory created: game_state")

    # Launch enemy threads
    threading.Thread(target=enemy_H, args=(shm,), daemon=True).start()
    threading.Thread(target=enemy_J, args=(shm,), daemon=True).start()
    threading.Thread(target=enemy_B, args=(shm,), daemon=True).start()

    # Launch action reader
    threading.Thread(target=apply_player_action, args=(shm,), daemon=True).start()

    # Keep server running
    while True:
        print(read_shared_memory(shm))
        time.sleep(2)

if __name__ == "__main__":
    main()
