"""Chinese → English translations for TCFD-related keywords."""
from __future__ import annotations

import re
import json
import hashlib
from pathlib import Path

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
    "能耗": "Energy Consumption",
    "降低": "Reduction",
    "淘汰": "Phase-Out",
    "淘汰落后": "Backward Capacity Phase-Out",
    "趋严": "Tightening Regulation",
    "处罚": "Penalty",
    "压力": "Pressure",
    "重点排污单位": "Key Polluting Entity",
    "环境保护": "Environmental Protection",
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
    # === Stage 4: sunburst cluster math_label translations ===
    # Real cluster labels from output/tcfd_keywords/phase5_category_mapping/
    # 三维度 93 unique labels — 全部英文化, 避免 "Cluster 12" 占位
    # 政策维度 (Policy)
    "可再生能源制氢技术": "Renewable Hydrogen Production",
    "排放限值": "Emission Cap",
    "低碳": "Low-Carbon",
    "排污费": "Sewage Discharge Fee",
    "关停": "Shutdown",
    "环保法": "Environmental Law",
    "环保": "Environmental Protection",
    "新能源": "Renewable Energy",
    "严控新建产能": "Strict Control of New Capacity",
    "产能淘汰": "Capacity Phase-Out",
    "产能指标": "Capacity Target",
    "两高": "High Energy/Emission (Two-High) Projects",
    "落后产能": "Backward Capacity",
    "限产": "Production Limit",
    "排放标准": "Emission Standard",
    "达标排放": "Compliance Discharge",
    "污染物控制标准": "Pollutant Control Standard",
    "大气污染防治": "Air Pollution Prevention",
    "排污许可": "Discharge Permit",
    "排污权交易费": "Discharge Rights Trading Fee",
    "无废企业": "Zero-Waste Enterprise",
    "环境应急预案": "Environmental Emergency Plan",
    "环保督查": "Environmental Inspection",
    "环保验收": "Environmental Acceptance Check",
    "安全环保监管": "Safety & Environmental Supervision",
    "补贴政策": "Subsidy Policy",
    "人行碳减排支持工具": "PBOC Carbon Reduction Support Tool",
    "双碳": "Dual Carbon Goals",
    "中长期现货交易": "Medium/Long-Term & Spot Trading",
    "配额缺口": "Allowance Shortfall",
    # 市场维度 (Market)
    "供应链金融": "Supply Chain Finance",
    "绿证": "Green Certificates",
    "碳资产": "Carbon Assets",
    "环境税": "Environmental Tax",
    "碳排放配额": "Carbon Emission Allowance",
    "绿色贷款": "Green Loans",
    "用能权交易": "Energy Use Rights Trading",
    "ESG": "ESG",
    "ESG 理财产品": "ESG Wealth Products",
    "ETS成本": "ETS Cost",
    "ODS 生产配额": "ODS Production Quota",
    "电力市场交易": "Electricity Market Trading",
    "碳排放交易市场": "Carbon Emission Trading Market",
    "碳排放权质押融资": "Carbon Emission Rights Pledged Financing",
    "碳核算": "Carbon Accounting",
    "碳金融": "Carbon Finance",
    "绿色信贷": "Green Credit",
    "绿色电力交易": "Green Electricity Trading",
    "绿色经济": "Green Economy",
    "可持续债券": "Sustainable Bonds",
    "贸易壁垒": "Trade Barriers",
    "关税": "Tariffs",
    "容量电价": "Capacity Tariff",
    "履约成本": "Compliance Cost",
    "ETS成本": "ETS Cost",  # alias for safety
    # 技术维度 (Technology)
    "电动": "Electric",
    "技术研发": "Technology R&D",
    "余热回收利用": "Waste Heat Recovery & Utilization",
    "智能化生产": "Smart Manufacturing",
    "低能耗": "Low Energy Consumption",
    "低碳": "Low-Carbon",
    "风力发电": "Wind Power Generation",
    "污染物处理": "Pollutant Treatment",
    "可再生能源替代": "Renewable Energy Substitution",
    "新能源替代": "New Energy Substitution",
    "智能化": "Smart / Intelligent",
    "材料替代": "Material Substitution",
    "氢燃料": "Hydrogen Fuel",
    "清洁生产": "Cleaner Production",
    "煤改气": "Coal-to-Gas Conversion",
    "回收利用": "Recycling & Reuse",
    "节能": "Energy Saving",
    "节能减耗": "Energy Saving & Consumption Reduction",
    "节能减排技术改造": "Energy Saving Tech Retrofit",
    "能耗": "Energy Consumption",
    "脱硫脱硝": "Desulfurization & Denitrification",
    "发电": "Power Generation",
    "减少排放": "Emission Reduction",
    "降低能耗": "Energy Consumption Reduction",
    "除尘": "Dust Removal",
    "高功率": "High Power",
    "设备改造": "Equipment Retrofit",
    "设备更新": "Equipment Renewal",
    "工艺技术优化": "Process Technology Optimization",
    "废水处理": "Wastewater Treatment",
    "停产整改": "Production Suspension & Rectification",
    "充电补贴": "EV Charging Subsidy",
    "环境保护税": "Environmental Protection Tax",
    "绿色技术": "Green Technology",
}

_GENERATED_TRANSLATIONS_PATH = Path(__file__).with_name("llm_translations.json")
if _GENERATED_TRANSLATIONS_PATH.exists():
    KEYWORD_TRANSLATIONS.update(
        json.loads(_GENERATED_TRANSLATIONS_PATH.read_text(encoding="utf-8"))
    )


def translate(keyword_zh: str) -> str:
    if keyword_zh in KEYWORD_TRANSLATIONS:
        return KEYWORD_TRANSLATIONS[keyword_zh]
    return ascii_fallback(keyword_zh)


def is_translated(keyword_zh: str) -> bool:
    return keyword_zh in KEYWORD_TRANSLATIONS


def missing_translations_for(keywords: list[str]) -> list[str]:
    return sorted({k for k in keywords if not is_translated(k)})


_NON_ALNUM_RE = re.compile(r"[^\w\s]+", re.UNICODE)
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_ASCII_LABEL_RE = re.compile(r"[^A-Za-z0-9+&/ .-]+")


def has_cjk(value: str) -> bool:
    return bool(_CJK_RE.search(value or ""))


def ascii_fallback(value: str) -> str:
    """Return a stable English-only label for any untranslated chart term."""
    if not value:
        return value
    ascii_part = _ASCII_LABEL_RE.sub(" ", value).strip()
    ascii_part = re.sub(r"\s+", " ", ascii_part)
    if len(ascii_part) >= 2 and re.search(r"[A-Za-z]{2,}", ascii_part):
        return ascii_part.title()
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:6].upper()
    return f"Climate Disclosure Term {digest}"


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
        return ascii_fallback(keyword)
    return ascii_fallback(cleaned)


def translate_chart_label(label: str) -> str:
    """Translate chart-facing labels and guarantee no Chinese characters."""
    translated = translate_smart(label)
    if has_cjk(translated):
        return ascii_fallback(label)
    return translated
