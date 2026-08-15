"""
Vercel Webhook Handler for Telegram Bot
"""
import os
import json
import asyncio
import logging
from http.server import BaseHTTPRequestHandler
from telegram import Update, Bot
from api.bot_logic import dispatch_update

BOT_TOKEN = os.environ.get("BOT_TOKEN")

logger = logging.getLogger(__name__)

_bot = None

def get_bot():
    global _bot
    if _bot is None:
        _bot = Bot(BOT_TOKEN)
    return _bot

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            bot = get_bot()
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            update_dict = json.loads(post_data)
            
            update = Update.de_json(update_dict, bot)
            asyncio.run(dispatch_update(update, bot))
            
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error"}).encode())

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Dating Bot is running!")
