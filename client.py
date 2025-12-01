import paramiko

VPS_IP = "YOUR_VPS_IP"
USERNAME = "YOUR_VPS_USERNAME"
PRIVATE_KEY = "/path/to/id_rsa"  # your private RSA key

def send_action_to_vps(action):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Connect using RSA key
    ssh.connect(
        hostname=VPS_IP,
        username=USERNAME,
        key_filename=PRIVATE_KEY
    )

    # Write action to server temp file
    cmd = f"echo {action} > /tmp/player_action"
    ssh.exec_command(cmd)

    ssh.close()

def main():
    print("Player A - Enter commands (LEFT, RIGHT, UP, DOWN, FIRE)")

    while True:
        action = input("Action: ").upper()

        if action not in ["LEFT", "RIGHT", "UP", "DOWN", "FIRE"]:
            print("Invalid command.")
            continue

        send_action_to_vps(action)
        print(f"Sent '{action}' to VPS.")

if __name__ == "__main__":
    main()
