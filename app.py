from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from pathlib import Path

from datetime import date
from html import escape

import streamlit as st

try:
    from ingestion import fetch_url, parse_image
except Exception:
    fetch_url = None
    parse_image = None


st.set_page_config(page_title="灵感捕手", page_icon="🪶", layout="wide")

SEARCH_BACKEND_TIMEOUT_SECONDS = 2
SEARCH_BACKEND_COOLDOWN_SECONDS = 120

PAGE_TITLE = "灵感捕手 | Inspiration Catcher"
PAGE_SUBTITLE = '创作者的 AI 素材管家 —— 让收藏夹从"吃灰"变成"第二大脑"'
INPUT_PAGE_DESCRIPTION = "把零散收藏、片段想法和素材线索轻轻收拢到同一个工作台里，先完成记录与整理，再继续接入后续标签抽取、知识归档与内容生成流程。"
LIBRARY_PAGE_DESCRIPTION = "在同一套工作台里查看、筛选和回看已经收录的灵感素材，让临时收藏逐步沉淀成真正可复用的创作资产。"
SMART_SEARCH_PAGE_DESCRIPTION = "输入一个关键词，从已经收录的灵感素材里快速定位相关内容。当前页面已预留 Agent 检索入口，后续接入真实搜索结果后可直接展示。"
DRAFT_PAGE_DESCRIPTION = "围绕一个明确主题，从已选素材里组织出一版可继续编辑的文章初稿，先完成结构化表达，再进入后续润色与扩写。"

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


def normalize_material_record(item: dict, index: int = 0) -> dict:
    tags = item.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]

    created_at = str(item.get("created_at", "") or "").strip()
    display_date = str(item.get("date", "") or "").strip()
    if not display_date and created_at:
        display_date = created_at.split(" ", 1)[0]
    if not display_date:
        display_date = str(date.today())

    normalized = {
        "id": item.get("id", f"demo-{index}"),
        "title": item.get("title") or f"未命名素材 {index + 1}",
        "tags": tags,
        "summary": item.get("summary") or item.get("content", ""),
        "content": item.get("content", ""),
        "type": item.get("type", "未分类"),
        "date": display_date,
    }
    if created_at:
        normalized["created_at"] = created_at
    return normalized


def load_materials_from_backend(fallback_to_demo: bool = True) -> list[dict]:
    try:
        from agent import list_materials as agent_list_materials

        backend_materials = agent_list_materials(limit=50)
    except Exception:
        backend_materials = None

    if backend_materials is None:
        if fallback_to_demo:
            return [normalize_material_record(item, index) for index, item in enumerate(sample_materials)]
        return []

    return [
        normalize_material_record(item, index)
        for index, item in enumerate(backend_materials)
        if isinstance(item, dict)
    ]


if "materials" not in st.session_state:
    st.session_state.materials = load_materials_from_backend()

if "draft_text" not in st.session_state:
    st.session_state.draft_text = ""

if "quick_note" not in st.session_state:
    st.session_state.quick_note = ""

if "url_input" not in st.session_state:
    st.session_state.url_input = ""

if "search_query" not in st.session_state:
    st.session_state.search_query = ""

if "search_results" not in st.session_state:
    st.session_state.search_results = None

if "search_error" not in st.session_state:
    st.session_state.search_error = ""

if "search_notice" not in st.session_state:
    st.session_state.search_notice = ""

if "draft_topic" not in st.session_state:
    st.session_state.draft_topic = ""

if "draft_selected_ids" not in st.session_state:
    st.session_state.draft_selected_ids = []

if "generated_draft" not in st.session_state:
    st.session_state.generated_draft = ""

if "generated_draft_refs" not in st.session_state:
    st.session_state.generated_draft_refs = []

if "generated_draft_error" not in st.session_state:
    st.session_state.generated_draft_error = ""

if "page" not in st.session_state:
    st.session_state.page = "存入灵感"

if "search_backend_retry_after" not in st.session_state:
    st.session_state.search_backend_retry_after = 0.0


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


def persist_material_payload(payload: dict) -> tuple[bool, str]:
    try:
        from agent import save_material as agent_save_material
    except ImportError:
        return False, "素材库接口暂未接入，请稍后再试。"
    except Exception as exc:
        return False, f"素材库接口加载失败：{exc}"

    try:
        saved_id = agent_save_material(payload)
    except Exception as exc:
        return False, f"存入素材库失败：{exc}"

    fresh_materials = load_materials_from_backend(fallback_to_demo=False)
    if fresh_materials:
        st.session_state.materials = fresh_materials
    else:
        saved_item = normalize_material_record(
            {
                **payload,
                "id": saved_id,
                "created_at": str(date.today()),
            }
        )
        st.session_state.materials = [saved_item, *st.session_state.materials]

    return True, "已成功存入素材库。"


def save_material(content: str) -> tuple[bool, str]:
    text = content.strip()
    if not text:
        return False, "请先输入一点素材内容。"

    title = text[:18] + ("..." if len(text) > 18 else "")
    summary = text[:72] + ("..." if len(text) > 72 else "")
    payload = {
        "title": title or "未命名素材",
        "content": text,
        "tags": infer_tags(text),
        "summary": summary,
        "type": "灵感",
        "source_type": "text",
        "url": "",
    }
    return persist_material_payload(payload)


def save_ingested_material(record: dict) -> tuple[bool, str]:
    if not isinstance(record, dict):
        return False, "素材解析结果无效。"
    if record.get("error"):
        return False, str(record["error"])

    content = str(record.get("content", "") or "").strip()
    if not content:
        return False, "没有可存入的素材内容。"

    tags = record.get("tags") or infer_tags(content)
    if isinstance(tags, str):
        tags = [tags]

    source_type = str(record.get("source_type", "text") or "text")
    title = str(record.get("title") or (content[:18] + ("..." if len(content) > 18 else ""))).strip()
    summary_source = str(record.get("summary") or content)
    summary = summary_source[:72] + ("..." if len(summary_source) > 72 else "")
    material_type = record.get("type") or {
        "url": "文章",
        "image": "图片",
        "text": "灵感",
    }.get(source_type, "灵感")

    payload = {
        "title": title or "未命名素材",
        "content": content,
        "tags": tags,
        "summary": summary,
        "type": material_type,
        "source_type": source_type,
        "url": str(record.get("url", "") or ""),
    }
    return persist_material_payload(payload)


def ingest_url_material(url: str) -> tuple[bool, str]:
    clean_url = url.strip()
    if not clean_url:
        return False, "请先输入网页链接。"
    if fetch_url is None:
        return False, "网页抓取功能暂不可用。"
    return save_ingested_material(fetch_url(clean_url))


def ingest_uploaded_image(uploaded_file) -> tuple[bool, str]:
    if uploaded_file is None:
        return False, "请先上传一张图片。"
    if parse_image is None:
        return False, "图片 OCR 功能暂不可用。"

    suffix = Path(getattr(uploaded_file, "name", "upload.png")).suffix or ".png"
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=tempfile.gettempdir()) as temp_file:
            temp_file.write(uploaded_file.getvalue())
            temp_path = temp_file.name
        return save_ingested_material(parse_image(temp_path))
    except Exception as exc:
        return False, f"图片处理失败：{exc}"
    finally:
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)


def search_materials(query: str) -> tuple[list[dict], str]:
    keyword = query.strip()
    if not keyword:
        return [], "请先输入一个关键词。"

    def fallback_search() -> list[dict]:
        fallback_results = []
        source_materials = load_materials_from_backend(fallback_to_demo=False) or st.session_state.materials
        for index, item in enumerate(source_materials):
            score = 0
            tags = item.get("tags", [])
            title_text = item.get("title", "")
            summary_text = item.get("summary", "")
            content_text = item.get("content", "")

            if keyword in title_text:
                score += 60
            if any(keyword in tag for tag in tags):
                score += 30
            if keyword in summary_text:
                score += 15
            if keyword in content_text:
                score += 12

            if score:
                fallback_results.append(
                    {
                        "title": title_text or f"结果 {index + 1}",
                        "tags": tags,
                        "summary": summary_text,
                        "type": item.get("type", "未分类"),
                        "score": score,
                    }
                )

        return sorted(fallback_results, key=lambda row: row["score"], reverse=True)

    def fallback_response(message: str) -> tuple[list[dict], str]:
        fallback_results = fallback_search()
        if fallback_results:
            return fallback_results, message
        return [], message

    if time.time() < st.session_state.search_backend_retry_after:
        return fallback_response("向量检索仍在初始化，当前先展示本地关键词匹配结果。")

    script = (
        "import json; "
        "from agent import search_materials; "
        f"result = search_materials({json.dumps(keyword, ensure_ascii=False)}); "
        "print(json.dumps(result, ensure_ascii=False))"
    )

    try:
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=Path(__file__).resolve().parent,
            capture_output=True,
            text=True,
            timeout=SEARCH_BACKEND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        st.session_state.search_backend_retry_after = time.time() + SEARCH_BACKEND_COOLDOWN_SECONDS
        fallback_results = fallback_search()
        if fallback_results:
            return fallback_results, "向量检索初始化较慢，当前先展示本地关键词匹配结果。"
        return [], "智能检索初始化较慢，请稍后再试。"
    except Exception as exc:
        st.session_state.search_backend_retry_after = time.time() + SEARCH_BACKEND_COOLDOWN_SECONDS
        fallback_results = fallback_search()
        if fallback_results:
            return fallback_results, f"智能检索暂时不可用，当前展示本地关键词匹配结果：{exc}"
        return [], f"智能检索暂时不可用：{exc}"

    if completed.returncode != 0:
        st.session_state.search_backend_retry_after = time.time() + SEARCH_BACKEND_COOLDOWN_SECONDS
        fallback_results = fallback_search()
        error_text = completed.stderr.strip() or completed.stdout.strip() or "未知错误"
        if fallback_results:
            return fallback_results, f"智能检索返回错误，当前展示本地关键词匹配结果：{error_text}"
        return [], error_text

    try:
        raw_results = json.loads(completed.stdout.strip()) if completed.stdout.strip() else {}
    except json.JSONDecodeError:
        st.session_state.search_backend_retry_after = time.time() + SEARCH_BACKEND_COOLDOWN_SECONDS
        fallback_results = fallback_search()
        if fallback_results:
            return fallback_results, "智能检索返回内容无法解析，当前展示本地关键词匹配结果。"
        return [], "智能检索返回内容无法解析。"

    if isinstance(raw_results, dict) and raw_results.get("error"):
        st.session_state.search_backend_retry_after = time.time() + SEARCH_BACKEND_COOLDOWN_SECONDS
        fallback_results = fallback_search()
        if fallback_results:
            return fallback_results, f"智能检索返回错误，当前展示本地关键词匹配结果：{raw_results['error']}"
        return [], str(raw_results["error"])

    result_items = raw_results.get("results", []) if isinstance(raw_results, dict) else (raw_results or [])
    if not result_items:
        return [], "没有找到相关素材。你可以换一个关键词试试。"

    normalized_results = []
    for index, item in enumerate(result_items):
        if not isinstance(item, dict):
            continue

        tags = item.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]

        normalized_results.append(
            {
                "title": item.get("title") or f"结果 {index + 1}",
                "tags": tags,
                "summary": item.get("summary") or item.get("content", ""),
                "type": item.get("type") or "未分类",
                "score": item.get("score", item.get("similarity", "-")),
            }
        )

    if not normalized_results:
        return [], "检索接口已返回，但没有可展示的结果。"

    st.session_state.search_backend_retry_after = 0.0
    return normalized_results, ""


def resolve_search_state(query: str) -> tuple[list[dict], str, str]:
    results, message = search_materials(query)
    if results:
        return results, "", message
    return results, message, ""

def build_material_selector_items(items: list[dict]) -> list[dict]:
    selector_items = []
    for index, item in enumerate(items):
        material_id = str(item.get("id", f"demo-{index}"))
        selector_items.append(
            {
                "id": material_id,
                "title": item.get("title", "未命名素材"),
                "summary": item.get("summary", ""),
                "tags": item.get("tags", []),
                "type": item.get("type", "未分类"),
            }
        )
    return selector_items


def coerce_selected_ids(selected_ids: list[str]) -> list:
    coerced = []
    for item_id in selected_ids:
        if isinstance(item_id, str) and item_id.isdigit():
            coerced.append(int(item_id))
        else:
            coerced.append(item_id)
    return coerced


def generate_draft_content(topic: str, selected_ids: list[str], selector_lookup: dict[str, dict]) -> tuple[str, list[dict], str]:
    clean_topic = topic.strip()
    if not clean_topic:
        return "", [], "请先输入一个主题。"
    if not selected_ids:
        return "", [], "请至少选择一条素材。"

    try:
        from agent import generate_draft as agent_generate_draft
    except ImportError:
        return "", [], "生成初稿接口暂未接入，请稍后连接 B 模块。"
    except Exception as exc:
        return "", [], f"生成初稿接口加载失败：{exc}"

    try:
        draft_result = agent_generate_draft(clean_topic, coerce_selected_ids(selected_ids))
    except Exception as exc:
        return "", [], f"生成初稿失败：{exc}"

    if isinstance(draft_result, dict) and draft_result.get("error"):
        return "", [], str(draft_result["error"])

    if isinstance(draft_result, dict):
        draft_text = (
            draft_result.get("draft")
            or draft_result.get("content")
            or draft_result.get("article")
            or draft_result.get("text")
            or ""
        )
        used_materials = draft_result.get("used_materials", [])
    else:
        draft_text = str(draft_result or "")
        used_materials = []

    if used_materials:
        material_refs = []
        for item in used_materials:
            item_id = str(item.get("id", ""))
            fallback_ref = selector_lookup.get(item_id, {})
            material_refs.append(
                {
                    "title": fallback_ref.get("title", f"素材 {item_id}" if item_id else "已使用素材"),
                    "summary": item.get("summary") or fallback_ref.get("summary", ""),
                }
            )
    else:
        material_refs = [selector_lookup[item_id] for item_id in selected_ids if item_id in selector_lookup]

    if not draft_text.strip():
        return "", material_refs, "生成接口已返回，但没有可展示的初稿内容。"

    return draft_text.strip(), material_refs, ""


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
    total_tags = sorted({tag for item in items for tag in item.get("tags", [])})
    stat_columns = st.columns(3)
    values = [
        ("素材总数", str(len(items))),
        ("标签种类", str(len(total_tags))),
        ("当前阶段", "本地联调"),
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
        for tag in item.get("tags", [])
    )
    return f"""
    <div class="library-card">
        <div class="library-card-title">{escape(item['title'])}</div>
        <div class="material-badge-row">{badges}</div>
        <div class="library-card-summary">{escape(item['summary'])}</div>
        <div class="library-card-date">日期：{escape(item['date'])}</div>
    </div>
    """


def make_search_result_card(item: dict) -> str:
    badges = "".join(
        f'<span class="material-badge {badge_class_map.get(tag, "badge-custom")}">{escape(tag)}</span>'
        for tag in item.get("tags", [])
    )
    return f"""
    <div class="library-card">
        <div class="library-card-title">{escape(item['title'])}</div>
        <div class="material-badge-row">{badges}</div>
        <div class="library-card-summary">{escape(item['summary'])}</div>
        <div class="library-card-date">类型：{escape(str(item.get('type', '未分类')))}</div>
        <div class="library-card-date">相似度分数：{escape(str(item.get('score', '-')))}</div>
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
        ["存入灵感", "素材知识库", "智能检索", "生成初稿"],
        key="page",
        label_visibility="collapsed",
    )

if page == "存入灵感":
    render_page_header(INPUT_PAGE_DESCRIPTION)
    render_stats(st.session_state.materials)
    st.write("")

    left_col, right_col = st.columns([1.55, 0.82], gap="large")

    with left_col:
        st.markdown('<div class="quick-capture-input">录入方式</div>', unsafe_allow_html=True)
        st.text_input(
            "快速定位",
            key="quick_note",
            label_visibility="collapsed",
            placeholder="例如：婚礼当天、童年夏夜、旧照片、第一次远行",
        )

        text_tab, url_tab, image_tab = st.tabs(["粘贴文字", "输入 URL", "上传图片"])

        with text_tab:
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

            if st.button("存入素材库", key="save_text_material_button", type="primary", use_container_width=True):
                if material_text.strip():
                    saved, message = save_material(material_text)
                    if saved:
                        st.success(message)
                    else:
                        st.warning(message)
                else:
                    st.warning("请先输入一点素材内容。")

        with url_tab:
            st.markdown('<div class="section-title">抓取网页内容</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="section-copy">输入文章链接，先抓取标题和正文，再按当前素材库流程直接入库。</div>',
                unsafe_allow_html=True,
            )
            st.text_input(
                "网页链接",
                key="url_input",
                label_visibility="collapsed",
                placeholder="例如：https://example.com/article",
            )
            if st.button("抓取并存入素材库", key="save_url_material_button", use_container_width=True):
                saved, message = ingest_url_material(st.session_state.url_input)
                if saved:
                    st.success(message)
                else:
                    st.warning(message)

        with image_tab:
            st.markdown('<div class="section-title">上传图片并 OCR</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="section-copy">上传图片后先抽取文字，再把识别结果作为素材写入当前素材库。</div>',
                unsafe_allow_html=True,
            )
            uploaded_image = st.file_uploader(
                "上传图片",
                type=["png", "jpg", "jpeg", "bmp", "tiff", "tif", "webp"],
                key="image_upload",
                label_visibility="collapsed",
            )
            if uploaded_image is not None:
                st.caption(f"已选择文件：{uploaded_image.name}")
            if st.button("OCR并存入素材库", key="save_image_material_button", use_container_width=True):
                saved, message = ingest_uploaded_image(uploaded_image)
                if saved:
                    st.success(message)
                else:
                    st.warning(message)

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
            make_info_panel("当前预览", build_preview(st.session_state.quick_note, st.session_state.draft_text)),
            unsafe_allow_html=True,
        )
elif page == "素材知识库":
    render_page_header(LIBRARY_PAGE_DESCRIPTION)
    render_stats(st.session_state.materials)
    st.write("")

    filter_col, search_col = st.columns([0.78, 1.22], gap="large")
    all_tags = sorted({tag for item in st.session_state.materials for tag in item.get("tags", [])})

    with filter_col:
        selected_tags = st.multiselect("按标签筛选", all_tags, placeholder="选择一个或多个标签")
    with search_col:
        keyword = st.text_input("搜索标题或摘要", placeholder="例如：夏天、婚礼、火车、老手艺")

    filtered_materials = []
    for item in st.session_state.materials:
        tag_match = not selected_tags or any(tag in item.get("tags", []) for tag in selected_tags)
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
elif page == "智能检索":
    render_page_header(SMART_SEARCH_PAGE_DESCRIPTION)
    render_stats(st.session_state.materials)
    st.write("")

    st.markdown('<div class="section-title">智能检索相关素材</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-copy">输入一个关键词，调用 Agent 检索接口，返回最相关的素材结果卡片。</div>',
        unsafe_allow_html=True,
    )

    search_col, button_col = st.columns([1.2, 0.38], gap="medium")
    with search_col:
        st.text_input(
            "搜索关键词",
            key="search_query",
            placeholder="例如：用户增长、AI教育、品牌案例、婚礼故事",
        )
    with button_col:
        st.write("")
        search_clicked = st.button("搜索", use_container_width=True)

    if search_clicked:
        (
            st.session_state.search_results,
            st.session_state.search_error,
            st.session_state.search_notice,
        ) = resolve_search_state(st.session_state.search_query)

    if st.session_state.search_notice:
        st.info(st.session_state.search_notice)

    if st.session_state.search_error:
        st.markdown(
            f'<div class="empty-shell">{escape(st.session_state.search_error)}</div>',
            unsafe_allow_html=True,
        )
    elif st.session_state.search_results is None:
        st.markdown(
            '<div class="empty-shell">这里会展示智能检索结果。先输入关键词，再点击“搜索”。</div>',
            unsafe_allow_html=True,
        )
    elif not st.session_state.search_results:
        st.markdown(
            '<div class="empty-shell">暂时没有可展示的检索结果。你可以换一个关键词，或者先补充更多素材。</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="section-title">搜索结果</div>', unsafe_allow_html=True)
        columns = st.columns(2, gap="large")
        for index, material in enumerate(st.session_state.search_results):
            with columns[index % 2]:
                st.markdown(make_search_result_card(material), unsafe_allow_html=True)
else:
    render_page_header(DRAFT_PAGE_DESCRIPTION)
    render_stats(st.session_state.materials)
    st.write("")

    selector_items = build_material_selector_items(st.session_state.materials)
    selector_lookup = {item["id"]: item for item in selector_items}

    st.markdown('<div class="section-title">生成一篇主题初稿</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-copy">输入一个明确主题，再勾选你希望引用的素材，先生成一版可编辑的文章草稿。</div>',
        unsafe_allow_html=True,
    )

    st.text_input(
        "初稿主题",
        key="draft_topic",
        placeholder="例如：AI 如何改变教育",
    )

    st.multiselect(
        "选择要使用的素材",
        options=list(selector_lookup.keys()),
        format_func=lambda item_id: f"{selector_lookup[item_id]['title']} | {selector_lookup[item_id]['summary']}",
        key="draft_selected_ids",
        placeholder="勾选 1 条或多条素材",
    )

    if st.button("生成初稿", use_container_width=True):
        (
            st.session_state.generated_draft,
            st.session_state.generated_draft_refs,
            st.session_state.generated_draft_error,
        ) = generate_draft_content(
            st.session_state.draft_topic,
            st.session_state.draft_selected_ids,
            selector_lookup,
        )

    if st.session_state.generated_draft_error:
        st.markdown(
            f'<div class="empty-shell">{escape(st.session_state.generated_draft_error)}</div>',
            unsafe_allow_html=True,
        )
    elif not st.session_state.generated_draft:
        st.markdown(
            '<div class="empty-shell">这里会展示生成后的文章初稿。先输入主题、选择素材，再点击“生成初稿”。</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="section-title">文章初稿</div>', unsafe_allow_html=True)
        st.markdown(st.session_state.generated_draft)

        st.markdown('<div class="section-title">使用了哪些素材</div>', unsafe_allow_html=True)
        for ref in st.session_state.generated_draft_refs:
            st.markdown(f"- **{escape(ref['title'])}**  \n  {escape(ref['summary'])}")

        if st.button("复制初稿", key="copy_draft_button", use_container_width=True):
            st.code(st.session_state.generated_draft, language="markdown")





