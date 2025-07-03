import requests
import time
import logging
import config as cfg
import core
import ui
import vpn

logger = logging.getLogger(__name__)

def get_updates() -> dict:
    """Gets updates from Telegram API.
    Returns a dictionary with updates or empty result on error.
    """
    logger.debug("Getting updates with offset=%s", cfg.LAST_UPDATE_ID)
    params = {"timeout": 100, "offset": cfg.LAST_UPDATE_ID}
    try:
        response = requests.get(f"{cfg.TELEGRAM_API_URL}/getUpdates", params=params)
        response.raise_for_status()
        logger.debug("Received updates: %s", response.json())
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error("Error when getting updates: %s", e)
        return {"result": []}

def handle_client_selection(chat_id: int, selection: str) -> bool:
    """Handles client selection if matching_clients list was previously saved.
    Returns True if the message was processed as client selection, False otherwise.
    """
    data = cfg.user_data.get(chat_id)
    if not data or not data.get("matching_clients"):
        return False
    try:
        matching_clients = data["matching_clients"]
        inbound_id = data["inbound_id"]
        server_port = data["server_port"]
        public_key = data["public_key"]
        short_id = data["short_id"]
        sni = data["sni"]
        username = data["username"]
        last_request_time = data["last_request_time"]
        country = data.get("country", "nl")
        original_api_url = data.get("original_api_url")
        original_server_domain = data.get("original_server_domain")

        # Set server configuration for selected country
        if original_api_url and original_server_domain:
            import config as cfg
            cfg.API_URL = cfg.SERVERS[country]
            from urllib.parse import urlparse
            parsed_url = urlparse(cfg.API_URL)
            cfg.SERVER_DOMAIN = parsed_url.hostname

        if selection.lower() == "новый":
            session = requests.Session()
            client_uuid = vpn.add_new_client(session, inbound_id, chat_id, username)
            if client_uuid is None:
                return True
            vpn.send_vpn_configuration(chat_id, client_uuid, server_port, public_key, sni, short_id, username, last_request_time)
        else:
            index = int(selection) - 1
            if index < 0 or index >= len(matching_clients):
                raise ValueError
            selected_client = matching_clients[index]
            client_uuid = selected_client.get("id")
            vpn.send_vpn_configuration(chat_id, client_uuid, server_port, public_key, sni, short_id, username, last_request_time)
    except ValueError:
        core.send_message(chat_id, "Некорректный выбор. Введите номер клиента из списка или 'новый' для создания нового клиента.")
    except Exception as e:
        logger.error("Error when processing client selection: %s", e)
        core.send_message(chat_id, f"Ошибка при обработке выбора клиента: {e}")
    finally:
        # Restore original configuration
        if original_api_url and original_server_domain:
            cfg.API_URL = original_api_url
            cfg.SERVER_DOMAIN = original_server_domain
        del cfg.user_data[chat_id]
    return True

def process_message(message: dict) -> None:
    """Processes incoming message from user and sends appropriate response."""
    logger.debug("Processing message: %s", message)
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    
    if handle_client_selection(chat_id, text.strip()):
        return

    contact = message.get("contact", None)
    user_data_msg = message["from"]
    first_name = user_data_msg.get("first_name", "")
    last_name = user_data_msg.get("last_name", "")
    username = user_data_msg.get("username", "")
    full_name = f"{first_name} {last_name}".strip()

    if text == "/start":
        logger.info(
            "Command /start from user %s", chat_id, extra={"username": username}
        )
        welcome_message = (
            f"Здравствуйте, {full_name}!\n\nЯ помогу вам настроить доступ к VLESS VPN."
        )
        core.send_message(chat_id, welcome_message, reply_markup=ui.main_menu())
    elif text == "/help":
        logger.info(
            "Command /help from user %s", chat_id, extra={"username": username}
        )
        core.send_message(
            chat_id,
            "Используйте меню для навигации по боту.",
            reply_markup=ui.main_menu(),
        )
    elif contact:
        logger.info(
            "Received contact from user %s", chat_id, extra={"username": username}
        )
        # Contact handling is no longer needed, redirect to main menu
        core.send_message(
            chat_id,
            "Запрос контакта больше не требуется. Используйте кнопку 'Получить VPN' в главном меню.",
            reply_markup=ui.main_menu(),
        )
    else:
        logger.info(
            "Received text message from user %s: %s",
            chat_id,
            text,
            extra={"username": username},
        )
        core.send_message(
            chat_id,
            "Пожалуйста, используйте меню для навигации.",
            reply_markup=ui.main_menu(),
        )


def handle_callback_query(callback_query: dict) -> None:
    """Handles callback_query from user and performs appropriate actions."""
    logger.debug("Processing callback_query: %s", callback_query)
    chat_id = callback_query["message"]["chat"]["id"]
    data = callback_query["data"]

    # Send answerCallbackQuery to remove loading indicator
    callback_query_id = callback_query["id"]
    try:
        requests.post(
            f"{cfg.TELEGRAM_API_URL}/answerCallbackQuery",
            data={"callback_query_id": callback_query_id},
        )
    except requests.exceptions.RequestException as e:
        logger.error("Error when sending answerCallbackQuery: %s", e)

    if data == "get":
        logger.info('User %s selected "Get VPN"', chat_id)
        core.send_message(
            chat_id, "Выберите страну для VPN сервера:", reply_markup=ui.country_menu()
        )
    elif data == "help":
        logger.info('User %s selected "VPN Setup Help"', chat_id)
        core.send_message(
            chat_id, "Выберите вашу платформу:", reply_markup=ui.help_menu()
        )
    elif data.startswith("help_"):
        platform = data.split("_")[1]
        logger.info(
            "User %s requested help for platform %s", chat_id, platform
        )
        ui.send_platform_help(chat_id, platform)
    elif data.startswith("country_"):
        country = data.split("_")[1]
        logger.info("User %s selected country %s", chat_id, country)
        # Get user data from callback_query
        user_data_cb = callback_query["from"]
        username = user_data_cb.get("username", "")
        vpn.create_vpn_account(chat_id, username, country)
    elif data == "back":
        logger.info("User %s returned to main menu", chat_id)
        core.send_message(
            chat_id, "Возврат в главное меню.", reply_markup=ui.main_menu()
        )
    else:
        logger.warning("Unknown command from user %s: %s", chat_id, data)
        core.send_message(chat_id, "Неизвестная команда.", reply_markup=ui.main_menu())
