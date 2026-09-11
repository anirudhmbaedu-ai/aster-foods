import subprocess
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
URL_FILE = ROOT / "tunnel_url.txt"
LOG_FILE = ROOT / "tunnel.log"

def run_tunnel():
    print("[Tunnel] Launching localhost.run tunnel for port 8766...", flush=True)
    cmd = [
        "ssh",
        "-o", "ServerAliveInterval=15",
        "-o", "ServerAliveCountMax=3",
        "-o", "StrictHostKeyChecking=no",
        "-R", "80:localhost:8766",
        "nokey@localhost.run"
    ]
    while True:
        try:
            with open(LOG_FILE, "a") as log_f:
                log_f.write(f"\n--- Starting tunnel at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                for line in proc.stdout:
                    log_f.write(line)
                    log_f.flush()
                    # Look for domain like https://xxxx.lhr.life
                    match = re.search(r"(https://[a-zA-Z0-9-]+\.lhr\.life)", line)
                    if match:
                        url = match.group(1)
                        URL_FILE.write_text(url, encoding="utf-8")
                        print(f"==================================================", flush=True)
                        print(f"🚀 Public Tunnel Online: {url}", flush=True)
                        print(f"==================================================", flush=True)
                proc.wait()
            print("[Tunnel] Tunnel disconnected. Reconnecting in 3s...", flush=True)
            time.sleep(3)
        except Exception as e:
            print(f"[Tunnel] Error: {e}. Retrying in 5s...", flush=True)
            time.sleep(5)

if __name__ == "__main__":
    run_tunnel()
