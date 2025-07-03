import requests
import json
import uuid
from datetime import datetime, timedelta
from io import BytesIO
import qrcode
import logging
import config as cfg
import core
import random
import string

logger = logging.getLogger(__name__)


def cleanup_expired_user_data(now):
    """Removes expired records from cfg.user_data."""
    expired_chat_ids = [
        cid for cid, data in cfg.user_data.items()
        if now - data['last_request_time'] > timedelta(minutes=2)
    ]
    for cid in expired_chat_ids:
        del cfg.user_data[cid]


def check_rate_limit(chat_id, now):
    """Checks if user has exceeded rate limit (3 requests per hour)."""
    if chat_id not in cfg.user_requests:
        cfg.user_requests[chat_id] = []
    
    # Remove requests older than 1 hour
    cfg.user_requests[chat_id] = [
        req_time for req_time in cfg.user_requests[chat_id]
        if now - req_time < timedelta(hours=1)
    ]
    
    # Check if user has made 3 or more requests in the last hour
    if len(cfg.user_requests[chat_id]) >= 3:
        return False
    
    # Add current request timestamp
    cfg.user_requests[chat_id].append(now)
    return True


def login_api(session):
    """Authenticates with the 3xui API and returns the result."""
    login_url = f"{cfg.API_URL}/login"
    login_data = {"username": cfg.API_USERNAME, "password": cfg.API_PASSWORD}
    logger.debug("Authenticating with 3xui API")
    response = session.post(login_url, data=login_data)
    response.raise_for_status()
    result = response.json()
    logger.debug("Response from 3xui API: %s", result)
    if not result.get('success'):
        logger.error("Failed to login to 3xui API: %s", result.get('msg'))
        return False, result.get('msg')
    return True, None


def get_vless_inbound(session, chat_id):
    """Gets inbound configuration with required VLESS+Reality parameters."""
    inbounds_url = f"{cfg.API_URL}/panel/api/inbounds/list"
    logger.debug("Getting list of inbounds")
    response = session.get(inbounds_url)
    response.raise_for_status()
    data = response.json()
    logger.debug("List of inbounds: %s", data)
    if not data.get('success'):
        logger.error("Failed to get list of inbounds: %s", data.get('msg'))
        core.send_message(chat_id, "Не удалось получить список inbounds.")
        return None
    inbounds = data.get('obj', [])
    if not inbounds:
        logger.error("No available inbounds")
        core.send_message(chat_id, "Нет доступных inbounds для добавления пользователя.")
        return None
    
    for inbound in inbounds:
        if inbound.get('protocol') == 'vless':
            settings = json.loads(inbound.get('settings', '{}'))
            clients = settings.get('clients', [])
            if clients:
                flow = clients[0].get('flow', '')
                if flow == 'xtls-rprx-vision':
                    inbound_id = inbound.get('id')
                    server_port = inbound.get('port')
                    stream_settings = json.loads(inbound.get('streamSettings', '{}'))
                    if stream_settings.get('security', '') == 'reality':
                        reality_settings = stream_settings.get('realitySettings', {})
                        public_key = reality_settings.get('settings', {}).get('publicKey', '')
                        short_id_list = reality_settings.get('shortIds', [])
                        short_id = short_id_list[0] if short_id_list else ""
                        sni = reality_settings.get('serverNames', [''])[0]
                        return inbound_id, server_port, public_key, short_id, sni
    
    logger.error("No available VLESS inbounds with required parameters")
    core.send_message(
        chat_id,
        "Нет доступных VLESS inbounds с flow=xtls-rprx-vision для добавления пользователя."
    )
    return None


def get_existing_client(session, inbound_id, username, chat_id):
    """Checks if a client with the given email exists in the inbound."""
    inbound_details_url = f"{cfg.API_URL}/panel/api/inbounds/get/{inbound_id}"
    logger.debug("Getting inbound details")
    response = session.get(inbound_details_url)
    response.raise_for_status()
    data = response.json()
    logger.debug("Inbound details: %s", data)
    if not data.get('success'):
        logger.error("Failed to get inbound details: %s", data.get('msg'))
        core.send_message(chat_id, "Не удалось получить детали inbound.")
        return None, None
    inbound_obj = data.get('obj', {})
    settings = json.loads(inbound_obj.get('settings', '{}'))
    clients = settings.get('clients', [])
    for client in clients:
        if client.get('email') == username:
            return True, client.get('id')
    return False, None

def get_matching_clients(session, inbound_id, username, chat_id):
    """Gets a list of clients from inbound whose email matches the username."""
    inbound_details_url = f"{cfg.API_URL}/panel/api/inbounds/get/{inbound_id}"
    logger.debug("Getting inbound details to find existing clients")
    response = session.get(inbound_details_url)
    response.raise_for_status()
    data = response.json()
    logger.debug("Inbound details: %s", data)
    if not data.get('success'):
        logger.error("Failed to get inbound details: %s", data.get('msg'))
        core.send_message(chat_id, "Не удалось получить детали inbound.")
        return []
    inbound_obj = data.get('obj', {})
    settings = json.loads(inbound_obj.get('settings', '{}'))
    clients = settings.get('clients', [])
    matching_clients = [client for client in clients if client.get('email') == username]
    return matching_clients


def send_vpn_configuration(chat_id, client_uuid, server_port, public_key, sni, short_id, username, now):
    """Generates a link, QR code and sends them to the user, also updates user data."""
    vless_link = (
        f"vless://{client_uuid}@{cfg.SERVER_DOMAIN}:{server_port}?type=tcp&security=reality&pbk={public_key}"
        f"&fp=chrome&sni={sni}&sid={short_id}&spx=%2F&flow=xtls-rprx-vision#{username}"
    )
    hidden_vless_link = f"```{vless_link}```"

    qr = qrcode.make(vless_link)
    bio = BytesIO()
    bio.name = "qr.png"
    qr.save(bio, "PNG")
    bio.seek(0)

    core.send_photo(
        chat_id,
        bio,
        caption=(
            f"Ваш VPN настроен. Сканируйте QR-код или используйте ссылку ниже для настройки клиента.\n{hidden_vless_link}"
        )
    )
    cfg.user_data[chat_id] = {"last_request_time": now, "vless_link": vless_link}


def add_new_client(session, inbound_id, chat_id, username):
    """Adds a new client to the inbound via 3xui API."""
    add_client_url = f"{cfg.API_URL}/panel/api/inbounds/addClient"
    client_uuid = str(uuid.uuid4())
    client_email = username
    client_limit_ip = 0  # No IP restrictions
    client_total_gb = 0  # Traffic limit: 0 means unlimited
    expiry_time = int((datetime.utcnow() + timedelta(days=60)).timestamp() * 1000)

    client_settings = {
        "clients": [
            {
                "id": client_uuid,
                "flow": "xtls-rprx-vision",
                "email": client_email,
                "limitIp": client_limit_ip,
                "totalGB": client_total_gb,
                "expiryTime": expiry_time,
                "enable": False,
                "tgId": str(chat_id),
                "subId": "",
            }
        ]
    }
    payload = {"id": inbound_id, "settings": json.dumps(client_settings)}
    headers = {"Content-Type": "application/json"}

    logger.debug("Adding client to inbound")
    response = session.post(add_client_url, json=payload, headers=headers)
    response.raise_for_status()
    data = response.json()
    logger.debug("Response when adding client: %s", data)
    if not data.get('success'):
        logger.error("Failed to add client: %s", data.get('msg'))
        core.send_message(chat_id, f"Не удалось добавить клиента: {data.get('msg')}")
        return None
    logger.info("Client successfully added for user %s", chat_id)
    return client_uuid


def create_vpn_account(chat_id, telegram_username):
    """Creates a VPN account for the user."""
    logger.info("Creating VPN account for user %s", chat_id)
    now = datetime.utcnow()
    
    # Check rate limit (3 requests per hour)
    if not check_rate_limit(chat_id, now):
        core.send_message(
            chat_id,
            "Вы превысили лимит запросов. Максимально 3 запроса в час. Пожалуйста, подождите.",
        )
        return
    
    # Generate unique email for 3x-ui
    timestamp = int(now.timestamp())
    if telegram_username:
        email = f"{telegram_username}_{timestamp}"
    else:
        # Use telegram user ID if username is not available
        email = f"user{chat_id}_{timestamp}"
    
    # Cleanup expired records
    cleanup_expired_user_data(now)
    
    session = requests.Session()
    try:
        success, error_msg = login_api(session)
        if not success:
            core.send_message(chat_id, "Не удалось войти в API 3xui. Проверьте логин и пароль.")
            return
    except requests.exceptions.RequestException as e:
        logger.error("Error when accessing 3xui API: %s", e)
        core.send_message(chat_id, f"Ошибка при обращении к API 3xui: {e}")
        return
    
    inbound_config = get_vless_inbound(session, chat_id)
    if inbound_config is None:
        return
    inbound_id, server_port, public_key, short_id, sni = inbound_config
    
    # Get list of existing clients matching user data
    matching_clients = get_matching_clients(session, inbound_id, email, chat_id)
    if matching_clients:
        # Save context for subsequent user selection processing
        cfg.user_data[chat_id] = {
            "last_request_time": now,
            "inbound_id": inbound_id,
            "server_port": server_port,
            "public_key": public_key,
            "short_id": short_id,
            "sni": sni,
            "username": email,
            "matching_clients": matching_clients
        }
        msg = "Найдены следующие существующие клиенты с вашими данными:\n"
        for i, client in enumerate(matching_clients, start=1):
            msg += f"{i}. ID: {client.get('id')}\n"
        msg += "\nВведите номер клиента для использования или введите 'новый' для создания нового клиента."
        core.send_message(chat_id, msg)
        return
    else:
        try:
            client_uuid = add_new_client(session, inbound_id, chat_id, email)
            if client_uuid is None:
                return
            send_vpn_configuration(chat_id, client_uuid, server_port, public_key, sni, short_id, email, now)
        except requests.exceptions.RequestException as e:
            logger.error("Error when adding client: %s", e)
            core.send_message(chat_id, f"Ошибка при добавлении клиента: {e}")
            return
