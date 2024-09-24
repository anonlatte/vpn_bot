import requests
import time
import logging
import config as cfg
import core
import ui
import vpn

logger = logging.getLogger(__name__)

def get_updates():
    logger.debug('Получение обновлений с offset=%s', cfg.LAST_UPDATE_ID)
    params = {'timeout': 100, 'offset': cfg.LAST_UPDATE_ID}
    try:
        response = requests.get(f'{cfg.TELEGRAM_API_URL}/getUpdates', params=params)
        response.raise_for_status()
        logger.debug('Получены обновления: %s', response.json())
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error('Ошибка при получении обновлений: %s', e)
        return {'result': []}

def process_message(message):
    logger.debug('Обработка сообщения: %s', message)
    chat_id = message['chat']['id']
    text = message.get('text', '')
    contact = message.get('contact', None)
    user_data_msg = message['from']
    first_name = user_data_msg.get('first_name', '')
    last_name = user_data_msg.get('last_name', '')
    username = user_data_msg.get('username', '')
    full_name = f"{first_name} {last_name}".strip()

    if text == '/start':
        logger.info('Команда /start от пользователя %s', chat_id, name="%(name)s for username")
        welcome_message = f'Здравствуйте, {full_name}!\n\nЯ помогу вам настроить доступ к VLESS VPN.'
        core.send_message(chat_id, welcome_message, reply_markup=ui.main_menu())
    elif text == '/help':
        logger.info('Команда /help от пользователя %s', chat_id, name="%(name)s for username")
        core.send_message(chat_id, 'Используйте меню для навигации по боту.', reply_markup=ui.main_menu())
    elif contact:
        logger.info('Получен контакт от пользователя %s', chat_id, name="%(name)s for username")
        # Пользователь отправил контакт
        phone_number = contact.get('phone_number', '')
        if str(contact['user_id']) != str(chat_id):
            logger.warning('Пользователь %s отправил контакт другого пользователя', chat_id, name="%(name)s for username")
            core.send_message(chat_id, 'Пожалуйста, отправьте ваш собственный контакт.')
            return
        vpn.create_vpn_account(chat_id, full_name, phone_number)
    else:
        logger.info('Получено текстовое сообщение от пользователя %s: %s', chat_id, text, name="%(name)s for username")
        core.send_message(chat_id, 'Пожалуйста, используйте меню для навигации.', reply_markup=ui.main_menu())

def handle_callback_query(callback_query):
    logger.debug('Обработка callback_query: %s', callback_query)
    chat_id = callback_query['message']['chat']['id']
    data = callback_query['data']

    # Обязательно отправляем answerCallbackQuery, чтобы убрать часики
    callback_query_id = callback_query['id']
    requests.post(f'{cfg.TELEGRAM_API_URL}/answerCallbackQuery', data={'callback_query_id': callback_query_id})

    if data == 'get':
        logger.info('Пользователь %s выбрал "Получить VPN"', chat_id)
        keyboard = ui.request_contact(chat_id)
        core.send_message(chat_id, 'Пожалуйста, поделитесь вашим контактом, нажав кнопку ниже.', reply_markup=keyboard)
    elif data == 'help':
        logger.info('Пользователь %s выбрал "Помощь в настройке VPN"', chat_id)
        core.send_message(chat_id, 'Выберите вашу платформу:', reply_markup=ui.help_menu())
    elif data.startswith('help_'):
        platform = data.split('_')[1]
        logger.info('Пользователь %s запросил помощь для платформы %s', chat_id, platform)
        ui.send_platform_help(chat_id, platform)
    elif data == 'back':
        logger.info('Пользователь %s вернулся в главное меню', chat_id)
        core.send_message(chat_id, 'Возврат в главное меню.', reply_markup=ui.main_menu())
    else:
        logger.warning('Неизвестная команда от пользователя %s: %s', chat_id, data)
        core.send_message(chat_id, 'Неизвестная команда.', reply_markup=ui.main_menu())