# -*- coding: utf-8 -*-
"""
Discord QQ Bridge Plugin
将 Discord 特定频道的消息转发到指定的 QQ 群
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import re

from astrbot.api.event import filter, AstrMessageEvent, MessageChain
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from astrbot.core.star.filter.permission import PermissionType

from astrbot.api.message_components import Plain, Image



@register("discord_qq_bridge", "SXP-Simon", "Discord QQ 消息桥接插件", "1.0.0")
class DiscordQQBridge(Star):
    # 初始化
    def __init__(self, context: Context, config: AstrBotConfig):
        """初始化插件"""
        super().__init__(context)
        self.config = config
        
        # 数据存储路径
        self.data_dir = "data/plugins/astrbot_plugin_discord_qq_bridge"
        os.makedirs(self.data_dir, exist_ok=True)
        self.bridge_config_path = os.path.join(self.data_dir, "bridge_config.json")
        
        # 加载桥接配置
        self.bridge_config = self._load_bridge_config()
        
        logger.info("Discord QQ Bridge: 插件初始化完成")

    def _load_bridge_config(self) -> Dict:
        """加载桥接配置"""
        if os.path.exists(self.bridge_config_path):
            try:
                with open(self.bridge_config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Discord QQ Bridge: 加载配置失败: {e}")
        
        # 默认配置
        return {
            "enabled_groups": {},  # QQ群ID -> Discord频道配置的映射
            "qq_adapter_name": "saki", # QQ适配器名称，默认为 saki
            "message_template": "🔗 Discord 消息转发\n\n服务器: {guild_name}\n频道: #{channel_name}\n发言人: {author_name}\n时间: {timestamp}\n\n内容:\n{content}"
        }

    def _save_bridge_config(self):
        """保存桥接配置"""
        try:
            with open(self.bridge_config_path, 'w', encoding='utf-8') as f:
                json.dump(self.bridge_config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Discord QQ Bridge: 保存配置失败: {e}")

    def _prepare_command(self, event: AstrMessageEvent):
        """准备命令执行环境"""
        event.stop_event()
        event.should_call_llm(False)

    @filter.command_group("bridge")
    def bridge_group(self):
        """Discord QQ Bridge 命令组"""
        pass

    @bridge_group.command("enable")
    @filter.permission_type(PermissionType.ADMIN)
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def enable_bridge(self, event: AstrMessageEvent, discord_guild_id: str = None, discord_channel_id: str = None):
        """启用当前QQ群的Discord消息桥接
        
        用法: /bridge enable [discord_guild_id] [discord_channel_id]
        如果不提供参数，将监听所有Discord消息
        """
        self._prepare_command(event)
        
        try:
            group_id = event.get_group_id()
            if not group_id:
                return event.plain_result("❌ 此命令只能在QQ群中使用").stop_event()
            
            # 配置Discord频道过滤
            discord_config = {}
            if discord_guild_id:
                discord_config["guild_id"] = str(discord_guild_id)
            if discord_channel_id:
                discord_config["channel_id"] = str(discord_channel_id)
            
            self.bridge_config["enabled_groups"][group_id] = {
                "discord_filter": discord_config,
                "enabled_at": datetime.now().isoformat()
            }
            
            self._save_bridge_config()
            
            filter_info = ""
            if discord_guild_id or discord_channel_id:
                filter_info = f"\n📍 过滤条件: 服务器ID={discord_guild_id or '任意'}, 频道ID={discord_channel_id or '任意'}"
            
            return event.plain_result(f"✅ 已为当前QQ群启用Discord消息桥接{filter_info}").stop_event()
            
        except Exception as e:
            logger.error(f"Discord QQ Bridge: 启用桥接失败: {e}")
            return event.plain_result(f"❌ 启用失败: {e}").stop_event()

    @bridge_group.command("disable")
    @filter.permission_type(PermissionType.ADMIN)
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def disable_bridge(self, event: AstrMessageEvent):
        """禁用当前QQ群的Discord消息桥接"""
        self._prepare_command(event)
        
        try:
            group_id = event.get_group_id()
            if not group_id:
                return event.plain_result("❌ 此命令只能在QQ群中使用").stop_event()
            
            if group_id not in self.bridge_config["enabled_groups"]:
                return event.plain_result("❌ 当前QQ群未启用Discord消息桥接").stop_event()
            
            del self.bridge_config["enabled_groups"][group_id]
            self._save_bridge_config()
            
            return event.plain_result("✅ 已禁用当前QQ群的Discord消息桥接").stop_event()
            
        except Exception as e:
            logger.error(f"Discord QQ Bridge: 禁用桥接失败: {e}")
            return event.plain_result(f"❌ 禁用失败: {e}").stop_event()

    @bridge_group.command("status")
    async def bridge_status(self, event: AstrMessageEvent):
        """查看桥接状态"""
        self._prepare_command(event)
        
        try:
            enabled_groups = self.bridge_config["enabled_groups"]
            
            if not enabled_groups:
                return event.plain_result("📊 Discord QQ Bridge 状态\n\n❌ 暂无启用桥接的QQ群").stop_event()
            
            status_lines = ["📊 Discord QQ Bridge 状态\n"]
            
            for group_id, config in enabled_groups.items():
                discord_filter = config.get("discord_filter", {})
                enabled_at = config.get("enabled_at", "未知")
                
                filter_info = []
                if discord_filter.get("guild_id"):
                    filter_info.append(f"服务器ID: {discord_filter['guild_id']}")
                if discord_filter.get("channel_id"):
                    filter_info.append(f"频道ID: {discord_filter['channel_id']}")
                
                filter_text = " | ".join(filter_info) if filter_info else "监听所有Discord消息"
                
                status_lines.append(f"🔗 QQ群 {group_id}")
                status_lines.append(f"   📍 过滤: {filter_text}")
                status_lines.append(f"   ⏰ 启用时间: {enabled_at[:19]}")
                status_lines.append("")
            
            return event.plain_result("\n".join(status_lines)).stop_event()
            
        except Exception as e:
            logger.error(f"Discord QQ Bridge: 获取状态失败: {e}")
            return event.plain_result(f"❌ 获取状态失败: {e}").stop_event()

    @bridge_group.command("debug_id")
    async def debug_session_id(self, event: AstrMessageEvent):
        """调试用：显示当前会话ID"""
        self._prepare_command(event)
        return event.plain_result(f"🆔 会话ID: {event.session_id}\n📍 UMO: {event.unified_msg_origin}\n平台: {event.get_platform_name()}").stop_event()

    @bridge_group.command("template")
    @filter.permission_type(PermissionType.ADMIN)
    async def set_template(self, event: AstrMessageEvent, template: str = None):
        """设置或查看消息模板
        
        用法: /bridge template [新模板]
        可用变量: {guild_name}, {channel_name}, {author_name}, {timestamp}, {content}
        """
        self._prepare_command(event)
        
        try:
            if template is None:
                # 查看当前模板
                current_template = self.bridge_config.get("message_template", "")
                return event.plain_result(f"📝 当前消息模板:\n\n{current_template}").stop_event()
            
            # 设置新模板
            self.bridge_config["message_template"] = template
            self._save_bridge_config()
            
            return event.plain_result("✅ 消息模板已更新").stop_event()
            
        except Exception as e:
            logger.error(f"Discord QQ Bridge: 设置模板失败: {e}")
            return event.plain_result(f"❌ 设置模板失败: {e}").stop_event()

    @filter.event_message_type(filter.EventMessageType.ALL, priority=100)
    async def handle_discord_message(self, event: AstrMessageEvent):
        """处理Discord消息并转发到QQ群"""
        try:
            # 只处理来自Discord平台的消息
            if event.get_platform_name() != "discord":
                return

            logger.debug(f"Discord QQ Bridge: 收到消息，平台: {event.get_platform_name()}")
            logger.debug(f"Discord QQ Bridge: 开始处理Discord消息: {event.message_str}")

            # 检查是否应该转发此消息
            if not self._should_forward_message(event):
                # 日志已在 _should_forward_message 中记录
                return

            # 获取Discord消息信息
            discord_info = self._extract_discord_info(event)
            if not discord_info:
                # 日志已在 _extract_discord_info 中记录
                return

            # 检查是否有需要转发的QQ群
            target_groups = self._get_target_groups(discord_info)
            if not target_groups:
                logger.debug("Discord QQ Bridge: 没有目标QQ群")
                return

            logger.debug(f"Discord QQ Bridge: 目标QQ群: {target_groups}")

            # 格式化消息
            formatted_message = self._format_message(discord_info)
            logger.debug(f"Discord QQ Bridge: 格式化消息: {formatted_message}")

            # 处理附件（图片等）
            attachments = self._extract_attachments(event)
            logger.debug(f"Discord QQ Bridge: 附件: {attachments}")

            # 转发到目标QQ群
            await self._forward_to_qq_groups(formatted_message, target_groups, attachments)

        except Exception as e:
            logger.error(f"Discord QQ Bridge: 处理消息失败: {e}", exc_info=True)

    def _extract_discord_info(self, event: AstrMessageEvent) -> Optional[Dict]:
        """提取Discord消息信息"""
        try:
            # 从事件中获取Discord特定信息
            message_obj = getattr(event, 'message_obj', None)
            if not message_obj:
                logger.debug("Discord QQ Bridge: message_obj 为空")
                return None

            # 获取Discord原始消息对象
            raw_message = getattr(message_obj, 'raw_message', None)
            if not raw_message:
                logger.warning("Discord QQ Bridge: raw_message 为空 (message_obj.raw_message is None)")
                return None

            # 获取Discord消息的详细信息
            guild_name = getattr(raw_message.guild, 'name', '未知服务器') if hasattr(raw_message, 'guild') and raw_message.guild else '私聊'
            channel_name = getattr(raw_message.channel, 'name', '未知频道') if hasattr(raw_message, 'channel') else '未知频道'
            author_name = getattr(raw_message.author, 'display_name', '未知用户') if hasattr(raw_message, 'author') else '未知用户'
            guild_id = str(raw_message.guild.id) if hasattr(raw_message, 'guild') and raw_message.guild else None
            channel_id = str(raw_message.channel.id) if hasattr(raw_message, 'channel') else None

            # 格式化时间戳
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if hasattr(raw_message, 'created_at'):
                timestamp = raw_message.created_at.strftime("%Y-%m-%d %H:%M:%S")

            return {
                'guild_name': guild_name,
                'channel_name': channel_name,
                'author_name': author_name,
                'guild_id': guild_id,
                'channel_id': channel_id,
                'timestamp': timestamp,
                'content': event.message_str
            }

        except Exception as e:
            logger.error(f"Discord QQ Bridge: 提取Discord信息失败: {e}", exc_info=True)
            return None

    def _get_target_groups(self, discord_info: Dict) -> List[str]:
        """获取需要转发的目标QQ群"""
        target_groups = []
        
        try:
            for group_id, config in self.bridge_config["enabled_groups"].items():
                discord_filter = config.get("discord_filter", {})

                # 检查服务器ID过滤（统一转换为字符串比较）
                if discord_filter.get("guild_id") and str(discord_filter["guild_id"]) != discord_info.get("guild_id"):
                    logger.debug(f"Discord QQ Bridge: 群 {group_id} 过滤不匹配: 配置GuildID={discord_filter['guild_id']} != 消息GuildID={discord_info.get('guild_id')}")
                    continue

                # 检查频道ID过滤（统一转换为字符串比较）
                if discord_filter.get("channel_id") and str(discord_filter["channel_id"]) != discord_info.get("channel_id"):
                    logger.debug(f"Discord QQ Bridge: 群 {group_id} 过滤不匹配: 配置ChannelID={discord_filter['channel_id']} != 消息ChannelID={discord_info.get('channel_id')}")
                    continue

                target_groups.append(group_id)
                logger.debug(f"Discord QQ Bridge: 匹配成功，添加群 {group_id}")

        except Exception as e:
            logger.error(f"Discord QQ Bridge: 匹配群组时发生错误: {e}", exc_info=True)

        return target_groups

    def _extract_attachments(self, event: AstrMessageEvent) -> List[str]:
        """提取Discord消息中的附件URL"""
        attachments = []

        try:
            message_obj = getattr(event, 'message_obj', None)
            if not message_obj:
                return attachments

            # 获取Discord原始消息对象
            raw_message = getattr(message_obj, 'raw_message', None)
            if not raw_message or not hasattr(raw_message, 'attachments'):
                return attachments

            for attachment in raw_message.attachments:
                if hasattr(attachment, 'url'):
                    attachments.append(attachment.url)

        except Exception as e:
            logger.error(f"Discord QQ Bridge: 提取附件失败: {e}")

        return attachments

    def _format_message(self, discord_info: Dict) -> str:
        """格式化转发消息"""
        template = self.bridge_config.get("message_template",
            "🔗 Discord 消息转发\n\n服务器: {guild_name}\n频道: #{channel_name}\n发言人: {author_name}\n时间: {timestamp}\n\n内容:\n{content}")

        # 处理消息内容，移除Discord特有的格式
        content = discord_info['content']

        # 移除Discord的markdown格式，因为QQ不支持
        content = content.replace('**', '').replace('*', '').replace('`', '').replace('~~', '')

        # 处理Discord的mention格式
        content = re.sub(r'<@!?(\d+)>', r'@用户\1', content)  # 用户mention
        content = re.sub(r'<#(\d+)>', r'#频道\1', content)    # 频道mention
        content = re.sub(r'<@&(\d+)>', r'@角色\1', content)   # 角色mention

        return template.format(
            guild_name=discord_info['guild_name'],
            channel_name=discord_info['channel_name'],
            author_name=discord_info['author_name'],
            timestamp=discord_info['timestamp'],
            content=content
        )

    async def _forward_to_qq_groups(self, message: str, target_groups: List[str], attachments: List[str] = None):
        """转发消息到QQ群"""
        for group_id in target_groups:
            try:
                # 检查消息长度限制
                max_length = self.bridge_config.get("max_message_length", 1000)
                if len(message) > max_length:
                    message = message[:max_length-3] + "..."

                # 构造QQ群会话ID（格式：平台名:消息类型:会话ID）
                adapter_name = self.bridge_config.get("qq_adapter_name", "saki")
                qq_session_id = f"{adapter_name}:GroupMessage:{group_id}"
                logger.debug(f"Discord QQ Bridge: 尝试发送到会话ID: {qq_session_id}")

                # 准备消息组件
                message_components = [Plain(message)]

                # 添加附件信息
                if attachments and self.bridge_config.get("enable_image_forward", True):
                    for attachment_url in attachments:
                        try:
                            # 对于图片，尝试作为图片组件发送
                            if any(attachment_url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                                message_components.append(Image(url=attachment_url))
                            else:
                                # 对于其他文件，添加链接到消息中
                                message_components.append(Plain(f"\n📎 附件: {attachment_url}"))
                        except Exception as e:
                            logger.error(f"Discord QQ Bridge: 处理附件失败: {e}")
                            message_components.append(Plain(f"\n📎 附件: {attachment_url}"))

                # 发送消息到QQ群
                message_chain = MessageChain(message_components)
                ret = await self.context.send_message(qq_session_id, message_chain)
                logger.debug(f"Discord QQ Bridge: 发送结果: {ret}")

                logger.debug(f"Discord QQ Bridge: 消息已转发到QQ群 {group_id}")

            except Exception as e:
                logger.error(f"Discord QQ Bridge: 转发到QQ群 {group_id} 失败: {e}")

    def _should_forward_message(self, event: AstrMessageEvent) -> bool:
        """判断是否应该转发此消息"""
        try:
            # 检查是否转发机器人消息
            message_obj = getattr(event, 'message_obj', None)
            if message_obj:
                raw_message = getattr(message_obj, 'raw_message', None)
                if raw_message and hasattr(raw_message, 'author'):
                    if raw_message.author.bot and not self.bridge_config.get("forward_bot_messages", False):
                        logger.debug(f"Discord QQ Bridge: 跳过机器人消息 (Author: {raw_message.author.name})")
                        return False

            # 检查消息内容是否为空
            if not event.message_str.strip():
                logger.debug("Discord QQ Bridge: 消息内容为空 (Empty Content)")
                return False

            return True

        except Exception as e:
            logger.error(f"Discord QQ Bridge: 判断是否转发消息失败: {e}")
            return False
