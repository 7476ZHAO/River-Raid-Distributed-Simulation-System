# ssh_connection.py
import paramiko

# -----------------------------
# SSH PASSWORD CONFIG
# -----------------------------
VPS_IP = "127.0.0.1"   # local WSL / VPS
USERNAME = "saad"
SSH_PASSWORD = "saad44131065"

PLAYER_ACTION_FILE = "/tmp/player_action"
GAME_STATE_FILE = "/tmp/game_state.json"

# -----------------------------
# Persistent SSH connection with password
# -----------------------------
class SSHPasswordClient:
    def __init__(self):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(VPS_IP, username=USERNAME, password=SSH_PASSWORD)
        self.sftp = self.ssh.open_sftp()

    def send_action(self, action: str):
        self.ssh.exec_command(f"echo {action} > {PLAYER_ACTION_FILE}")

    def get_state(self):
        try:
            remote_file = self.sftp.file(GAME_STATE_FILE, "r")
            data = remote_file.read().decode()
            remote_file.close()
            return data
        except Exception as e:
            print("Error reading state:", e)
            return None

    def close(self):
        self.sftp.close()
        self.ssh.close()


# -----------------------------
# Usage example:
# -----------------------------
# ssh_client = SSHPasswordClient()
# ssh_client.send_action("LEFT")
# state_json = ssh_client.get_state()
# ssh_client.close()
