# encoding:utf-8

import plugins
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from plugins import *
from config import conf, global_config
import os
import json
import requests

@plugins.register(
    name="ImageRecognitionPlugin",
    desire_priority=970,
    desc="Recognize content in images and return the result as text",
    version="1.0",
    author="YourName",
)
class ImageRecognitionPlugin(Plugin):
    def __init__(self):
        super().__init__()

        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context

        # 初始化存储图像路径的字典
        self.image_data = {}

        # 初始化配置
        curdir = os.path.dirname(__file__)
        config_path = os.path.join(curdir, "config.json")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                logger.info(f"[ImageRecognitionPlugin] 配置文件加载成功: {config}")

                # 读取配置文件中的参数
                self.recognition_keyword = config.get("recognition_keyword", ["pi"])
                self.no_image_message = config.get("no_image_message", "请先发送图像。")
                self.no_query_message = config.get("no_query_message", "请描述您想了解的内容。")
                self.recognition_failed_message = config.get("recognition_failed_message", "图像识别失败。")
                self.api_url = config.get("api_url", "")

                logger.info("[[ImageRecognition]] 初始化已完成")
        except Exception as e:
            logger.error(f"[[ImageRecognition]] 初始化错误: {e}")
            self.recognition_keyword = ["pi"]
            self.no_image_message = "请先发送图像。"
            self.no_query_message = "请描述您想了解的内容。"
            self.recognition_failed_message = "图像识别失败。"
            self.api_url = ""

    def on_handle_context(self, e_context):
        context = e_context['context']
        reply = Reply()
        receiver = context.get('receiver')  # 用于唯一标识用户或会话

        if not receiver:
            logger.error("Receiver ID is missing")
            return

        if context.type == ContextType.IMAGE:
            image_path = context.content
            if not image_path:
                logger.error("Image path is empty")
                reply.type = ReplyType.ERROR
                reply.content = self.no_image_message
            else:
                # 存储或更新图像路径
                self.image_data[receiver] = {'image_path': image_path}
                reply.type = ReplyType.TEXT
                reply.content = "图像已接收，请描述您想了解的内容。"
        elif context.type == ContextType.TEXT:
            query = context.content.strip()
            if any(keyword in query for keyword in self.recognition_keyword):
                if receiver in self.image_data:
                    # 获取存储的图像路径
                    image_path = self.image_data[receiver].get('image_path')
                    if image_path:
                        # 调用图像识别方法
                        recognition_result = self.recognize_image(image_path, query)
                        reply.type = ReplyType.TEXT
                        reply.content = recognition_result
                    else:
                        reply.type = ReplyType.ERROR
                        reply.content = self.no_image_message
                else:
                    reply.type = ReplyType.INFO
                    reply.content = "请先发送图像进行识别。"
            else:
                logger.info("文本中不包含触发词，跳过处理")
                return  # 跳过处理
        else:
            logger.info("非图像或文本数据，跳过处理")
            return

        e_context['reply'] = reply
        e_context.action = EventAction.BREAK_PASS

    def recognize_image(self, image_path, query):
        """
        调用外部API
        """
        if self.api_url:
            try:
                with open(image_path, 'rb') as image_file:
                    files = {'file': image_file}
                    data = {'query': query}  # 将查询添加到请求中
                    headers = {'Authorization': f'Bearer {self.api_key}'}
                    response = requests.post(self.api_url, files=files, headers=headers, data=data)

                    if response.status_code == 200:
                        data = response.json()
                        return data.get('text', '未识别到任何文本')
                    else:
                        return f"识别失败，错误代码：{response.status_code}"
            except Exception as e:
                logger.error(f"[ImageRecognition]图像识别过程中出现错误: {e}")
                return "图像识别过程中出现错误。"
        else:
            return "API URL或API密钥未设置。"

    def get_help_text(self, **kwargs):
        help_text = f"请先发送图像，然后描述您想了解的问题。"
        return help_text
