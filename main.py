import logging
import config as cfg
import message_handler as handler
import time
import os

logging.basicConfig(
    format="%(asctime)s %(levelname)s: %(message)s",
    level=logging.DEBUG,
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()],
    force=True,
)
logger = logging.getLogger(__name__)


def main():
    logger.debug("-" * 50)
    logger.info("Бот запущен и готов к работе")
    while True:
        updates = handler.get_updates()
        if "result" in updates and updates["result"]:
            for update in updates["result"]:
                logger.debug("Обработка обновления: %s", update)
                cfg.LAST_UPDATE_ID = update["update_id"] + 1
                if "message" in update:
                    message = update["message"]
                    if "contact" in message or "text" in message:
                        handler.process_message(message)
                elif "callback_query" in update:
                    handler.handle_callback_query(update["callback_query"])
        time.sleep(1)


if __name__ == "__main__":
    with open("/run/secrets/TELEGRAM_BOT_TOKEN", encoding="utf-8") as f:
        cfg.TOKEN = f.read().strip()
    with open("/run/secrets/API_URL", encoding="utf-8") as f:
        cfg.API_URL = f.read().strip()
    with open("/run/secrets/API_USERNAME", encoding="utf-8") as f:
        cfg.API_USERNAME = f.read().strip()
    with open("/run/secrets/API_PASSWORD", encoding="utf-8") as f:
        cfg.API_PASSWORD = f.read().strip()
    with open("/run/secrets/SERVER_IP", encoding="utf-8") as f:
        cfg.SERVER_IP = f.read().strip()
    cfg.TELEGRAM_API_URL = f"https://api.telegram.org/bot{cfg.TOKEN}"
    main()
