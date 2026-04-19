"""医疗专业术语词典

提供医疗专业术语的定义、同义词和上下文信息
帮助LLM准确理解医疗场景需求
"""

from typing import List, Dict, Any

# 医疗术语词典
MEDICAL_TERMS = {
    "切片借阅": {
        "definition": "患者或第三方机构申请借阅医院病理科保存的组织切片进行会诊或检测",
        "synonyms": ["玻片借阅", "病理切片外借", "切片外送"],
        "related_terms": ["病理科", "会诊", "免疫组化", "HE染色", "蜡块"],
        "context": "病理科业务流程",
        "examples": ["患者需要借阅切片去外院会诊", "第三方检测机构申请借阅切片进行基因检测"]
    },
    "病历复印": {
        "definition": "患者申请复印住院病历、门诊病历等医疗文书",
        "synonyms": ["病历复制", "病案复印", "病历打印"],
        "related_terms": ["病案室", "出院病历", "病程记录", "入院记录"],
        "context": "病案管理业务",
        "examples": ["患者申请复印出院病历用于保险理赔", "患者复印病历带去其他医院就诊"]
    },
    "病理科": {
        "definition": "医院中负责疾病病理诊断的科室，处理组织切片、细胞学检查等",
        "synonyms": ["病理诊断中心", "病理检验科"],
        "related_terms": ["病理医生", "病理技术员", "切片", "蜡块", "HE染色", "免疫组化"],
        "context": "临床科室",
        "examples": ["病理科对切除组织进行病理诊断", "病理科出具病理报告"]
    },
    "免疫组化": {
        "definition": "免疫组织化学检测，利用抗原抗体反应检测组织中特定蛋白的表达，用于病理诊断和肿瘤分型",
        "synonyms": ["IHC", "免疫染色", "免疫组织化学"],
        "related_terms": ["病理诊断", "肿瘤标志物", "切片", "抗体", "阳性", "阴性"],
        "context": "病理检测技术",
        "examples": ["通过免疫组化检测HER2表达", "免疫组化辅助诊断淋巴瘤分型"]
    },
    "HE染色": {
        "definition": "苏木精-伊红染色，病理诊断的基础染色方法",
        "synonyms": ["常规染色", "苏木精伊红染色"],
        "related_terms": ["切片", "病理诊断", "显微镜检查"],
        "context": "病理检测技术",
        "examples": []
    },
    "会诊": {
        "definition": "邀请其他医院专家对疑难病例进行诊断意见交流",
        "synonyms": ["专家会诊", "MDT", "多学科会诊"],
        "related_terms": ["外院", "转诊", "病理诊断", "疑难病例"],
        "context": "医疗服务",
        "examples": ["携带切片去外院会诊", "申请远程病理会诊"]
    },
    "病案室": {
        "definition": "医院中负责病历资料管理和归档的部门",
        "synonyms": ["病案管理科", "医疗档案室"],
        "related_terms": ["病历", "复印", "归档", "编码"],
        "context": "医院管理部门",
        "examples": []
    },
    "等保三级": {
        "definition": "信息系统安全等级保护第三级，适用于涉及患者隐私的医疗信息系统",
        "synonyms": ["三级等保", "等级保护三级"],
        "related_terms": ["信息安全", "数据加密", "访问控制", "审计日志"],
        "context": "信息安全合规",
        "examples": ["医院信息系统需要通过等保三级认证"]
    },
    "HIS": {
        "definition": "医院信息系统(Hospital Information System)，医院核心业务系统",
        "synonyms": ["医院信息系统"],
        "related_terms": ["EMR", "LIS", "PACS", "电子病历"],
        "context": "医疗信息化",
        "examples": ["HIS系统管理患者就诊流程"]
    },
    "EMR": {
        "definition": "电子病历系统(Electronic Medical Record)",
        "synonyms": ["电子病历", "电子健康档案"],
        "related_terms": ["HIS", "病历书写", "病历质控"],
        "context": "医疗信息化",
        "examples": []
    },
    "PACS": {
        "definition": "影像归档和通信系统(Picture Archiving and Communication Systems)",
        "synonyms": ["影像系统"],
        "related_terms": ["CT", "MRI", "X光", "影像存储"],
        "context": "医疗信息化",
        "examples": []
    },
    "LIS": {
        "definition": "实验室信息系统(Laboratory Information System)",
        "synonyms": ["检验系统"],
        "related_terms": ["检验科", "检验报告", "标本"],
        "context": "医疗信息化",
        "examples": []
    },
    "蜡块": {
        "definition": "组织标本经石蜡包埋后形成的块状物，用于制作切片",
        "synonyms": ["石蜡包埋块"],
        "related_terms": ["切片", "病理标本", "HE染色"],
        "context": "病理标本",
        "examples": []
    },
}


def detect_medical_terms(text: str) -> List[str]:
    """
    检测文本中的医疗专业术语

    Args:
        text: 输入文本

    Returns:
        检测到的术语列表
    """
    detected = []
    text_lower = text.lower()

    for term in MEDICAL_TERMS.keys():
        # 直接匹配
        if term in text or term in text_lower:
            if term not in detected:
                detected.append(term)
            continue

        # 检查同义词
        for synonym in MEDICAL_TERMS[term].get("synonyms", []):
            if synonym in text or synonym in text_lower:
                if term not in detected:
                    detected.append(term)
                break

    return detected


def get_term_info(term: str) -> Dict[str, Any]:
    """
    获取术语详细信息

    Args:
        term: 术语名称

    Returns:
        术语信息字典，如果不存在返回None
    """
    return MEDICAL_TERMS.get(term)


def enrich_prompt_with_terminology(prompt: str, detected_terms: List[str]) -> str:
    """
    根据检测到的术语丰富prompt

    Args:
        prompt: 原始prompt
        detected_terms: 检测到的术语列表

    Returns:
        增强后的prompt
    """
    if not detected_terms:
        return prompt

    enrichment = ["\n\n【术语说明】"]

    for term in detected_terms:
        info = MEDICAL_TERMS.get(term)
        if info:
            enrichment.append(f"\n• {term}:")
            enrichment.append(f"  定义: {info['definition']}")
            enrichment.append(f"  同义词: {', '.join(info['synonyms'])}")
            enrichment.append(f"  相关术语: {', '.join(info['related_terms'])}")
            if info.get('examples'):
                enrichment.append(f"  示例: {'; '.join(info['examples'])}")

    return prompt + "\n".join(enrichment)


def add_medical_context(prompt: str, context_type: str = "general") -> str:
    """
    添加医疗场景上下文

    Args:
        prompt: 原始prompt
        context_type: 上下文类型 (general/pathology/medical_record)

    Returns:
        添加上下文后的prompt
    """
    contexts = {
        "general": """
【医疗信息化背景】
你正在设计医疗信息化系统，需要特别关注：
- 患者隐私保护和数据安全
- 符合医疗行业法规（等保、HIPAA等）
- 与医院现有系统（HIS/EMR/PACS）的集成
- 医疗工作流程的合规性
- 多院区/多科室的协同需求
""",
        "pathology": """
【病理科业务背景】
你正在设计病理科相关系统，需要了解：
- 病理科负责疾病诊断的金标准
- 主要工作流程: 标本接收→制片→诊断→报告
- 核心物品: 切片、蜡块、标本
- 常见需求: 切片借阅、会诊、免疫组化检测
- 相关科室: 临床科室、检验科、影像科
""",
        "medical_record": """
【病案管理背景】
你正在设计病案管理系统，需要了解：
- 病历是医疗纠纷和法律诉讼的重要依据
- 病历管理涉及: 归档、编码、复印、借阅
- 合规要求: 病历保存期限、复印审批流程
- 相关规范: 病历书写规范、病案管理规定
"""
    }

    context = contexts.get(context_type, contexts["general"])
    return context + "\n\n" + prompt


def get_related_terms(term: str) -> List[str]:
    """
    获取相关术语

    Args:
        term: 术语名称

    Returns:
        相关术语列表
    """
    info = MEDICAL_TERMS.get(term)
    if info:
        return info.get("related_terms", [])
    return []


# 导出所有函数
__all__ = [
    'MEDICAL_TERMS',
    'detect_medical_terms',
    'get_term_info',
    'enrich_prompt_with_terminology',
    'add_medical_context',
    'get_related_terms',
]
