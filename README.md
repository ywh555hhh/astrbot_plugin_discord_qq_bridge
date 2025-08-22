# Discord QQ Bridge Plugin

Discord QQ 消息桥接插件 - 将 Discord 特定频道的消息转发到指定的 QQ 群

## 功能特性

- 🔗 **智能桥接**: 将 Discord 频道消息实时转发到 QQ 群
- 🎯 **精确过滤**: 支持按 Discord 服务器ID和频道ID进行精确过滤
- 📝 **自定义模板**: 可自定义转发消息的格式模板
- 🛡️ **权限控制**: 管理员权限控制，确保安全使用
- 📊 **状态监控**: 实时查看桥接状态和配置信息
- ⚡ **高性能**: 异步处理，不影响机器人其他功能

## 安装说明

1. 将插件文件夹放置在 `data/plugins/` 目录下
2. 重启 AstrBot 或重新加载插件
3. 插件将自动初始化并创建必要的配置文件

## 使用方法

### 基础命令

所有命令都以 `/bridge` 开头：

#### 启用桥接
```
/bridge enable [discord_guild_id] [discord_channel_id]
```
- 在QQ群中使用此命令启用Discord消息桥接
- `discord_guild_id`: 可选，Discord服务器ID，不填则监听所有服务器
- `discord_channel_id`: 可选，Discord频道ID，不填则监听所有频道

**示例：**
```
/bridge enable                           # 监听所有Discord消息
/bridge enable 123456789                 # 只监听指定服务器的消息
/bridge enable 123456789 987654321       # 只监听指定服务器的指定频道
```

#### 禁用桥接
```
/bridge disable
```
- 在QQ群中使用此命令禁用当前群的Discord消息桥接

#### 查看状态
```
/bridge status
```
- 查看当前所有启用桥接的QQ群及其配置信息

#### 设置消息模板
```
/bridge template [新模板]
```
- 不带参数：查看当前消息模板
- 带参数：设置新的消息模板

**可用模板变量：**
- `{guild_name}`: Discord服务器名称
- `{channel_name}`: Discord频道名称  
- `{author_name}`: 发言人昵称
- `{timestamp}`: 消息时间戳
- `{content}`: 消息内容

**默认模板：**
```
🔗 Discord 消息转发

服务器: {guild_name}
频道: #{channel_name}
发言人: {author_name}
时间: {timestamp}

内容:
{content}
```

### 权限要求

- `enable` 和 `disable` 命令需要管理员权限
- `template` 命令需要管理员权限
- `status` 命令所有用户都可使用

## 配置说明

插件配置文件位于 `data/plugins/astrbot_plugin_discord_qq_bridge/bridge_config.json`

### 配置项说明

- `enabled_groups`: 启用桥接的QQ群配置（通过命令管理）
- `message_template`: 转发消息模板
- `max_message_length`: 最大消息长度限制
- `enable_image_forward`: 是否转发图片附件
- `enable_embed_forward`: 是否转发Embed内容
- `forward_bot_messages`: 是否转发机器人消息
- `rate_limit_seconds`: 转发频率限制

## 使用场景

1. **跨平台沟通**: 将Discord社区讨论同步到QQ群
2. **重要通知转发**: 将Discord公告频道消息转发到QQ管理群
3. **多平台监控**: 监控特定Discord频道的活动
4. **社区整合**: 整合Discord和QQ两个平台的用户交流

## 注意事项

1. 确保机器人在目标Discord服务器和QQ群中都有相应权限
2. 合理设置过滤条件，避免消息刷屏
3. 定期检查桥接状态，确保功能正常运行
4. 注意消息长度限制，过长消息会被截断

## 故障排除

### 常见问题

1. **消息未转发**
   - 检查Discord机器人是否在线
   - 确认QQ群桥接是否已启用
   - 查看过滤条件是否正确

2. **权限错误**
   - 确保使用管理员账号执行命令
   - 检查机器人在QQ群中的权限

3. **配置丢失**
   - 检查配置文件是否存在
   - 重新执行enable命令

## 更新日志

### v1.0.0
- 初始版本发布
- 支持基础的Discord到QQ消息桥接功能
- 支持服务器和频道过滤
- 支持自定义消息模板
- 支持权限控制和状态监控

## 作者信息

- **作者**: SXP-Simon
- **版本**: 1.0.0
- **许可证**: MIT License

## 贡献

欢迎提交Issue和Pull Request来改进这个插件！
