import requests
import json
import logging
import config as cfg

logger = logging.getLogger(__name__)


def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    method = "sendMessage"

    try:
        logger.debug("Отправка сообщения методом %s: %s", method, payload)
        response = requests.post(f"{cfg.TELEGRAM_API_URL}/{method}", data=payload)
        response.raise_for_status()
        logger.debug("Ответ от Telegram: %s", response.json())
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error("Ошибка при отправке сообщения: %s", e)


def send_photo(chat_id, photo, caption=None):
    files = {"photo": photo}
    payload = {"chat_id": chat_id, "caption": caption, "has_spoiler": True}
    if caption:
        payload["caption"] = caption

    try:
        logger.debug("Отправка фото")
        response = requests.post(
            f"{cfg.TELEGRAM_API_URL}/sendPhoto", data=payload, files=files
        )
        response.raise_for_status()
        logger.debug("Ответ от Telegram: %s", response.json())
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error("Ошибка при отправке фото: %s", e)


def get_android_vpn_link():
    try:
        response = requests.get(
            "https://api.github.com/repos/2dust/v2rayNG/releases?per_page=1"
        )
        response.raise_for_status()
        logger.debug("Получены теги: %s", response.json())
        release_link: str = response.json()[0]["url"]
        return release_link
    except requests.exceptions.RequestException as e:
        logger.error("Ошибка при получении релизов: %s", e)
