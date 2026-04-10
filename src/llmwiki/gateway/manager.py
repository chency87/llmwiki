import asyncio
from typing import Dict
from llmwiki.utils import Settings, get_logger
from llmwiki.gardener.dispatcher import Dispatcher
from .base import BaseChannel

class GatewayManager:
    def __init__(self, config: Settings):
        self.config = config
        self.logger = get_logger(config.paths.vault)
        self.dispatcher = Dispatcher(
            provider=config.llm.provider,
            model_name=config.llm.model,
            base_url=config.llm.base_url,
            api_key=config.llm.api_key,
            vault_path=config.paths.vault
        )
        self.channels: Dict[str, BaseChannel] = {}

    def register_channel(self, channel: BaseChannel):
        self.channels[channel.name] = channel
        self.logger.log("GATEWAY", "INFO", f"Registered channel: {channel.name}")

    async def handle_message(self, channel_name: str, chat_id: str, text: str, user_id: str = None) -> str:
        """
        Normalized entry point for all channels.
        Routes the message to the Dispatcher and sends the response back.
        Returns the response string.
        """
        self.logger.log("GATEWAY", "INFO", f"[{channel_name}] Message from {user_id or chat_id}: {text[:50]}...")
        
        try:
            # Send to dispatcher
            response = await self.dispatcher.dispatch(text)
            
            # Send back to channel (for async platforms)
            channel = self.channels.get(channel_name)
            if channel:
                # We still call send_message for platforms that expect it (like Telegram)
                # But we also return it for sync platforms (like REST)
                await channel.send_message(chat_id, response)
            
            return response
        except Exception as e:
            self.logger.log("GATEWAY", "ERROR", f"Error handling message for {channel_name}: {e}")
            error_msg = f"Sorry, I encountered an error: {e}"
            channel = self.channels.get(channel_name)
            if channel:
                await channel.send_message(chat_id, error_msg)
            return error_msg

    async def start(self):
        """Starts all registered channels."""
        self.logger.log("GATEWAY", "INFO", "Starting Gateway Manager...")
        tasks = [channel.start(self) for channel in self.channels.values()]
        if tasks:
            await asyncio.gather(*tasks)
        else:
            self.logger.log("GATEWAY", "WARNING", "No channels registered to start.")
            # Keep loop alive if needed, or just return
            while True:
                await asyncio.sleep(3600)
