# -*- coding: utf-8 -*-
"""
Discord QQ Bridge Plugin
将 Discord 特定频道的消息转发到指定的 QQ 群
"""
import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from astrbot.api.event import filter, AstrMessageEvent, MessageChain
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from astrbot.core.star.filter.permission import PermissionType
from astrbot.api.message_components import Plain, Image

# --- Data Models ---

@dataclass
class BridgeMessage:
    """Standardized message format for bridging"""
    content: str
    author_name: str
    guild_name: str
    channel_name: str
    guild_id: str
    channel_id: str
    timestamp: str
    attachments: List[str]
    is_bot: bool = False

@dataclass
class Destination:
    """Target destination for a message"""
    group_id: str
    adapter_name: str

# --- Components ---

class DiscordParser:
    """Parses Discord events into BridgeMessage objects"""
    
    def parse(self, event: AstrMessageEvent) -> Optional[BridgeMessage]:
        try:
            message_obj = getattr(event, 'message_obj', None)
            if not message_obj:
                return None
            
            raw_message = getattr(message_obj, 'raw_message', None)
            if not raw_message:
                return None

            # Extract basic info
            guild_name = getattr(raw_message.guild, 'name', '私聊') if hasattr(raw_message, 'guild') and raw_message.guild else '私聊'
            channel_name = getattr(raw_message.channel, 'name', '未知频道') if hasattr(raw_message, 'channel') else '未知频道'
            author_name = getattr(raw_message.author, 'display_name', '未知用户') if hasattr(raw_message, 'author') else '未知用户'
            is_bot = getattr(raw_message.author, 'bot', False) if hasattr(raw_message, 'author') else False
            guild_id = str(raw_message.guild.id) if hasattr(raw_message, 'guild') and raw_message.guild else None
            channel_id = str(raw_message.channel.id) if hasattr(raw_message, 'channel') else None

            # Timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if hasattr(raw_message, 'created_at'):
                timestamp = raw_message.created_at.strftime("%Y-%m-%d %H:%M:%S")

            # Attachments
            attachments = []
            if hasattr(raw_message, 'attachments'):
                for attachment in raw_message.attachments:
                    if hasattr(attachment, 'url'):
                        attachments.append(attachment.url)

            return BridgeMessage(
                content=event.message_str,
                author_name=author_name,
                guild_name=guild_name,
                channel_name=channel_name,
                guild_id=guild_id,
                channel_id=channel_id,
                timestamp=timestamp,
                attachments=attachments,
                is_bot=is_bot
            )
        except Exception as e:
            logger.error(f"DiscordParser: Failed to parse event: {e}", exc_info=True)
            return None

class BridgeRouter:
    """Routes messages to their target destinations"""
    
    def __init__(self, data_file: str):
        self.data_file = data_file
        self.data = self._load_data()

    def _load_data(self) -> Dict:
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"BridgeRouter: Failed to load data: {e}")
        return {"enabled_groups": {}}

    def save_data(self):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"BridgeRouter: Failed to save data: {e}")

    def add_rule(self, group_id: str, adapter_name: str, guild_id: str = None, channel_id: str = None):
        discord_config = {}
        if guild_id: discord_config["guild_id"] = str(guild_id)
        if channel_id: discord_config["channel_id"] = str(channel_id)
        
        self.data["enabled_groups"][group_id] = {
            "discord_filter": discord_config,
            "adapter_name": adapter_name,
            "enabled_at": datetime.now().isoformat()
        }
        self.save_data()

    def remove_rule(self, group_id: str) -> bool:
        if group_id in self.data["enabled_groups"]:
            del self.data["enabled_groups"][group_id]
            self.save_data()
            return True
        return False

    def get_destinations(self, msg: BridgeMessage, default_adapter: str) -> List[Destination]:
        dests = []
        for group_id, config in self.data["enabled_groups"].items():
            discord_filter = config.get("discord_filter", {})
            
            # Check filters
            if discord_filter.get("guild_id") and str(discord_filter["guild_id"]) != msg.guild_id:
                continue
            if discord_filter.get("channel_id") and str(discord_filter["channel_id"]) != msg.channel_id:
                continue
            
            # Determine adapter
            adapter = config.get("adapter_name", default_adapter)
            dests.append(Destination(group_id=group_id, adapter_name=adapter))
        return dests

    def get_status(self) -> List[str]:
        lines = []
        for group_id, config in self.data["enabled_groups"].items():
            discord_filter = config.get("discord_filter", {})
            adapter = config.get("adapter_name", "default")
            
            filter_info = []
            if discord_filter.get("guild_id"): filter_info.append(f"Guild:{discord_filter['guild_id']}")
            if discord_filter.get("channel_id"): filter_info.append(f"Channel:{discord_filter['channel_id']}")
            filter_text = " | ".join(filter_info) if filter_info else "All"
            
            lines.append(f"🔗 Group {group_id} ({adapter}) -> {filter_text}")
        return lines

class QQSender:
    """Sends messages to QQ via AstrBot context"""
    
    def __init__(self, context: Context):
        self.context = context

    def _format_content(self, msg: BridgeMessage, template: str) -> str:
        content = msg.content
        # Remove Discord markdown
        content = content.replace('**', '').replace('*', '').replace('`', '').replace('~~', '')
        # Handle mentions
        content = re.sub(r'<@!?(\d+)>', r'@用户\1', content)
        content = re.sub(r'<#(\d+)>', r'#频道\1', content)
        content = re.sub(r'<@&(\d+)>', r'@角色\1', content)
        
        return template.format(
            guild_name=msg.guild_name,
            channel_name=msg.channel_name,
            author_name=msg.author_name,
            timestamp=msg.timestamp,
            content=content
        )

    async def send(self, dest: Destination, msg: BridgeMessage, config: AstrBotConfig):
        try:
            # Format message
            template = config.get("message_template", "")
            formatted_text = self._format_content(msg, template)
            
            # Truncate
            max_len = config.get("max_message_length", 1000)
            if len(formatted_text) > max_len:
                formatted_text = formatted_text[:max_len-3] + "..."

            # Build components
            components = [Plain(formatted_text)]
            
            # Add attachments
            if config.get("enable_image_forward", True):
                for url in msg.attachments:
                    if any(url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                        components.append(Image(url=url))
                    else:
                        components.append(Plain(f"\n📎 附件: {url}"))

            # Send
            qq_session_id = f"{dest.adapter_name}:GroupMessage:{dest.group_id}"
            logger.debug(f"QQSender: Sending to {qq_session_id}")
            
            ret = await self.context.send_message(qq_session_id, MessageChain(components))
            logger.debug(f"QQSender: Result: {ret}")
            
        except Exception as e:
            logger.error(f"QQSender: Failed to send to {dest.group_id}: {e}")

# --- Main Plugin ---

@register("discord_qq_bridge", "SXP-Simon", "Discord QQ 消息桥接插件 (Modular)", "2.0.0")
class DiscordQQBridge(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        
        # Init components
        self.data_dir = "data/plugins/astrbot_plugin_discord_qq_bridge"
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.parser = DiscordParser()
        self.router = BridgeRouter(os.path.join(self.data_dir, "bridge_config.json"))
        self.sender = QQSender(context)
        
        logger.info("Discord QQ Bridge 2.0: Initialized")

    # --- Commands ---

    @filter.command_group("bridge")
    def bridge_group(self):
        pass

    @bridge_group.command("enable")
    @filter.permission_type(PermissionType.ADMIN)
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def enable(self, event: AstrMessageEvent, guild_id: str = None, channel_id: str = None):
        """Enable bridging for current group"""
        group_id = event.get_group_id()
        if not group_id:
            return event.plain_result("❌ Only available in QQ groups").stop_event()
            
        # Auto-detect adapter
        adapter_name = event.get_platform_name()
        
        self.router.add_rule(group_id, adapter_name, guild_id, channel_id)
        
        return event.plain_result(f"✅ Bridge enabled for group {group_id}\n🤖 Adapter: {adapter_name}").stop_event()

    @bridge_group.command("disable")
    @filter.permission_type(PermissionType.ADMIN)
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def disable(self, event: AstrMessageEvent):
        """Disable bridging for current group"""
        group_id = event.get_group_id()
        if self.router.remove_rule(group_id):
            return event.plain_result("✅ Bridge disabled").stop_event()
        return event.plain_result("❌ Bridge not enabled for this group").stop_event()

    @bridge_group.command("status")
    async def status(self, event: AstrMessageEvent):
        """Show bridge status"""
        lines = self.router.get_status()
        if not lines:
            return event.plain_result("📊 No active bridges").stop_event()
        return event.plain_result("📊 Bridge Status:\n" + "\n".join(lines)).stop_event()

    @bridge_group.command("debug_id")
    async def debug_id(self, event: AstrMessageEvent):
        """Show session info"""
        return event.plain_result(
            f"🆔 Session: {event.session_id}\n"
            f"📍 UMO: {event.unified_msg_origin}\n"
            f"🤖 Platform: {event.get_platform_name()}"
        ).stop_event()

    # --- Event Handler ---

    @filter.event_message_type(filter.EventMessageType.ALL, priority=100)
    async def handle_message(self, event: AstrMessageEvent):
        try:
            if event.get_platform_name() != "discord":
                return

            # 1. Parse
            msg = self.parser.parse(event)
            if not msg:
                return
            
            # Check bot filter
            if msg.is_bot and not self.config.get("forward_bot_messages", False):
                logger.debug(f"Bridge: Skipping bot message from {msg.author_name}")
                return

            # 2. Route
            default_adapter = self.config.get("default_qq_adapter_name", "saki")
            dests = self.router.get_destinations(msg, default_adapter)
            if not dests:
                return

            logger.debug(f"Bridge: Forwarding to {len(dests)} groups")

            # 3. Send
            for dest in dests:
                await self.sender.send(dest, msg, self.config)

        except Exception as e:
            logger.error(f"Bridge: Error handling message: {e}", exc_info=True)
