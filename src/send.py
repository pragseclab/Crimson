import os
import pika
import json
import logging
import pytz
from datetime import datetime
from collections import OrderedDict
from logging.handlers import TimedRotatingFileHandler
import time
import utils.keyword_utils as kw_utils

# Configuration
RABBITMQ_HOST = 'localhost'
QUEUE_NAME = 'cryptoscams'
LOG_DIR = "sender-logs"
CACHE_CAPACITY = 50000

# Setup logging
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "send.log")
logger = logging.getLogger("SendLogger")
logger.setLevel(logging.DEBUG)
handler = TimedRotatingFileHandler(LOG_FILE, when="midnight", interval=1, backupCount=7)
handler.suffix = "%Y-%m-%d"
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
formatter.converter = time.gmtime
handler.setFormatter(formatter)
logger.addHandler(handler)

# Timezone configuration
newYorkTz = pytz.timezone("America/New_York")

def parse_domain_name(domain_name):
    return domain_name[2:] if domain_name.startswith('*') else domain_name

def log_domains(url_name, curr_date, filename, mode='a'):
    log_path = os.path.join("logs", curr_date)
    os.makedirs(log_path, exist_ok=True)
    with open(os.path.join(log_path, filename), mode) as f:
        f.write(f'{url_name}\n')

def enqueue_domains(message, context, channel):
    if message['message_type'] != "certificate_update":
        return
    all_domains = message['data']['leaf_cert']['all_domains']
    curr_date = str(datetime.now(newYorkTz)).split(' ')[0].replace('-', '')[2:]
    for each_domain in all_domains:
        url_name = parse_domain_name(each_domain.lower())
        log_domains(url_name, curr_date, 'all_domains_seen.txt', 'a')
        if not kw_utils.match_domain_name_with_keywords(url_name):
            log_domains(url_name, curr_date, 'failed_url_filter.txt', 'a')
            continue
        log_domains(url_name, curr_date, 'passed_url_filter.txt', 'a')
        
        channel.basic_publish(
            exchange='',
            routing_key=QUEUE_NAME,
            body=url_name,
            properties=pika.BasicProperties(delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE)
        )
        log_domains(f" [x] Sent {url_name}", curr_date, 'sent.txt', 'a')