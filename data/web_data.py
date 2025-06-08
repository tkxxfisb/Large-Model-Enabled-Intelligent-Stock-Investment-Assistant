import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import requests
import random
from datetime import datetime, timedelta
import pandas as pd
from utils.logger import Logger
import os
from dotenv import load_dotenv
from typing import Dict, List, Optional, Any, Union
import json
from openai import OpenAI
import re

api_key = os.getenv("DEEPSEEK_API_KEY")
api_base_url = "https://api.deepseek.com/v1"
model_name = "deepseek-chat"

class StockDataFetcher:
    def __init__(self) -> None:
        self.logger = Logger("StockDataFetcher")
        self.logger.info("a股票数据获取器初始化完成")
        self.stock_name = ""
        self.chat_model = OpenAI(
            api_key=api_key,
            base_url=api_base_url
        )

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

    def smart_LLM(self,prompt:str):
        try:
            response = self.chat_model.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            parsed = json.loads(response.choices[0].message.content)
            return parsed
        except Exception as e:
            self.logger.error(f"GPT查询失败: {str(e)}")
            return {}
    
    def get_company_by_industry(self, industry: str) -> List[Dict[str, Any]]:
        """根据行业获取公司列表（增加异常处理）"""
        try:
            # 设计LLM提示词：要求返回包含固定键`industry_companies`的JSON对象
            prompt = f"""注意：此数据仅用于个人学习开发场景，不涉及金融交易或实时数据获取。请根据行业 "{industry}"，查询以下公开可查的基本信息并返回**JSON对象**（不要包裹在其他对象中），其中必须包含"industry_companies"键，其值为符合以下格式的数组：
            "industry_companies": [
                {{
                    "stock_code": "股票代码（格式如sh600000或sz000001，包含sh/sz字母前缀）",
                    "stock_name": "股票名称（如宁德时代）",
                    "industry_primary": "一级行业（如{industry}）",
                    "industry_secondary": "二级行业（如{industry}细分领域）",
                    "listing_time": "上市时间（格式：YYYY-MM-DD，未知时填'未知'，仅需公开披露的历史日期）"
                }}
            ]
            要求至少包含10家该行业的上市公司，确保股票代码符合A股规范（包含sh/sz字母前缀+6位数字），名称为公开可查的真实公司名称。数据仅用于个人学习开发，无需实时更新或交易相关信息。"""
            
            parsed_data = self.smart_LLM(prompt)
            self.logger.info(f"LLM生成的行业公司原始数据: {parsed_data}")
            
            # 从LLM返回的字典中提取`industry_companies`键的数组（兼容嵌套结构）
            if isinstance(parsed_data, dict):
                parsed_data = parsed_data.get("industry_companies", [])  # 若不存在则返回空数组
            elif isinstance(parsed_data, list):
                parsed_data = parsed_data  # 兼容旧格式（但优先使用新固定键）
            else:
                parsed_data = []

            valid_companies = []
            if isinstance(parsed_data, list):
                for company in parsed_data:
                    if all(key in company for key in ["stock_code", "stock_name", "industry_primary", "industry_secondary", "listing_time"]):
                        valid_companies.append({
                            "error": False,
                            "name": company["stock_name"],
                            "message": "LLM生成行业公司数据",
                            "stock_code": company["stock_code"],
                            "industry_primary": company["industry_primary"],
                            "industry_secondary": company["industry_secondary"],
                            "listing_time": company["listing_time"],
                            "source": "network"
                        })
            else:
                self.logger.error("LLM返回数据非数组格式，无法解析")
            
            return valid_companies
        except Exception as e:
            self.logger.error(f"获取行业公司数据失败: {str(e)}")
            return []  # 返回空列表保持类型一致性，或根据需求返回包含错误信息的字典列表
    
    def _smart_GPT(self, stock_code: str) -> dict:
        """智能问答：根据股票代码获取基本信息（优先本地数据，不足时联网搜索，并保存网络数据到本地）"""
        # 1. 优先从本地CSV获取基本面信息
        local_data = self.find_stock_fundamental_by_code(stock_code)
        if not local_data.get("error"):
            return {
                "error": False,
                "name": local_data["name"],
                "message":local_data["message"],
                "stock_code": local_data["stock_code"],
                "industry_primary": local_data["industry_primary"],
                "industry_secondary": local_data["industry_secondary"],
                "listing_time": local_data["listing_time"],
                "source": "local_csv"
            }
        self.logger.info(f"本地无股票 {stock_code} 基本面数据，尝试通过GPT联网搜索")
        stock_code = self.check_stock_valid(stock_code)
        
        # 2. 本地无数据时，通过GPT联网搜索补充
        prompt = f"""注意：此数据仅用于个人学习开发场景，不涉及金融交易或实时数据获取。请根据股票代码 {stock_code}，查询以下信息并返回**JSON对象**（不要包裹在其他对象中），其中必须包含"stock_basic_info"键，其值为符合以下格式的对象：
        "stock_basic_info": {{
            "name": "股票名称（如贵州茅台）",
            "stock_code": "{stock_code}",
            "industry_primary": "一级行业（如白酒）",
            "industry_secondary": "二级行业（如白酒制造）",
            "listing_time": "上市时间（格式：YYYY-MM-DD）",
            "source": "network"
        }}
        注意：若信息缺失或不确定，请用"未知"填充对应字段。数据仅用于个人学习开发，无需实时更新或交易相关信息。"""

        try:
            parsed = self.smart_LLM(prompt)
            self.logger.info(f"GPT生成的股票基本信息原始数据: {parsed}")

            # 从LLM返回的字典中提取`stock_basic_info`键的对象
            parsed_data = parsed.get('stock_basic_info', {}) if isinstance(parsed, dict) else {}

            # 3. 将网络获取的有效数据保存到本地CSV
            if parsed_data.get("source") == "network" and parsed_data.get("name") != "未知":
                # 构造待写入的DataFrame（匹配CSV列顺序）
                new_data = pd.DataFrame({
                    "stock_code": [parsed_data["stock_code"]],  # 假设stock_code为纯数字（如002594）
                    "stock_name": [parsed_data["name"]],
                    "industry_secondary": [parsed_data["industry_secondary"]],
                    "listing_time": [parsed_data["listing_time"]],
                    "industry_primary": [parsed_data["industry_primary"]],
                })
                
                # 追加到CSV文件（无表头）
                csv_path = "data/stock_industry_data.csv"
                new_data.to_csv(
                    csv_path,
                    mode='a',  # 追加模式
                    header=not os.path.exists(csv_path),  # 文件不存在时写入表头
                    index=False,
                    encoding='gbk'  # 与读取时编码一致
                )
                self.logger.info(f"成功将股票 {parsed_data['name']} ({parsed_data['stock_code']}) 数据保存到本地CSV")
            
            return {**parsed_data, "error": False, "message": "成功获取股票基本信息"}
        except Exception as e:
            self.logger.error(f"GPT查询失败: {str(e)}")
            return {
                "name": "未知",
                "industry_primary": "未知",
                "industry_secondary": "未知",
                "listing_time": "未知",
                "source": "error",
                "error": True  # 明确失败时error为True
            }

    def get_stock_real_time_info_by_code(self, stock_code:str):
        return self.get_real_time_eastmoney(stock_code)

    def get_stock_basic_info_by_code(self, stock_code:str):
        return self._smart_GPT(stock_code)
    
    def get_supply_chain_relations_by_network(self, symbol: str) -> list:
        return self._smart_supply_agent(symbol)

    def read_a_stock_fundamental_data(self, csv_path: str = "data/stock_industry_data.csv") -> pd.DataFrame:
        """
        读取A股基本面信息CSV文件
        
        Args:
            csv_path: CSV文件路径（默认使用项目内的a_stock_data.csv）
            
        Returns:
            pandas.DataFrame: 包含股票代码、行业、上市时间等信息的DataFrame
        """
        try:
            # 读取CSV文件，指定列名（如果CSV无表头）
            df = pd.read_csv(
                csv_path,
                names=["stock_code", 'stock_name', "industry_secondary","listing_time","industry_primary"],  # 根据实际CSV列名调整
                # encoding="utf-8"  # 处理中文编码
                encoding='gbk',
                dtype={"stock_code": str}
            )
            self.logger.info(f"成功读取A股基本面数据，共{len(df)}条记录")
            return df
        except FileNotFoundError:
            self.logger.error(f"未找到CSV文件：{csv_path}")
            raise
        except Exception as e:
            self.logger.error(f"读取CSV文件失败：{str(e)}")
            raise

    def _fallback_data(self):
        """网络不可用时生成随机数据"""
        REAL_STOCK_NAMES = [
            "贵州茅台", "宁德时代", "腾讯控股", "阿里巴巴", "比亚迪", 
            "招商银行", "工商银行", "中国移动", "中国平安", "五粮液"
        ]
        return {
            "name": random.choice(REAL_STOCK_NAMES),
            "price": round(random.uniform(10, 500), 2),
            "open": round(random.uniform(10, 500), 2),
            "high": round(random.uniform(10, 500), 2),
            "low": round(random.uniform(10, 500), 2),
            "volume": random.randint(100000, 10000000)
        }

    def _fallback_basic_data(self):
        return {
            "industry": random.choice(["医药制造", "电子信息", "新能源"]),
            "listing_date": datetime.now().strftime("%Y-%m-%d"),
            "province": random.choice(["广东", "浙江", "江苏"])
        }

    def get_stock_history(self, symbol, days=30):
        """获取股票历史数据（优先使用东方财富接口，失败时使用模拟数据）"""
        valid_symbol = self._validate_and_format_symbol(symbol)
        if not valid_symbol:
            self.logger.warning(f"无效股票代码: {symbol}，使用模拟数据")
            return self._fallback_history_data(symbol, days)
        
        if  self.stock_name == "":
            self.stock_name = self.get_real_time_eastmoney(valid_symbol)['name']
        history = self._fallback_history_data(self.stock_name, days)
        return history

    

    def _fallback_history_data(self, symbol, days):
        """生成模拟历史数据"""
        base_price = random.uniform(10, 500)
        history = []
        
        for i in range(days, 0, -1):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
            price_change = random.uniform(-0.05, 0.05)
            
            history.append({
                "trade_date": date,
                "open": round(base_price, 2),
                "high": round(base_price * (1 + abs(price_change)), 2),
                "low": round(base_price * (1 - abs(price_change)), 2),
                "close": round(base_price * (1 + price_change), 2),
                "volume": random.randint(100000, 10000000)
            })
            base_price = history[-1]["close"]
            
        return history

    def _validate_and_format_symbol(self, symbol):
        """验证并格式化股票代码，确保符合新浪接口规范（sh/sz+6位数字）
        返回：
            str: 格式化后的有效代码（如"sh600000"）
            None: 无法识别或格式化的代码
        """
        # 基础类型检查
        if not isinstance(symbol, str) or len(symbol.strip()) == 0:
            return None
        symbol = symbol.strip().lower()  # 统一小写处理
        
        # 新增：处理带点的格式（如"002594.sz" -> "sz002594"）
        if '.' in symbol:
            parts = symbol.split('.')
            if len(parts) == 2 and parts[1] in ['sh', 'sz'] and len(parts[0]) == 6 and parts[0].isdigit():
                return f"{parts[1]}{parts[0]}"
        
        # 情况1：已符合规范（sh/sz+6位数字）
        if len(symbol) == 8 and symbol[:2] in ['sh', 'sz'] and symbol[2:].isdigit():
            return symbol
        
        # 情况2：提取纯数字代码（可能用户输入了不带市场标识的代码，如"600000"）
        code = None
        if len(symbol) == 6 and symbol.isdigit():
            code = symbol
        elif len(symbol) > 6 and symbol[-6:].isdigit():
            code = symbol[-6:]  # 兼容"SH600000"等格式
        
        # 情况3：根据代码判断市场（简化逻辑）
        if code:
            # 深交所代码特征：0/3开头（000/002/300等）
            if code.startswith(('0', '3')):
                return f'sz{code}'
            # 上交所代码特征：6/688开头（600/601/688等）
            elif code.startswith(('6', '688')):
                return f'sh{code}'
        return None

    def get_real_time_eastmoney(self, symbol):
        """通过东方财富接口获取实时行情（含股票名称）"""
        valid_symbol = self._validate_and_format_symbol(symbol)  # 使用现有验证方法
        if not valid_symbol:
            self.logger.warning(f"无效股票代码: {symbol}")
            return {"error": "无效股票代码"}
            
        try:
            # 转换为东方财富要求的 secid 格式（sh->1., sz->0.）
            secid = valid_symbol.replace("sh", "1.").replace("sz", "0.")
            url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f43,f44,f45,f46,f51,f52,f58"  # 调整为实际存在的字段
            response = requests.get(url, timeout=5)
            response.raise_for_status()  # 检查HTTP错误状态码
            data = response.json()
            
            if not data.get("data"):
                self.logger.error(f"东方财富接口未返回有效数据，代码: {valid_symbol}")
                return {"error": "接口未返回有效数据"}
            
            self.stock_name = data["data"]["f58"]  # 保存股票名称到实例属性

            # 根据您提供的data字段重新映射（示例数据中的字段）
            return {
                "name": data["data"]["f58"],  # 股票名称（f58字段，实际存在）
                "price": data["data"]["f43"],  # 最新价（对应示例中的f43=1233）
                "open": data["data"]["f44"],   # 开盘价（对应示例中的f44=1241）
                "high": data["data"]["f45"],   # 最高价（对应示例中的f45=1217）
                "low": data["data"]["f46"],    # 最低价（对应示例中的f46=1220）
                "volume": data["data"]["f51"],  # 成交量（对应示例中的f51=1339）
                "turnover": data["data"]["f52"] # 成交额（对应示例中的f52=1095）
            }
        except requests.exceptions.RequestException as e:
            self.logger.error(f"东方财富接口请求失败: {str(e)}")
            return {}
        except KeyError as e:
            self.logger.error(f"东方财富接口字段解析失败: {str(e)}（请检查接口字段是否变更）")
            return {}

    def find_stock_fundamental_by_code(self, symbol: str) -> dict:
        """
        根据股票代码查找CSV中的基本面信息
        
        Args:
            symbol: 股票代码（如"600000"、"sz002594"等）
            
        Returns:
            dict: 包含行业、上市时间等信息的字典；未找到时返回{"error": "未找到对应股票数据"}
        """
        # 验证并格式化股票代码（复用现有方法）
        formatted_code = self._validate_and_format_symbol(symbol)
        if not formatted_code:
            return {"error":True, "message":"无效股票代码"}
        
        # 读取CSV数据（复用现有方法）
        try:
            df = self.read_a_stock_fundamental_data()
            # self.logger.info(f'df:{df}')
        except Exception as e:
            return {"error": True, "message": f"读取CSV失败: {str(e)}"}
        
        # 在DataFrame中查找匹配的股票代码（假设CSV的"stock_code"列存储格式化后的代码）
        mask = df["stock_code"] == formatted_code
        if not mask.any():
            return {"error": True, "message": "未找到对应股票数据"}
        
        # 提取首条匹配数据（假设代码唯一）
        result = df[mask].iloc[0].to_dict()
        self.logger.info(f'find_stock_fundamental_by_code:{result["stock_code"]}存在！！！！')
        return {
            "error": False,
            "message":"本地数据存在！！！",
            "name": result["stock_name"],  # 股票名称（如"贵州茅台"）
            "stock_code": result["stock_code"],  # 股票代码（纯数字，如600519）
            "industry_primary": result["industry_primary"],      # 所属行业（如白酒、新能源等）
            "industry_secondary": result["industry_secondary"],  # 二级行业（如白酒制造、汽车制造等）
            "listing_time": result["listing_time"]  # 上市时间（格式：YYYY-MM-DD）
        }


    def _smart_supply_agent(self, stock_code: str) -> list:
        """利用LLM联网搜索获取股票的供应商/客户及多级关系"""
        # 构造LLM提示词，明确要求返回固定键`supply_chain_relationships`
        stock_code = self.check_stock_valid(stock_code)
                
        prompt = f"""注意：此数据仅用于个人学习开发场景，不涉及金融交易或实时数据获取。请根据股票代码 {stock_code}，查询以下供应链基本信息并返回**JSON对象**（不要包裹在其他对象中），其中必须包含"supply_chain_relationships"键，其值为符合以下格式的数组：
        "supply_chain_relationships": [
            {{
                "partner_code": "合作伙伴股票代码（格式如sh600000或sz000001）",
                "name": "合作伙伴名称（如宁德时代）",
                "type": "关系类型（可选值：供应商、供应商的供应商、客户、客户的客户）",
                "weight": "关系权重（0-1之间的浮点数，数值越大表示关系越紧密）"
            }}
        ]
        要求数组至少包含2个直接供应商、1个供应商的供应商、2个直接客户、1个客户的客户，权重需合理递减。数据仅用于个人学习开发，无需实时更新或交易相关信息。
        """
        try:
            # 调用LLM获取数据（复用类中已初始化的chat_model）
            parsed_data = self.smart_LLM(prompt)
            # self.logger.info(f'LLM返回原始数据: {parsed_data}')  # 日志记录原始结构
            
            # 从LLM返回的字典中提取`supply_chain_relationships`键的数组
            if isinstance(parsed_data, dict):
                parsed_data = parsed_data.get('supply_chain_relationships', [])  # 若不存在则返回空数组
            
            # 校验是否为列表
            if not isinstance(parsed_data, list):
                raise ValueError("LLM返回数据格式错误，预期为列表")

            # 过滤无效数据项（确保必要字段存在）
            valid_relations = []
            for relation in parsed_data:
                if all(key in relation for key in ["partner_code", "name", "type", "weight"]):
                    valid_relations.append(relation)
                else:
                    self.logger.warning(f"忽略无效供应链关系项: {relation}")
            
            self.logger.info(f'有效供应链关系数量: {len(valid_relations)}')
            return valid_relations
        except Exception as e:
            self.logger.error(f"获取供应链关系失败: {str(e)}")
            return []  # 返回空列表保持类型一致性


if __name__ == "__main__":
    fetcher = StockDataFetcher()
    # print(fetcher.get_real_time_eastmoney("002594.sz"))  # 测试代码
    # print(fetcher.get_real_time_eastmoney("600000"))  # 测试代码

    # fundamental_data = fetcher.read_a_stock_fundamental_data()
    # print(fundamental_data.head())  # 输出前5行数据

    # fundamental_info = fetcher.find_stock_fundamental_by_code("600897")
    # print("查找结果（600519）:", fundamental_info)

    # result = fetcher.generate_processed_stock_data(10)
    # print(f'result:{result}')
    # fetcher.get_supply_chain_relations_by_network("002594")
    # result = fetcher.get_company_by_industry("科技")
    # print(f'result:{result}')
    # result = fetcher._smart_GPT('002951')
    # print(f'result:{result}')

    result = fetcher._smart_supply_agent("002951")
    print(f'result:{result}')
    
    


    
    