# encoding:utf-8

import plugins
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from channel.chat_message import ChatMessage
from common.log import logger
from plugins import *
from config import conf, global_config
import os
import json
import requests


@plugins.register(
    name="searchplugin",
    desire_priority=800,
    desc="Search for content based on user input",
    version="1.0",
    author="PanllQ",
)
class SearchPlugin(Plugin):
    def __init__(self):
        super().__init__()

        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context

        # 加载配置文件
        curdir = os.path.dirname(__file__)
        config_path = os.path.join(curdir, "config.json")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                logger.info(f"[search] 加载配置文件成功: {config}")

                # 读取配置文件中的参数
                self.search_keyword = config.get("search_keyword", ["搜索"])
                self.no_query_message = config.get("no_query_message", "请提供搜索关键词。")
                self.no_results_message = config.get("no_results_message", "未找到相关内容。")
                self.api_url = config.get("api_url", "")
                self.api_key = config.get("api_key", "")

                logger.info("[search] 初始化配置完成")
        except Exception as e:
            logger.error(f"[search] 初始化错误: {e}")
            self.search_keyword = ["搜索"]
            self.no_query_message = "请提供搜索关键词。"
            self.no_results_message = "未找到相关内容。"
            self.api_url = ""
            self.api_key = ""

    def on_handle_context(self, e_context: EventContext):
        # 仅处理文本类型的消息
        if e_context['context'].type not in [ContextType.TEXT]:
            return
        context = e_context['context']

        msg: ChatMessage = context['msg']
        content = context.content.strip()
        reply = Reply()

        # 检查消息中是否包含搜索关键词
        if any(keyword in content for keyword in self.search_keyword):
            query = content
            for keyword in self.search_keyword:
                query = query.replace(keyword, "").strip()
            if query:
                # 执行搜索操作
                search_result = self.search_content(query)
                reply.type = ReplyType.INFO
                reply.content = search_result
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
            else:
                reply.type = ReplyType.INFO
                reply.content = self.no_query_message
                e_context["reply"] = reply
                e_context.action = EventAction.CONTINUE

    def search_content(self, query):
        """
        调用外部API
        """
        # 如果API URL和API密钥已设置，进行搜索
        if self.api_url and self.api_key:
            try:
                params = {
                    'q': query,
                    'format': 'json',
                    'token': self.api_key
                }
                response = requests.get(self.api_url, params=params)
                if response.status_code == 200:
                    search_results = response.json().get('results', [])
                    if search_results:
                        # 格式化搜索结果，仅显示前3个结果
                        formatted_results = [
                            f"标题: {item['title']}\n内容: {item['content']}\n链接: {item['url']}"
                            for item in search_results[:3]
                        ]
                        return "\n\n".join(formatted_results)
                    else:
                        return self.no_results_message
                else:
                    return f"搜索失败，错误代码：{response.status_code}"
            except Exception as e:
                logger.error(f"[search] 搜索过程中出现错误: {e}")
                return "搜索过程中出现错误。"
        else:
            return "API URL或API密钥未设置。"

    def get_help_text(self, **kwargs):
        help_text = f"使用命令 '{self.search_keyword[0]} <关键词>' 来搜索内容。"
        return help_text
