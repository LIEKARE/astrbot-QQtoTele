# 消息处理
import asyncio

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from .evaluation.emoji import type1_ids, type2_ids

class MessageHandler:
    def __init__(self, event: AstrMessageEvent):
        self.event = event
        pass
    async def fetch_emoji_like(self, message_id: int, emoji_ids: dict = None):
        """获取消息的各种贴表情数量, 默认获取所有表情数量

        Args:
            message_id (int): 消息id
            emoji_ids (dict): 表情id字典, 键为表情id, 值为表情类型, 可选
        Returns:
            dict: 表情数量字典, 键为表情id, 值为表情数量
        """
        client = self.event.bot
        emoji_count_dict = {}
        if not emoji_ids:
            emoji_ids = {
                "type1_ids": type1_ids,
                "type2_ids": type2_ids
            }

        semaphore = asyncio.Semaphore(20)

        async def _fetch_one(emoji_id: int, emoji_type: int):
            async with semaphore:
                payloads = {
                    "message_id": message_id,
                    "emojiId": emoji_id,
                    "emojiType": emoji_type,
                }
                response = await client.api.call_action("fetch_emoji_like", **payloads)
                emoji_likes_list = (
                    response.get("emojiLikesList")
                    if isinstance(response, dict)
                    else None
                )
                return emoji_id, len(emoji_likes_list) if emoji_likes_list else 0

        tasks = [
            _fetch_one(emoji_id, 1) for emoji_id in emoji_ids.get("type1_ids", [])
        ] + [
            _fetch_one(emoji_id, 2) for emoji_id in emoji_ids.get("type2_ids", [])
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"[MessageHandler] fetch_emoji_like 调用失败: {result}")
                continue
            emoji_id, emoji_count = result
            emoji_count_dict[emoji_id] = emoji_count

        return emoji_count_dict
    

