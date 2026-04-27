# 转发管理
from typing import Dict, List, Union

from astrbot.api.event import AstrMessageEvent

class ForwardManager:
    def __init__(self, event: AstrMessageEvent):
        self.event = event
    
        
    async def get_forward_msg(self, message_id=None, *, forward_id=None):
        """获取转发消息

        Returns:
            Dict: 转发消息
        """
        client = self.event.bot
        if forward_id is not None:
            payloads = {"id": forward_id}
        else:
            if message_id is None:
                message_id = getattr(
                    getattr(self.event, "message_obj", None), "message_id", None
                )
            if message_id is None:
                return {}
            payloads = {"message_id": message_id}
        response = await client.api.call_action("get_forward_msg", **payloads)
        return response
    
    async def send_forward_msg_raw(self,message_id:int, group_id:int):
        """发送转发消息

        Args:
            group_id (int): 群号
        """
        client = self.event.bot
        payloads = {
            "group_id": group_id,
            "message_id": message_id
        }
        await client.api.call_action("forward_group_single_msg", **payloads)
    
    async def build_base_node(self, msg_data:Dict) -> Dict:
        """构建基础节点

        Args:
            msg_data (Dict): 消息数据

        Returns:
            Dict: 基础节点
        """
        if not isinstance(msg_data, dict):
            msg_data = {}

        sender = msg_data.get("sender") if isinstance(msg_data, dict) else {}
        if not isinstance(sender, dict):
            sender = {}

        return {
            "type": "node",
            "data": {
                "uin": str(msg_data.get("user_id", "")),
                "content": msg_data.get("raw_message", "[空消息]"),
                "time": msg_data.get("time", 0),
                "nick": sender.get("nickname", "未知用户")
            }
        }

    @staticmethod
    def _extract_forward_id(msg_data: Dict):
        if not isinstance(msg_data, dict):
            return None

        for key in ("messages", "message"):
            segments = msg_data.get(key)
            if not isinstance(segments, list) or not segments:
                continue

            first_segment = segments[0]
            if not isinstance(first_segment, dict) or first_segment.get("type") != "forward":
                continue

            data = first_segment.get("data")
            if not isinstance(data, dict):
                continue

            forward_id = data.get("id")
            if forward_id is not None:
                return forward_id
        return None
        
    async def build_nested_nodes(self, msg_data:Dict, depth: int = 0) -> Union[Dict, List]:
        """构建嵌套节点

        Args:
            msg_data (Dict): 消息数据
            depth (int, optional): 深度. Defaults to 0.

        Returns:
            Union[Dict, List]: 嵌套节点
        """
        if depth >=3 :
            return {"type": "text", "data": {"text": "[嵌套层数过多]"}}

        forward_id = self._extract_forward_id(msg_data)
        if forward_id is not None:
            res = await self.get_forward_msg(forward_id=forward_id)
            messages = res.get("messages") if isinstance(res, dict) else None
            if not isinstance(messages, list):
                return {"type": "text", "data": {"text": "[合并转发加载失败]"}}
            
            # 递归处理嵌套信息
            child_nodes = []
            for child_msg in messages:
                child_node = await self.build_nested_nodes(child_msg, depth + 1)
                child_nodes.append(child_node)
            
            return {
                "type": "forward",
                "data": {
                    "nodes": child_nodes,
                    "title": f"嵌套转发层数: {depth + 1}"
                }
            }
        return await self.build_base_node(msg_data)

    async def send_forward_msg_reconstruct(self, group_id:int):
        """重构转发消息并发送
        注意!!! 由于似乎无法获取转发消息中的forward类型标签(get_forward_msg api无法获取), 故暂时弃用

        Args:
            group_id (int): 群号
        """
        client = self.event.bot
        response = await self.get_forward_msg()
        nodes = await self.build_nested_nodes(response)
        payloads = {
            "group_id": group_id,
            "message": nodes
        }
        await client.api.call_action("send_forward_msg", **payloads)
