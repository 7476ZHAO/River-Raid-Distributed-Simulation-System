import paramiko
import turtle
import time

# -------------------------
# SSH Configuration
# -------------------------
VPS_IP = "YOUR_VPS_IP"
USERNAME = "YOUR_VPS_USERNAME"
PRIVATE_KEY = "/path/to/id_rsa"

def send_action_to_vps(action):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ssh.connect(
        hostname=VPS_IP,
        username=USERNAME,
        key_filename=PRIVATE_KEY
    )

    cmd = f"echo {action} > /tmp/player_action"
    ssh.exec_command(cmd)
    ssh.close()


# -------------------------
# Turtle Graphics Setup
# -------------------------
screen = turtle.Screen()
screen.title("River Raid - Client Controller")
screen.bgcolor("black")
screen.setup(width=600, height=600)

# Draw Player
player = turtle.Turtle()
player.shape("triangle")
player.color("lime")
player.penup()
player.goto(0, -200)

# Draw enemies (dummy local display)
enemy_H = turtle.Turtle()
enemy_H.shape("circle")
enemy_H.color("red")
enemy_H.penup()
enemy_H.goto(-200, 100)

enemy_J = turtle.Turtle()
enemy_J.shape("circle")
enemy_J.color("yellow")
enemy_J.penup()
enemy_J.goto(0, 150)

enemy_B = turtle.Turtle()
enemy_B.shape("circle")
enemy_B.color("cyan")
enemy_B.penup()
enemy_B.goto(200, 50)

# -------------------------
# Movement Functions
# -------------------------
def move_left():
    x = player.xcor()
    player.setx(x - 20)
    send_action_to_vps("LEFT")

def move_right():
    x = player.xcor()
    player.setx(x + 20)
    send_action_to_vps("RIGHT")

def move_up():
    y = player.ycor()
    player.sety(y + 20)
    send_action_to_vps("UP")

def move_down():
    y = player.ycor()
    player.sety(y - 20)
    send_action_to_vps("DOWN")

def fire():
    print("FIRE!")
    send_action_to_vps("FIRE")


# -------------------------
# Key Bindings
# -------------------------
screen.listen()
screen.onkeypress(move_left, "Left")
screen.onkeypress(move_right, "Right")
screen.onkeypress(move_up, "Up")
screen.onkeypress(move_down, "Down")
screen.onkeypress(fire, "space")

# -------------------------
# Local Enemy Animation (Optional)
# -------------------------
def animate_enemies():
    while True:
        enemy_H.setx(enemy_H.xcor() + 1)
        enemy_J.setx(enemy_J.xcor() - 1)
        enemy_B.setx(enemy_B.xcor() + 2)
        screen.update()
        time.sleep(0.05)

# If you want real VPS state visualization, I can add that too.

# -------------------------
# Main Loop
# -------------------------
screen.tracer(0)

while True:
    screen.update()
    time.sleep(0.01)

turtle.done()
