import logging
import core
import platform_help


def main_menu():
    """Returns the main menu keyboard with VPN setup and help options."""
    keyboard = {
        "inline_keyboard": [
            [{"text": "Получить VPN", "callback_data": "get"}],
            [{"text": "Помощь в настройке VPN", "callback_data": "help"}],
        ]
    }
    return keyboard


def help_menu():
    """Returns the help menu keyboard with platform selection options."""
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
    """Returns a keyboard for requesting user contact information."""
    keyboard = {
        "keyboard": [[{"text": "Отправить контакт", "request_contact": True}]],
        "one_time_keyboard": True,
        "resize_keyboard": True,
    }
    return keyboard


def country_menu():
    """Returns the country selection menu for VPN server location."""
    keyboard = {
        "inline_keyboard": [
            [{"text": "🇳🇱 Нидерланды", "callback_data": "country_nl"}],
            [{"text": "🇫🇷 Франция", "callback_data": "country_fr"}],
            [{"text": "Назад", "callback_data": "back"}],
        ]
    }
    return keyboard


def send_platform_help(chat_id, platform_name: str):
    """Sends VPN setup instructions for the specified platform."""
    logging.info(
        "Sending help for platform %s to user %s", platform_name, chat_id
    )
    platform = platform_help.Platform.platform_name_to_enum(platform_name).value
    if platform is None:
        help_text = "Неизвестная платформа"
    else:
        help_text = platform.instructions
    help_text+="\nБольше клиентов можете найти на [этом сайте](https://itdog.info/klienty-vless-shadowsocks-trojan-xray-sing-box-dlya-windows-android-ios-macos-linux/#v2box---v2ray-client)."
    core.send_message(chat_id, help_text, reply_markup=help_menu())
