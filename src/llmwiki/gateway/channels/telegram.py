import asyncio
from typing import Any
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from ..base import BaseChannel

class TelegramChannel(BaseChannel):
    def __init__(self, token: str, allowed_users: list = None):
        super().__init__("telegram")
        self.token = token
        self.allowed_users = allowed_users or []
        self.app = None

    async def start(self, manager: Any):
        if not self.token:
            manager.logger.log("GATEWAY", "ERROR", "Telegram token not provided. Skipping.")
            return

        self.app = ApplicationBuilder().token(self.token).build()
        
        async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = str(update.effective_user.id)
            if self.allowed_users and user_id not in self.allowed_users:
                await update.message.reply_text("Sorry, you are not authorized to use this bot.")
                return
            
            # Handle incoming message
            text = update.message.text
            chat_id = str(update.effective_chat.id)
            
            await manager.handle_message(self.name, chat_id, text, user_id=user_id)

        self.app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), on_message))
        
        manager.logger.log("GATEWAY", "INFO", "Telegram listener starting (polling)...")
        # Run polling in a separate task to avoid blocking the manager's start()
        async with self.app:
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling()
            
            # Keep alive
            while True:
                await asyncio.sleep(3600)

    async def send_message(self, chat_id: str, text: str):
        if self.app and self.app.bot:
            # Chunk long messages for Telegram (max 4096 chars)
            if len(text) > 4000:
                for i in range(0, len(text), 4000):
                    await self.app.bot.send_message(chat_id=chat_id, text=text[i:i+4000])
            else:
                await self.app.bot.send_message(chat_id=chat_id, text=text)
