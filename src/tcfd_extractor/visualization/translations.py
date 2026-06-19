"""Chinese → English translations for TCFD-related keywords."""
from __future__ import annotations

import re

KEYWORD_TRANSLATIONS: dict[str, str] = {
    "气候变化": "Climate Change",
    "碳排放": "Carbon Emissions",
    "碳中和": "Carbon Neutrality",
    "碳达峰": "Carbon Peak",
    "碳交易": "Carbon Trading",
    "节能减排": "Energy Saving & Emission Reduction",
    "低碳": "Low-Carbon",
    "环保": "Environmental Protection",
    "绿色": "Green",
    "可持续发展": "Sustainable Development",
    "新能源": "Renewable Energy",
    "可再生能源": "Renewable Energy",
    "清洁能源": "Clean Energy",
    "绿色金融": "Green Finance",
    "政策": "Policy",
    "法规": "Regulation",
    "合规": "Compliance",
    "碳税": "Carbon Tax",
    "排放权": "Emission Rights",
    "环保政策": "Environmental Policy",
    "碳排放权": "Carbon Emission Rights",
    "碳市场": "Carbon Market",
    "排放": "Emission",
    "减排": "Emission Reduction",
    "限排": "Emission Cap",
    "市场": "Market",
    "需求": "Demand",
    "供应链": "Supply Chain",
    "消费者": "Consumer",
    "原材料": "Raw Materials",
    "价格": "Price",
    "成本": "Cost",
    "采购": "Procurement",
    "投资": "Investment",
    "投资者": "Investor",
    "股东": "Shareholder",
    "融资": "Financing",
    "贷款": "Loan",
    "信用": "Credit",
    "技术": "Technology",
    "节能": "Energy Saving",
    "能效": "Energy Efficiency",
    "光伏": "Solar PV",
    "风电": "Wind Power",
    "储能": "Energy Storage",
    "电池": "Battery",
    "电动汽车": "Electric Vehicle",
    "新能源汽车": "New Energy Vehicle",
    "氢能": "Hydrogen Energy",
    "生物质能": "Biomass Energy",
    "地热能": "Geothermal Energy",
    "智能": "Smart",
    "数字化": "Digitalization",
    "碳捕集": "Carbon Capture",
    "碳封存": "Carbon Sequestration",
    "风险": "Risk",
    "风险管理": "Risk Management",
    "机遇": "Opportunity",
    "治理": "Governance",
    "披露": "Disclosure",
    "报告": "Report",
    "透明度": "Transparency",
    "ESG": "ESG",
    "评级": "Rating",
    "评估": "Assessment",
    "工业": "Industry",
    "制造业": "Manufacturing",
    "钢铁": "Steel",
    "水泥": "Cement",
    "化工": "Chemicals",
    "电力": "Electricity",
    "交通": "Transportation",
    "建筑": "Construction",
    "农业": "Agriculture",
    "林业": "Forestry",
    "能源": "Energy",
    "煤炭": "Coal",
    "石油": "Petroleum",
    "天然气": "Natural Gas",
    "汽车": "Automotive",
    "电子": "Electronics",
    "半导体": "Semiconductor",
    "互联网": "Internet",
    "金融": "Finance",
    "银行": "Bank",
    "保险": "Insurance",
    "证券": "Securities",
    "基金": "Fund",
    "管理": "Management",
    "战略": "Strategy",
    "规划": "Planning",
    "目标": "Target",
    "标准": "Standard",
    "体系": "System",
    "认证": "Certification",
    "审计": "Audit",
    "监督": "Supervision",
    "责任": "Responsibility",
    "可持续": "Sustainable",
    "环境": "Environment",
    "社会": "Social",
    "公司": "Company",
    "集团": "Group",
    "企业": "Enterprise",
    "项目": "Project",
    "产品": "Product",
    "服务": "Service",
    "客户": "Customer",
    "员工": "Employee",
    "利益相关方": "Stakeholder",
    "经济": "Economy",
    "保护": "Protection",
    "资源": "Resources",
    "生态系统": "Ecosystem",
    "生物多样性": "Biodiversity",
    "污染": "Pollution",
    "废水": "Wastewater",
    "废气": "Waste Gas",
    "废弃物": "Waste",
    "回收": "Recycling",
    "循环": "Circular",
    "再利用": "Reuse",
    "绿色发展": "Green Development",
    "生态": "Ecology",
    "生态环境": "Eco-Environment",
    "污染物": "Pollutant",
    "排污": "Discharge",
    "排放标准": "Emission Standard",
    "碳足迹": "Carbon Footprint",
    "碳标签": "Carbon Label",
    "碳预算": "Carbon Budget",
    "净零": "Net Zero",
    "巴黎协定": "Paris Agreement",
    "京都议定书": "Kyoto Protocol",
    "联合国": "United Nations",
    "可持续发展目标": "SDGs",
    "TCFD": "TCFD",
    # === Stage 2 additions (spec §5.2) ===
    "无": "N/A",
    "聚类A": "Cluster A",
    "聚类B": "Cluster B",
    "聚类C": "Cluster C",
    "聚类D": "Cluster D",
    "聚类E": "Cluster E",
    "聚类F": "Cluster F",
    "聚类G": "Cluster G",
    "聚类H": "Cluster H",
    "聚类I": "Cluster I",
    "聚类J": "Cluster J",
    "披露趋势": "Disclosure Trend",
    "流水线": "Pipeline",
    "数据提纯": "Data Refinement",
    "分块": "Chunking",
    "维度归类": "By Dimension",
    "阶段1": "Stage 1",
    "阶段2": "Stage 2",
    "阶段3": "Stage 3",
    "阶段4": "Stage 4",
    "公司数": "Companies",
    "披露数": "Disclosures",
    "年份范围": "Years Covered",
    "工程质量": "Engineering Quality",
    "测试通过": "tests passing",
    "工程": "Engineering",
    "技术深度": "Tech Deep Dive",
    "模块依赖图": "Module Dependency Graph",
    "已构建": "Built",
    "源代码按需索取": "Source available on request",
    "数据已脱敏": "All data anonymized",
    "构建中": "Under construction",
    "刷新": "Refresh",
    "加载失败": "Load failed",
    "点击节点下钻": "Click a node to drill down",
    "拖动滑块缩放": "Drag the slider to zoom",
    "可拖拽节点": "Draggable nodes",
    "点击查看详情": "Click to view details",
}


def translate(keyword_zh: str) -> str:
    if keyword_zh in KEYWORD_TRANSLATIONS:
        return KEYWORD_TRANSLATIONS[keyword_zh]
    return f"[[ZH: {keyword_zh}]]"  # 双中括号, 与 translate_smart 统一


def is_translated(keyword_zh: str) -> bool:
    return keyword_zh in KEYWORD_TRANSLATIONS


def missing_translations_for(keywords: list[str]) -> list[str]:
    return sorted({k for k in keywords if not is_translated(k)})


_NON_ALNUM_RE = re.compile(r"[^\w\s]+", re.UNICODE)


def translate_smart(keyword: str) -> str:
    """Smart translate with graceful fallback.

    Spec §5.1:
    1. Exact dict match → return English
    2. Pure ASCII → return as-is (English term, no need to translate)
    3. Mixed/Chinese → strip symbols, wrap as [[ZH: cleaned]]
    """
    if not keyword:
        return keyword
    if keyword in KEYWORD_TRANSLATIONS:
        return KEYWORD_TRANSLATIONS[keyword]
    if keyword.isascii():
        return keyword
    cleaned = _NON_ALNUM_RE.sub("", keyword).strip()
    if not cleaned:
        return keyword
    return f"[[ZH: {cleaned}]]"