from data.web_data import StockDataFetcher
from utils.logger import Logger
import numpy as np
import pandas as pd

class RiskAssessment:
    def __init__(self):
        self.logger = Logger("RiskAssessment")
        self.logger.info("风险评估模块初始化完成")
        self.stock_api = StockDataFetcher()
        self.volatility_weight = 0.5
        self.market_cap_weight = 0.3
        self.price_trend_weight = 0.2

    def evaluate_risk(self, stock_code: str) -> float:
        """评估股票风险"""
        try:
            # 获取历史数据
            historical_data = self.stock_api.get_stock_history(stock_code, days=30)
            # self.logger.info(f"获取{stock_code}的历史数据: {historical_data}")
            if not historical_data:
                self.logger.warning(f"无法获取{stock_code}的历史数据")
                return 0.8  # 默认高风险
            
            # 计算波动率 (简化版)
            prices = [data["close"] for data in historical_data]
            returns = np.diff(prices) / prices[:-1]
            volatility = np.std(returns)
            
            # 获取市值信息
            # 使用web_data模块获取实时数据
            real_time_data = self.stock_api.get_real_time_eastmoney(stock_code)
            market_cap = real_time_data.get("volume", 0) * real_time_data.get("price", 0)  # 通过成交量*价格估算市值
            
            # 或使用模拟数据（如果无法获取真实数据）
            # market_cap = random.uniform(1e9, 1e12)  # 生成1亿到1000亿之间的随机市值
            
            # 计算价格趋势 (简化版)
            recent_prices = prices[-5:]  # 最近5天
            price_trend = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
            
            # 计算价格趋势（增强版）
            # 使用指数加权移动平均分析趋势
            ewma_5 = pd.Series(prices).ewm(span=5).mean().values
            ewma_20 = pd.Series(prices).ewm(span=20).mean().values
            trend_strength = (ewma_5[-1] - ewma_20[-1]) / ewma_20[-1]
            
            # 动态归一化指标
            norm_volatility = np.tanh(volatility / 0.03)  # 双曲正切函数平滑处理
            norm_market_cap = 1 / (1 + np.exp(-(np.log(market_cap) - 23)))  # 对数sigmoid转换
            norm_trend = 1 / (1 + np.exp(-10*trend_strength))  # 趋势强度概率化
            
            # 动态权重调整（根据市场波动率）
            total_volatility = np.std(prices)
            dynamic_weights = self._calculate_dynamic_weights(total_volatility)
            
            # 风险评分计算
            risk_score = (
                dynamic_weights['volatility'] * norm_volatility +
                dynamic_weights['market_cap'] * norm_market_cap +
                dynamic_weights['trend'] * norm_trend
            )
            
            return risk_score
            
        except Exception as e:
            self.logger.error(f"风险评估出错: {str(e)}")
            return 0.8  # 默认高风险

    def _calculate_dynamic_weights(self, total_volatility):
        """根据市场波动动态调整权重"""
        volatility_factor = np.tanh(total_volatility / 0.05)
        return {
            'volatility': min(self.volatility_weight * (1 + volatility_factor), 0.7),
            'market_cap': self.market_cap_weight * (1 - 0.5*volatility_factor),
            'trend': self.price_trend_weight * (1 - 0.5*volatility_factor)
        }