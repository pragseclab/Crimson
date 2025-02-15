import os
import time
import subprocess
import logging
import psutil
from datetime import datetime, timezone, timedelta
from logging.handlers import TimedRotatingFileHandler

# Configuration
CERTSTREAM_DIR = "certstream-server"
SERVER_COMMAND = "mix run --no-halt"
LOG_DIR = "../server-logs"
SLEEP_INTERVAL = 15  # Check server status every 15 seconds

# Setup logging
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "server.log")
logger = logging.getLogger("CertStreamLogger")
logger.setLevel(logging.DEBUG)
handler = TimedRotatingFileHandler(LOG_FILE, when="midnight", interval=1, backupCount=7)
handler.suffix = "%Y-%m-%d"
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
formatter.converter = time.gmtime
handler.setFormatter(formatter)
logger.addHandler(handler)

SERVER_PROCESS = None

def start_server():
    """Starts the CertStream server."""
    global SERVER_PROCESS
    try:
        os.chdir(CERTSTREAM_DIR)
        SERVER_PROCESS = subprocess.Popen(SERVER_COMMAND, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        logger.info("CertStream server started successfully.")
    except Exception as e:
        logger.exception(f"Error starting CertStream server: {e}")

def check_server_status():
    """Checks if the server is running."""
    if SERVER_PROCESS is None:
        return False
    try:
        return psutil.pid_exists(SERVER_PROCESS.pid) and psutil.Process(SERVER_PROCESS.pid).is_running()
    except psutil.NoSuchProcess:
        return False

if __name__ == "__main__":
    while True:
        if not check_server_status():
            logger.info("CertStream server is not running. Restarting...")
            start_server()
        time.sleep(SLEEP_INTERVAL)
