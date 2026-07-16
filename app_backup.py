from __future__ import annotations

from datetime import date
from html import escape

import streamlit as st


st.set_page_config(page_title="灵感捕手", page_icon="🪶", layout="wide")

PAGE_TITLE = "灵感捕手 | Inspiration Catcher"
PAGE_SUBTITLE = '创作者的 AI 素材管家 —— 让收藏夹从"吃灰"变成"第二大脑"'
INPUT_PAGE_DESCRIPTION = "把零散收藏、片段想法和素材线索轻轻收拢到同一个工作台里，先完成记录与整理，再继续接入后续标签抽取、知识归档与内容生成流程。"
LIBRARY_PAGE_DESCRIPTION = "在同一套工作台里查看、筛选和回看已经收录的灵感素材，让临时收藏逐步沉淀成真正可复用的创作资产。"

st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(circle at top right, rgba(218, 191, 150, 0.18), transparent 24%),
            linear-gradient(180deg, #f8f3ea 0%, #f3ede3 100%);
        color: #2f2924;
    }
    .main .block-container {
        max-width: 1380px;
        padding-top: 2rem;
        padding-bottom: 2.4rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #262220 0%, #181513 100%);
        border-right: 1px solid rgba(255, 255, 255, 0.06);
    }
    section[data-testid="stSidebar"] * {
        color: #f7f1e7;
    }
    section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"] {
        padding-top: 1.15rem;
    }
    .sidebar-brand {
        padding: 1.2rem 1.1rem;
        border-radius: 26px;
        background: linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.04));
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.06);
        margin-bottom: 1.1rem;
    }
    .sidebar-kicker {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #d8cbb9;
        margin-bottom: 0.75rem;
    }
    .sidebar-kicker::before {
        content: "";
        width: 0.42rem;
        height: 0.42rem;
        border-radius: 999px;
        background: #e96f63;
        display: inline-block;
    }
    .sidebar-brand-title {
        font-size: 1.18rem;
        font-weight: 800;
        line-height: 1.45;
        color: #fff9f3;
        margin-bottom: 0.45rem;
    }
    .sidebar-brand-copy {
        font-size: 0.9rem;
        line-height: 1.72;
        color: #d6cabc;
    }
    .sidebar-nav {
        margin-top: 0.7rem;
    }
    .sidebar-nav-label {
        font-size: 0.74rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #bdae9d;
        margin-bottom: 0.55rem;
        padding-left: 0.15rem;
    }
    .nav-indicator {
        width: 0.5rem;
        height: 0.5rem;
        border-radius: 999px;
        background: #df6a5f;
        display: inline-block;
    }
    section[data-testid="stSidebar"] [role="radiogroup"] {
        gap: 0.55rem;
    }
    section[data-testid="stSidebar"] label[data-baseweb="radio"] {
        margin: 0;
        padding: 0.72rem 0.92rem;
        border-radius: 18px;
        border: 1px solid rgba(255,255,255,0.06);
        background: rgba(255,255,255,0.03);
        transition: all 0.18s ease;
    }
    section[data-testid="stSidebar"] label[data-baseweb="radio"]:hover {
        background: rgba(255,255,255,0.06);
        border-color: rgba(255,255,255,0.1);
    }
    section[data-testid="stSidebar"] label[data-baseweb="radio"] > div:first-child {
        display: none;
    }
    section[data-testid="stSidebar"] label[data-baseweb="radio"] p {
        font-size: 0.95rem;
        font-weight: 600;
        color: #ece2d5;
    }
    section[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) {
        background: rgba(255,255,255,0.1);
        border-color: rgba(255,255,255,0.12);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.06);
    }
    section[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) p {
        color: #ff8e82;
    }
    .page-hero {
        padding: 1.55rem 1.6rem;
        border-radius: 30px;
        background: linear-gradient(180deg, rgba(255,255,255,0.9), rgba(252,248,242,0.95));
        border: 1px solid rgba(181, 160, 131, 0.28);
        box-shadow: 0 18px 40px rgba(129, 109, 84, 0.09);
        margin-bottom: 1rem;
    }
    .hero-tag {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        padding: 0.34rem 0.8rem;
        border-radius: 999px;
        background: #efe4d2;
        color: #8a6540;
        font-size: 0.78rem;
        font-weight: 700;
        margin-bottom: 0.9rem;
    }
    .hero-tag::before {
        content: "";
        width: 0.42rem;
        height: 0.42rem;
        border-radius: 999px;
        background: #d56b61;
        display: inline-block;
    }
    .page-title {
        font-size: 2.55rem;
        line-height: 1.18;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: #2d2621;
        margin-bottom: 0.45rem;
    }
    .page-subtitle {
        font-size: 1.05rem;
        line-height: 1.8;
        color: #685c4f;
        margin-bottom: 0.75rem;
    }
    .page-description {
        font-size: 0.96rem;
        line-height: 1.82;
        color: #7c6f61;
        max-width: 60rem;
    }
    .stat-card {
        padding: 1rem 1rem 1.05rem;
        border-radius: 22px;
        background: rgba(255,255,255,0.84);
        border: 1px solid rgba(186, 169, 144, 0.25);
        box-shadow: 0 10px 24px rgba(111, 96, 76, 0.06);
    }
    .stat-label {
        color: #8f8070;
        font-size: 0.77rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 0.18rem;
    }
    .stat-value {
        color: #2d2621;
        font-size: 1.3rem;
        font-weight: 800;
    }
    .section-title {
        font-size: 1.18rem;
        font-weight: 800;
        color: #2f2924;
        margin-top: 0.25rem;
        margin-bottom: 0.38rem;
    }
    .section-copy {
        color: #7b6d5d;
        font-size: 0.95rem;
        line-height: 1.75;
        margin-bottom: 0.85rem;
    }
    .quick-capture-input {
        color: #7d6f5f;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-bottom: 0.45rem;
    }
    .info-panel {
        padding: 1rem 1rem 0.95rem;
        border-radius: 24px;
        background: #f6efe3;
        border: 1px solid rgba(206, 190, 167, 0.6);
        box-shadow: 0 12px 24px rgba(121, 102, 78, 0.05);
        margin-bottom: 0.85rem;
    }
    .info-panel-label {
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #8b6642;
        margin-bottom: 0.42rem;
    }
    .info-panel-body {
        font-size: 0.93rem;
        line-height: 1.72;
        color: #5e5246;
    }
    .library-card {
        min-height: 220px;
        padding: 1.05rem 1.05rem 1rem;
        border-radius: 24px;
        background: rgba(255,255,255,0.86);
        border: 1px solid rgba(189, 172, 146, 0.25);
        box-shadow: 0 14px 28px rgba(113, 98, 77, 0.06);
        margin-bottom: 1rem;
    }
    .library-card-title {
        color: #2f2924;
        font-size: 1.08rem;
        font-weight: 800;
        line-height: 1.55;
        margin-bottom: 0.75rem;
    }
    .material-badge-row {
        margin-bottom: 0.9rem;
    }
    .material-badge {
        display: inline-block;
        padding: 0.22rem 0.72rem;
        border-radius: 999px;
        color: #fffdf9;
        font-size: 0.76rem;
        font-weight: 700;
        margin-right: 0.42rem;
        margin-bottom: 0.35rem;
    }
    .badge-memory { background: #c7855b; }
    .badge-emotion { background: #d76d63; }
    .badge-family { background: #8a9a72; }
    .badge-scene { background: #8098ad; }
    .badge-daily { background: #bb8f5c; }
    .badge-custom { background: #7c7369; }
    .library-card-summary {
        color: #77695b;
        font-size: 0.94rem;
        line-height: 1.8;
        margin-bottom: 1rem;
    }
    .library-card-date {
        color: #9a8c7d;
        font-size: 0.81rem;
    }
    .empty-shell {
        padding: 1.2rem 1.15rem;
        border-radius: 22px;
        border: 1px dashed #ccb99f;
        background: rgba(255,255,255,0.6);
        color: #7a6d5d;
    }
    div[data-testid="stTextInput"] input,
    div[data-testid="stTextArea"] textarea,
    div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div {
        background: rgba(255,255,255,0.9);
        border: 1px solid #ddcfbd;
        color: #2f2924;
        box-shadow: 0 8px 20px rgba(124, 106, 81, 0.05);
    }
    div[data-testid="stTextInput"] input {
        min-height: 3rem;
        border-radius: 16px;
    }
    div[data-testid="stTextArea"] textarea {
        min-height: 320px;
        border-radius: 24px;
        line-height: 1.75;
    }
    div[data-testid="stTextInput"] input::placeholder,
    div[data-testid="stTextArea"] textarea::placeholder {
        color: #a39585;
    }
    div[data-testid="stTextInput"] label p,
    div[data-testid="stTextArea"] label p,
    div[data-testid="stMultiSelect"] label p {
        color: #6f6357;
        font-weight: 700;
    }
    div[data-testid="stButton"] > button {
        min-height: 3rem;
        border-radius: 16px;
        border: 1px solid #2c251f;
        background: #2c251f;
        color: #fffaf4;
        font-weight: 700;
        box-shadow: 0 10px 20px rgba(44, 37, 31, 0.14);
    }
    div[data-testid="stButton"] > button:hover {
        border-color: #3c342d;
        background: #3c342d;
    }
    div[data-testid="stAlert"] {
        border-radius: 18px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

sample_materials = [
    {
        "title": "旧照片背后的夏夜院子",
        "tags": ["回忆", "场景"],
        "summary": "一张旧照片牵出一整段夏夜记忆，院子里有蒲扇、西瓜和晚归的人声，细节很轻，却很能留住气氛。",
        "date": "2026-07-15",
    },
    {
        "title": "第一次离家远行的火车片段",
        "tags": ["日常", "家人"],
        "summary": "关于第一次坐火车离开家乡的讲述里，既有紧张和新鲜感，也有家里人为出门准备行李时的细碎动作。",
        "date": "2026-07-14",
    },
    {
        "title": "婚礼当天最难忘的一句话",
        "tags": ["情感", "回忆"],
        "summary": "真正留下来的不是场面的热闹，而是那句被轻轻说出口的话，它让整段回忆突然有了重心。",
        "date": "2026-07-13",
    },
]

badge_class_map = {
    "回忆": "badge-memory",
    "情感": "badge-emotion",
    "家人": "badge-family",
    "场景": "badge-scene",
    "日常": "badge-daily",
}

if "materials" not in st.session_state:
    st.session_state.materials = list(sample_materials)

if "draft_text" not in st.session_state:
    st.session_state.draft_text = ""

if "quick_note" not in st.session_state:
    st.session_state.quick_note = ""

if "page" not in st.session_state:
    st.session_state.page = "存入灵感"


def infer_tags(text: str) -> list[str]:
    tags = []
    if any(keyword in text for keyword in ["爷爷", "奶奶", "外婆", "外公", "母亲", "父亲", "家里"]):
        tags.append("家人")
    if any(keyword in text for keyword in ["小时候", "以前", "那年", "年轻时", "记得"]):
        tags.append("回忆")
    if any(keyword in text for keyword in ["院子", "火车", "学校", "村里", "街上"]):
        tags.append("场景")
    if any(keyword in text for keyword in ["开心", "难过", "紧张", "想念", "感动"]):
        tags.append("情感")
    if not tags:
        tags.append("日常")
    return tags[:2]


def save_material(content: str) -> None:
    text = content.strip()
    if not text:
        return

    title = text[:18] + ("..." if len(text) > 18 else "")
    summary = text[:72] + ("..." if len(text) > 72 else "")
    st.session_state.materials.insert(
        0,
        {
            "title": title or "未命名素材",
            "tags": infer_tags(text),
            "summary": summary,
            "date": str(date.today()),
        },
    )


def render_page_header(description: str) -> None:
    st.markdown(
        f"""
        <div class="page-hero">
            <div class="hero-tag">Inspiration Workspace</div>
            <div class="page-title">{PAGE_TITLE}</div>
            <div class="page-subtitle">{PAGE_SUBTITLE}</div>
            <div class="page-description">{description}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stats(items: list[dict]) -> None:
    total_tags = sorted({tag for item in items for tag in item["tags"]})
    stat_columns = st.columns(3)
    values = [
        ("素材总数", str(len(items))),
        ("标签种类", str(len(total_tags))),
        ("当前阶段", "前端 Demo"),
    ]
    for column, (label, value) in zip(stat_columns, values):
        with column:
            st.markdown(
                f'<div class="stat-card"><div class="stat-label">{label}</div><div class="stat-value">{value}</div></div>',
                unsafe_allow_html=True,
            )


def make_info_panel(title: str, body: str) -> str:
    return (
        '<div class="info-panel">'
        f'<div class="info-panel-label">{title}</div>'
        f'<div class="info-panel-body">{body}</div>'
        '</div>'
    )


def make_material_card(item: dict) -> str:
    badges = "".join(
        f'<span class="material-badge {badge_class_map.get(tag, "badge-custom")}">{escape(tag)}</span>'
        for tag in item["tags"]
    )
    return f"""
    <div class="library-card">
        <div class="library-card-title">{escape(item['title'])}</div>
        <div class="material-badge-row">{badges}</div>
        <div class="library-card-summary">{escape(item['summary'])}</div>
        <div class="library-card-date">日期：{escape(item['date'])}</div>
    </div>
    """


def build_preview(quick_note: str, material_text: str) -> str:
    sections = []
    if quick_note.strip():
        sections.append(f"主题线索：{escape(quick_note.strip())}")
    if material_text.strip():
        sections.append(escape(material_text.strip()).replace("\n", "<br>"))
    if not sections:
        return "这里会显示你当前输入的灵感预览，方便快速确认要点是否已经记完整。"
    return "<br><br>".join(sections)


with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-brand">
            <div class="sidebar-kicker">Creative Asset Desk</div>
            <div class="sidebar-brand-title">灵感捕手 Inspiration Catcher</div>
            <div class="sidebar-brand-copy">一个轻量、安静的创作工作台，用来收纳灵感碎片、整理素材线索，并把收藏夹沉淀成可复用的第二大脑。</div>
        </div>
        <div class="sidebar-nav">
            <div class="sidebar-nav-label">Navigation</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    page = st.radio(
        "页面导航",
        ["存入灵感", "素材知识库"],
        key="page",
        label_visibility="collapsed",
        format_func=lambda option: (
            f"●  {option}" if option == st.session_state.get("page", "存入灵感") else f"○  {option}"
        ),
    )

if page == "存入灵感":
    render_page_header(INPUT_PAGE_DESCRIPTION)
    render_stats(st.session_state.materials)
    st.write("")

    left_col, right_col = st.columns([1.55, 0.82], gap="large")

    with left_col:
        st.markdown('<div class="quick-capture-input">中部单行简短输入框</div>', unsafe_allow_html=True)
        st.text_input(
            "快速定位",
            key="quick_note",
            label_visibility="collapsed",
            placeholder="例如：婚礼当天、童年夏夜、旧照片、第一次远行",
        )
        st.markdown('<div class="section-title">存入一段灵感碎片</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">先把原话、场景、情绪和细节收进来，不必整理成正式文章。越接近真实语气，后续整理和生成就越自然。</div>',
            unsafe_allow_html=True,
        )
        material_text = st.text_area(
            "请输入灵感碎片",
            key="draft_text",
            label_visibility="collapsed",
            height=320,
            placeholder="例如：奶奶说她年轻时最喜欢傍晚坐在院子门口等家里人回来，那时候风里有稻谷味，远处还能听见收音机。",
        )

        if st.button("存入素材库", type="primary", use_container_width=True):
            if material_text.strip():
                save_material(material_text)
                st.success("已成功存入素材库。")
            else:
                st.warning("请先输入一点素材内容。")

    with right_col:
        st.markdown(
            make_info_panel(
                "输入建议",
                "优先保留人物称呼、原话语气、动作细节和具体场景，让后续整理出的内容更有辨识度和温度。",
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            make_info_panel(
                "推荐素材",
                "第一次远行、家里饭桌、婚礼片段、旧照片背后的故事、夏天夜晚和老手艺回忆，都是很适合先收录的灵感起点。",
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            make_info_panel("当前预览", build_preview(st.session_state.quick_note, material_text)),
            unsafe_allow_html=True,
        )
else:
    render_page_header(LIBRARY_PAGE_DESCRIPTION)
    render_stats(st.session_state.materials)
    st.write("")

    filter_col, search_col = st.columns([0.78, 1.22], gap="large")
    all_tags = sorted({tag for item in st.session_state.materials for tag in item["tags"]})

    with filter_col:
        selected_tags = st.multiselect("按标签筛选", all_tags, placeholder="选择一个或多个标签")
    with search_col:
        keyword = st.text_input("搜索标题或摘要", placeholder="例如：夏天、婚礼、火车、老手艺")

    filtered_materials = []
    for item in st.session_state.materials:
        tag_match = not selected_tags or any(tag in item["tags"] for tag in selected_tags)
        text_match = not keyword.strip() or keyword.strip() in f"{item['title']} {item['summary']}"
        if tag_match and text_match:
            filtered_materials.append(item)

    if not filtered_materials:
        st.markdown(
            '<div class="empty-shell">当前筛选条件下没有找到素材。你可以清空搜索词，或者先去“存入灵感”页面继续添加新的灵感碎片。</div>',
            unsafe_allow_html=True,
        )
    else:
        columns = st.columns(2, gap="large")
        for index, material in enumerate(filtered_materials):
            with columns[index % 2]:
                st.markdown(make_material_card(material), unsafe_allow_html=True)
