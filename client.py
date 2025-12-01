import turtle
import threading
import time
import paramiko
import json
import io

# -----------------------------
# SSH CONFIG
# -----------------------------
VPS_IP = "34.139.110.221" #need to update every the vps restart
USERNAME = "rsa-key-20251020"
SSH_KEY = r"D:\SCSU\25Fall\CSCI 593\SSH\rsa-key-20251020.ppk"
GAME_STATE_FILE = "/tmp/game_state.json"
PLAYER_ACTION_FILE = "/tmp/player_action"


# -----------------------------
# SSH helpers
# -----------------------------
def ssh_connect():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VPS_IP, username=USERNAME, key_filename=SSH_KEY)
    return ssh


def send_action(action):
    ssh = ssh_connect()
    cmd = f"echo {action} > {PLAYER_ACTION_FILE}"
    ssh.exec_command(cmd)
    ssh.close()


def get_state():
    ssh = ssh_connect()
    sftp = ssh.open_sftp()

    try:
        remote_file = sftp.file(GAME_STATE_FILE, "r")
        data = remote_file.read().decode()
        remote_file.close()
        sftp.close()
        ssh.close()
        return json.loads(data)
    except:
        sftp.close()
        ssh.close()
        return None


# -----------------------------
# Turtle Graphics Setup
# -----------------------------
screen = turtle.Screen()
screen.title("Distributed River Raid (Client View)")
screen.setup(600, 600)
screen.bgcolor("black")
screen.tracer(False)

player = turtle.Turtle()
player.shape("triangle")
player.color("green")
player.penup()

ai = turtle.Turtle()
ai.shape("triangle")
ai.color("red")
ai.penup()

enemy_turtles = []

# -----------------------------
# Render Thread
# -----------------------------
def render_thread():
    global enemy_turtles

    while True:
        state = get_state()
        if not state:
            continue

        screen.clear()

        # Draw river
        river = turtle.Turtle()
        river.hideturtle()
        river.penup()
        river.goto(state["river_left"], -300)
        river.pendown()
        river.goto(state["river_left"], 300)
        river.goto(state["river_right"], 300)
        river.goto(state["river_right"], -300)
        river.goto(state["river_left"], -300)

        # Player
        player.goto(state["player_x"], state["player_y"])

        # AI
        ai.goto(state["ai_x"], state["ai_y"])

        # Enemies
        for t in enemy_turtles:
            t.hideturtle()
        enemy_turtles = []

        for e in state["enemies"]:
            t = turtle.Turtle()
            t.shape("square")
            t.color("yellow")
            t.penup()
            t.goto(e[0], e[1])
            enemy_turtles.append(t)

        # Bullets
        for b in state["bullets"]:
            bt = turtle.Turtle()
            bt.shape("circle")
            bt.color("orange")
            bt.penup()
            bt.goto(b[0], b[1])

        screen.update()
        time.sleep(0.03)


# -----------------------------
# Keyboard controls
# -----------------------------
def go_left(): send_action("LEFT")
def go_right(): send_action("RIGHT")
def go_up(): send_action("UP")
def go_down(): send_action("DOWN")
def fire(): send_action("FIRE")

screen.onkey(go_left, "Left")
screen.onkey(go_right, "Right")
screen.onkey(go_up, "Up")
screen.onkey(go_down, "Down")
screen.onkey(fire, "space")
screen.listen()


# -----------------------------
# Start threads
# -----------------------------
t = threading.Thread(target=render_thread, daemon=True)
t.start()

turtle.done()
