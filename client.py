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
USERNAME = "VPS101"
SSH_KEY = "AAABAAH84RC4ydmVCzWFXuUQ6NgNk+FnWWok3+KMLn7w7XWhKo0/FxlfORS/JtpG
oHs79ncNWdswLttpfSmS5EpO655GPLHaWzIOZ2sHwuxiJ1aW9N60KKj96WaabxjD
wT8f/dcTxhZlDfLqbMjdfkN9003vZWbqSGs5YqxuSrlSDOpgFW7/a83Td62ZODLz
aGtdFs2+tdJRchsDJ4x7P+rrAvPjBlylWvSBjupqpN/FxCpkgZjfngI/9vuk4WV2
ntpJLElJwXXkoXG3kG9KbCK+Sed+ft4Ev5ZvOErdHELjLs86ldgkpLJQz3x9uu/r
r5c18vRxkJfArTIpeAy/dClmUYEAAACBAOCD/iv49lpqbKIGZ1KcyqXp/5AUOPrm
+h6AIOFvNvkBCjDkN0Ggt1IhRjk1UWAaNjuUBkbTjtaSFkzsakG4A+kHf59TNF1R
8b8YCk3gtUYU3RGldT+l53jlwGeNOP55Uo+gYwI2pNnBP85fJdoYAug6kzv3P1vI
PcR7+X+1LOhHAAAAgQCkgBovPhYzKyp8A5FPo/ztTccFGwJzWGHsYMBoa7cAgjzz
mqSfgJeP6xAzdtVXQwPl7TTswTYZK3mT8y3AUikSEGAPSGXD6F3tp+B0ai+zw9Wd
l1h3ARyK8ZUHZsusfafoI4aQ7hCanylarf5UXTd3g7BFKkQQgDiYFZH1DtytwQAA
AIBCHqugjw3TTVowWyY84eTM79MUrLPH4QzTolUHR1g2qmmMm4AI5JXp5Vx1ylaL
WxpOkJ2hhowYED359U9QkT2WJ2n4VeiTNAboSNsOKwBXVk4vg7kEusuSnz9yHvEV
CAKvP3l/ulK5WHIGmjI1zn475WOZaK12cwUeYD8WThE3kQ=="   
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
screen.tracer(False)

player = turtle.Turtle()
player.shape("triangle")
player.color("white")
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
