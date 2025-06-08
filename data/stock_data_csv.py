import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
from typing import Dict, List

class StockDataCSVProcessor:
    def __init__(self, csv_path: str = "data/a_stock_data.csv"):
        self.csv_path = csv_path
        # 二级行业到一级行业的映射字典（根据实际业务调整）
        self.INDUSTRY_MAPPING: Dict[str, str] = {
            "酒、饮料和精制茶制造业": "消费",
            "保险": "金融",
            "货币金融服务": "金融",
            "资本市场服务": "金融",
            "互联网和相关服务": "科技",
            "计算机、通信和其他电子设备制造业": "科技",
            "软件和信息技术服务业": "科技",
            "电气机械和器材制造业": "新能源",
            "房地产业": "房地产",
            "房地产开发与经营业": "房地产",
            "汽车制造业": "汽车",
            "有色金属冶炼和压延加工业": "有色金属",
            "有色金属矿采选业": "有色金属"
        }

    def process_csv(self) -> None:
        """
        核心处理逻辑：
        1. 读取原始 CSV 并调整列名（industry -> industry_secondary）
        2. 新增 industry_primary 列并根据映射填充
        3. 保存处理后的 CSV
        """
        try:
            # 读取原始 CSV（假设原始列顺序为：stock_code, industry, listing_time）
            df = pd.read_csv(
                self.csv_path,
                names=["stock_code", "industry_secondary", "listing_time"],  # 调整列名
                header=0,  # 覆盖原始表头（若有）
                encoding="gbk"  # 修改为 GBK 编码（Windows 常见中文编码）
            )
            
            # 新增并填充 industry_primary 列（未匹配的归为"其他"）
            df["industry_primary"] = df["industry_secondary"].map(self.INDUSTRY_MAPPING).fillna("其他")
            
            # 保存处理后的 CSV（覆盖或另存为新文件）
            df.to_csv(self.csv_path, index=False, encoding="utf-8")  # 保存为 utf-8 避免后续编码问题
            print(f"CSV 处理完成，已保存至 {self.csv_path}")
            
        except FileNotFoundError:
            raise FileNotFoundError(f"未找到 CSV 文件：{self.csv_path}")
        except Exception as e:
            raise RuntimeError(f"CSV 处理失败：{str(e)}")

    def get_processed_data(self) -> pd.DataFrame:
        """获取处理后的完整数据（含 industry_primary）"""
        return pd.read_csv(self.csv_path, encoding="utf-8")

if __name__ == "__main__":
    # 示例用法
    processor = StockDataCSVProcessor()
    processor.process_csv()  # 执行列名调整和一级行业填充
    
    # 验证处理结果
    processed_data = processor.get_processed_data()
    print("处理后的前5行数据：")
    print(processed_data.head())