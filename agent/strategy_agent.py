import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from api.stock_api import StockAPI
from utils.logger import Logger
import random
from openai import OpenAI
import os
import json
from knowledge_graph.kg_query import KnowledgeGraphQuery  # 新增知识图谱查询导入
from knowledge_graph.kg_importer import KGImporter  # 新增知识图谱导入器导入
import traceback  # 新增错误追踪模块
api_key = os.getenv("DEEPSEEK_API_KEY")
api_base_url = "https://api.deepseek.com/v1"
model_name = "deepseek-chat"


class StrategyAgent:
    def __init__(self):
        self.logger = Logger("strategy_agent")
        self.logger.info("策略代理初始化完成")
        self.stock_api = StockAPI()
        self.chat_model = OpenAI(api_key=api_key, base_url=api_base_url)
        self.kg_import = KGImporter()
    

    def generate_strategy(self, instruction: str) -> dict:  # 返回类型改为字典
        """策略生成主流程
        参数处理流程：
        1. 解析自然语言指令 -> parse_strategy_type()
        2. 验证策略有效性 -> kg_query.unified_query()
        3. 获取市场数据 -> get_enhanced_market_data()
        4. 行业选择 -> select_industries()
        5. 股票推荐 -> get_supply_chain_stocks()
        6. 生成提示词 -> build_strategy_prompt()
        7. 调用AI生成报告 -> generate_final_strategy()
        """
        try:
            # 新增知识图谱查询实例
            kg_query = KnowledgeGraphQuery()
            self.logger.info(f"收到策略指令: {instruction}")
            # 解析策略类型时加入知识图谱验证
            strategy_type = self.parse_strategy_type(instruction)
            self.logger.info(f"解析出的策略类型: {strategy_type}")
            
            # 改为本地固定类型验证（避免递归调用）
            valid_strategy_types = {"稳健型", "激进型", "平衡型"}
            if strategy_type not in valid_strategy_types:
                raise ValueError(f"策略类型'{strategy_type}'无效，标准类型为：{', '.join(valid_strategy_types)}")
            
            # 获取增强版市场数据
            market_data = self.get_enhanced_market_data()
            # self.logger.info(f"获取的市场数据: {market_data}")
            # 行业选择算法优化
            # 参数使用示例（第28行）：
            industries = self.select_industries(
                strategy_type,  # 来自指令解析
                market_data     # 来自API接口
            )
            self.logger.info(f"选择的行业: {industries}")
            
            # 供应链参数处理（第34行）：
            recommended_stocks = self.get_supply_chain_stocks(
                industries,    # 上一步选择的行业
                kg_query       # 知识图谱查询实例
            )
            self.logger.info(f"推荐的股票: {recommended_stocks}")
            
            # 生成策略提示词优化
            prompt = self.build_strategy_prompt(market_data, strategy_type, industries, recommended_stocks)
            # print(f'prompt:{prompt}')
            # 关键修改：传递推荐的股票数据到生成方法
            return self.generate_final_strategy(prompt, recommended_stocks)  # 新增recommended_stocks参数
            
        except Exception as e:
            self.logger.error(f"策略生成失败: {str(e)}")
            return self.handle_strategy_error(e)  # 直接返回错误字典

    def get_supply_chain_stocks(self, industries: list, kg_query: KnowledgeGraphQuery) -> list:
        """基于供应链的核心企业推荐（最终优化：降低动态阈值）"""
        core_companies = []
        for industry in industries:
            
            # 检查是否存在特定行业的公司数量
            self.logger.info(f"开始查询行业 '{industry}' 的信息")
            if not kg_query.query_industry_info(industry):
                self.logger.warning(f"未找到行业 '{industry}' 的信息，或者生成数据失败！！！！")
                continue
            self.logger.info(f"查询特定行业'{industry}'完成")
            
            cypher = f"MATCH (c:Company) WHERE c.industry_primary='{industry}' RETURN c ORDER BY c.market_cap DESC LIMIT 5"
            leaders = kg_query.graph.run(cypher).data()
            self.logger.info(f"获取行业龙头: {leaders}")
            
            # 计算行业内企业的平均供应链关系数（关键优化）
            supply_counts = []
            for company in leaders:
                company_node = company['c']
                supply_chain = kg_query.query_supply_chain(company_node['code'])
                supply_counts.append(len(supply_chain))
            avg_supply = sum(supply_counts) / len(supply_counts) if supply_counts else 0
            threshold = max(2, int(avg_supply * 1.0))  # 调整倍数为1.0（原1.2），最低阈值2（原3）
            self.logger.info(f"行业'{industry}'的平均供应链关系数: {avg_supply}, 动态阈值: {threshold}")  # 保留调试日志
            
            # 筛选供应链关系丰富的企业
            for company in leaders:
                company_node = company['c']
                supply_chain = kg_query.query_supply_chain(company_node['code'])
                if len(supply_chain) > threshold:  # 使用降低后的阈值
                    core_companies.append({
                        'code': company_node['code'],
                        'name': company_node['name'],
                        'supply_relations': len(supply_chain),
                        'threshold': threshold  # 记录当前阈值（便于调试）
                    })
        return core_companies[:6]  # 返回前6家核心企业

    def get_enhanced_market_data(self) -> dict:
        """获取增强版市场数据（包含详细估值指标）"""
        valuation = self.stock_api.get_market_valuation()
        return {
            "valuation": {
                "pe": valuation.get('pe_ratio'),  
                "pb": valuation.get('pb_ratio'), 
                "dividend_yield": valuation.get('dividend_yield')
            },
            "supply_chain_index": self.stock_api.get_supply_chain_index(),
            "industry_rotation": self.stock_api.get_industry_rotation()
        }

    def select_industries(self, strategy_type: str, market_data: dict) -> list:
        """优化后的行业选择算法（返回行业名称列表）"""
        # 获取市场估值指标
        pe_ratio = market_data['valuation']['pe']
        pb_ratio = market_data['valuation']['pb']
        
        # 动态调整权重系数并排序（返回行业名称列表）
        sorted_industries = []
        if strategy_type == "稳健型":
            sorted_list = sorted(market_data['industry_rotation'],
                        key=lambda x: (x['stability'] * 0.6 + 
                                      (1 - abs(x['pe'] - pe_ratio)) * 0.2 +
                                      (1 - abs(x['pb'] - pb_ratio)) * 0.2),
                        reverse=True)[:3]
        elif strategy_type == "激进型":
            sorted_list = sorted(market_data['industry_rotation'],
                        key=lambda x: (x['growth_potential'] * 0.7 +
                                      (x['pe'] / pe_ratio) * 0.3),
                        reverse=True)[:3]
        else:  # 平衡型
            sorted_list = sorted(market_data['industry_rotation'],
                        key=lambda x: (x['stability'] * 0.4 + 
                                      x['growth_potential'] * 0.4 +
                                      (1 - abs(x['pb'] - pb_ratio)) * 0.2),
                        reverse=True)[:3]
        
        # 提取行业名称（关键修复：从字典中提取industry字段）
        return [item['industry'] for item in sorted_list]

    def build_strategy_prompt(self, market_data: dict, strategy_type: str, 
                            industries: list, stocks: list) -> str:
        """构建策略提示词（新增供应链要素）"""
        prompt = f"""当前市场估值水平：{market_data['valuation']}，供应链景气指数：{market_data['supply_chain_index']}，
        策略类型：{strategy_type}，优选行业：{'、'.join(industries)}，核心供应链企业："""
        for stock in stocks:
            prompt += f"\n- {stock['name']}({stock['code']}) 供应链关系数：{stock['supply_relations']}"
        prompt += """\n请基于以上要素生成包含以下内容的投资策略：
        1. 行业配置逻辑（结合供应链稳定性）
        2. 个股选择依据（供应链核心地位）
        3. 风险控制措施（供应链断裂风险）"""
        return self.clean_prompt(prompt)

    def generate_final_strategy(self, prompt: str, recommended_stocks: list) -> dict:  # 新增recommended_stocks参数
        """生成结构化策略数据（包含推荐股票信息）"""
        try:
            response = self.chat_model.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    # 关键修改：系统提示要求返回推荐股票字段
                    {"role": "system", "content": """你是一位精通供应链分析的首席投资顾问，请返回严格符合以下格式的JSON数据（无额外文本）：
                    {"title": "策略标题", "description": "策略描述", "annualReturn": "预期年化收益率（百分比）", "riskLevel": "低/中/高", "recommendedStocks": [{"name": "股票名称", "code": "股票代码"}]}
                    示例（仅供格式参考）：{"title": "稳健型新能源投资策略", "description": "聚焦新能源行业核心供应链企业...", "annualReturn": "8%", "riskLevel": "低", "recommendedStocks": [{"name": "宁德时代", "code": "300750"}]}"""},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            response_content = response.choices[0].message.content
            # 清理Markdown标记和换行符
            response_content = (
                response_content
                .replace("```json", "")
                .replace("```", "")
                .replace("\n", " ")
                .strip()
            )
            self.logger.info(f"AI模型返回内容: {response_content}")
            
            # 解析JSON并补充推荐股票信息（若AI未自动生成则手动添加）
            strategy_data = json.loads(response_content)
            # 确保返回数据包含recommendedStocks字段（兼容AI未生成的情况）
            strategy_data.setdefault("recommendedStocks", [
                {"name": stock["name"], "code": stock["code"]} 
                for stock in recommended_stocks
            ])
            return strategy_data  # 第187行返回包含股票信息的字典
        except json.JSONDecodeError as e:
            self.logger.error(f"AI返回内容非有效JSON: {response_content}")
            return {
                "error": True,
                "message": "AI模型返回内容格式错误，请检查提示词或模型配置",
                "raw_response": response_content  # 返回原始内容辅助调试
            }

    def handle_strategy_error(self, e: Exception) -> dict:
        """增强型策略错误处理（返回结构化错误信息）"""
        error_msg = f"策略生成失败：{str(e)}"
        self.logger.error(f"详细错误追踪：\n{traceback.format_exc()}")
        return {
            "error": True,  # 标记错误状态
            "message": error_msg,
            "suggestions": [
                "检查输入是否符合格式要求（示例：生成稳健型新能源行业投资策略，资金规模500万元，风险等级低，投资期限3年）",
                "确认网络连接正常（确保能访问AI模型和知识图谱服务）",
                "联系技术支持并提供日志文件（路径：查看程序运行日志输出）"
            ]
        }

    def parse_strategy_type(self, instruction: str) -> str:
        """自然语言解析投资策略类型（改为规则匹配）"""
        strategy_mapping = {
            "稳健型": ["稳健", "保守", "低风险", "稳定收益"],
            "激进型": ["激进", "高风险", "进取", "超额收益"],
            "平衡型": ["平衡", "适度风险", "收益与稳定兼顾"]
        }
        
        # 优先精确匹配完整类型名称
        for strategy_type in strategy_mapping.keys():
            if strategy_type in instruction:
                return strategy_type
        
        # 模糊匹配关键词
        for strategy_type, keywords in strategy_mapping.items():
            for keyword in keywords:
                if keyword in instruction:
                    return strategy_type
        
        raise ValueError("无法识别投资策略类型，请明确说明投资偏好（稳健型/激进型/平衡型）")
        

    def clean_prompt(self, prompt: str) -> str:
        """提示词净化处理"""
        # 移除多余空白字符并标准化换行
        cleaned = '\n'.join([line.strip() for line in prompt.split('\n')])
        # 去除连续空行
        cleaned = '\n'.join([line for line in cleaned.split('\n') if line.strip()])
        # 限制最大长度（保留核心要素）
        return cleaned[:2000]  # 根据模型上下文窗口设置合理阈值



if __name__ =="__main__":
    sa = StrategyAgent()
    # instructions=["我想投资于新能源行业，关注长期稳定收益","我希望获得较高的收益，但同时也需要承担一定的风险","我想要一个平衡的投资组合，既有稳定收益也有增长潜力"]
    # for instruction in instructions:
    #     result = sa.parse_strategy_type(instruction)
    #     print(result)
    sa.generate_strategy("生成稳健型新能源行业投资策略，资金规模500万元，风险等级低，投资期限3年")
