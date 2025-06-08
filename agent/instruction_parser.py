import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))


from langchain_openai.chat_models import ChatOpenAI
from langchain.schema import HumanMessage
from utils.logger import Logger
import os

api_key = os.getenv("DEEPSEEK_API_KEY")
api_base_url = "https://api.deepseek.com/v1"
model_name = "deepseek-chat"


class InstructionParser:
    def __init__(self, api_key=api_key, model_name=model_name, temperature=0, streaming=True):
        self.logger = Logger("instruction_parser")
        self.logger.info("InstructionParser初始化完成")
        self.chatmodel = ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            openai_api_base=api_base_url,
            temperature=temperature,
            streaming=streaming
        )

    def parse_instruction_type(self, instruction: str) -> str:
        """解析指令类型"""
        prompt = f"你是个指令分析大师，请严格从以下选项中判断这条指令的类型：交易指令、咨询指令、策略指令、未知指令。指令内容为：{instruction}"
        messages = [HumanMessage(content=prompt)]
        try:
            # 使用 invoke 方法代替 __call__
            response = self.chatmodel.invoke(messages)
            self.logger.info(f"Response: {response}")
            
            # 检查 response 是否有 content 属性，并提取内容
            if hasattr(response, 'content'):
                # 假设 content 是一个字符串，直接提取
                content_str = str(response.content)
                # 提取 "这条指令的类型是：**交易指令**" 中的 "交易指令"
                start_index = content_str.find("：**") + 3
                end_index = content_str.find("**", start_index)
                if start_index != -1 and end_index != -1:
                    instruction_type = content_str[start_index:end_index]
                else:
                    instruction_type = "未知指令"
            else:
                self.logger.error("Response 对象没有 content 属性")
                return "未知指令"
            
            valid_types = ["交易指令", "咨询指令", "策略指令", "未知指令"]
            if instruction_type not in valid_types:
                instruction_type = "未知指令"
            return instruction_type
        except Exception as e:
            self.logger.error(f"调用大模型时出错: {e}", exc_info=True)
            return "未知指令"


if __name__ == "__main__":
    parser = InstructionParser(api_key)
    instruction = "买入100股股票"
    # 示例用户指令
    user_commands = [
        "买入100股平安银行",
        "查询贵州茅台的基本信息",
        "生成一个稳健型投资策略"
    ]
    for command in user_commands:
        response = parser.parse_instruction_type(command)
        print(f"\n用户指令: {command}")
        print(f"系统回复: {response}")
    # instruction_type = parser.parse_instruction_type(instruction)
    # print(f"指令类型: {instruction_type}")