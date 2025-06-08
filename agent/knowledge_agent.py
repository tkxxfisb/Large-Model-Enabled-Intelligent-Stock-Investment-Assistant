import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from knowledge_graph.kg_query import KnowledgeGraphQuery
from utils.logger import Logger

from dotenv import load_dotenv
import json

# 在文件开头添加环境变量加载
load_dotenv()

class Knowledge_Graph_Agent:
    def __init__(self):
        self.logger = Logger("KnowledgeAgent")
        self.kg_query = KnowledgeGraphQuery()
        self.logger.info("知识图谱代理初始化完成")

    def answer_question(self, question: str) -> dict:
        """精简后的问答代理"""
        try:
            result = self.kg_query.unified_query(question)
            return self.format_response(result)
        except Exception as e:
            return self.handle_error(e)

    def handle_error(self, e: Exception) -> dict:
        self.logger.error(e)
        return {
            'success':False,
            'message':f'查询失败：{str(e)}'
        }

    def format_response(self, result: dict) -> dict:
        """统一格式化查询结果"""
        if result['status'] == 'success':
            if 'supply_chain_info' == result['message_type']:
                # 修正：提取 supply_chain 对应的列表数据
                supply_chain_answer = self.format_supply_chain(result['data'])
                # self.logger.info(f"供应链查询格式化结果: {supply_chain_answer}")
                return supply_chain_answer
            elif 'industry_info' == result['message_type']:
                industry = result.get('metadata', {}).get('industry', '未知行业')
                return self.format_industry_info(result['data'], industry)
            else:
                return self.format_stock_info(result['data'])  # 统一返回格式化后的结果，无需区分 supply_chain_info 或 industry_info
                     
        else:
            return {
                'success':False,
                'message':f"查询失败：{result['message']}\n错误类型：{result['error_type']}"
            }

    def format_supply_chain(self, data: list) -> dict:
        """格式化供应链查询结果"""
        if not data:
            return {
                'success': False,
                'message': "供应链关系查询失败，未找到相关数据"
            }
        
        output = ["供应链关系分析："]
        for item in data:  # 直接遍历查询结果
            # 修改：同时显示公司名称和代码（假设 item 包含 name 字段）
            output.append(f"<br>• 公司 {item['company_name']} ({item['company_code']}) 是 {item['parter_name']}({item['partner_code']}) 的 {item['relation']}")
        
        output.append("<br>数据来源：<mcfile name='kg_importer.py' path='knowledge_graph/kg_importer.py'></mcfile>")
        ans = "<br>".join(output)
        self.logger.info(f"供应链查询格式化结果: {ans}")
    
        return {
            'success': True,
            'message': ans,  # 返回格式化后的结果
        }

    def format_industry_info(self, data: list, industry: str) -> dict:
        """格式化行业信息查询结果（修复参数结构）"""
        if not data:
            return {'success': False, 'message': f"{industry}行业暂无上市公司数据"}
            
        output = [f"{industry}行业主要上市公司："]
        for company in data:
            output.append(f"• {company['name']} ({company['code']})<br>")
        
        output.append("<br>数据来源：<mcfile name='kg_importer.py' path='knowledge_graph/kg_importer.py'></mcfile>")
        ans = "<br>".join(output)
        return {
           'success': True,
           'message': ans,  # 返回格式化后的结果
        }
    def format_stock_info(self, result:dict) -> dict:
        if not result:
            return {'success': False,'message': f"未找到相关股票数据"}
        self.logger.info(f'result:{result}')
        # ans = f"股票基本信息：\n{json.dumps(result, indent=2, ensure_ascii=False)}\n,来源：{json.dumps(data['basic_info']['source'])}"
        basic_info = result.get('basic_info', {})
        real_time_info =result.get('realtime_data',{})
        ans ="股票基本信息与实时数据：<br>"
        ans += f"股票名：{basic_info.get('name', "")}<br>" \
            f"股票代码：{basic_info.get('stock_code',"")}<br>" \
            f"所属行业：{basic_info.get('industry_primary',"")}<br>" \
            f"二级行业：{basic_info.get('industry_secondary',"")}<br>" \
            f"上市时间：{basic_info.get('listing_time',"")}<br>" \
            f"成交量：{real_time_info.get('volume',"")}<br>" \
            f"成交额：{real_time_info.get('turnover',"")}<br>" \
            f"最高价：{real_time_info.get('high',"")}<br>" \
            f"当前价格：{real_time_info.get('price',"")}<br>" \
            f"最低价：{real_time_info.get('low',"")}<br>" 
        self.logger.info(f"股票基本信息格式化结果: {ans}")  # 打印格式化结果，方便调试和理解
        return {
            'success': True,
            'message': ans,  # 返回格式化后的结果
        }

if __name__ == '__main__':
    kg= Knowledge_Graph_Agent()
    # question = "请问AAPL的最新股价是多少？"
    question = "我想查询贵州茅台的基本信息?"
    answer = kg.answer_question(question)
    print(answer)

    # question = "我想查询贵州茅台的供应链有哪些?"
    # answer = kg.answer_question(question)
    # print(answer)

    # question = "我想查询比亚迪的基本信息？"
    # answer = kg.answer_question(question)
    # print(answer)
    
    # question = "我想查询比亚迪的供应链有哪些？"
    # answer = kg.answer_question(question)
    # print(answer)

    # question = "我想查询房地产行业有哪些？"
    # answer = kg.answer_question(question)
    # print(answer)

    # question = "我想查询科技行业有哪些？"
    # answer = kg.answer_question(question)
    # print(answer)

    # question = "我想查询宁德时代的供应链有哪些？"
    # answer = kg.answer_question(question)
    # print(answer)
