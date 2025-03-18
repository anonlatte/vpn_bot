import requests
import json
import uuid
from datetime import datetime, timedelta
from io import BytesIO
import qrcode
import logging
import config as cfg
import core

logger = logging.getLogger(__name__)


def cleanup_expired_user_data(now):
    """Удаляет устаревшие записи из cfg.user_data."""
    expired_chat_ids = [
        cid for cid, data in cfg.user_data.items()
        if now - data['last_request_time'] > timedelta(minutes=2)
    ]
    for cid in expired_chat_ids:
        del cfg.user_data[cid]


def login_api(session):
    """Авторизуется в API 3xui и возвращает результат."""
    login_url = f"{cfg.API_URL}/login"
    login_data = {"username": cfg.API_USERNAME, "password": cfg.API_PASSWORD}
    logger.debug("Авторизация в API 3xui")
    response = session.post(login_url, data=login_data)
    response.raise_for_status()
    result = response.json()
    logger.debug("Ответ от API 3xui: %s", result)
    if not result.get('success'):
        logger.error("Не удалось войти в API 3xui: %s", result.get('msg'))
        return False, result.get('msg')
    return True, None


def get_vless_inbound(session, chat_id):
    """Получает конфигурацию inbound с требуемыми параметрами VLESS+Reality."""
    inbounds_url = f"{cfg.API_URL}/panel/api/inbounds/list"
    logger.debug("Получение списка inbounds")
    response = session.get(inbounds_url)
    response.raise_for_status()
    data = response.json()
    logger.debug("Список inbounds: %s", data)
    if not data.get('success'):
        logger.error("Не удалось получить список inbounds: %s", data.get('msg'))
        core.send_message(chat_id, "Не удалось получить список inbounds.")
        return None
    inbounds = data.get('obj', [])
    if not inbounds:
        logger.error("Нет доступных inbounds")
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
    
    logger.error("Нет доступных VLESS inbounds с требуемыми параметрами")
    core.send_message(
        chat_id,
        "Нет доступных VLESS inbounds с flow=xtls-rprx-vision для добавления пользователя."
    )
    return None


def get_existing_client(session, inbound_id, username, chat_id):
    """Проверяет, существует ли клиент с данным email в inbound."""
    inbound_details_url = f"{cfg.API_URL}/panel/api/inbounds/get/{inbound_id}"
    logger.debug("Получение деталей inbound")
    response = session.get(inbound_details_url)
    response.raise_for_status()
    data = response.json()
    logger.debug("Детали inbound: %s", data)
    if not data.get('success'):
        logger.error("Не удалось получить детали inbound: %s", data.get('msg'))
        core.send_message(chat_id, "Не удалось получить детали inbound.")
        return None, None
    inbound_obj = data.get('obj', {})
    settings = json.loads(inbound_obj.get('settings', '{}'))
    clients = settings.get('clients', [])
    for client in clients:
        if client.get('email') == username:
            return True, client.get('id')
    return False, None


def send_vpn_configuration(chat_id, client_uuid, server_port, public_key, sni, short_id, username, now):
    """Генерирует ссылку, QR-код и отправляет их пользователю, а также обновляет данные пользователя."""
    vless_link = (
        f"vless://{client_uuid}@{cfg.SERVER_IP}:{server_port}?type=tcp&security=reality&pbk={public_key}"
        f"&fp=chrome&sni={sni}&sid={short_id}&spx=%2F&flow=xtls-rprx-vision#{username}"
    )
    hidden_vless_link = f"```{vless_link}```"

    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
    qr.add_data(vless_link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = BytesIO()
    bio.name = "qr.png"
    img.save(bio, "PNG")
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
    """Добавляет нового клиента в inbound через API 3xui."""
    add_client_url = f"{cfg.API_URL}/panel/api/inbounds/addClient"
    client_uuid = str(uuid.uuid4())
    client_email = username
    client_limit_ip = 0  # Без ограничений
    client_total_gb = 0  # Лимит трафика: 0 означает безлимит
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

    logger.debug("Добавление клиента в inbound")
    response = session.post(add_client_url, json=payload, headers=headers)
    response.raise_for_status()
    data = response.json()
    logger.debug("Ответ при добавлении клиента: %s", data)
    if not data.get('success'):
        logger.error("Не удалось добавить клиента: %s", data.get('msg'))
        core.send_message(chat_id, f"Не удалось добавить клиента: {data.get('msg')}")
        return None
    logger.info("Клиент успешно добавлен для пользователя %s", chat_id)
    return client_uuid


def create_vpn_account(chat_id, full_name, phone_number):
    logger.info("Создание VPN аккаунта для пользователя %s", chat_id)
    username = f"user_{chat_id}"
    now = datetime.utcnow()
    
    # Очистка устаревших записей и проверка ограничения частоты запросов
    cleanup_expired_user_data(now)
    if chat_id in cfg.user_data and now - cfg.user_data[chat_id]['last_request_time'] < timedelta(minutes=2):
        core.send_message(
            chat_id,
            "Вы можете запрашивать конфигурацию не чаще, чем раз в 2 минуты. Пожалуйста, подождите немного.",
        )
        return
    
    session = requests.Session()
    try:
        success, error_msg = login_api(session)
        if not success:
            core.send_message(chat_id, "Не удалось войти в API 3xui. Проверьте логин и пароль.")
            return
    except requests.exceptions.RequestException as e:
        logger.error("Ошибка при обращении к API 3xui: %s", e)
        core.send_message(chat_id, f"Ошибка при обращении к API 3xui: {e}")
        return
    
    inbound_config = get_vless_inbound(session, chat_id)
    if inbound_config is None:
        return
    inbound_id, server_port, public_key, short_id, sni = inbound_config
    
    client_exists, client_uuid = get_existing_client(session, inbound_id, username, chat_id)
    if client_exists:
        logger.info("Клиент уже существует для пользователя %s", chat_id)
        send_vpn_configuration(chat_id, client_uuid, server_port, public_key, sni, short_id, username, now)
    else:
        try:
            client_uuid = add_new_client(session, inbound_id, chat_id, username)
            if client_uuid is None:
                return
            send_vpn_configuration(chat_id, client_uuid, server_port, public_key, sni, short_id, username, now)
        except requests.exceptions.RequestException as e:
            logger.error("Ошибка при добавлении клиента: %s", e)
            core.send_message(chat_id, f"Ошибка при добавлении клиента: {e}")
            return
