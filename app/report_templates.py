from typing import Dict, List


BUILTIN_REPORT_TEMPLATES: List[Dict[str, object]] = [
    {
        "template_id": "ppt-default",
        "name": "默认PPT模板",
        "description": "摘要-技术洞察-总结的通用PPT结构",
        "sections": [
            {
                "id": "summary",
                "title": "洞察摘要",
                "type": "summary",
                "source": "insight_summary",
                "use_llm": False,
                "instruction": "输出核心洞察摘要与关键趋势。",
            },
            {
                "id": "tech",
                "title": "技术洞察",
                "type": "tech",
                "per_topic": True,
                "source": "trend_synthesis",
                "viewpoint_template": "启示：优先验证{topic}相关安全能力与标准对齐。",
                "instruction": "每类技术单独一页，包含一句启示观点。",
            },
            {
                "id": "closing",
                "title": "洞察总结与验证能力",
                "type": "closing",
                "source": "capability_verification",
                "instruction": "总结结论并输出安全验证能力与下一步。",
            },
        ],
    }
]
