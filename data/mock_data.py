import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import random
import time
from datetime import datetime, timedelta

class MockData:
    def __init__(self):
        # 模拟股票数据
        self.stocks = [
            {"ts_code": "000001.SZ", "name": "平安银行", "industry": "金融", "market": "主板", "list_date": "19910403"},
            {"ts_code": "000002.SZ", "name": "万科A", "industry": "房地产", "market": "主板", "list_date": "19910129"},
            {"ts_code": "600000.SH", "name": "浦发银行", "industry": "金融", "market": "主板", "list_date": "19991110"},
            {"ts_code": "600519.SH", "name": "贵州茅台", "industry": "消费", "market": "主板", "list_date": "20010827"},
            {"ts_code": "002594.SZ", "name": "比亚迪", "industry": "汽车", "market": "中小板", "list_date": "20110630"},
            {"ts_code": "300750.SZ", "name": "宁德时代", "industry": "新能源", "market": "创业板", "list_date": "20180611"},
            {"ts_code": "601318.SH", "name": "中国平安", "industry": "金融", "market": "主板", "list_date": "20070301"},
            {"ts_code": "000858.SZ", "name": "五粮液", "industry": "消费", "market": "主板", "list_date": "19980427"},
            {"ts_code": "600036.SH", "name": "招商银行", "industry": "金融", "market": "主板", "list_date": "20020409"},
            {"ts_code": "601899.SH", "name": "紫金矿业", "industry": "有色金属", "market": "主板", "list_date": "20080425"}
        ]
        
        # 为每只股票生成价格范围
        self.price_ranges = {
            "000001.SZ": (10, 25),
            "000002.SZ": (15, 30),
            "600000.SH": (7, 15),
            "600519.SH": (1500, 2000),
            "002594.SZ": (200, 300),
            "300750.SZ": (300, 500),
            "601318.SH": (40, 80),
            "000858.SZ": (150, 250),
            "600036.SH": (30, 50),
            "601899.SH": (8, 15)
        }

    def get_stock_info(self, stock_name: str) -> dict:
        """获取股票基本信息"""
        for stock in self.stocks:
            if stock["name"] == stock_name:
                # 添加当前价格（随机生成）
                min_price, max_price = self.price_ranges[stock["ts_code"]]
                current_price = round(random.uniform(min_price, max_price), 2)
                
                return {
                    "ts_code": stock["ts_code"],
                    "name": stock["name"],
                    "industry": stock["industry"],
                    "market": stock["market"],
                    "list_date": stock["list_date"],
                    "current_price": current_price,
                    "market_cap": round(random.uniform(100, 10000), 2)  # 模拟市值（亿元）
                }
        return None

    def get_stock_info_by_code(self, stock_code: str) -> dict:
        """通过代码获取股票信息"""
        for stock in self.stocks:
            if stock["ts_code"] == stock_code:
                return stock
        return None

    def get_stock_history(self, stock_code: str, days: int = 30) -> list:
        """获取股票历史数据"""
        if stock_code not in self.price_ranges:
            return []
        
        # 生成最近days天的历史数据
        min_price, max_price = self.price_ranges[stock_code]
        current_price = round(random.uniform(min_price, max_price), 2)
        history = []
        
        for i in range(days, 0, -1):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
            
            # 模拟价格变化（随机但连续）
            change = round(random.uniform(-0.03, 0.03), 2)
            new_price = round(current_price * (1 + change), 2)
            
            # 确保价格在范围内
            if new_price < min_price:
                new_price = min_price
            elif new_price > max_price:
                new_price = max_price
            
            # 生成单日数据
            history.append({
                "trade_date": date,
                "open": round(new_price * random.uniform(0.99, 1.01), 2),
                "high": round(new_price * random.uniform(1.0, 1.03), 2),
                "low": round(new_price * random.uniform(0.97, 1.0), 2),
                "close": new_price,
                "pre_close": current_price,
                "change": round(new_price - current_price, 2),
                "pct_change": round((new_price - current_price) / current_price * 100, 2),
                "vol": random.randint(100000, 10000000),
                "amount": round(random.uniform(1000, 100000), 2)
            })
            
            current_price = new_price
        
        return history

    def get_market_overview(self) -> dict:
        """获取市场概览"""
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M:%S"),
            "indexes": {
                "上证指数": round(random.uniform(3200, 3400), 2),
                "深证成指": round(random.uniform(11000, 12000), 2),
                "创业板指": round(random.uniform(2200, 2500), 2),
                "沪深300": round(random.uniform(3800, 4200), 2)
            },
            "market_status": {
                "rising": random.randint(2000, 3000),
                "falling": random.randint(1000, 2000),
                "flat": random.randint(100, 300),
                "limit_up": random.randint(30, 100),
                "limit_down": random.randint(10, 50)
            },
            "industry_performance": {
                "金融": round(random.uniform(-1.5, 1.5), 2),
                "房地产": round(random.uniform(-2.0, 1.0), 2),
                "科技": round(random.uniform(-1.0, 2.5), 2),
                "消费": round(random.uniform(-1.0, 2.0), 2),
                "医药": round(random.uniform(-1.5, 1.5), 2),
                "新能源": round(random.uniform(-2.0, 2.0), 2),
                "汽车": round(random.uniform(-1.5, 2.0), 2),
                "有色金属": round(random.uniform(-2.0, 2.5), 2)
            }
        }

    def get_stocks_by_industry(self, industry: str) -> list:
        """获取特定行业的股票"""
        return [stock for stock in self.stocks if stock["industry"] == industry]
    
    def get_macro_indicators(self):
        """获取宏观经济指标"""
        return {
            "gdp_growth": round(random.uniform(2.0, 5.0), 1),
            "inflation": round(random.uniform(1.5, 3.5), 1),
            "interest_rate": round(random.uniform(1.0, 3.0), 1)
        }
    
    def get_industry_valuation(self,industry):
        """获取行业估值"""
        if industry in ["金融"]:
            pe_range = (6.0, 12.0)
            pb_range = (0.8, 1.8)
        elif industry in ["消费", "医药"]:
            pe_range = (20.0, 40.0)
            pb_range = (3.0, 6.0)
        else:  # 科技、新能源、半导体
            pe_range = (30.0, 60.0)
            pb_range = (4.0, 8.0)
        
        return {
            "pe_ratio": round(random.uniform(*pe_range), 1),
            "pb_ratio": round(random.uniform(*pb_range), 1)
        }
    
    def get_stock_names(self)-> list:
        names=[]
        for item in self.stocks:
             names.append(item["name"])
        return names

    @staticmethod
    def generate_mock_data(num=100):
        """生成包含多维特征的股票模拟数据"""
        from faker import Faker
        fake = Faker('zh_CN')
        
        mock_data = {}
        for i in range(num):
            stock_code = f"{str(fake.random_number(digits=6, fix_len=True))}.{fake.random_element(['SZ','SH'])}"
            mock_data[stock_code] = {
                "industry": {
                    "primary": fake.random_element(["新能源", "半导体", "医药", "消费"]),
                    "secondary": fake.random_element(["锂电池", "芯片制造", "创新药", "白酒"])
                },
                "supply_chain": [
                    {"relation": "供应商", "code": f"{fake.random_number(digits=6)}.SZ", "weight": fake.pyfloat(1, 4)},  # 修正为1位整数+4位小数
                    {"relation": "客户", "code": f"{fake.random_number(digits=6)}.SH", "weight": fake.pyfloat(1, 3)},
                ],
                "financials": {
                    "2023-Q3": {
                        "roe": fake.pyfloat(0, 2),  # 允许0位整数+2位小数
                        "pe_ratio": fake.pyfloat(2, 2)  # 2位整数+2位小数
                    }
                }
            }
        return mock_data

# 生成100条数据
MOCK_100 = MockData.generate_mock_data(100)
        

    
        