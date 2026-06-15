# AstrBot QQ -> Local

把 QQ 群消息实时归档成本地 Markdown 文件，同时可选转发到 Astrbot 支持的其他平台（目前已支持 Telegram、Discord、QQ 目标群）。

## 适合什么场景

- 把指定 QQ 群消息稳定落盘，后续拿去检索、整理，或二次加工
- 同一份消息同时输出到本地归档和其他平台，每个转发通道都能单独开关
- 只想做本地归档，不需要跨平台转发
- 需要保留图片、文件、合并转发内容，以及失败时的原始链接

## 功能

- 监听 `banshi_group_list` 中的 QQ 群消息
- 支持四个输出方向：本地 Markdown（强制开启）、Telegram、Discord、QQ 目标群
- 所有外部转发通道均可独立开关，目标列表各自配置
- 支持图片、文件，以及合并转发消息展开
- 支持按前缀临时抑制跨平台转发（归档不受影响）
- 可选屏蔽源群消息，避免机器人重复响应

## 配置项

### 来源群

- `banshi_group_list`: QQ 来源群号列表

### 归档（强制开启，无开关）

- `archive_root`: Markdown 归档根目录。默认 `qq2tg_archive` 会写入 AstrBot 插件数据目录下；容器部署时也可以填绝对路径，例如 `/workspace/archive`
- `archive_save_assets`: 是否下载并保存归档附件（默认 `true`）
- `archive_asset_max_mb`: 归档附件下载大小上限 MB，必须 >= 1（默认 `20`）

### 转发抑制

- `qq_block_prefixes`: 抑制转发前缀列表（默认 `["!!"]`）
  - 当某群出现以这些前缀开头的消息后，该群会进入抑制状态
  - 抑制状态下后续消息（含图片、附件）不会转发到外部平台
  - 本地 Markdown 归档不受这个抑制开关影响
  - 直到该群出现一条不以这些前缀开头的消息，才恢复转发

### QQ 转发

- `enable_qq_forward`: 是否启用 QQ->QQ 转发通道（默认 `false`）
- `qq_target_groups`: QQ 目标群号列表，直接填群号即可，例如 `[123456789]`

### Telegram 转发

- `enable_telegram_forward`: 是否启用 Telegram 转发通道（默认 `true`）
- `telegram_target_unified_origins`: Telegram 目标会话列表
  - 每项形如 `telegram:group_message:<chat_id>` 或 `telegram:private_message:<chat_id>`
- `telegram_upload_files`: 是否下载 QQ 文件并重新上传 Telegram（默认 `true`）
- `telegram_upload_max_mb`: Telegram 文件上传大小上限，超限回退为链接（默认 `10`）

### Discord 转发

- `enable_discord_forward`: 是否启用 Discord 转发通道（默认 `true`）
- `discord_target_unified_origins`: Discord 目标会话列表
  - 建议在 Discord 目标频道执行 `/qq2dc_bind_target` 获取并确认 `unified_msg_origin`

### 其他

- `block_source_messages`: 是否屏蔽源群消息（默认 `true`）
- `banshi_waiting_time`: 缓存后等待多少秒再转发
- `banshi_cache_seconds`: 缓存最大保留时长
- `banshi_cooldown_day_seconds`: 白天转发冷却秒数
- `banshi_cooldown_night_seconds`: 夜间转发冷却秒数
- `banshi_cooldown_day_start`: 白天开始时间（`HH:MM`）
- `banshi_cooldown_night_start`: 夜间开始时间（`HH:MM`）

## 输出逻辑

- 本地归档强制开启，无需配置开关，始终落盘
- Telegram、Discord、QQ 转发各自独立，可分别开关
- 某个转发通道即使开启了，如果目标列表为空，也会自动跳过该通道
- `telegram_upload_files` 和 `telegram_upload_max_mb` 只影响 Telegram 文件发送，不影响本地归档或其他通道

## 快速配置

1. 在 AstrBot 里启用 QQ 适配器。
2. 把需要监听的 QQ 群号填进 `banshi_group_list`。
3. 按需设置 `archive_root`。如果要和 EDU-PUBLISH 配合，可以填容器内绝对路径，例如 `/workspace/archive`。
4. 如需转发到 QQ 目标群，开启 `enable_qq_forward`，并把目标群号填进 `qq_target_groups`。
5. 如需转发到 Telegram，启用 Telegram 适配器，在目标聊天执行 `/qq2tg_bind_target`，把结果填进 `telegram_target_unified_origins`。
6. 如需转发到 Discord，启用 Discord 适配器，在目标频道执行 `/qq2dc_bind_target`，把结果填进 `discord_target_unified_origins`。
7. 保存插件配置并重载插件。

## 示例配置

```json
{
  "banshi_group_list": ["123456789"],
  "archive_root": "/workspace/archive",
  "archive_save_assets": true,
  "archive_asset_max_mb": 20,
  "qq_block_prefixes": ["!!"],
  "enable_qq_forward": false,
  "qq_target_groups": [],
  "enable_telegram_forward": true,
  "telegram_target_unified_origins": ["telegram:group_message:-1001234567890"],
  "telegram_upload_files": true,
  "telegram_upload_max_mb": 10,
  "enable_discord_forward": false,
  "discord_target_unified_origins": [],
  "block_source_messages": true,
  "banshi_waiting_time": 2,
  "banshi_cache_seconds": 3600,
  "banshi_cooldown_day_seconds": 30,
  "banshi_cooldown_night_seconds": 60,
  "banshi_cooldown_day_start": "09:00",
  "banshi_cooldown_night_start": "01:00"
}
```

## 归档目录结构

归档按天写入：

```text
archive/
  2026-02-13/
    messages.md
    files/
    photos/
  index/
    message_ids.json
```

- `messages.md`: 每条消息一个块，包含时间、来源群、发送者、正文、附件
- `files/` 和 `photos/`: 保存下载成功的附件；下载失败或超限时回退为链接记录
- `index/message_ids.json`: 消息去重索引，避免重复写入

## 辅助命令

- `/qq2tg_show_umo`: 显示当前会话的 `unified_msg_origin`
- `/qq2tg_show_archive`: 显示当前输出通道状态与归档目录
- `/qq2tg_bind_target`: 在 Telegram 中执行，把当前会话加入内存目标列表，并回显可写入配置的值
- `/qq2dc_bind_target`: 在 Discord 中执行，把当前会话加入内存目标列表，并回显可写入配置的值

注意：`/qq2tg_bind_target` 和 `/qq2dc_bind_target` 都只在当前进程内生效，重启后仍需以配置文件为准。
