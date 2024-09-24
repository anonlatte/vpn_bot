from enum import Enum


class PlatformHelp:

    def __init__(self, platform, link_to_vpn, instructions):
        self.platform = platform
        self.link_to_vpn = link_to_vpn
        self.instructions = instructions


class AndroidHelp(PlatformHelp):

    def __init__(self):
        link = core.get_android_vpn_link()
        super().__init__(
            "android",
            link,
            """
**Настройка VPN на Android**

1. Скачайте и установите приложение [v2rayNG]({actual_vpn_link}).
2. Загрузите QR-код или скопируйте ссылку на конфигурацию.
3. Откройте приложение и нажмите на иконку ＋.
4. Выберите импорт:
 - из QR-кода и отсканируйте QR-код.
 - из буфера обмена и вставьте полученный конфиг.
5. Нажмите на созданный профиль и нажмите на иконку ▶️ в правом нижнем углу.
""",
        )


class IOSHelp(PlatformHelp):

    def __init__(self):
        super().__init__(
            "ios",
            None,
            """
**Настройка VPN на iOS**

1. Скачайте и установите приложение [Shadowrocket](https://apps.apple.com/app/shadowrocket/id932747118) (платное) или [Quantumult](https://apps.apple.com/app/quantumult/id1252015438).
2. Откройте приложение и импортируйте конфигурацию, используя полученную ссылку или QR-код.
3. Подключитесь к VPN через приложение.
""",
        )


class WindowsHelp(PlatformHelp):

    def __init__(self):
        super().__init__(
            "windows",
            None,
            """
**Настройка VPN на Windows**

1. Скачайте и установите [V2RayN](https://github.com/2dust/v2rayN/releases).
2. Откройте приложение и выберите "Сервер" -> "Добавить сервер из URL".
3. Вставьте полученную ссылку и сохраните.
4. Подключитесь к VPN через приложение.
""",
        )


class MacOSHelp(PlatformHelp):

    def __init__(self):
        super().__init__(
            "macos",
            None,
            """
**Настройка VPN на macOS**

1. Скачайте и установите [V2RayX](https://github.com/Cenmrev/V2RayX/releases) или [V2RayU](https://github.com/yanue/V2rayU/releases).
2. Откройте приложение и импортируйте конфигурацию, используя полученную ссылку или QR-код.
3. Подключитесь к VPN через приложение.
""",
        )


class Platform(Enum):
    ANDROID = AndroidHelp()
    IOS = IOSHelp()
    WINDOWS = WindowsHelp()
    MACOS = MacOSHelp()

    @staticmethod
    def platfrom_name_to_enum(platform_name):
        return Platform[platform_name.upper()]
