# encoding:utf-8

import plugins
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from plugins import *
import json
import requests


@plugins.register(
    name="SimpleSearchPlugin",
    desire_priority=850,
    desc="发送用户查询并接收响应",
    version="1.0",
    author="PanllQ",
)
class SimpleSearchPlugin(Plugin):
    def __init__(self):
        super().__init__()

        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context

        # 加载配置文件
        config_path = "config.json"
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                logger.info(f"[SimpleSearchPlugin] 加载配置: {config}")

                # 读取配置参数
                self.search_keywords = config.get("search_keywords")
                self.api_url = config.get("api_url")
                self.no_query_message = config.get("no_query_message")
                self.no_results_message = config.get("no_results_message")

                logger.info("[PaperSearch] 配置初始化完成")
        except Exception as e:
            logger.error(f"[PaperSearch] 初始化错误: {e}")
            self.search_keywords = ["论文"]
            self.api_url = "http://localhost:5000/api/search"
            self.no_query_message = "请提供搜索关键词。"
            self.no_results_message = "未找到相关结果。"

    def on_handle_context(self, e_context: EventContext):
        if e_context['context'].type != ContextType.TEXT:
            return
        context = e_context['context']
        content = context.content.strip()

        reply = Reply()

        # 检查内容中是否包含搜索关键词
        if any(keyword in content for keyword in self.search_keywords):
            query = content
            for keyword in self.search_keywords:
                query = query.replace(keyword, "").strip()
            if query:
                # 发送查询请求
                search_result = self.send_query(query)
                reply.type = ReplyType.INFO
                reply.content = search_result
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
            else:
                reply.type = ReplyType.INFO
                reply.content = self.no_query_message
                e_context["reply"] = reply
                e_context.action = EventAction.CONTINUE
        else:
            logger.info("内容中未找到触发关键词。")

    def send_query(self, query):
        """
        调用外部API
        """
        try:
            response = requests.post(self.api_url, json={"query": query})
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    logger.info(f"[SimpleSearchPlugin] 接收到响应数据: {response_data}")

                    results = []
                    for item in response_data:
                        title = item.get('title', '无标题')
                        abstract = item.get('abstract', '无摘要')
                        pdf_url = item.get('pdf_url', '无PDF地址')
                        chinese_summary = item.get('chinese_summary', '无中文摘要')

                        result = (
                            f"标题: {title}\n------------------------\n"
                            f"介绍信息: {abstract}\n------------------------\n"
                            f"pdf地址: {pdf_url}\n------------------------\n"
                            f"大模型分析结果: {chinese_summary}\n------------------------\n"
                        )
                        results.append(result)

                    return "\n\n".join(results) if results else self.no_results_message

                except json.JSONDecodeError:
                    logger.error("[PaperSearch] 解析响应时出现JSON解码错误。")
                    return "处理响应时出现解析错误。"
            else:
                logger.error(f"[PaperSearch] 请求失败，状态码: {response.status_code}")
                return f"请求失败，错误代码：{response.status_code}"
        except requests.RequestException as e:
            logger.error(f"[PaperSearch] API请求过程中出现错误: {e}")
            return "请求过程中出现错误。"

    def get_help_text(self, **kwargs):
        help_text = f"使用命令 '{self.search_keywords[0]} <关键词>' 或 '{self.search_keywords[1]} <关键词>' 来发送查询请求。"
        return help_text
