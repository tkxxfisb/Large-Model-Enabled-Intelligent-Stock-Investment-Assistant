import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

# from data.mock_data import MockData
from data.web_data import StockDataFetcher
from utils.logger import Logger

class StockAPI:
    def __init__(self):
        self.logger = Logger("StockAPI")
        self.logger.info("股票API初始化完成")
        self.mock_data = StockDataFetcher()

    def get_macro_indicators(self):
        """获取宏观经济指标"""
        return self.mock_data.get_macro_indicators()
    
    def get_stock_basic_info(self, stock_name: str) -> dict:
        """获取股票基本信息"""
        return self.mock_data.get_stock_basic_info_by_code(stock_name)

    def get_stock_real_time_info_by_code(self, stock_code: str) -> dict:
        """通过代码获取股票信息"""
        return self.mock_data.get_stock_real_time_info_by_code(stock_code)

    def get_stock_history(self, stock_code: str, days: int = 30) -> list:
        """获取股票历史数据"""
        return self.mock_data.get_stock_history(stock_code, days)

    def get_market_overview(self) -> dict:
        """获取市场概览"""
        return self.mock_data.get_market_overview()

    def get_stocks_by_industry(self, industry: str) -> list:
        """获取特定行业的股票"""
        return self.mock_data.get_company_by_industry(industry)
    
    def get_industry_valuation(self,industry):
        """获取行业估值指标"""
        return self.mock_data.get_industry_valuation(industry)

    def get_market_valuation(self) -> dict:
        """获取市场估值数据（示例数据）"""
        return {
            "pe_ratio": 15.2,
            "pb_ratio": 2.1,
            "dividend_yield": 2.5,
            
        }

    def get_supply_chain_index(self) -> dict:
        """获取供应链景气指数（随机生成数据）"""
        import random  # 引入随机数模块
        
        # 定义各指标的随机数生成函数（保留1位小数）
        def rand_core_components():
            return round(random.uniform(100, 120), 1)  # 核心组件：100-120
        
        def rand_semiconductors():
            return round(random.uniform(105, 130), 1)  # 半导体：105-130
        
        def rand_new_energy():
            return round(random.uniform(110, 130), 1)  # 新能源：110-130

        return {
            "core_components": rand_core_components(),
            "semiconductors": rand_semiconductors(),
            "new_energy": rand_new_energy()
        }

    def get_industry_rotation(self) -> list:
        """获取行业轮动数据（补充pe/pb字段）"""
        import random  # 引入随机数模块
        
        # 定义随机数生成范围（根据金融数据常见范围设定）
        def rand_stability():
            return round(random.uniform(0.6, 1.0), 2)  # 稳定性：0.6-1.0，保留2位小数
        
        def rand_growth():
            return round(random.uniform(0.5, 1.0), 2)  # 增长潜力：0.5-1.0，保留2位小数
        
        def rand_pe():
            return round(random.uniform(10, 40), 1)  # PE：10-40，保留1位小数
        
        def rand_pb():
            return round(random.uniform(1, 5), 1)  # PB：1-5，保留1位小数

        return [
            {"industry": "科技", "stability": rand_stability(), "growth_potential": rand_growth(), "pe": rand_pe(), "pb": rand_pb()},
            {"industry": "新能源", "stability": rand_stability(), "growth_potential": rand_growth(), "pe": rand_pe(), "pb": rand_pb()},
            {"industry": "房地产", "stability": rand_stability(), "growth_potential": rand_growth(), "pe": rand_pe(), "pb": rand_pb()},
            {"industry": "汽车", "stability": rand_stability(), "growth_potential": rand_growth(), "pe": rand_pe(), "pb": rand_pb()},
            {"industry": "金融", "stability": rand_stability(), "growth_potential": rand_growth(), "pe": rand_pe(), "pb": rand_pb()},
            {"industry": "消费", "stability": rand_stability(), "growth_potential": rand_growth(), "pe": rand_pe(), "pb": rand_pb()},
            {"industry": "有色金属", "stability": rand_stability(), "growth_potential": rand_growth(), "pe": rand_pe(), "pb": rand_pb()}
        ]