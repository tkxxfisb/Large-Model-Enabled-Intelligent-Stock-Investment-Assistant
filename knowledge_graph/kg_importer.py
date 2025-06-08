import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from py2neo import Graph, Node, Relationship  # 添加Node和Relationship导入
from utils.config import settings
from data.mock_data import MOCK_100
from utils.logger import Logger
from data.web_data import StockDataFetcher
import random

class KGImporter:
    def __init__(self):
        self.fetcher = StockDataFetcher()
        self.logger = Logger("KGImporter")
        self.logger.info("KGImporter初始化完成")  # 现在可以正常调用
        self.graph = Graph(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        self._create_indexes()
    
    def clear_database(self):
        """清除图数据库所有数据"""
        self.graph.run("MATCH (n) DETACH DELETE n")
        self.logger.warning("图数据库所有数据已清空")
    
    def batch_import_mock(self,nums:int = 100):
        """批量导入模拟数据到图数据库"""
        try:
            tx = self.graph.begin()
        
            # 修正变量名引用错误
            for stock_code, data in self.fetcher.generate_processed_stock_data(nums=nums).items():  # 删除多余的mock_data前缀
                # 创建公司节点（新增market_cap）
                company = Node("Company", 
                              code=stock_code,
                              name=data['name'],
                              industry_primary=data['industry']['primary'],
                              industry_secondary=data['industry']['secondary'],
                              market_cap=random.uniform(100, 10000)  # 随机生成市值（单位：亿元）
                )
                tx.create(company)
                
                # 创建供应链关系（添加name字段）
                for relation in data['supply_chain']:
                    # 新增name=relation['name']，补充合作伙伴名称
                    partner = Node("Company", 
                                  code=relation['stock_code'],
                                  name=relation['name'])  # 添加name字段
                    rel = Relationship(company, 
                                      relation['relation'], 
                                      partner, 
                                      weight=relation['weight'])
                    tx.create(rel)
                    
            self.graph.commit(tx)  # 替换 tx.commit() 为 graph.commit(tx)
        except Exception as e:
            tx.rollback()
            self.logger.error(f"数据导入失败: {str(e)}")
            raise
    
    def _create_indexes(self):
        """创建图数据库索引以加速查询"""
        self.graph.run("CREATE INDEX company_code IF NOT EXISTS FOR (c:Company) ON (c.code)")
        self.graph.run("CREATE INDEX industry_type IF NOT EXISTS FOR (c:Company) ON (c.industry_primary)")
        self.logger.info("图数据库索引创建完成")  # 现在可以正常调用

    def batch_import_real_data_industry(self, industry):
        try:
            tx = self.graph.begin()  # 开始事务
            self.logger.info(f"开始导入{industry}行业股票数据")  # 打印行业名称
            data = self.fetcher.get_company_by_industry(industry)  # 获取行业股票数据
            if not data:
                self.logger.warning(f"LLM未找到{industry}行业股票数据")
                return # 无数据则退出
            for stock in data:
                company = Node("Company",
                            code=stock['stock_code'],
                            name=stock['name'],
                            industry_primary=stock['industry_primary'],
                            industry_secondary=stock['industry_secondary'],
                            listing_date=stock['listing_time'],
                            market_cap=random.uniform(100, 10000))  # 使用过滤后的realtime
                tx.create(company)
            self.logger.info(f"{industry}行业股票数据导入完成")  # 打印导入完成信息
            self.graph.commit(tx)
                
        except Exception as e:
            tx.rollback()  # 回滚事务
            self.logger.error(f"数据导入失败: {str(e)}")  # 打印错误信息
            raise

    def batch_import_real_data(self, symbols):
        """批量导入真实数据（修复name参数重复问题）"""
        try:
            tx = self.graph.begin()
            self.logger.info(f"开始导入股票数据: {symbols}")  # 打印股票symbo
            for symbol in symbols:
                # 获取实时行情、基本面和供应链数据
                realtime = self.fetcher.get_real_time_eastmoney(symbol)
                basic = self.fetcher._smart_GPT(symbol)
                if basic["error"]:
                    self.logger.warning(f"股票{symbol}基本面数据获取失败: {basic['message']}")
                    continue

                # supply_relations = self.fetcher.get_supply_chain_relations(symbol)  # 新增：获取供应链关系
                supply_relations = self.fetcher.get_supply_chain_relations_by_network(symbol)
                if not supply_relations:
                    self.logger.warning(f"股票{symbol}供应链关系获取失败")
                    continue
                # 过滤realtime中的name字段（避免重复）
                realtime_without_name = {k: v for k, v in realtime.items() if k != 'name'}
                
                # 创建公司节点（修复name重复问题）
                company = Node("Company",
                            code=symbol,
                            name=basic['name'],
                            industry_primary=basic['industry_primary'],
                            industry_secondary=basic['industry_secondary'],
                            listing_date=basic['listing_time'],
                            market_cap=realtime.get('market_cap', random.uniform(100, 10000)),
                            **realtime_without_name)  # 使用过滤后的realtime
                tx.create(company)
                
                # 新增：创建供应链关系
                for relation in supply_relations:
                    # 确保合作伙伴节点存在（若不存在则创建）
                    partner = self.graph.nodes.match("Company", code=relation['partner_code']).first()
                    if not partner:
                        # 添加 name 字段，从 relation 中获取合作伙伴名称
                        partner = Node("Company", 
                                      code=relation['partner_code'],
                                      name=relation['name'])  # 新增 name 属性
                        tx.create(partner)
                    # 创建供应链关系（类型为SUPPLY_CHAIN，包含关系类型和权重）
                    rel = Relationship(company, "SUPPLY_CHAIN", partner,
                                      relationType=relation['type'],
                                      weight=relation['weight'])
                    tx.create(rel)
            
            self.graph.commit(tx)
        except Exception as e:
            tx.rollback()
            self.logger.error(f"真实数据导入失败: {str(e)}")
            raise

if __name__ == "__main__":
    importer = KGImporter()
    importer.clear_database()  # 清除数据库
    # # importer.batch_import_real_data(["600897","601800"])  # 导入真实数据
    # importer.batch_import_mock(100)  # 导入模拟数据