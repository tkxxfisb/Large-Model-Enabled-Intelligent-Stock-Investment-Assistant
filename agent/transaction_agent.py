import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from openai import OpenAI
from api.stock_api import StockAPI
from agent.risk_assessment import RiskAssessment
from api.transaction_api import TransactionAPI
from utils.logger import Logger
from utils.db_utils import DatabaseManager
import os
from data.web_data import StockDataFetcher

api_key = os.getenv("DEEPSEEK_API_KEY")
api_base_url = "https://api.deepseek.com/v1"
model_name = "deepseek-chat"

class TransactionAgent:
    def __init__(self):
        self.logger = Logger("TransactionAgent")
        self.logger.info("交易代理初始化完成")
        self.stock_api = StockDataFetcher()
        self.risk_assessment = RiskAssessment()
        # self.transaction_api = TransactionAPI()
        self.transaction_api = DatabaseManager()

    def process_transaction(self, instruction: str, uid:str) -> str:
        """处理交易指令"""
        result={'success':False, 'message':"操作失败: 未知错误。"}
        try:
            action, quantity, stock_code = self.parse_instruction_with_llm(instruction)
            self.logger.info(f"解析结果: 操作:{action}, 数量:{quantity}, 股票代码:{stock_code}")

            if action is None or quantity is None or stock_code is None:
                return "错误: 无法解析交易指令，请检查格式"
            if action not in ["买入", "卖出"]:
                return "错误: 仅支持买入或卖出操作"
            if quantity <= 0:
                return "错误: 数量必须大于0"

            # 获取股票代码
            stock_info = self.stock_api.get_real_time_eastmoney(stock_code)
            if not stock_info:
                return f"错误: 未找到股票 {stock_code}"
            
            current_price = stock_info["price"]
            
            # 风险评估
            risk_score = self.risk_assessment.evaluate_risk(stock_code)
            self.logger.info(f"股票 {stock_code} 风险评分: {risk_score}")
            
            if risk_score > 0.7:  # 风险阈值
                result['message']=f"股票 {stock_code} 风险过高，无法执行交易"
                return result
    
                        
            # 执行交易
            result = self.transaction_api.add_transaction(
                uid=uid, 
                action=action, 
                stock_code=stock_code, 
                quantity=quantity, 
                price=current_price
            )
            
            if result["success"]:
                result['message']=f"成功执行 {action} 交易:({stock_code}) {quantity}股，价格: {current_price}"
                self.logger.info(f"成功执行 {action} 交易:({stock_code}) {quantity}股，价格: {current_price}")
            else:
                result['message']=f"交易失败: {result['message']}"
                self.logger.error(f"交易失败: {result['message']}")
            return result 
                
        except Exception as e:
            self.logger.error(f"处理交易指令出错: {str(e)}")
            result["message"]=f"操作失败: {str(e)}"
            return result

    
    
    def parse_instruction_with_llm(self, instruction):
        """使用LLM解析交易指令"""
        client = OpenAI(api_key=api_key, base_url=api_base_url)
        system_message = "你是一个专业的交易指令解析助手，能准确从交易指令中提取操作、数量和股票代码/名称。"
        prompt = f"""请从以下交易指令中准确提取操作、数量和股票代码/名称，并按照“操作,数量,股票代码”的格式输出结果。操作只能是“买入”或“卖出”，数量必须是正整数。
        股票代码格式示例：600519.SH（沪市）或 000001.SZ（深市）
        
        如果指令中不包含有效的操作、数量或股票代码，请输出“错误: 无法解析交易指令，请检查格式”
        
        示例：
        - 输入：买入200股600519.SH
        输出：买入,200,600519.SH
        
        - 输入：我要卖出300股000001.SZ
        输出：卖出,300,000001.SZ
        
        指令：{instruction}"""
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
            stream=False
        )
        result = response.choices[0].message.content
        # print(f'result: {result}, type: {type(result)}, length: {len(result)}')
        try:
            action, quantity, stock_name = result.strip().split(",")
            return action, int(quantity), stock_name
        except Exception as e:
            print(f'result: {result}, type: {type(result)}, length: {len(result)}')
            self.logger.error(f"解析指令出错: {str(e)}")
            return None, None, None
        # print(f'action: {action}, quantity: {quantity}, stock_name: {stock_name}')
        


if __name__=="__main__":
    transaction_agent = TransactionAgent()
    # 示例交易指令
    # instruction = "买入100股腾讯"
    # instruction = "我现在想买入1000股紫金矿业"
    instruction = "我现在想卖出1000股紫金矿业"
    # instruction = "我想卖入100股紫金矿业"
    # result = transaction_agent.process_transaction(instruction)
    
    result = transaction_agent.parse_instruction_with_llm(instruction)
    print(result)
    
    result = transaction_agent.process_transaction(instruction,1)
    print(result)