import core
import logging
import platform_help


def main_menu():
    keyboard = {
        "inline_keyboard": [
            [{"text": "Получить VPN", "callback_data": "get"}],
            [{"text": "Помощь в настройке VPN", "callback_data": "help"}],
        ]
    }
    return keyboard


def help_menu():
    keyboard = {
        "inline_keyboard": [
            [{"text": "Android", "callback_data": "help_android"}],
            [{"text": "iOS", "callback_data": "help_ios"}],
            [{"text": "Windows", "callback_data": "help_windows"}],
            [{"text": "macOS", "callback_data": "help_macos"}],
            [{"text": "Назад", "callback_data": "back"}],
        ]
    }
    return keyboard


def request_contact(chat_id):
    keyboard = {
        "keyboard": [[{"text": "Отправить контакт", "request_contact": True}]],
        "one_time_keyboard": True,
        "resize_keyboard": True,
    }
    return keyboard


def send_platform_help(chat_id, platform_name: str):
    logging.info(
        "Отправка помощи для платформы %s пользователю %s", platform_name, chat_id
    )
    platform = platform_help.Platform.platfrom_name_to_enum(platform_name).value
    if platform is None:
        help_text = "Неизвестная платформа"
    else:
        help_text = platform.instructions
    help_text+="\nБольше клиентов можете найти на [этом сайте](https://itdog.info/klienty-vless-shadowsocks-trojan-xray-sing-box-dlya-windows-android-ios-macos-linux/#v2box---v2ray-client)."
    core.send_message(chat_id, help_text, reply_markup=help_menu())
