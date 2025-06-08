import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from datetime import datetime  # 新增datetime导入
from py2neo import Graph
from utils.config import settings
from data.mock_data import MOCK_100
from knowledge_graph.kg_importer import KGImporter
from openai import OpenAI  # 新增OpenAI导入
from dotenv import load_dotenv
import os
import json  # 新增json模块导入
import re  # 新增正则表达式模块
from utils.logger import Logger
import traceback  # 新增错误追踪模块
from api.stock_api import StockAPI
import Levenshtein

api_key = os.getenv("DEEPSEEK_API_KEY")
api_base_url = "https://api.deepseek.com/v1"
model_name = "deepseek-chat"



class KnowledgeGraphQuery:
    def __init__(self):
        self.graph = Graph(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        self.logger = Logger("KnowledgeGraphQuery")
        self.logger.info("知识图谱查询初始化完成")  # 现在可以正常调用
        self.kg_importer = KGImporter()  # 初始化导入器
        self.stock_api = StockAPI()

        self.chat_model = OpenAI(
            api_key=api_key,
            base_url=api_base_url
        )  # 初始化OpenAI客户端
        
    def query_supply_chain(self, stock_code: str, depth: int = 2, retry: int = 2) -> list:
        """供应链查询（带联网重试机制）"""
        # stock_code = stock_code.replace("sh", "").replace("sz", "")
        try:
            for attempt in range(retry):
                result = self._query_local(stock_code, depth)
                if result:
                    self.logger.info(f"供应链查询成功（第{attempt+1}次尝试）")
                    return result
                self.kg_importer.batch_import_real_data([stock_code])
            raise ValueError(f"股票代码 {stock_code} 不存在，请检查后重试")
        except Exception as e:
            self.logger.error(f"供应链查询失败: {str(e)}")
            self.logger.error(f"详细错误追踪：\n{traceback.format_exc()}")
            return []
    
    def check_stock_existence(self, stock_code: str) -> bool:
        """验证股票在知识图谱中的存在性"""
        cypher = f"MATCH (c:Company) WHERE c.code = '{stock_code}' RETURN count(c) > 0 as exists"
        return self.graph.run(cypher).evaluate()

    def check_stock_valid(self, stock_code: str) -> str:
        """增强校验规则（A股代码规范）"""
        # 验证沪深交易所代码格式
        stock_code = stock_code.strip().lower()
        if not re.match(r"^(sh|sz)\d{6}$", stock_code, re.IGNORECASE):
            if stock_code.startswith(("002", "000", "300")):  # 新增300开头判断
                stock_code = f"sz{stock_code}"
            elif stock_code.startswith(("600", "601", "603", "688")):
                stock_code = f"sh{stock_code}"
        return stock_code
        
    def query_industry_chain(self, stock_code: str) -> dict:
        """查询完整产业链关系"""
        cypher = f"""
        MATCH (c:Company)-[r]->(n)
        WHERE c.code = '{stock_code}'
        RETURN c.code as company, 
               collect(distinct type(r)) as relations,
               collect(distinct n.code) as partners
        """
        result = self.graph.run(cypher).data()
        return result[0] if result else {
            "company": stock_code,
            "relations": [],
            "partners": []
        }
    
    def unified_query(self, question: str) -> dict:
        """统一查询入口（集成自然语言解析与业务逻辑）"""
        self.logger.info(f"收到查询请求: {question}")
        parsed = self._parse_question(question)
        self.logger.info(f"解析结果: {parsed}")
        
        if parsed['intent'] == 'supply_chain':
            return self.handle_supply_chain(parsed)
        elif parsed['intent'] == 'industry':
            return self.handle_industry(parsed)
        else:
            return self.handle_general(parsed)

    def _fuzzy_match_stock_name(self, input_name: str, alias_mapping: dict) -> str:
        """模糊匹配股票名称/别名，返回最接近的股票代码"""
        max_similarity = 0
        matched_code = ""
        
        for code, info in alias_mapping.items():
            # 检查标准名称和所有别名的相似度
            all_names = [info["name"]] + info["aliases"]
            for name in all_names:
                similarity = Levenshtein.ratio(input_name.lower(), name.lower())
                if similarity > max_similarity and similarity > 0.6:  # 阈值设为0.6（可调整）
                    max_similarity = similarity
                    matched_code = code
                    
        return matched_code

    def _parse_question(self, question: str) -> dict:
        """DeepSeek自然语言解析"""
        prompt = f"""将股票查询问题解析为JSON格式，字段包括：
        intent: 查询意图（supply_chain/industry/stock_info/strategy）  # 新增strategy意图
        stock_code: 股票代码（如存在）
        stock_name: 股票名称（如存在，用户输入中提到的股票名称或别名）  # 新增字段用于识别名称
        industry: 行业名称（如存在）
        depth: 查询层级（仅供应链需要）
        strategy_type: 策略类型（如存在"稳健型""激进型"等关键词时填写）  # 新增字段
        
        问题：{question}"""
        
        response = self.chat_model.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        parsed = json.loads(response.choices[0].message.content)
        # 若未解析到stock_code，尝试模糊匹配名称/别名
        if not parsed.get("stock_code"):
            # 从问题中提取可能的股票名称（简单示例：提取"查询"后的关键词）
            import re
            alias_mapping_path = Path(__file__).parent / "stock_alias.json"
            with open(alias_mapping_path, "r", encoding="utf-8") as f:
                alias_mapping = json.load(f)
                name_candidates = re.findall(r"查询(.*?)的", question)  # 匹配"查询XX的"中的XX
                for candidate in name_candidates:
                    matched_code = self._fuzzy_match_stock_name(candidate, alias_mapping)
                    matched_code = self.check_stock_valid(matched_code)
                    # self.logger.info(f"模糊匹配结果: {matched_code}")
                    parsed['stock_code'] = matched_code  # 直接更新解析结果
                    break
                # self.logger.info(f"stock_code: {parsed['stock_code']}")
        return parsed
        
    
    def query_industry_info_local(self, industry: str) -> list:
        """查询特定行业的公司"""
        cypher = f"""
        MATCH (c:Company)
        WHERE c.industry_primary = '{industry}'
        RETURN c.code as code, c.name as name
        LIMIT 50
        """
        return [dict(item) for item in self.graph.run(cypher)]
    
    def query_all_industries(self) -> list:
        """获取所有行业分类"""
        cypher = """
        MATCH (c:Company)
        RETURN DISTINCT c.industry_primary as industry
        ORDER BY industry
        """
        return [item['industry'] for item in self.graph.run(cypher)]

    def handle_supply_chain(self, parsed: dict) -> dict:
        """处理供应链查询请求"""
        try:
            stock_code = parsed['stock_code']
            depth = parsed.get('depth', 2)
            
            if not self.check_stock_valid(stock_code):  # 新增股票代码校验
                raise ValueError(f"无效股票代码: {stock_code}")
                
            data = self.query_supply_chain(stock_code, depth)
            if not data:
                return {
                    "status": "error",
                    "message": "handle_supply_chain empty!!!\n",
                    "error_type": "supply_chain_query_error"
                }

            return {
                "status": "success",
                "data": data,
                "message_type":"supply_chain_info",
                "metadata": {
                    "source": "<mcfile name='kg_importer.py' path='knowledge_graph/kg_importer.py'></mcfile>",
                    "query_time": datetime.now().isoformat()
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "error_type": "supply_chain_query_error"
            }

    def query_industry_info(self, industry: str, retry:int=2) -> list:
        """查询特定行业的公司"""
        try:
            for attempt in range(retry):
                result = self.query_industry_info_local(industry)
                if result:
                    self.logger.info(f"特定行业的公司查询成功（第{attempt+1}次尝试）")
                    return result
                self.kg_importer.batch_import_real_data_industry(industry)
            return []
        except Exception as e:
            self.logger.error(f"特定行业的公司查询失败: {str(e)}")
            self.logger.error(f"详细错误追踪：\n{traceback.format_exc()}")
            return []

    def handle_industry(self, parsed: dict) -> dict:
        """处理行业信息查询"""
        try:
            industry = parsed['industry']
            data = self.query_industry_info(industry)

            if not data:
                return {
                    "status": "error",
                    "message": "handle_industry empty!!!\n",
                    "error_type": "industry_query_error"
                }

            return {
                "status": "success",
                "data": data,
                "message_type": "industry_info",
                "metadata": {
                    "source": "<mcfile name='kg_importer.py' path='knowledge_graph/kg_importer.py'></mcfile>",
                    "query_time": datetime.now().isoformat(),
                    "industry": industry  # 新增：显式记录查询的行业名称
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "error_type": "industry_query_error"
            }

    def handle_general(self, parsed: dict) -> dict:
        """处理股票基本信息查询"""
        try:
            stock_code = parsed.get('stock_code', "未知股票")
            if stock_code == '未知股票':
                # 明确提示需要股票代码
                return {
                    "status": "error",
                    "message": "未检测到股票代码，请在查询中包含具体股票代码（如 'sh600519' 或 'sz000001'）",
                    "error_type": "missing_stock_code"
                }
                
            # 获取实时数据
            realtime = self.stock_api.get_stock_real_time_info_by_code(stock_code)
            if not realtime:
                return {
                    "status": "error",
                    "message": f"股票代码 {stock_code} 不存在，请检查后重试",
                    "error_type": "handle_general_stock_not_found"
                }
            self.logger.info(f"股票 {stock_code} 实时数据: {realtime}")
            # 获取公司信息
            basic = self.stock_api.get_stock_basic_info(stock_code)
            # self.logger.info(f"股票 {stock_code} 基本信息: {basic}")
            if basic["error"]:
                return {
                    "status": "error",
                    "message": f"股票代码 {stock_code} 基本信息获取失败: {basic['message']}",
                    "error_type": "handle_general_basic_info_error"
                }
            
            
            return {
                "status": "success",
                "message_type": "stock_info",
                "data": {
                    "basic_info": basic,
                    "realtime_data": realtime
                },
                "metadata": {
                    "source": "<mcfile name='web_data.py' path='data/web_data.py'></mcfile>",
                    "query_time": datetime.now().isoformat()
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"股票信息查询失败: {str(e)}",
                "error_type": "stock_info_error"
            }

    def _query_local(self, stock_code: str, depth: int) -> list:
        """本地知识图谱供应链查询（增加name字段）"""
        
        cypher = f"""
        MATCH (c:Company)-[r:SUPPLY_CHAIN*1..{depth}]->(partner:Company)
        WHERE c.code = '{stock_code}'
        RETURN c.code as company_code, 
               c.name as company_name,  // 新增公司名称
               partner.code as partner_code,
               partner.name as parter_name,  // 新增合作伙伴名称
               r[-1].relationType as relation
        LIMIT 50
        """
        result = self.graph.run(cypher).data()
        return [dict(item) for item in result] if result else []



    
    
    
    

    