import os
import time
import threading
import websocket
import pika
import json
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import timezone, timedelta

# Configuration
SELF_IP = '130.245.32.122'
RABBITMQ_HOST = 'localhost'
QUEUE_NAME = 'urls'
LOG_DIR = "sender-logs"
REPORT_LOG_DIR = "hourly_reports"

# Setup logging
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(REPORT_LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "websocket_listener.log")
REPORT_LOG_FILE = os.path.join(REPORT_LOG_DIR, "hourly_report.log")

logger = logging.getLogger("WebSocketListenerLogger")
logger.setLevel(logging.DEBUG)
handler = TimedRotatingFileHandler(LOG_FILE, when="midnight", interval=1, backupCount=7)
handler.suffix = "%Y-%m-%d"
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
formatter.converter = time.gmtime
handler.setFormatter(formatter)
logger.addHandler(handler)

report_logger = logging.getLogger("HourlyReportLogger")
report_logger.setLevel(logging.INFO)
report_handler = TimedRotatingFileHandler(REPORT_LOG_FILE, when="midnight", interval=1, backupCount=7)
report_handler.suffix = "%Y-%m-%d"
report_handler.setFormatter(formatter)
report_logger.addHandler(report_handler)

class CryptoScamListener:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.message_count = 0
        self.hourly_message_count = 0
        self.ws = None
        self.setup_rabbitmq_connection()
        self.schedule_hourly_report()

    def setup_rabbitmq_connection(self):
        while True:
            try:
                self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
                self.channel = self.connection.channel()
                self.channel.queue_declare(queue=QUEUE_NAME, durable=True)
                logger.info("RabbitMQ Connection established.")
                break
            except Exception as e:
                logger.exception("Error connecting to RabbitMQ:")
                time.sleep(1)

    def report_hourly_messages(self):
        report_logger.info(f"Messages in last hour: {self.hourly_message_count}, Total: {self.message_count}")
        self.hourly_message_count = 0
        self.schedule_hourly_report()

    def schedule_hourly_report(self):
        threading.Timer(3600, self.report_hourly_messages).start()

    def on_message(self, ws, message):
        self.message_count += 1
        self.hourly_message_count += 1
        try:
            self.channel.basic_publish(exchange='', routing_key=QUEUE_NAME, body=json.dumps(message), properties=pika.BasicProperties(delivery_mode=2))
        except Exception as e:
            logger.error(f"Error publishing message to RabbitMQ: {e}")

    def on_error(self, ws, error):
        logger.error(f"WebSocket error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        logger.warning(f"WebSocket closed: {close_status_code} {close_msg}. Reconnecting...")
        self.start_websocket_listener()

    def on_open(self, ws):
        logger.info("WebSocket connection opened")

    def start_websocket_listener(self):
        self.ws = websocket.WebSocketApp(f"ws://{SELF_IP}:4000", on_open=self.on_open, on_message=self.on_message, on_error=self.on_error, on_close=self.on_close)
        threading.Thread(target=self.ws.run_forever, daemon=True).start()

    def run(self):
        self.start_websocket_listener()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            if self.connection:
                self.connection.close()

if __name__ == "__main__":
    listener = CryptoScamListener()
    listener.run()
