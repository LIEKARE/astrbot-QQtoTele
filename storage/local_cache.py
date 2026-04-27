# local_cache.py

import os
import json
import time
import asyncio
from astrbot.api import logger
from astrbot.api.star import StarTools

from ..config import WAITING_TIME


class LocalCache:
    def __init__(
        self,
        max_age_seconds: int = 3600,
        waiting_time: int | None = None,
        cache_dir=None,
    ):
        if cache_dir is None:
            cache_dir = StarTools.get_data_dir() / "sowing_discord_cache"
        self.cache_file = os.path.join(os.fspath(cache_dir), "local_cache.json")
        self.WAITING_TIME = waiting_time if waiting_time is not None else WAITING_TIME
        self.MAX_CACHE_AGE_SECONDS = max_age_seconds

        self._file_lock = asyncio.Lock()

        cache_dir = os.path.dirname(self.cache_file)
        os.makedirs(cache_dir, exist_ok=True)
        self._cache = self._load_cache()

        if not os.path.exists(self.cache_file):
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f)

    def _load_cache(self) -> dict:
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                cache = json.load(f)
            return cache if isinstance(cache, dict) else {}
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError as exc:
            logger.warning(f"[LocalCache] 缓存文件已损坏，将按空缓存处理: {exc}")
            return {}

    def _save_cache(self):
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self._cache, f)

    @staticmethod
    def _parse_cache_entry(entry):
        if isinstance(entry, (int, float)):
            return float(entry), None, False
        if isinstance(entry, dict):
            ts_raw = entry.get("ts", entry.get("timestamp", 0))
            group_id = entry.get("group_id")
            ignore_forward = bool(entry.get("ignore_forward", False))
            try:
                ts = float(ts_raw)
            except (TypeError, ValueError):
                ts = 0.0
            return ts, group_id, ignore_forward
        return 0.0, None, False

    async def cleanup_expired_cache(self) -> int:
        """清理缓存中超过 MAX_CACHE_AGE_SECONDS 的消息，并返回清理数量。"""
        current_time = time.time()
        cleaned_count = 0

        async with self._file_lock:
            if not self._cache:
                return 0

            keys_to_keep = {}
            for message_id_str, entry in self._cache.items():
                timestamp, group_id, ignore_forward = self._parse_cache_entry(entry)
                if (
                    timestamp <= 0
                    or current_time - timestamp > self.MAX_CACHE_AGE_SECONDS
                ):
                    cleaned_count += 1
                else:
                    keys_to_keep[message_id_str] = {
                        "ts": timestamp,
                        "group_id": group_id,
                        "ignore_forward": ignore_forward,
                    }

            if cleaned_count > 0:
                self._cache = keys_to_keep
                self._save_cache()

            return cleaned_count

    async def add_cache(
        self, message_id: int, group_id=None, ignore_forward: bool = False
    ):
        """添加一条message_id进入缓存, 保存时间"""
        str_message_id = str(message_id)

        async with self._file_lock:
            self._cache[str_message_id] = {
                "ts": time.time(),
                "group_id": group_id,
                "ignore_forward": bool(ignore_forward),
            }

            self._save_cache()

    async def get_waiting_messages(self) -> list:
        """获取已经等待足够时间的消息列表"""

        waiting_messages = []
        current_time = time.time()

        async with self._file_lock:
            cache = dict(self._cache)
            if not cache:
                return []

        for message_id_str, entry in cache.items():
            timestamp, _, _ = self._parse_cache_entry(entry)
            if current_time - timestamp > self.WAITING_TIME:
                waiting_messages.append(message_id_str)

        return waiting_messages

    async def get_earliest_timestamp(self) -> float | None:
        """获取缓存中最早的时间戳，用于计算等待时间。如果没有消息返回 None。"""
        async with self._file_lock:
            cache = dict(self._cache)
            if not cache:
                return None

        timestamps = []
        for entry in cache.values():
            ts, _, _ = self._parse_cache_entry(entry)
            if ts > 0:
                timestamps.append(ts)
        return min(timestamps) if timestamps else None

    async def get_message_group_id(self, message_id: int | str):
        str_message_id = str(message_id)

        async with self._file_lock:
            entry = self._cache.get(str_message_id)
            if entry is None:
                return None

        _, group_id, _ = self._parse_cache_entry(entry)
        return group_id

    async def get_message_ignore_forward(self, message_id: int | str) -> bool:
        str_message_id = str(message_id)

        async with self._file_lock:
            entry = self._cache.get(str_message_id)
            if entry is None:
                return False

        _, _, ignore_forward = self._parse_cache_entry(entry)
        return ignore_forward

    async def has_pending_messages(self) -> bool:
        """检查缓存中是否还有消息（无论是否成熟）"""
        async with self._file_lock:
            return bool(self._cache)

    async def remove_cache(self, message_id: int):
        """转发成功或失败后，手动删除指定的 message_id"""
        str_message_id = str(message_id)

        async with self._file_lock:
            if not self._cache:
                return False

            if str_message_id in self._cache:
                del self._cache[str_message_id]

                self._save_cache()

                return True
            return False
