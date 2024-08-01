# encoding:utf-8

import plugins
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from plugins import *
import json
import requests

@plugins.register(
    name="StoryCreationPlugin",
    desire_priority=400,
    desc="根据用户的主题创建故事，并通过迭代反馈进行完善。",
    version="1.0",
    author="YourName",
)
class StoryCreationPlugin(Plugin):
    def __init__(self):
        super().__init__()

        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context

        # 初始化配置
        curdir = os.path.dirname(__file__)
        config_path = os.path.join(curdir, "config.json")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                logger.info(f"[StoryCreation] 配置文件加载成功: {config}")

                self.api_url = config.get("api_url")
                self.no_text_message = config.get("no_text_message")
                self.story_generation_failed_message = config.get("story_generation_failed_message")
                self.storylines = {}  # 存储用户的故事线和大纲
                self.current_step = {}  # 存储用户的当前步骤
                self.trigger_word = config.get("trigger_word")  # 默认触发词为"生成故事"

                logger.info("[StoryCreation] 配置初始化完成")
        except Exception as e:
            logger.error(f"[StoryCreation] 初始化错误: {e}")
            self.api_url = "后端端点"
            self.no_text_message = "请提供一个故事主题。"
            self.story_generation_failed_message = "故事生成失败。"
            self.storylines = {}
            self.current_step = {}
            self.trigger_word = "生成故事"

    def on_handle_context(self, e_context):
        context = e_context['context']
        receiver = context.get('receiver', None)
        reply = Reply()

        if receiver is None:
            logger.error("在上下文中找不到接收者。")
            reply.type = ReplyType.ERROR
            reply.content = "无法识别用户身份，请重试。"
            self.send_reply(e_context, reply)
            return

        if context.type == ContextType.TEXT:
            text = context.content.strip()
            if not text:
                reply.type = ReplyType.ERROR
                reply.content = self.no_text_message
                self.send_reply(e_context, reply)
                return

            if text == "退出":
                self.end_story_creation(receiver, reply)
            elif receiver in self.storylines or self.trigger_word in text:
                self.handle_story_creation(receiver, text, reply)
            else:
                logger.info("文本中不包含触发词或不在故事创建过程中，跳过处理")
                return
        else:
            logger.info("非文本数据，跳过处理")
            return

        self.send_reply(e_context, reply)

    def send_reply(self, e_context, reply):
        e_context['reply'] = reply
        e_context.action = EventAction.BREAK_PASS

    def handle_story_creation(self, receiver, text, reply):
        if receiver in self.storylines:
            self.process_existing_story(receiver, text, reply)
        else:
            self.initiate_story_creation(receiver, text.replace(self.trigger_word, '').strip(), reply)

    def initiate_story_creation(self, receiver, theme, reply):
        if not theme:
            reply.type = ReplyType.ERROR
            reply.content = "请输入(生成故事 故事的主题)。中途想退出，输入:退出"
            return

        story_outline = self.generate_story_outline(theme)
        self.storylines[receiver] = {'theme': theme, 'outline': story_outline, 'storyline': '', 'story': ''}
        self.current_step[receiver] = 'outline'
        reply.type = ReplyType.TEXT
        reply.content = f"这是根据主题生成的故事大纲:\n{story_outline}\n---------------\n你是否满意这个大纲？如果满意，我们可以开始创作故事线。不满意就重新创作或者输入（修改 修改的内容）"

    def process_existing_story(self, receiver, text, reply):
        current_step = self.current_step[receiver]

        if current_step == 'outline':
            if text.startswith("修改 "):
                modified_text = self.storylines[receiver]['outline'] + " " + text.replace("修改 ", "")
                self.storylines[receiver]['outline'] = modified_text
                story_outline = self.generate_story_outline(modified_text)
                self.storylines[receiver]['outline'] = story_outline
                reply.type = ReplyType.TEXT
                reply.content = f"这是修改后的故事大纲:\n{story_outline}\n---------------\n你是否满意这个大纲？如果满意，我们可以开始创作故事线。不满意就重新创作或者输入（修改 修改的内容）"
            elif '不满意' in text:
                story_outline = self.generate_story_outline(self.storylines[receiver]['theme'])
                self.storylines[receiver]['outline'] = story_outline
                reply.type = ReplyType.TEXT
                reply.content = f"这是重新生成的故事大纲:\n{story_outline}\n---------------\n你是否满意这个大纲？如果满意，我们可以开始创作故事线。不满意就重新创作或者输入（修改 修改的内容）"
            elif '满意' in text:
                self.current_step[receiver] = 'storyline'
                story_line = self.generate_storyline(self.storylines[receiver]['outline'])
                self.storylines[receiver]['storyline'] = story_line
                reply.type = ReplyType.TEXT
                reply.content = f"这是根据大纲生成的故事线:\n{story_line}\n---------------\n你是否满意这个故事线？如果满意，我们可以开始创作完整的故事内容。不满意就重新创作或者输入（修改 修改的内容）"
            else:
                reply.type = ReplyType.TEXT
                reply.content = "请明确您是否满意故事大纲。"

        elif current_step == 'storyline':
            if text.startswith("修改 "):
                modified_text = self.storylines[receiver]['storyline'] + " " + text.replace("修改 ", "")
                self.storylines[receiver]['storyline'] = modified_text
                story_line = self.generate_storyline(modified_text)
                self.storylines[receiver]['storyline'] = story_line
                reply.type = ReplyType.TEXT
                reply.content = f"这是修改后的故事线:\n{story_line}\n---------------\n你是否满意这个故事线？如果满意，我们可以开始创作完整的故事内容。不满意就重新创作或者输入（修改 修改的内容）"
            elif '不满意' in text:
                story_line = self.generate_storyline(self.storylines[receiver]['outline'])
                self.storylines[receiver]['storyline'] = story_line
                reply.type = ReplyType.TEXT
                reply.content = f"这是重新生成的故事线:\n{story_line}\n---------------\n你是否满意这个故事线？如果满意，我们可以开始创作完整的故事内容。不满意就重新创作或者输入（修改 修改的内容）"
            elif '满意' in text:
                self.current_step[receiver] = 'story'
                story_content = self.generate_story_content(self.storylines[receiver]['outline'], self.storylines[receiver]['storyline'])
                self.storylines[receiver]['story'] = story_content
                reply.type = ReplyType.TEXT
                reply.content = f"这是根据大纲和故事线生成的完整故事:\n{story_content}\n---------------\n你是否满意这个故事？不满意就重新创作或者输入（修改 修改的内容）"
            else:
                reply.type = ReplyType.TEXT
                reply.content = "请明确您是否满意故事线。"

        elif current_step == 'story':
            if text.startswith("修改 "):
                modified_text = self.storylines[receiver]['story'] + " " + text.replace("修改 ", "")
                story_content = self.generate_story_content(self.storylines[receiver]['outline'], modified_text)
                self.storylines[receiver]['story'] = story_content
                reply.type = ReplyType.TEXT
                reply.content = f"这是修改后的故事内容:\n{story_content}\n---------------\n你是否满意这个故事？不满意就重新创作或者输入（修改 修改的内容）"
            elif '不满意' in text:
                story_content = self.generate_story_content(self.storylines[receiver]['outline'], self.storylines[receiver]['storyline'])
                self.storylines[receiver]['story'] = story_content
                reply.type = ReplyType.TEXT
                reply.content = f"重新生成的故事内容如下:\n{story_content}\n---------------\n你是否满意这个故事？不满意就重新创作或者输入（修改 修改的内容）"
            elif '满意' in text:
                final_story = self.compile_final_story(receiver)
                reply.type = ReplyType.TEXT
                reply.content = f"故事创作完成！\n{final_story}，\n---------------\n 故事君告退，撒花、撒花、撒花！！！"
                del self.storylines[receiver]
                del self.current_step[receiver]
            else:
                reply.type = ReplyType.TEXT
                reply.content = "请明确您是否满意故事内容。"

    def end_story_creation(self, receiver, reply):
        if receiver in self.storylines:
            del self.storylines[receiver]
            del self.current_step[receiver]
        reply.type = ReplyType.TEXT
        reply.content = "故事创作已结束。感谢您的参与！您可以随时通过使用触发词重新开始新的故事创作。"

    def generate_story_outline(self, theme):
        """
        生成故事大纲的逻辑。
        """
        try:
            response = requests.post(f"{self.api_url}/generate_outline", json={'theme': theme})
            response.raise_for_status()
            data = response.json()
            return data.get('outline', '生成故事大纲失败。')
        except requests.RequestException as e:
            logger.error(f"生成故事大纲时出错: {e}")
            return self.story_generation_failed_message

    def generate_storyline(self, outline):
        """
        生成故事线的逻辑。
        """
        try:
            response = requests.post(f"{self.api_url}/generate_storyline", json={'outline': outline})
            response.raise_for_status()
            data = response.json()
            return data.get('storyline', '生成故事线失败。')
        except requests.RequestException as e:
            logger.error(f"生成故事线时出错: {e}")
            return "生成故事线失败。"

    def generate_story_content(self, outline, storyline):
        """
        生成故事内容的逻辑。
        """
        try:
            response = requests.post(f"{self.api_url}/generate_story", json={'outline': outline, 'storyline': storyline})
            response.raise_for_status()
            data = response.json()
            return data.get('story', '生成故事内容失败。')
        except requests.RequestException as e:
            logger.error(f"生成故事内容时出错: {e}")
            return self.story_generation_failed_message

    def compile_final_story(self, receiver):
        """
        将故事大纲、故事线和故事内容编译成完整的故事。
        """
        outline = self.storylines[receiver].get('outline', '')
        storyline = self.storylines[receiver].get('storyline', '')
        story = self.storylines[receiver].get('story', '')
        return f"完整的故事:\n---------------\n故事大纲:\n{outline}\n---------------\n故事线:\n{storyline}\n---------------\n故事内容:\n{story}"

    def get_help_text(self, **kwargs):
        help_text = "请发送一个故事主题，我们将帮助您创作一个完整的故事。"
        return help_text
