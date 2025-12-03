import turtle
import threading
import time
import paramiko
import json



# PASSWORD MODE, ONLY FOR DEV PURPOSES

# # -----------------------------
# # SSH CONFIG
# # -----------------------------
# VPS_IP = "127.0.0.1"
# USERNAME = "saad"
# SSH_PASSWORD = "scsu1869"
# GAME_STATE_FILE = "/tmp/game_state.json"
# PLAYER_ACTION_FILE = "/tmp/player_action"

# # -----------------------------
# # SSH persistent connection
# # -----------------------------
# ssh = paramiko.SSHClient()
# ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
# ssh.connect(VPS_IP, username=USERNAME, password=SSH_PASSWORD)
# sftp = ssh.open_sftp()

# def send_action(action):
#     ssh.exec_command(f"echo {action} > {PLAYER_ACTION_FILE}")

# _last_mtime = 0
# def get_state():
#     try:
#         remote_file = sftp.file(GAME_STATE_FILE, "r")
#         data = remote_file.read().decode()
#         remote_file.close()
#         return json.loads(data)
#     except Exception as e:
#         print("Error reading state:", e)
#         return None



# -----------------------------
# SSH CONFIG (PUBLIC KEY)
# -----------------------------
VPS_IP_KEY = "127.0.0.1"  # local WSL / VPS
USERNAME_KEY = "saad"
ssh_FILE = r"C:\path\to\your\private_key.ppk"  # replace with your actual private key path
GAME_STATE_FILE_KEY = "/tmp/game_state.json"
PLAYER_ACTION_FILE_KEY = "/tmp/player_action"

# -----------------------------
# SSH persistent connection (PUBLIC KEY)
# -----------------------------
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VPS_IP_KEY, username=USERNAME_KEY, key_filename=ssh_FILE)
sftp = ssh.open_sftp()

def send_action(action):
    """Send player action using public key SSH connection"""
    ssh.exec_command(f"echo {action} > {PLAYER_ACTION_FILE_KEY}")

def get_state():
    """Fetch game state using public key SSH connection"""
    try:
        remote_file = sftp.file(GAME_STATE_FILE_KEY, "r")
        data = remote_file.read().decode()
        remote_file.close()
        return json.loads(data)
    except Exception as e:
        print("Error reading state (key SSH):", e)
        return None


# -----------------------------
# Turtle setup
# -----------------------------
screen = turtle.Screen()
screen.title("River Raid")
screen.setup(600, 800)  # portrait
screen.bgcolor("black")
screen.tracer(False)

# -----------------------------
# Load river GIF
# -----------------------------
RIVER_IMAGE = "assets/river.gif"  # single-frame GIF
screen.register_shape(RIVER_IMAGE)

# Create two turtles for scrolling
river1 = turtle.Turtle()
river1.penup()
river1.shape(RIVER_IMAGE)
river1.goto(0, 400)
river1.showturtle()  # must show turtle for GIF to appear

river2 = turtle.Turtle()
river2.penup()
river2.shape(RIVER_IMAGE)
river2.goto(0, 1200)  # stacked above river1
river2.showturtle()

scroll_speed = 2  # pixels per frame

def scroll_river():
    for r in [river1, river2]:
        r.sety(r.ycor() - scroll_speed)
        if r.ycor() < -400:  # off bottom
            r.sety(r.ycor() + 800 + 400)  # move above the other (height+overlap)
    screen.ontimer(scroll_river, 20)  # ~50 FPS

scroll_river()

# -----------------------------
# Player
# -----------------------------
player = turtle.Turtle()
player.shape("triangle")
player.color("green")
player.penup()
player.setheading(90)
player.goto(0, -300)

# -----------------------------
# Bullet / Enemy stamps
# -----------------------------
bullet_turtle = turtle.Turtle()
bullet_turtle.hideturtle()
bullet_turtle.penup()
bullet_turtle.shape("circle")
bullet_turtle.color("orange")

enemy_turtle = turtle.Turtle()
enemy_turtle.hideturtle()
enemy_turtle.penup()
enemy_turtle.shape("square")
enemy_turtle.color("yellow")

# -----------------------------
# Render thread
# -----------------------------
def render_thread():
    last_enemy_positions = []
    last_bullet_positions = []
    last_player_pos = (None, None)

    while True:
        state = get_state()
        if not state:
            time.sleep(0.08)
            continue

        # Player
        if (state["player_x"], state["player_y"]) != last_player_pos:
            player.goto(state["player_x"], state["player_y"])
            last_player_pos = (state["player_x"], state["player_y"])

        # Enemies
        enemy_positions = [(e[0], e[1]) for e in state["enemies"]]
        if enemy_positions != last_enemy_positions:
            enemy_turtle.clearstamps()
            for e in state["enemies"]:
                enemy_turtle.goto(e[0], e[1])
                enemy_turtle.stamp()
            last_enemy_positions = enemy_positions

        # Bullets
        bullet_positions = [(b[0], b[1]) for b in state["bullets"]]
        if bullet_positions != last_bullet_positions:
            bullet_turtle.clearstamps()
            for b in state["bullets"]:
                bullet_turtle.goto(b[0], b[1])
                bullet_turtle.stamp()
            last_bullet_positions = bullet_positions

        screen.update()
        time.sleep(0.03)  # smoother than 0.08

# -----------------------------
# Keyboard controls
# -----------------------------
screen.listen()
screen.onkey(lambda: send_action("LEFT"), "Left")
screen.onkey(lambda: send_action("RIGHT"), "Right")
screen.onkey(lambda: send_action("UP"), "Up")
screen.onkey(lambda: send_action("DOWN"), "Down")
screen.onkey(lambda: send_action("FIRE"), "space")

# -----------------------------
# Start render thread
# -----------------------------
t = threading.Thread(target=render_thread, daemon=True)
t.start()

turtle.done()

# -----------------------------
# Cleanup
# -----------------------------
sftp.close()
ssh.close()
