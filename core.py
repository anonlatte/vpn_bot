import json
import logging
import requests
import config as cfg

logger = logging.getLogger(__name__)


def send_message(chat_id, text, reply_markup=None):
    """Sends a text message to the specified Telegram chat.

    Args:
        chat_id: Chat ID to send the message to
        text: Message text
        reply_markup: Optional keyboard markup

    Returns:
        dict: Response from Telegram API or None in case of error
    """
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    method = "sendMessage"

    try:
        logger.debug("Sending message using method %s: %s", method, payload)
        response = requests.post(
            f"{cfg.TELEGRAM_API_URL}/{method}", data=payload, timeout=30
        )
        response.raise_for_status()
        logger.debug("Response from Telegram: %s", response.json())
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error("Error when sending message: %s", e)
        return None


def send_photo(chat_id, photo, caption=None):
    """Sends a photo to the specified Telegram chat.

    Args:
        chat_id: Chat ID to send the photo to
        photo: Photo file
        caption: Optional caption text for the photo

    Returns:
        dict: Response from Telegram API or None in case of error
    """
    files = {"photo": photo}
    payload = {
        "chat_id": chat_id,
        "caption": caption,
        "has_spoiler": True,
        "parse_mode": "Markdown",
    }
    if caption:
        payload["caption"] = caption
    try:
        logger.debug("Sending photo")
        response = requests.post(
            f"{cfg.TELEGRAM_API_URL}/sendPhoto", data=payload, files=files, timeout=30
        )
        response.raise_for_status()
        logger.debug("Response from Telegram: %s", response.json())
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error("Error when sending photo: %s", e)
        return None


def get_android_vpn_link():
    """Gets the link to the latest v2rayNG release from GitHub.

    Returns:
        str: URL of the latest release or None in case of error
    """
    try:
        response = requests.get(
            "https://api.github.com/repos/2dust/v2rayNG/releases?per_page=1", timeout=30
        )
        response.raise_for_status()
        logger.debug("Received tags: %s", response.json())
        release_link: str = response.json()[0]["url"]
        return release_link
    except requests.exceptions.RequestException as e:
        logger.error("Error when getting releases: %s", e)
        return None
