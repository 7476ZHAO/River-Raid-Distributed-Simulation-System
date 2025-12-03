import os
import json
import time
import random
import threading
from typing import Optional, List

import paramiko
import turtle

# -----------------------------
# SSH CONFIG (override via env vars)
# -----------------------------
VPS_IP = os.environ.get("RIVER_RAID_VPS_IP", "34.26.231.165")
USERNAME = os.environ.get("RIVER_RAID_VPS_USER", "rsa-key-20251020")
SSH_KEY = os.environ.get("RIVER_RAID_SSH_KEY", r"D:\\SCSU\\25Fall\\CSCI 593\\SSH\\rsa-key-20251020")

GAME_STATE_FILE = "/tmp/game_state.json"
PLAYER_ACTION_FILE = "/tmp/player_action"

# -----------------------------
# Turtle setup
# -----------------------------
screen = turtle.Screen()
screen.setup(700, 600)
screen.bgcolor("#BFEFFF")
screen.title("River Raid - Client")
screen.tracer(0)

player = turtle.Turtle()
player.penup()
player.shape("triangle")
player.color("purple")
player.shapesize(1.5, 1.5)
player.goto(0, -250)
player.setheading(90)

score_pen = turtle.Turtle()
score_pen.hideturtle()
score_pen.penup()
score_pen.goto(200, 260)
score_pen.write("SCORE: 0", align="left", font=("Arial", 16, "bold"))

enemy_turtles: List[Optional[turtle.Turtle]] = []
bullet_turtles: List[turtle.Turtle] = []


# -----------------------------
# Static river drawing
# -----------------------------
def draw_river() -> None:
    left = turtle.Turtle()
    left.hideturtle()
    left.penup()
    left.goto(-350, 300)
    left.color("green")
    left.begin_fill()
    for _ in range(2):
        left.forward(175)
        left.right(90)
        left.forward(600)
        left.right(90)
    left.end_fill()

    right = turtle.Turtle()
    right.hideturtle()
    right.penup()
    right.goto(175, 300)
    right.color("green")
    right.begin_fill()
    for _ in range(2):
        right.forward(175)
        right.right(90)
        right.forward(600)
        right.right(90)
    right.end_fill()


def ensure_ssh_key_exists() -> str:
    expanded = os.path.expanduser(SSH_KEY)
    if not os.path.exists(expanded):
        raise FileNotFoundError(
            f"SSH private key not found at '{expanded}'. "
            "Set RIVER_RAID_SSH_KEY to point to your .pem/.ppk file."
        )
    return expanded


def ssh_connect() -> Optional[paramiko.SSHClient]:
    try:
        ssh_key_path = ensure_ssh_key_exists()
    except FileNotFoundError as exc:
        print(exc)
        return None

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            VPS_IP,
            username=USERNAME,
            key_filename=ssh_key_path,
            timeout=5,
            banner_timeout=5,
            auth_timeout=5,
        )
        return client
    except Exception as exc:  # noqa: BLE001 - display friendly error
        print(f"SSH connection failed: {exc}")
        client.close()
        return None


def send_action(action: str) -> None:
    ssh = ssh_connect()
    if not ssh:
        return

    nonce = int(time.time() * 1000 + random.randint(0, 999))
    payload = json.dumps({"action": action.upper(), "nonce": nonce})
    remote_script = f"""python3 - <<'PY'
import fcntl
import os
payload = {json.dumps(payload)}
path = {json.dumps(PLAYER_ACTION_FILE)}
fd = os.open(path, os.O_WRONLY | os.O_CREAT)
with os.fdopen(fd, 'w') as handle:
    fcntl.flock(handle, fcntl.LOCK_EX)
    handle.write(payload)
    handle.flush()
    os.fsync(handle.fileno())
    fcntl.flock(handle, fcntl.LOCK_UN)
PY"""

    try:
        stdin, stdout, stderr = ssh.exec_command(remote_script)
        stdout.channel.recv_exit_status()
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to send action: {exc}")
    finally:
        ssh.close()


def get_state() -> Optional[dict]:
    ssh = ssh_connect()
    if not ssh:
        return None
    try:
        sftp = ssh.open_sftp()
        with sftp.file(GAME_STATE_FILE, "r") as remote:
            data = remote.read().decode("utf-8")
        sftp.close()
        ssh.close()
        if not data:
            return None
        return json.loads(data)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to get state: {exc}")
        try:
            ssh.close()
        except Exception:  # noqa: BLE001
            pass
    return None


def create_enemy_turtle(enemy_type: str) -> turtle.Turtle:
    t = turtle.Turtle()
    t.penup()
    t.hideturtle()

    if enemy_type == "H":
        t.shape("triangle")
        t.color("green")
        t.shapesize(1.2, 1.2)
        t.setheading(0)
    elif enemy_type == "J":
        t.shape("triangle")
        t.color("red")
        t.shapesize(1.2, 1.2)
        t.setheading(0)
    else:
        t.shape("square")
        t.color("sienna")
        t.shapesize(0.8, 2.8)
    return t


def create_bullet_turtle() -> turtle.Turtle:
    b = turtle.Turtle()
    b.penup()
    b.shape("circle")
    b.color("yellow")
    b.shapesize(0.4, 0.4)
    b.hideturtle()
    return b


def game_over() -> None:
    msg = turtle.Turtle()
    msg.hideturtle()
    msg.penup()
    msg.goto(0, 0)
    msg.color("red")
    msg.write("GAME OVER", align="center", font=("Arial", 30, "bold"))
    time.sleep(3)
    turtle.bye()


def update_player(state: dict) -> None:
    player_state = state.get("player", {})
    player.goto(player_state.get("x", 0), player_state.get("y", -250))


def update_score(state: dict) -> None:
    score_pen.clear()
    score_pen.write(f"SCORE: {state.get('score', 0)}", align="left", font=("Arial", 16, "bold"))


def update_enemies(state: dict) -> None:
    enemies = state.get("enemies", [])
    while len(enemy_turtles) < len(enemies):
        enemy_turtles.append(None)
    for idx in range(len(enemies), len(enemy_turtles)):
        if enemy_turtles[idx]:
            enemy_turtles[idx].hideturtle()

    for idx, enemy in enumerate(enemies):
        if enemy_turtles[idx] is None:
            enemy_turtles[idx] = create_enemy_turtle(enemy.get("type", "H"))
        t = enemy_turtles[idx]
        t.goto(enemy.get("x", 0), enemy.get("y", 0))
        t.showturtle()

    for idx in range(len(enemies), len(enemy_turtles)):
        if enemy_turtles[idx]:
            enemy_turtles[idx].hideturtle()


def update_bullets(state: dict) -> None:
    bullets = state.get("bullets", [])
    while len(bullet_turtles) < len(bullets):
        bullet_turtles.append(create_bullet_turtle())
    for idx, bullet in enumerate(bullets):
        bt = bullet_turtles[idx]
        bt.goto(bullet.get("x", 0), bullet.get("y", 0))
        bt.showturtle()
    for idx in range(len(bullets), len(bullet_turtles)):
        bullet_turtles[idx].hideturtle()


def render_thread() -> None:
    while True:
        try:
            state = get_state()
            if not state:
                time.sleep(0.05)
                continue

            if state.get("game_over"):
                game_over()
                return

            update_player(state)
            update_score(state)
            update_enemies(state)
            update_bullets(state)
            screen.update()
            time.sleep(0.03)
        except Exception as exc:  # noqa: BLE001
            print(f"Render error: {exc}")
            time.sleep(0.1)


def move_left() -> None:
    send_action("LEFT")


def move_right() -> None:
    send_action("RIGHT")


def fire() -> None:
    send_action("FIRE")


def quit_game() -> None:
    turtle.bye()


if __name__ == "__main__":
    draw_river()
    screen.listen()
    screen.onkeypress(move_left, "Left")
    screen.onkeypress(move_right, "Right")
    screen.onkeypress(fire, "space")
    screen.onkeypress(quit_game, "q")

    print("River Raid Client started...")
    print("Controls: Left/Right to move, Space to fire, Q to quit")

    threading.Thread(target=render_thread, daemon=True).start()

    try:
        turtle.done()
    except turtle.Terminator:
        print("Game closed")
