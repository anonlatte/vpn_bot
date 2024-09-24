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

def create_vpn_account(chat_id, full_name, phone_number):
    logger.info('Создание VPN аккаунта для пользователя %s', chat_id)
    username = f'user_{chat_id}'

    # Удаление устаревших записей из cfg.user_data
    now = datetime.utcnow()
    expired_chat_ids = [cid for cid, data in cfg.user_data.items() if now - data['last_request_time'] > timedelta(minutes=2)]
    for cid in expired_chat_ids:
        del cfg.user_data[cid]

    # Проверка ограничения частоты запросов
    if chat_id in cfg.user_data:
        last_request_time = cfg.user_data[chat_id]['last_request_time']
        if now - last_request_time < timedelta(minutes=2):
            core.send_message(chat_id, 'Вы можете запрашивать конфигурацию не чаще, чем раз в 2 минуты. Пожалуйста, подождите немного.')
            return
        else:
            del cfg.user_data[chat_id]  # Удаляем пользователя из cfg.user_data, так как таймаут истек

    # Шаг 1: Авторизация в API 3xui для получения сессии
    login_url = f'{cfg.API_URL}/login'
    login_data = {
        'username': cfg.API_USERNAME,
        'password': cfg.API_PASSWORD
    }

    session = requests.Session()
    try:
        logger.debug('Авторизация в API 3xui')
        login_response = session.post(login_url, data=login_data)
        login_response.raise_for_status()
        login_result = login_response.json()
        logger.debug('Ответ от API 3xui: %s', login_result)
        if login_result.get('success'):
            pass
        else:
            logger.error('Не удалось войти в API 3xui: %s', login_result.get('msg'))
            core.send_message(chat_id, 'Не удалось войти в API 3xui. Проверьте логин и пароль.')
            return
    except requests.exceptions.RequestException as e:
        logger.error('Ошибка при обращении к API 3xui: %s', e)
        core.send_message(chat_id, f'Ошибка при обращении к API 3xui: {e}')
        return

    # Шаг 2: Получение списка inbounds для выбора нужного inboundId
    inbounds_url = f'{cfg.API_URL}/panel/api/inbounds/list'
    try:
        logger.debug('Получение списка inbounds')
        inbounds_response = session.get(inbounds_url)
        inbounds_response.raise_for_status()
        inbounds_data = inbounds_response.json()
        logger.debug('Список inbounds: %s', inbounds_data)
        if inbounds_data.get('success'):
            inbounds = inbounds_data.get('obj', [])
            if not inbounds:
                logger.error('Нет доступных inbounds')
                core.send_message(chat_id, 'Нет доступных inbounds для добавления пользователя.')
                return
            # Используем inbound с нужным протоколом (VLESS + Reality)
            inbound_id = None
            server_port = None
            public_key = None
            short_id = ''
            sni = ''
            for inbound in inbounds:
                if inbound['protocol'] == 'vless':
                    settings = json.loads(inbound['settings'])
                    clients = settings.get('clients', [])
                    if clients:
                        flow = clients[0].get('flow', '')
                        if flow == 'xtls-rprx-vision':
                            inbound_id = inbound['id']
                            server_port = inbound['port']
                            stream_settings = json.loads(inbound['streamSettings'])
                            security = stream_settings.get('security', '')
                            if security == 'reality':
                                reality_settings = stream_settings.get('realitySettings', {})
                                public_key = reality_settings.get('publicKey', '')
                                short_id_list = reality_settings.get('shortIds', [])
                                if short_id_list:
                                    short_id = short_id_list[0]
                                sni = reality_settings.get('serverNames', [''])[0]
                                break
            if not inbound_id:
                logger.error('Нет доступных VLESS inbounds с требуемыми параметрами')
                core.send_message(chat_id, 'Нет доступных VLESS inbounds с flow=xtls-rprx-vision для добавления пользователя.')
                return
        else:
            logger.error('Не удалось получить список inbounds: %s', inbounds_data.get('msg'))
            core.send_message(chat_id, 'Не удалось получить список inbounds.')
            return
    except requests.exceptions.RequestException as e:
        logger.error('Ошибка при получении списка inbounds: %s', e)
        core.send_message(chat_id, f'Ошибка при получении списка inbounds: {e}')
        return

    # Проверка существования клиента
    inbound_details_url = f'{cfg.API_URL}/panel/api/inbounds/get/{inbound_id}'
    try:
        logger.debug('Получение деталей inbound')
        inbound_details_response = session.get(inbound_details_url)
        inbound_details_response.raise_for_status()
        inbound_details_data = inbound_details_response.json()
        logger.debug('Детали inbound: %s', inbound_details_data)
        if inbound_details_data.get('success'):
            inbound_obj = inbound_details_data.get('obj', {})
            settings = json.loads(inbound_obj.get('settings', '{}'))
            clients = settings.get('clients', [])
            # Проверяем, существует ли клиент с email == username
            client_exists = False
            for client in clients:
                if client.get('email') == username:
                    client_exists = True
                    client_uuid = client.get('id')
                    break
        else:
            logger.error('Не удалось получить детали inbound: %s', inbound_details_data.get('msg'))
            core.send_message(chat_id, 'Не удалось получить детали inbound.')
            return
    except requests.exceptions.RequestException as e:
        logger.error('Ошибка при получении деталей inbound: %s', e)
        core.send_message(chat_id, f'Ошибка при получении деталей inbound: {e}')
        return

    if client_exists:
        logger.info('Клиент уже существует для пользователя %s', chat_id)
        # Генерация ссылки на конфигурацию VLESS
        server_ip = 'your.server.ip'  # Замените на ваш IP или домен
        vless_link = f'vless://{client_uuid}@{server_ip}:{server_port}?encryption=none&flow=xtls-rprx-vision&security=reality&fp=chrome&pbk={public_key}&shortId={short_id}&sni={sni}&type=tcp&headerType=none#{username}'
        hidden_vless_link = f'|| {vless_link} ||'

        # Генерация QR-кода
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
        qr.add_data(vless_link)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        bio = BytesIO()
        bio.name = 'qr.png'
        img.save(bio, 'PNG')
        bio.seek(0)

        # Отправка QR-кода и ссылки пользователю
        core.send_photo(chat_id, bio, caption=f'Ваш VPN настроен. Сканируйте QR-код или используйте ссылку ниже для настройки клиента.\n{hidden_vless_link}')

        # Обновление времени последнего запроса пользователя
        cfg.user_data[chat_id] = {'last_request_time': now, 'vless_link': vless_link}
    else:
        # Клиент не существует, создаем нового
        add_client_url = f'{cfg.API_URL}/panel/api/inbounds/addClient'

        # Генерация UUID для клиента
        client_uuid = str(uuid.uuid4())

        # Подготовка настроек клиента
        client_email = username
        client_limit_ip = 0  # Без ограничений
        client_total_gb = 0  # Лимит трафика: 0 означает безлимит
        # Установка срока действия на 60 дней с текущего момента
        expiry_time = int((datetime.utcnow() + timedelta(days=60)).timestamp() * 1000)  # в миллисекундах

        client_settings = {
            "clients": [
                {
                    "id": client_uuid,
                    "flow": "xtls-rprx-vision",
                    "email": client_email,
                    "limitIp": client_limit_ip,
                    "totalGB": client_total_gb,
                    "expiryTime": expiry_time,
                    "enable": True,
                    "tgId": str(chat_id),
                    "subId": ""
                }
            ]
        }

        payload = {
            "id": inbound_id,
            "settings": json.dumps(client_settings)
        }

        headers = {
            'Content-Type': 'application/json'
        }

        try:
            logger.debug('Добавление клиента в inbound')
            add_client_response = session.post(add_client_url, json=payload, headers=headers)
            add_client_response.raise_for_status()
            add_client_data = add_client_response.json()
            logger.debug('Ответ при добавлении клиента: %s', add_client_data)
            if add_client_data.get('success'):
                # Клиент успешно добавлен
                logger.info('Клиент успешно добавлен для пользователя %s', chat_id)
                # Генерация ссылки на конфигурацию VLESS
                server_ip = 'your.server.ip'  # Замените на ваш IP или домен
                vless_link = f'vless://{client_uuid}@{server_ip}:{server_port}?encryption=none&flow=xtls-rprx-vision&security=reality&fp=chrome&pbk={public_key}&shortId={short_id}&sni={sni}&type=tcp&headerType=none#{client_email}'
                hidden_vless_link = f'|| {vless_link} ||'

                # Генерация QR-кода
                qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
                qr.add_data(vless_link)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                bio = BytesIO()
                bio.name = 'qr.png'
                img.save(bio, 'PNG')
                bio.seek(0)

                # Отправка QR-кода и ссылки пользователю
                core.send_photo(chat_id, bio, caption=f'Ваш VPN настроен. Сканируйте QR-код или используйте ссылку ниже для настройки клиента.\n{hidden_vless_link}')

                # Обновление времени последнего запроса пользователя
                cfg.user_data[chat_id] = {'last_request_time': now, 'vless_link': vless_link}
            else:
                logger.error('Не удалось добавить клиента: %s', add_client_data.get('msg'))
                core.send_message(chat_id, f'Не удалось добавить клиента: {add_client_data.get("msg")}')
        except requests.exceptions.RequestException as e:
            logger.error('Ошибка при добавлении клиента: %s', e)
            core.send_message(chat_id, f'Ошибка при добавлении клиента: {e}')
            return