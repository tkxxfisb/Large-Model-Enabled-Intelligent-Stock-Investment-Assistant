from agent.instruction_parser import InstructionParser
from agent.transaction_agent import TransactionAgent
from agent.knowledge_agent import Knowledge_Graph_Agent
from agent.strategy_agent import StrategyAgent
from utils.logger import Logger

class StockAssistant:
    def __init__(self):
        self.logger = Logger("StockAssistant")
        self.logger.info("股票助手初始化完成")
        self.parser = InstructionParser()
        self.transaction_agent = TransactionAgent()
        self.knowledge_agent = Knowledge_Graph_Agent()
        self.strategy_agent = StrategyAgent()

    def process_instruction(self, user_input: str) -> str:
        """处理用户指令"""
        self.logger.info(f"收到用户指令: {user_input}")
        
        # 解析指令类型
        instruction_type = self.parser.parse_instruction_type(user_input)
        self.logger.info(f"指令类型: {instruction_type}")
        
        # 根据指令类型分发处理
        if instruction_type == "交易指令":
            return self.transaction_agent.process_transaction(user_input)
        elif instruction_type == "咨询指令":
            return self.knowledge_agent.answer_question(user_input)
        elif instruction_type == "策略指令":
            return self.strategy_agent.generate_strategy(user_input)
        else:
            return "抱歉，我不理解该指令类型。请尝试重新描述您的需求。"

if __name__ == "__main__":
    assistant = StockAssistant()
    
    # 示例用户指令
    user_commands = [
        "买入100股平安银行",
        "查询贵州茅台的基本信息",
        "生成一个稳健型投资策略"
    ]
    
    for command in user_commands:
        response = assistant.process_instruction(command)
        print(f"\n用户指令: {command}")
        print(f"系统回复: {response}")