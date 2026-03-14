"""
热点池管理模块
用于管理金融和计算机领域的专业术语
"""
from typing import Dict, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class HotspotCategory:
    """热点类别"""
    name: str
    description: str
    terms: List[str]


class HotspotPool:
    """
    热点池 - 管理专业术语

    功能：
    1. 按类别管理术语
    2. 生成 AI prompt 中的热点列表
    3. 可扩展添加新类别
    """

    # 金融类别
    FINANCE = HotspotCategory(
        name="金融",
        description="金融、投资、交易相关术语",
        terms=[
            # 期权术语（英文）
            "sell put", "sell call", "buy put", "buy call",
            "covered call", "naked put", "cash secured put",
            "protective put", "bull call spread", "bear put spread",
            "iron condor", "butterfly spread", "calendar spread",
            "straddle", "strangle",
            "put option", "call option",
            "strike price", "expiration", "premium",
            "in the money", "at the money", "out of the money",
            "ITM", "ATM", "OTM",
            # 期权术语（中文）
            "行权价", "执行价", "到期日", "到期", "权利金", "期权费",
            "看涨期权", "看跌期权", "认购期权", "认沽期权",
            "备兑开仓", "裸卖", "保护性看跌", "牛市价差", "熊市价差",
            "铁鹰策略", "蝶式策略", "跨式策略", "宽跨式策略",
            "实值", "平值", "虚值", "内在价值", "时间价值", "时间衰减",
            # 交易术语（英文）
            "long", "short", "bullish", "bearish",
            "dividend", "yield", "margin", "leverage",
            "equity", "volatility", "implied volatility", "IV",
            "support", "resistance", "trend line",
            # 交易术语（中文）
            "做多", "做空", "多头", "空头", "看涨", "看跌",
            "股息", "分红", "收益率", "保证金", "杠杆", "杠杆倍数",
            "股票", "持仓", "仓位", "头寸", "开仓", "平仓", "爆仓",
            "波动率", "隐含波动率", "历史波动率", "波动",
            "支撑位", "压力位", "阻力位", "趋势线", "通道",
            # 希腊字母
            "delta", "gamma", "theta", "vega", "rho",
            "德尔塔", "伽马", "西塔", "维加", "柔",
            # 金融产品（英文）
            "ETF", "REITs", "IPO", "CPI", "PPI", "GDP", "PMI",
            "M1", "M2", "PE ratio", "PB ratio", "ROE", "EPS",
            # 金融产品（中文）
            "指数基金", "房地产投资信托", "首次公开发行", "新股",
            "市盈率", "市净率", "净资产收益率", "每股收益",
            "消费者价格指数", "生产者价格指数", "国内生产总值", "采购经理指数",
            # 交易指令（英文）
            "limit order", "market order", "stop loss", "take profit",
            # 交易指令（中文）
            "限价单", "市价单", "止损", "止盈", "止损单", "止盈单",
            "买入", "卖出", "加仓", "减仓", "补仓", "全仓", "半仓",
            # 技术分析
            "K线", "阳线", "阴线", "十字星", "锤子线",
            "MACD", "RSI", "KDJ", "布林带", "Bollinger Bands",
            "移动平均线", "均线", "MA", "EMA", "SMA",
            "成交量", "成交额", "换手率", "量比", "委比",
            # 账户相关
            "账户", "资金账户", "证券账户", "现金账户", "融资账户",
            "可用资金", "可取资金", "冻结资金", "总资产", "总市值",
            "当日盈亏", "浮动盈亏", "实现盈亏", "累计盈亏",
        ]
    )

    # 计算机类别
    TECH = HotspotCategory(
        name="计算机",
        description="编程、框架、技术相关术语",
        terms=[
            # 编程语言
            "Python", "JavaScript", "TypeScript", "Swift", "Rust",
            "Go", "Java", "C++", "C#", "Kotlin", "Ruby", "PHP",
            # 框架和库
            "React", "Vue", "Angular", "Svelte", "Next.js",
            "Django", "Flask", "FastAPI", "Express", "Spring",
            # 开发工具
            "Git", "GitHub", "GitLab", "Docker", "Kubernetes",
            "K8s", "Linux", "Unix", "Shell", "Bash",
            # 云和基础设施
            "AWS", "Azure", "GCP", "Vercel", "Netlify",
            "CI/CD", "DevOps", "Microservices",
            # 数据库
            "SQL", "NoSQL", "PostgreSQL", "MySQL", "MongoDB",
            "Redis", "SQLite", "GraphQL",
            # 其他技术术语
            "API", "REST", "GraphQL", "WebSocket", "HTTP",
            "JSON", "XML", "YAML", "Markdown",
            "AI", "ML", "LLM", "GPT", "NLP", "CNN", "RNN",
            "Frontend", "Backend", "Fullstack",
            "OAuth", "JWT", "SSL", "TLS", "HTTPS",
        ]
    )

    # 券商软件类别
    BROKER = HotspotCategory(
        name="券商",
        description="券商软件、交易平台",
        terms=[
            # 国际券商
            "IBKR", "Interactive Brokers", "盈透证券",
            "Robinhood", "罗宾汉",
            "TD Ameritrade", "TD",
            "Charles Schwab", "Schwab",
            "Fidelity", "富达",
            "E*TRADE", "Etrade",
            "Webull", "微牛",
            "Saxo", "盛宝银行",
            "Tiger Brokers", "老虎证券",
            "Futu", "富途", "富途牛牛",
            "Snowball", "雪盈证券",
            "Longbridge", "长桥证券",
            # 国内券商
            "华泰证券", "涨乐财富通",
            "中信证券", "信e投",
            "招商证券", "智远一户通",
            "东方财富", "东财",
            "广发证券", "易淘金",
            "国泰君安", "君弘",
            "平安证券",
            "银河证券", "中国银河",
            "海通证券", "e海通财",
            "申万宏源", "大赢家",
            "国信证券", "金太阳",
            # 港美股平台
            "尊嘉金融", "尊嘉",
            "必贝证券", "必贝", "BBAE",
            "华盛通",
            "艾德证券", "艾德一站通",
        ]
    )

    def __init__(self):
        """初始化热点池"""
        self.categories: List[HotspotCategory] = [self.FINANCE, self.TECH, self.BROKER]
        # 使用类别名本身（中文）作为 key
        self.enabled_categories: set = {self.FINANCE.name, self.TECH.name, self.BROKER.name}  # 默认全部启用

    def add_category(self, category: HotspotCategory):
        """添加新类别"""
        self.categories.append(category)
        logger.info(f"Added hotspot category: {category.name} ({len(category.terms)} terms)")

    def get_enabled_terms(self) -> List[str]:
        """获取所有已启用类别的术语"""
        terms = []
        for category in self.categories:
            category_key = category.name.upper()
            if category_key in self.enabled_categories:
                terms.extend(category.terms)
        return terms

    def get_terms_by_category(self, category_name: str) -> List[str]:
        """按类别获取术语"""
        for category in self.categories:
            if category.name == category_name:
                return category.terms
        return []

    def enable_category(self, category_name: str):
        """启用类别"""
        self.enabled_categories.add(category_name)
        logger.info(f"Enabled hotspot category: {category_name}")

    def disable_category(self, category_name: str):
        """禁用类别"""
        self.enabled_categories.discard(category_name)
        logger.info(f"Disabled hotspot category: {category_name}")

    def generate_prompt_section(self) -> str:
        """
        生成 AI prompt 中的热点池部分

        Returns:
            格式化的热点池文本，用于插入到 AI prompt 中
        """
        if not self.enabled_categories:
            return ""

        sections = []

        for category in self.categories:
            category_key = category.name.upper()
            if category_key not in self.enabled_categories:
                continue

            # 格式化术语列表（每行 5 个）
            terms_str = ", ".join(category.terms[:50])  # 限制显示前 50 个
            if len(category.terms) > 50:
                terms_str += f"... (共{len(category.terms)}个术语)"

            section = f"""
## {category.name}热点池（{category.description}）
{terms_str}
"""
            sections.append(section)

        intro = """## 专业术语保护（最高优先级）
以下术语必须完整保留，禁止翻译、改写或替换为同义词：
- 金融术语：行权价、执行价、到期日、权利金、看涨期权、看跌期权、做多、做空等
- 技术术语：Docker, Kubernetes, Python, React 等框架和工具名
- 券商名称：IBKR, 盈透证券, 老虎证券, 富途等

⚠️ 严禁修改上述术语，即使它们在语法上看起来不自然！
"""

        return intro + "\n".join(sections)

    def get_stats(self) -> Dict[str, any]:
        """获取统计信息"""
        return {
            "total_categories": len(self.categories),
            "enabled_categories": len(self.enabled_categories),
            "total_terms": sum(len(c.terms) for c in self.categories),
            "enabled_terms": len(self.get_enabled_terms()),
            "categories": [
                {
                    "name": c.name,
                    "count": len(c.terms),
                    "enabled": c.name.upper() in self.enabled_categories
                }
                for c in self.categories
            ]
        }


# 全局热点池实例
hotspot_pool = HotspotPool()


if __name__ == "__main__":
    # 测试
    pool = HotspotPool()

    print("=== 热点池统计 ===")
    stats = pool.get_stats()
    print(f"总类别数: {stats['total_categories']}")
    print(f"启用类别数: {stats['enabled_categories']}")
    print(f"总术语数: {stats['total_terms']}")
    print(f"启用术语数: {stats['enabled_terms']}")

    print("\n=== AI Prompt 部分 ===")
    print(pool.generate_prompt_section())

    print("\n=== 金融术语示例 ===")
    finance_terms = pool.get_terms_by_category("金融")
    print(f"前 10 个: {finance_terms[:10]}")
