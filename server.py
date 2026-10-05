import json
import os
import re
import secrets
import shutil
import subprocess
import threading
import time
from datetime import datetime
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse


# ─────────────────────────────────────
# Configuration
# ─────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
ENV_PATH = os.path.join(BASE_DIR, ".env")


def load_env_file(path):
    """
    Basit .env okuyucu.
    Ekstra python-dotenv paketi gerektirmez.
    """
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()

            if not line:
                continue

            if line.startswith("#"):
                continue

            if "=" not in line:
                continue

            key, value = line.split("=", 1)

            key = key.strip()
            value = value.strip()

            # "value" veya 'value' desteği
            if (
                len(value) >= 2
                and value[0] == value[-1]
                and value[0] in ("'", '"')
            ):
                value = value[1:-1]

            os.environ.setdefault(key, value)


load_env_file(ENV_PATH)


ALLOWED_WIFI = os.environ.get(
    "DASHBOARD_ALLOWED_WIFI",
    ""
).strip()

PORT = int(
    os.environ.get(
        "DASHBOARD_PORT",
        "57321"
    )
)

CHECK_INTERVAL = int(
    os.environ.get(
        "DASHBOARD_WIFI_CHECK_INTERVAL",
        "15"
    )
)

NIGHT_START = int(
    os.environ.get(
        "NIGHT_MODE_START",
        "23"
    )
)

NIGHT_END = int(
    os.environ.get(
        "NIGHT_MODE_END",
        "7"
    )
)


# Her server başlangıcında değişir.
PAIRING_CODE = (
    f"{secrets.randbelow(1000000):06d}"
)

ACCESS_TOKEN = secrets.token_urlsafe(32)


# Wi-Fi durumunu request başına
# system_profiler çalıştırmadan saklayacağız.

WIFI_STATE_LOCK = threading.Lock()

WIFI_STATE = {
    "ssid": None,
    "allowed": False
}


# ─────────────────────────────────────
# Helpers
# ─────────────────────────────────────

def run(command, timeout=8):
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout
        )

    except subprocess.TimeoutExpired:
        print(
            "[Command] Zaman aşımı:",
            " ".join(command)
        )

        return None

    except Exception as error:
        print(
            "[Command]",
            error
        )

        return None


def applescript(script):
    result = run(
        [
            "osascript",
            "-e",
            script
        ],
        timeout=6
    )

    if (
        not result
        or result.returncode != 0
    ):
        return ""

    return result.stdout.strip()


# ─────────────────────────────────────
# Wi-Fi
# ─────────────────────────────────────

def get_current_wifi():
    """
    macOS'tan mevcut SSID'yi alır.

    Bu işlem nispeten yavaş olduğundan
    HTTP request başına çağrılmaz.
    """

    result = run(
        [
            "system_profiler",
            "SPAirPortDataType"
        ],
        timeout=12
    )

    if not result:
        return None

    lines = result.stdout.splitlines()

    for index, line in enumerate(lines):

        if (
            "Current Network Information:"
            in line
        ):
            if index + 1 >= len(lines):
                continue

            ssid = (
                lines[index + 1]
                .strip()
            )

            if ssid.endswith(":"):
                ssid = ssid[:-1]

            return ssid

    return None


def set_wifi_state(ssid):
    with WIFI_STATE_LOCK:

        WIFI_STATE["ssid"] = ssid

        WIFI_STATE["allowed"] = bool(
            ALLOWED_WIFI
            and ssid == ALLOWED_WIFI
        )


def get_cached_wifi():
    with WIFI_STATE_LOCK:
        return WIFI_STATE["ssid"]


def wifi_allowed():
    with WIFI_STATE_LOCK:
        return WIFI_STATE["allowed"]


def wifi_monitor(server):
    """
    Wi-Fi belirli aralıklarla kontrol edilir.

    Mac izin verilen ağdan ayrılırsa
    dashboard server tamamen kapanır.
    """

    while True:

        time.sleep(CHECK_INTERVAL)

        current_wifi = get_current_wifi()

        set_wifi_state(
            current_wifi
        )

        if current_wifi != ALLOWED_WIFI:

            print()
            print(
                "⚠️ İzin verilen Wi-Fi "
                "bağlantısı kayboldu."
            )

            print(
                "Mevcut ağ:",
                current_wifi
                or "Bağlantı yok"
            )

            print(
                "Dashboard kapatılıyor..."
            )

            server.shutdown()

            break


def get_local_ip():
    result = run(
        [
            "ipconfig",
            "getifaddr",
            "en0"
        ]
    )

    if result:

        ip = result.stdout.strip()

        if ip:
            return ip

    return None


# ─────────────────────────────────────
# Battery
# ─────────────────────────────────────

def get_battery():
    result = run(
        [
            "pmset",
            "-g",
            "batt"
        ]
    )

    if not result:

        return {
            "percentage": None,
            "state": "unknown",
            "plugged_in": False
        }

    output = result.stdout
    lower = output.lower()

    match = re.search(
        r"(\d+)%",
        output
    )

    percentage = (
        int(match.group(1))
        if match
        else None
    )

    if "discharging" in lower:
        state = "discharging"

    elif "charged" in lower:
        state = "charged"

    elif "charging" in lower:
        state = "charging"

    else:
        state = "unknown"

    return {
        "percentage": percentage,
        "state": state,
        "plugged_in":
            "ac power" in lower
    }


# ─────────────────────────────────────
# CPU
# ─────────────────────────────────────

def get_cpu_usage():
    result = run(
        [
            "ps",
            "-A",
            "-o",
            "%cpu="
        ]
    )

    if not result:
        return None

    try:
        values = []

        for line in result.stdout.splitlines():

            line = line.strip()

            if line:
                values.append(
                    float(line)
                )

        logical = (
            os.cpu_count()
            or 1
        )

        usage = (
            sum(values)
            / logical
        )

        return round(
            min(
                100,
                max(
                    0,
                    usage
                )
            ),
            1
        )

    except Exception:
        return None


# ─────────────────────────────────────
# Memory
# ─────────────────────────────────────

def get_memory():
    total_bytes = None

    result = run(
        [
            "sysctl",
            "-n",
            "hw.memsize"
        ]
    )

    if result:

        try:
            total_bytes = int(
                result.stdout.strip()
            )

        except Exception:
            pass

    vm = run(
        ["vm_stat"]
    )

    if (
        not vm
        or not total_bytes
    ):
        return {
            "used_gb": None,
            "total_gb": None,
            "percentage": None
        }

    page_size = 16384

    lines = vm.stdout.splitlines()

    if lines:

        match = re.search(
            r"page size of (\d+) bytes",
            lines[0]
        )

        if match:
            page_size = int(
                match.group(1)
            )

    stats = {}

    for line in lines[1:]:

        if ":" not in line:
            continue

        key, value = line.split(
            ":",
            1
        )

        value = re.sub(
            r"[^\d]",
            "",
            value
        )

        if value:

            stats[
                key.strip()
            ] = int(value)

    active = stats.get(
        "Pages active",
        0
    )

    wired = stats.get(
        "Pages wired down",
        0
    )

    compressed = stats.get(
        "Pages occupied by compressor",
        0
    )

    speculative = stats.get(
        "Pages speculative",
        0
    )

    used_bytes = (
        active
        + wired
        + compressed
        + speculative
    ) * page_size

    gb = 1024 ** 3

    used_gb = (
        used_bytes / gb
    )

    total_gb = (
        total_bytes / gb
    )

    percentage = (
        used_bytes
        / total_bytes
        * 100
    )

    return {
        "used_gb":
            round(
                used_gb,
                1
            ),

        "total_gb":
            round(
                total_gb,
                1
            ),

        "percentage":
            round(
                percentage,
                1
            )
    }


# ─────────────────────────────────────
# Disk
# ─────────────────────────────────────

def get_disk():
    try:

        usage = shutil.disk_usage(
            "/"
        )

        gb = 1024 ** 3

        used = (
            usage.total
            - usage.free
        )

        return {
            "used_gb":
                round(
                    used / gb,
                    1
                ),

            "total_gb":
                round(
                    usage.total / gb,
                    1
                ),

            "percentage":
                round(
                    used
                    / usage.total
                    * 100,
                    1
                )
        }

    except Exception:

        return {
            "used_gb": None,
            "total_gb": None,
            "percentage": None
        }


# ─────────────────────────────────────
# Uptime
# ─────────────────────────────────────

def get_uptime():
    result = run(
        [
            "sysctl",
            "-n",
            "kern.boottime"
        ]
    )

    if not result:
        return None

    match = re.search(
        r"sec = (\d+)",
        result.stdout
    )

    if not match:
        return None

    boot = int(
        match.group(1)
    )

    seconds = max(
        0,
        int(time.time()) - boot
    )

    days = (
        seconds // 86400
    )

    hours = (
        seconds % 86400
    ) // 3600

    minutes = (
        seconds % 3600
    ) // 60

    if days:
        return (
            f"{days}g "
            f"{hours}s"
        )

    if hours:
        return (
            f"{hours}s "
            f"{minutes}dk"
        )

    return f"{minutes}dk"


# ─────────────────────────────────────
# Bluetooth
# ─────────────────────────────────────

def find_connected_bluetooth(
    value,
    devices
):
    if isinstance(
        value,
        dict
    ):

        connected = value.get(
            "device_connected"
        )

        if connected == "attrib_Yes":

            name = (
                value.get(
                    "device_name"
                )
                or value.get(
                    "_name"
                )
                or "Bluetooth Cihazı"
            )

            battery = None

            for key, item in value.items():

                key_lower = (
                    str(key)
                    .lower()
                )

                if (
                    "battery"
                    in key_lower
                    and isinstance(
                        item,
                        (
                            str,
                            int,
                            float
                        )
                    )
                ):

                    match = re.search(
                        r"(\d+)",
                        str(item)
                    )

                    if match:

                        battery = int(
                            match.group(1)
                        )

                        break

            devices.append(
                {
                    "name": name,
                    "battery": battery
                }
            )

        for child in value.values():

            find_connected_bluetooth(
                child,
                devices
            )

    elif isinstance(
        value,
        list
    ):

        for child in value:

            find_connected_bluetooth(
                child,
                devices
            )


def get_bluetooth_devices():
    result = run(
        [
            "system_profiler",
            "SPBluetoothDataType",
            "-json"
        ],
        timeout=15
    )

    if (
        not result
        or result.returncode != 0
    ):
        return []

    try:

        data = json.loads(
            result.stdout
        )

        devices = []

        find_connected_bluetooth(
            data,
            devices
        )

        unique = []
        names = set()

        for device in devices:

            name = device["name"]

            if name in names:
                continue

            names.add(name)

            unique.append(
                device
            )

        return unique

    except Exception as error:

        print(
            "[Bluetooth]",
            error
        )

        return []


# ─────────────────────────────────────
# Volume
# ─────────────────────────────────────

def get_volume():
    # İki ayrı AppleScript yerine
    # tek sorguda volume + mute alıyoruz.

    output = applescript(
        '''
        set currentSettings to get volume settings
        return (output volume of currentSettings as string) & "|" & (output muted of currentSettings as string)
        '''
    )

    try:
        volume_text, muted_text = (
            output.split(
                "|",
                1
            )
        )

        volume = int(
            volume_text
        )

        muted = (
            muted_text
            .strip()
            .lower()
            == "true"
        )

    except Exception:

        volume = 0
        muted = False

    return {
        "volume": volume,
        "muted": muted
    }


# ─────────────────────────────────────
# Spotify
# ─────────────────────────────────────

def get_spotify():
    # Spotify bilgilerini tek AppleScript
    # çağrısında alıyoruz.

    script = r'''
    tell application "System Events"
        if not (exists process "Spotify") then
            return "__NOT_RUNNING__"
        end if
    end tell

    tell application "Spotify"

        set currentState to player state as string

        if currentState is not "playing" and currentState is not "paused" then
            return "__NO_TRACK__"
        end if

        set fieldSeparator to ASCII character 31

        return currentState & fieldSeparator & ¬
            (name of current track) & fieldSeparator & ¬
            (artist of current track) & fieldSeparator & ¬
            (album of current track) & fieldSeparator & ¬
            ((duration of current track) as string) & fieldSeparator & ¬
            ((player position) as string)

    end tell
    '''

    output = applescript(
        script
    )

    if (
        not output
        or output
        in (
            "__NOT_RUNNING__",
            "__NO_TRACK__"
        )
    ):
        return None

    parts = output.split(
        chr(31)
    )

    if len(parts) != 6:
        return None

    (
        state,
        title,
        artist,
        album,
        duration,
        position
    ) = parts

    try:
        duration = (
            float(duration)
            / 1000
        )

    except Exception:
        duration = 0

    try:
        position = float(
            position
        )

    except Exception:
        position = 0

    return {
        "available": True,
        "playing":
            state == "playing",
        "source": "Spotify",
        "title": title,
        "artist": artist,
        "album": album,
        "duration": duration,
        "position": position
    }


# ─────────────────────────────────────
# Apple Music
# ─────────────────────────────────────

def get_apple_music():
    script = r'''
    tell application "System Events"
        if not (exists process "Music") then
            return "__NOT_RUNNING__"
        end if
    end tell

    tell application "Music"

        set currentState to player state as string

        if currentState is not "playing" and currentState is not "paused" then
            return "__NO_TRACK__"
        end if

        set fieldSeparator to ASCII character 31

        return currentState & fieldSeparator & ¬
            (name of current track) & fieldSeparator & ¬
            (artist of current track) & fieldSeparator & ¬
            (album of current track) & fieldSeparator & ¬
            ((duration of current track) as string) & fieldSeparator & ¬
            ((player position) as string)

    end tell
    '''

    output = applescript(
        script
    )

    if (
        not output
        or output
        in (
            "__NOT_RUNNING__",
            "__NO_TRACK__"
        )
    ):
        return None

    parts = output.split(
        chr(31)
    )

    if len(parts) != 6:
        return None

    (
        state,
        title,
        artist,
        album,
        duration,
        position
    ) = parts

    try:
        duration = float(
            duration
        )

    except Exception:
        duration = 0

    try:
        position = float(
            position
        )

    except Exception:
        position = 0

    return {
        "available": True,
        "playing":
            state == "playing",
        "source": "Apple Music",
        "title": title,
        "artist": artist,
        "album": album,
        "duration": duration,
        "position": position
    }


def get_music():
    spotify = get_spotify()

    if spotify:
        return spotify

    apple = get_apple_music()

    if apple:
        return apple

    return {
        "available": False,
        "playing": False,
        "source": None,
        "title": None,
        "artist": None,
        "album": None,
        "duration": 0,
        "position": 0
    }


def music_command(command):
    music = get_music()

    source = music.get(
        "source"
    )

    if source == "Spotify":
        app = "Spotify"

    elif source == "Apple Music":
        app = "Music"

    else:
        return False

    if command == "playpause":

        script = (
            f'tell application "{app}" '
            'to playpause'
        )

    elif command == "next":

        script = (
            f'tell application "{app}" '
            'to next track'
        )

    elif command == "previous":

        script = (
            f'tell application "{app}" '
            'to previous track'
        )

    else:
        return False

    applescript(
        script
    )

    return True


# ─────────────────────────────────────
# Mac Controls
# ─────────────────────────────────────

def mac_control(command):

    if command == "volume-up":

        applescript(
            '''
            set v to output volume of (get volume settings)
            set newVolume to v + 10
            if newVolume > 100 then set newVolume to 100
            set volume output volume newVolume
            '''
        )

        return True

    if command == "volume-down":

        applescript(
            '''
            set v to output volume of (get volume settings)
            set newVolume to v - 10
            if newVolume < 0 then set newVolume to 0
            set volume output volume newVolume
            '''
        )

        return True

    if command == "mute":

        applescript(
            '''
            set currentMute to output muted of (get volume settings)
            set volume output muted (not currentMute)
            '''
        )

        return True

    if command == "lock":

        run(
            [
                "/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession",
                "-suspend"
            ]
        )

        return True

    if command == "sleep":

        run(
            [
                "pmset",
                "sleepnow"
            ]
        )

        return True

    return False


# ─────────────────────────────────────
# Night mode
# ─────────────────────────────────────

def night_mode_active():
    hour = datetime.now().hour

    if NIGHT_START > NIGHT_END:

        return (
            hour >= NIGHT_START
            or hour < NIGHT_END
        )

    return (
        NIGHT_START
        <= hour
        < NIGHT_END
    )


# ─────────────────────────────────────
# HTTP
# ─────────────────────────────────────

class Handler(
    SimpleHTTPRequestHandler
):

    def __init__(
        self,
        *args,
        **kwargs
    ):
        super().__init__(
            *args,
            directory=STATIC_DIR,
            **kwargs
        )

    def log_message(
        self,
        *args
    ):
        # Terminali her HTTP isteğiyle
        # doldurmuyoruz.
        pass

    def authenticated(self):

        cookie = self.headers.get(
            "Cookie",
            ""
        )

        return (
            f"dashboard_token={ACCESS_TOKEN}"
            in cookie
        )

    def json_response(
        self,
        data,
        status=200,
        extra_headers=None
    ):

        body = json.dumps(
            data,
            ensure_ascii=False
        ).encode(
            "utf-8"
        )

        try:

            self.send_response(
                status
            )

            self.send_header(
                "Content-Type",
                "application/json; charset=utf-8"
            )

            self.send_header(
                "Cache-Control",
                "no-store"
            )

            self.send_header(
                "Content-Length",
                str(
                    len(body)
                )
            )

            if extra_headers:

                for (
                    key,
                    value
                ) in extra_headers.items():

                    self.send_header(
                        key,
                        value
                    )

            self.end_headers()

            self.wfile.write(
                body
            )

        except (
            BrokenPipeError,
            ConnectionResetError
        ):
            # Safari isteği yarıda keserse
            # traceback basma.
            return

    def allowed_request(self):
        return wifi_allowed()

    def do_GET(self):

        parsed = urlparse(
            self.path
        )

        path = parsed.path

        # Pairing yapılmadan önce frontend
        # erişilebilir olmalı.

        if path in (
            "/",
            "/index.html",
            "/style.css",
            "/app.js"
        ):
            super().do_GET()
            return

        if path == "/api/auth":

            self.json_response(
                {
                    "authenticated":
                        self.authenticated(),

                    "wifi_allowed":
                        self.allowed_request()
                }
            )

            return

        if not self.allowed_request():

            self.json_response(
                {
                    "error":
                        "wrong_wifi"
                },
                403
            )

            return

        if not self.authenticated():

            self.json_response(
                {
                    "error":
                        "unauthorized"
                },
                403
            )

            return

        if path == "/api/status":

            self.json_response(
                {
                    "connected": True,

                    "battery":
                        get_battery(),

                    "music":
                        get_music(),

                    "volume":
                        get_volume(),

                    "night_mode":
                        night_mode_active()
                }
            )

            return

        if path == "/api/system":

            self.json_response(
                {
                    "cpu":
                        get_cpu_usage(),

                    "memory":
                        get_memory(),

                    "disk":
                        get_disk(),

                    "uptime":
                        get_uptime(),

                    "battery":
                        get_battery(),

                    "bluetooth":
                        get_bluetooth_devices()
                }
            )

            return

        try:
            self.send_error(
                404
            )

        except (
            BrokenPipeError,
            ConnectionResetError
        ):
            pass

    def do_POST(self):

        path = urlparse(
            self.path
        ).path

        if not self.allowed_request():

            self.json_response(
                {
                    "error":
                        "wrong_wifi"
                },
                403
            )

            return

        # ───── Pairing ─────

        if path == "/api/pair":

            length = int(
                self.headers.get(
                    "Content-Length",
                    "0"
                )
            )

            try:

                data = json.loads(
                    self.rfile.read(
                        length
                    ).decode(
                        "utf-8"
                    )
                )

                code = re.sub(
                    r"\D",
                    "",
                    str(
                        data.get(
                            "code",
                            ""
                        )
                    )
                )

            except Exception:

                self.json_response(
                    {
                        "success":
                            False
                    },
                    400
                )

                return

            if code != PAIRING_CODE:

                print(
                    "❌ Hatalı eşleştirme "
                    "kodu denemesi."
                )

                self.json_response(
                    {
                        "success":
                            False,

                        "error":
                            "invalid_code"
                    },
                    403
                )

                return

            print(
                "✅ iPhone eşleştirildi."
            )

            self.json_response(
                {
                    "success":
                        True
                },
                extra_headers={
                    "Set-Cookie":
                        (
                            "dashboard_token="
                            f"{ACCESS_TOKEN}; "
                            "Path=/; "
                            "HttpOnly; "
                            "SameSite=Lax; "
                            "Max-Age=31536000"
                        )
                }
            )

            return

        # Pairing dışındaki POST endpointleri
        # auth gerektirir.

        if not self.authenticated():

            self.json_response(
                {
                    "error":
                        "unauthorized"
                },
                403
            )

            return

        # ───── Music ─────

        if path.startswith(
            "/api/music/"
        ):

            command = (
                path.split("/")[-1]
            )

            self.json_response(
                {
                    "success":
                        music_command(
                            command
                        )
                }
            )

            return

        # ───── Mac controls ─────

        if path.startswith(
            "/api/control/"
        ):

            command = (
                path.split("/")[-1]
            )

            success = mac_control(
                command
            )

            self.json_response(
                {
                    "success":
                        success,

                    "volume":
                        get_volume()
                }
            )

            return

        self.json_response(
            {
                "error":
                    "not_found"
            },
            404
        )


# ─────────────────────────────────────
# Main
# ─────────────────────────────────────

def main():

    print()

    print(
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    print(
        "              MAC DESK"
    )

    print(
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    print()

    # .env kontrolü

    if not ALLOWED_WIFI:

        print(
            "❌ DASHBOARD_ALLOWED_WIFI "
            ".env içinde tanımlı değil."
        )

        print()

        return

    # Başlangıçta Wi-Fi yalnızca bir kez
    # kontrol edilir.

    wifi = get_current_wifi()

    set_wifi_state(
        wifi
    )

    ip = get_local_ip()

    print(
        f"Wi-Fi : "
        f"{wifi or 'Bağlantı yok'}"
    )

    print(
        f"Port  : {PORT}"
    )

    print()

    # Yanlış Wi-Fi'daysa serverı
    # hiç açmıyoruz.

    if wifi != ALLOWED_WIFI:

        print(
            "❌ Dashboard başlatılmadı."
        )

        print(
            "İzin verilen Wi-Fi ağına "
            "bağlı değilsin."
        )

        print()

        return

    if ip:

        print(
            f"📱 http://{ip}:{PORT}"
        )

    print()

    print(
        "🔐 Yeni cihaz eşleştirme kodu:"
    )

    print()

    print(
        f"             "
        f"{PAIRING_CODE[:3]} "
        f"{PAIRING_CODE[3:]}"
    )

    print()

    print(
        f"🔒 Wi-Fi kontrolü: "
        f"{CHECK_INTERVAL} saniye"
    )

    print(
        "Kapatmak için: Control + C"
    )

    print()

    server = ThreadingHTTPServer(
        (
            "0.0.0.0",
            PORT
        ),
        Handler
    )

    # Wi-Fi kontrolü requestlerden bağımsız
    # arka planda yapılır.

    monitor = threading.Thread(
        target=wifi_monitor,
        args=(
            server,
        ),
        daemon=True
    )

    monitor.start()

    try:

        server.serve_forever()

    except KeyboardInterrupt:

        print()
        print(
            "Mac Desk kapatılıyor..."
        )

    finally:

        server.server_close()

        print(
            "✅ Server kapatıldı."
        )


if __name__ == "__main__":
    main()