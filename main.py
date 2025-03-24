import logging
import time
import json
from urllib.parse import urlparse
import argparse
import config as cfg
import message_handler as handler
import requests

logging.basicConfig(
    format="%(asctime)s %(levelname)s: %(message)s",
    level=logging.DEBUG,
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()],
    force=True,
)
logger = logging.getLogger(__name__)


def load_config_from_secrets():
    """Loads configuration from Docker secrets"""
    with open("/run/secrets/TELEGRAM_BOT_TOKEN", encoding="utf-8") as f:
        cfg.TOKEN = f.read().strip()
    with open("/run/secrets/API_URL", encoding="utf-8") as f:
        config = json.loads(f.read().strip())
        cfg.SERVERS = config["servers"]
        cfg.DEFAULT_COUNTRY = config["default"]
        cfg.API_URL = cfg.SERVERS[cfg.DEFAULT_COUNTRY]
    with open("/run/secrets/API_USERNAME", encoding="utf-8") as f:
        cfg.API_USERNAME = f.read().strip()
    with open("/run/secrets/API_PASSWORD", encoding="utf-8") as f:
        cfg.API_PASSWORD = f.read().strip()


def load_config_from_args(args):
    """Loads configuration from command line arguments"""
    cfg.TOKEN = args.token
    config = json.loads(args.servers)
    cfg.SERVERS = config["servers"]
    cfg.DEFAULT_COUNTRY = config["default"]
    cfg.API_URL = cfg.SERVERS[cfg.DEFAULT_COUNTRY]
    cfg.API_USERNAME = args.username
    cfg.API_PASSWORD = args.password


def get_updates() -> dict:
    """Gets updates from Telegram API.
    Returns a dictionary with updates or empty result on error.
    """
    logger.debug("Getting updates with offset=%s", cfg.LAST_UPDATE_ID)
    params = {"timeout": 100, "offset": cfg.LAST_UPDATE_ID}
    try:
        response = requests.get(f"{cfg.TELEGRAM_API_URL}/getUpdates", params=params)
        if response.status_code == 409:
            logger.warning("Conflict with previous bot instance detected. Resetting LAST_UPDATE_ID")
            cfg.LAST_UPDATE_ID = None
            return {"result": []}
        response.raise_for_status()
        logger.debug("Received updates: %s", response.json())
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error("Error when getting updates: %s", e)
        return {"result": []}


def delete_webhook():
    """Deletes webhook before starting the bot"""
    try:
        response = requests.post(f"{cfg.TELEGRAM_API_URL}/deleteWebhook")
        response.raise_for_status()
        logger.info("Webhook successfully deleted")
    except requests.exceptions.RequestException as e:
        logger.error("Error when deleting webhook: %s", e)


def main():
    logger.debug("-" * 50)
    logger.info("Bot started and ready to work")
    delete_webhook()  # Delete webhook before starting
    while True:
        updates = get_updates()
        if "result" in updates and updates["result"]:
            for update in updates["result"]:
                logger.debug("Processing update: %s", update)
                cfg.LAST_UPDATE_ID = update["update_id"] + 1
                if "message" in update:
                    message = update["message"]
                    if "contact" in message or "text" in message:
                        handler.process_message(message)
                elif "callback_query" in update:
                    handler.handle_callback_query(update["callback_query"])
        time.sleep(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Telegram VPN Bot')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode with arguments')
    parser.add_argument('--token', help='Telegram Bot Token')
    parser.add_argument('--servers', help='JSON string with server configuration. Example: {"servers":{"nl":"https://server1.com","fr":"https://server2.com"},"default":"nl"}')
    parser.add_argument('--username', help='API Username')
    parser.add_argument('--password', help='API Password')

    args = parser.parse_args()

    try:
        if args.debug:
            if not all([args.token, args.servers, args.username, args.password]):
                parser.error("In debug mode, all arguments are required: --token, --servers, --username, --password")
            load_config_from_args(args)
        else:
            load_config_from_secrets()
        
        cfg.TELEGRAM_API_URL = f"https://api.telegram.org/bot{cfg.TOKEN}"
        main()
    except FileNotFoundError as e:
        logger.error("Error when reading configuration: %s", e)
        if not args.debug:
            logger.info("Try running in debug mode with command line arguments")
        raise
