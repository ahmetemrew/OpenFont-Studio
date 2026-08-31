#!/usr/bin/env python3
"""
Font onizleme sayfasi icin basit bir HTTP sunucusu.
TTF dosyalarina dogru Content-Type ve CORS header'lari ekler.
"""
import http.server
import socketserver
import sys
from pathlib import Path

PORT = 8765
ROOT = Path(__file__).resolve().parent.parent


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def guess_type(self, path):
        if path.lower().endswith(".ttf"):
            return "font/ttf"
        return super().guess_type(path)

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {args[0]}")


def main():
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Sunucu calisiyor: http://localhost:{PORT}/preview.html")
        print("Durdurmak icin Ctrl+C")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nSunucu durduruldu.")


if __name__ == "__main__":
    main()
