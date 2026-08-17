"""
Vercel Webhook Handler for Telegram Bot
"""

import os
import json
import asyncio
import logging
import traceback
from http.server import BaseHTTPRequestHandler

from telegram import Update, Bot

from api.bot_logic import dispatch_update


# =========================
# CONFIG
# =========================

BOT_TOKEN = os.environ.get("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =========================
# PROCESS TELEGRAM UPDATE
# =========================

async def process_update(update_dict):
    """
    Create a fresh Telegram Bot for this request,
    process the update, then properly close the Bot.
    """

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is missing")

    # Create a new bot for this request.
    bot = Bot(token=BOT_TOKEN)

    # Bot is an async context manager in python-telegram-bot 21.4.
    # This initializes it and shuts it down automatically.
    async with bot:

        update = Update.de_json(
            update_dict,
            bot
        )

        await dispatch_update(
            update,
            bot
        )


# =========================
# VERCEL HANDLER
# =========================

class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        try:

            # -------------------------
            # Read request body
            # -------------------------

            content_length = int(
                self.headers.get("Content-Length", 0)
            )

            if content_length <= 0:
                raise ValueError("Empty webhook request")

            post_data = self.rfile.read(content_length)

            update_dict = json.loads(
                post_data.decode("utf-8")
            )

            logger.info("Telegram update received")

            # -------------------------
            # Run async processing
            # -------------------------

            asyncio.run(
                process_update(update_dict)
            )

            # -------------------------
            # Success response
            # -------------------------

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "application/json"
            )

            self.end_headers()

            response = {
                "status": "ok"
            }

            self.wfile.write(
                json.dumps(response).encode("utf-8")
            )

        except Exception as e:

            # -------------------------
            # Log FULL traceback
            # -------------------------

            logger.error(
                "Webhook error: %s",
                str(e)
            )

            logger.error(
                traceback.format_exc()
            )

            # -------------------------
            # Always return 200 to Telegram
            # -------------------------

            try:

                self.send_response(200)

                self.send_header(
                    "Content-Type",
                    "application/json"
                )

                self.end_headers()

                response = {
                    "status": "error",
                    "message": str(e)
                }

                self.wfile.write(
                    json.dumps(response).encode("utf-8")
                )

            except Exception:
                pass

    # =========================
    # HEALTH CHECK
    # =========================

    def do_GET(self):

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/plain"
        )

        self.end_headers()

        self.wfile.write(
            b"Dating Bot is running!"
        )
