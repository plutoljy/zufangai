"""
水电价格数据加载器
从 水电.txt 文件加载全国主要城市的水电气价格数据
"""

import csv
from pathlib import Path
from typing import Dict, List, Optional


class UtilityPriceLoader:
    """水电价格数据加载器"""

    def __init__(self, data_file: Optional[str] = None):
        """
        初始化加载器

        Args:
            data_file: 数据文件路径，默认为项目根目录的 水电.txt
        """
        if data_file is None:
            # 默认路径
            data_file = r"E:\github-program\github-date\租房ai\水电.txt"

        self.data_file = Path(data_file)
        self.prices = self._load_prices()

    def _load_prices(self) -> Dict:
        """加载价格数据"""
        prices = {}

        if not self.data_file.exists():
            print(f"[WARN] 水电价格文件不存在: {self.data_file}")
            return self._get_default_prices()

        try:
            with open(self.data_file, 'r', encoding='gbk') as f:
                reader = csv.reader(f, delimiter='\t')
                next(reader)  # 跳过表头

                for row in reader:
                    if len(row) < 6:
                        continue

                    city = row[0].strip()
                    utility_type = row[1].strip()
                    tier = row[2].strip()
                    usage_range = row[3].strip()
                    price = row[4].strip()

                    if not city or not utility_type or not price:
                        continue

                    # 解析价格
                    try:
                        price_value = float(price)
                    except ValueError:
                        continue

                    # 解析用量范围
                    usage_min, usage_max = self._parse_usage_range(usage_range)

                    # 构建数据结构
                    if city not in prices:
                        prices[city] = {}

                    # 映射类型名称
                    type_map = {
                        "居民用水": "water",
                        "居民用电": "electricity",
                        "居民燃气": "gas"
                    }

                    utility_key = type_map.get(utility_type)
                    if not utility_key:
                        continue

                    if utility_key not in prices[city]:
                        prices[city][utility_key] = []

                    prices[city][utility_key].append({
                        "tier": tier,
                        "usage_min": usage_min,
                        "usage_max": usage_max,
                        "price": price_value
                    })

            print(f"[OK] 成功加载 {len(prices)} 个城市的水电价格数据")
            return prices

        except Exception as e:
            print(f"[ERROR] 加载水电价格数据失败: {e}")
            return self._get_default_prices()

    def _parse_usage_range(self, usage_range: str) -> tuple:
        """
        解析用量范围

        Args:
            usage_range: 用量范围字符串，如 "0-180", "181-260", "261以上"

        Returns:
            (min, max) 元组，max 为 None 表示无上限
        """
        usage_range = usage_range.strip()

        if "以上" in usage_range or "及以上" in usage_range:
            # 无上限
            min_val = int(usage_range.replace("以上", "").replace("及以上", "").strip())
            return (min_val, None)

        if "-" in usage_range:
            parts = usage_range.split("-")
            return (int(parts[0]), int(parts[1]))

        # 单个数字
        val = int(usage_range)
        return (val, val)

    def get_official_price(self, city: str, utility_type: str, usage: float = 0) -> float:
        """
        获取官方价格（考虑阶梯定价）

        Args:
            city: 城市名称（如 "北京", "上海", "杭州"）
            utility_type: 类型（"water", "electricity", "gas"）
            usage: 用量（用于阶梯定价）

        Returns:
            官方价格
        """
        city_data = self.prices.get(city, {})
        tiers = city_data.get(utility_type, [])

        if not tiers:
            # 使用默认价格
            default = self._get_default_prices().get(city, {})
            return default.get(utility_type, 0)

        # 查找对应档位
        for tier in tiers:
            usage_min = tier["usage_min"]
            usage_max = tier["usage_max"]

            if usage_max is None:
                # 无上限档位
                if usage >= usage_min:
                    return tier["price"]
            else:
                # 有上限档位
                if usage_min <= usage <= usage_max:
                    return tier["price"]

        # 默认返回第一档价格
        return tiers[0]["price"]

    def get_city_prices(self, city: str) -> Dict[str, float]:
        """
        获取城市的第一档价格（用于显示）

        Args:
            city: 城市名称

        Returns:
            {"water": 价格, "electricity": 价格, "gas": 价格}
        """
        result = {}

        for utility_type in ["water", "electricity", "gas"]:
            result[utility_type] = self.get_official_price(city, utility_type, 0)

        return result

    def _get_default_prices(self) -> Dict:
        """获取默认价格（硬编码）"""
        return {
            "北京": {"water": 5.0, "electricity": 0.5583, "gas": 2.63},
            "上海": {"water": 3.45, "electricity": 0.617, "gas": 3.0},
            "广州": {"water": 3.5, "electricity": 0.68, "gas": 3.45},
            "深圳": {"water": 3.2, "electricity": 0.68, "gas": 3.5},
            "杭州": {"water": 4.0, "electricity": 0.538, "gas": 3.5},
        }

    def get_supported_cities(self) -> List[str]:
        """获取支持的城市列表"""
        return list(self.prices.keys())


# 全局单例
_loader = None


def get_utility_price_loader() -> UtilityPriceLoader:
    """获取全局水电价格加载器单例"""
    global _loader
    if _loader is None:
        _loader = UtilityPriceLoader()
    return _loader
