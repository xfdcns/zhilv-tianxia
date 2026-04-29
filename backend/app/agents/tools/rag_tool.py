from app.rag.retriever import retrieve_travel_guide


# rag_tool.py 自己不直接检索，
# 它只负责把"旅行规划语义"转成"检索查询"。
def _append_unique(parts: list[str], value: str) -> None:
    normalized = value.strip()
    if not normalized:
        return
    if normalized not in parts:
        parts.append(normalized)


def _extract_note_keywords(special_notes: str | None, destination: str | None = None) -> list[str]:
    """从用户备注里提炼更适合检索的关键词，而不是直接拼整句。"""
    if not special_notes:
        return []

    keywords: list[str] = []
    note = special_notes.strip()

    # 格式：(触发词, 目的地过滤, 输出关键词)
    # 目的地为 None 表示通用，不限目的地
    rule_keywords = [
        (("日落", "傍晚"), "大理", ["日落", "傍晚", "洱海", "双廊"]),
        (("日出", "清晨"), "大理", ["日出", "才村", "龙龛"]),
        (("拍照", "出片", "摄影"), None, ["拍照", "摄影", "出片"]),
        (("美食", "小吃", "吃"), None, ["美食", "小吃"]),
        (("轻松", "慢节奏", "休闲"), None, ["轻松", "慢节奏", "休闲"]),
        (("不想太早起床", "睡到自然醒"), None, ["轻松", "慢节奏"]),
        (("古镇",), "大理", ["古镇", "大理古城", "喜洲古镇"]),
        (("古镇",), "西安", ["古镇", "回民街"]),
        (("古镇",), "厦门", ["古镇", "鼓浪屿", "曾厝垵"]),
        (("骑行",), "大理", ["骑行", "洱海生态廊道"]),
        (("骑行",), "厦门", ["骑行", "环岛路"]),
        (("熊猫", "大熊猫"), "成都", ["大熊猫", "熊猫"]),
        (("潜水",), "三亚", ["潜水", "蜈支洲岛"]),
        (("海鲜",), "三亚", ["海鲜", "第一市场"]),
    ]

    for triggers, required_dest, values in rule_keywords:
        if required_dest and destination and required_dest not in destination:
            continue
        if any(trigger in note for trigger in triggers):
            for value in values:
                _append_unique(keywords, value)

    return keywords


def build_destination_query(
    destination: str,
    preferences: list[str] | None = None,
    pace: str | None = None,
    special_notes: str | None = None,
) -> str:
    """把目的地、偏好、节奏和备注改写成更贴近检索场景的 query。"""
    parts: list[str] = [destination]

    if preferences:
        for preference in preferences:
            _append_unique(parts, preference)

    if pace:
        _append_unique(parts, pace)

    for keyword in _extract_note_keywords(special_notes, destination=destination):
        _append_unique(parts, keyword)

    # 为向量检索补一些更稳定的旅游语义词，帮助召回景点、行程、攻略等片段。
    for stable_term in ["景点", "行程", "攻略", "推荐"]:
        _append_unique(parts, stable_term)

    return " ".join(part for part in parts if part).strip()


def _build_destination_query(
    destination: str,
    preferences: list[str] | None = None,
    pace: str | None = None,
    special_notes: str | None = None,
) -> str:
    """兼容旧调用，内部转到公开的 query 构造函数。"""
    return build_destination_query(
        destination=destination,
        preferences=preferences,
        pace=pace,
        special_notes=special_notes,
    )


def get_destination_guide_context(
    destination: str,
    preferences: list[str] | None = None,
    pace: str | None = None,
    special_notes: str | None = None,
    top_k: int = 5,
) -> list[str]:
    """根据目的地和偏好返回本地攻略里的相关片段。"""
    query = build_destination_query(
        destination=destination,
        preferences=preferences,
        pace=pace,
        special_notes=special_notes,
    )
    return retrieve_travel_guide(query=query, top_k=top_k)
