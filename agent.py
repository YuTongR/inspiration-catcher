import json
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI

# ============================================================
# 配置
# ============================================================
try:
    from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
except ImportError:
    DEEPSEEK_API_KEY = ""
    DEEPSEEK_BASE_URL = "https://api.deepseek.com"

PLACEHOLDER_TITLE_PREFIX = "未命名素材"
ENRICHMENT_WORKERS = 2

_llm_client = None
_enrichment_executor = ThreadPoolExecutor(max_workers=ENRICHMENT_WORKERS)


def _get_llm_client(api_key=None):
    """惰性初始化 LLM client,避免缺少本地 config 时在 import 阶段报错。"""
    global _llm_client

    key = api_key or DEEPSEEK_API_KEY
    if not key or key == "请创建config.py并填入API Key":
        return None

    if _llm_client is None:
        _llm_client = OpenAI(api_key=key, base_url=DEEPSEEK_BASE_URL)
    return _llm_client


# ============================================================
# 0. ChromaDB 向量库初始化
# ============================================================
_chroma_client = None
_ef = None
_collection = None


def _get_collection():
    """惰性初始化 ChromaDB 和 embedding,避免 import agent 时卡住。"""
    global _chroma_client, _ef, _collection

    if _collection is not None:
        return _collection

    _chroma_client = chromadb.PersistentClient(path="./chroma_db")
    _ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    _collection = _chroma_client.get_or_create_collection(
        name="materials", embedding_function=_ef
    )
    return _collection


def _safe_collection_delete(material_ids):
    if not material_ids:
        return
    try:
        client = chromadb.PersistentClient(path="./chroma_db")
        collection = client.get_or_create_collection(name="materials")
        collection.delete(ids=[str(material_id) for material_id in material_ids])
    except Exception:
        pass


def _upsert_material_index(material_id, tags, summary, content):
    """把一条素材的文本向量化后存入 Chroma,供搜索用。"""
    search_text = f"{' '.join(tags)} {summary} {content[:1000]}".strip()
    if not search_text:
        search_text = content[:1000]
    try:
        collection = _get_collection()
        try:
            collection.delete(ids=[str(material_id)])
        except Exception:
            pass
        collection.add(
            documents=[search_text],
            metadatas=[{"id": material_id}],
            ids=[str(material_id)],
        )
    except Exception:
        pass


# ============================================================
# 1. AI 分析素材:标题 + 标签 + 摘要 + 分类
# ============================================================

def _normalize_llm_json_payload(result_text: str) -> str:
    result_text = result_text.strip()
    if result_text.startswith("```"):
        result_text = result_text.split("\n", 1)[1]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
    return result_text.strip()


def analyze_material(content, api_key=None):
    """输入原始文本,返回 {title, tags, summary, type}"""
    key = api_key or DEEPSEEK_API_KEY
    if not key or key == "请创建config.py并填入API Key":
        return {"error": "请先在 config.py 里填入你的 DeepSeek API Key"}

    client = _get_llm_client(key)
    if client is None:
        return {"error": "请先在 config.py 里填入你的 DeepSeek API Key"}

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是一个素材管理助手。对用户提供的内容,做以下四件事:\n"
                        "1. 生成一个准确的中文标题,长度尽量控制在 8-20 个字\n"
                        "2. 生成3-5个中文标签(以#开头,如 #用户增长 #案例分析)\n"
                        "3. 写一句50字以内的中文摘要\n"
                        "4. 判断素材类型(文章/灵感/数据/案例/教程)\n"
                        "只返回JSON格式,不要任何额外文字。\n"
                        '例: {"title":"院子里的夏夜回忆","tags":["#回忆","#家庭"],"summary":"一段关于夏夜院子和家人等待的细节回忆","type":"灵感"}'
                    ),
                },
                {"role": "user", "content": content[:4000]},
            ],
            temperature=0.3,
            max_tokens=600,
        )

        result_text = _normalize_llm_json_payload(response.choices[0].message.content)
        parsed = json.loads(result_text)
        parsed.setdefault("title", "")
        parsed.setdefault("tags", [])
        parsed.setdefault("summary", "")
        parsed.setdefault("type", "灵感")
        return parsed
    except Exception as exc:
        return {"error": str(exc)}


def generate_title_from_content(content, api_key=None):
    result = analyze_material(content, api_key=api_key)
    if result.get("error"):
        return ""
    return str(result.get("title", "") or "").strip()


# ============================================================
# 2. SQLite 数据库操作
# ============================================================

def _connect_db(db_path="materials.db"):
    return sqlite3.connect(str(db_path), check_same_thread=False)


def _ensure_column(conn, table_name, column_name, column_sql):
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table_name})")}
    if column_name not in columns:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")
        conn.commit()


def init_db(db_path="materials.db"):
    """创建素材表(如果不存在),并补齐轻量状态字段。"""
    conn = _connect_db(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            tags TEXT,
            summary TEXT,
            type TEXT,
            source_type TEXT,
            url TEXT,
            created_at TEXT
        )
        """
    )
    _ensure_column(conn, "materials", "ai_status", "ai_status TEXT DEFAULT 'complete'")
    _ensure_column(conn, "materials", "title_source", "title_source TEXT DEFAULT 'user'")
    conn.close()



def _normalize_tags(tags):
    if isinstance(tags, str):
        return [tags]
    if not isinstance(tags, list):
        return []
    return [str(tag).strip() for tag in tags if str(tag).strip()]



def _build_placeholder_title():
    return f"{PLACEHOLDER_TITLE_PREFIX} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"



def _excerpt_summary(content: str, limit: int = 72) -> str:
    text = str(content or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."



def _coerce_title_source(title_source: str, title: str) -> str:
    clean_title = str(title or "").strip()
    if not clean_title:
        return "fallback"
    if title_source in {"user", "fallback", "ai"}:
        return title_source
    if clean_title.startswith(PLACEHOLDER_TITLE_PREFIX):
        return "fallback"
    return "user"



def find_duplicate_material(title, content, db_path="materials.db"):
    init_db(db_path)
    conn = _connect_db(db_path)
    row = conn.execute(
        """
        SELECT id, title, content, created_at
        FROM materials
        WHERE title = ? AND content = ?
        ORDER BY created_at ASC, id ASC
        LIMIT 1
        """,
        (str(title or "").strip(), str(content or "").strip()),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row[0],
        "title": row[1],
        "content": row[2],
        "created_at": row[3],
    }



def _update_material_fields(material_id, fields, db_path="materials.db"):
    if not fields:
        return
    init_db(db_path)
    assignments = ", ".join(f"{column} = ?" for column in fields)
    values = list(fields.values()) + [material_id]
    conn = _connect_db(db_path)
    conn.execute(f"UPDATE materials SET {assignments} WHERE id = ?", values)
    conn.commit()
    conn.close()



def _get_material_by_id(material_id, db_path="materials.db"):
    init_db(db_path)
    conn = _connect_db(db_path)
    row = conn.execute(
        """
        SELECT id, title, content, tags, summary, type, source_type, url, created_at, ai_status, title_source
        FROM materials
        WHERE id = ?
        """,
        (material_id,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row[0],
        "title": row[1],
        "content": row[2],
        "tags": json.loads(row[3]) if row[3] else [],
        "summary": row[4],
        "type": row[5],
        "source_type": row[6],
        "url": row[7],
        "created_at": row[8],
        "ai_status": row[9],
        "title_source": row[10],
    }



def enrich_material(material_id, db_path="materials.db", allow_title_override=False):
    material = _get_material_by_id(material_id, db_path=db_path)
    if not material:
        return False

    analysis = analyze_material(material["content"])
    if analysis.get("error"):
        _update_material_fields(material_id, {"ai_status": "failed"}, db_path=db_path)
        return False

    title = str(analysis.get("title", "") or "").strip()
    tags = _normalize_tags(analysis.get("tags", []))
    summary = str(analysis.get("summary", "") or "").strip() or _excerpt_summary(material["content"])
    material_type = str(analysis.get("type", "") or material.get("type") or "灵感").strip()

    update_fields = {
        "tags": json.dumps(tags, ensure_ascii=False),
        "summary": summary,
        "type": material_type,
        "ai_status": "complete",
    }
    if allow_title_override and title:
        update_fields["title"] = title
        update_fields["title_source"] = "ai"

    _update_material_fields(material_id, update_fields, db_path=db_path)

    latest = _get_material_by_id(material_id, db_path=db_path)
    if latest:
        _upsert_material_index(latest["id"], latest["tags"], latest["summary"], latest["content"])
    return True



def _schedule_material_enrichment(material_id, db_path="materials.db", allow_title_override=False):
    try:
        _enrichment_executor.submit(enrich_material, material_id, db_path, allow_title_override)
    except Exception:
        pass



def save_material(data, db_path="materials.db"):
    """快速存入一条素材,命中重复时拒绝入库,并在后台补全 AI 信息。"""
    init_db(db_path)

    content = str(data.get("content", "") or "").strip()
    if not content:
        return {"error": "没有可存入的素材内容。"}

    clean_title = str(data.get("title", "") or "").strip()
    title_source = _coerce_title_source(str(data.get("title_source", "") or ""), clean_title)
    stored_title = clean_title or _build_placeholder_title()
    duplicate = find_duplicate_material(stored_title, content, db_path=db_path)
    if duplicate:
        return {
            "duplicate": True,
            "id": duplicate["id"],
            "message": "已存在标题和正文完全相同的素材，未重复入库。",
        }

    tags = _normalize_tags(data.get("tags", []))
    summary = str(data.get("summary", "") or "").strip() or _excerpt_summary(content)
    material_type = str(data.get("type", "") or "灵感").strip()
    source_type = str(data.get("source_type", "") or "text").strip()
    url = str(data.get("url", "") or "").strip()
    ai_status = "pending"

    conn = _connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO materials (title, content, tags, summary, type, source_type, url, created_at, ai_status, title_source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            stored_title,
            content,
            json.dumps(tags, ensure_ascii=False),
            summary,
            material_type,
            source_type,
            url,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ai_status,
            title_source,
        ),
    )
    material_id = cursor.lastrowid
    conn.commit()
    conn.close()

    _schedule_material_enrichment(material_id, db_path=db_path, allow_title_override=(title_source != "user"))
    return {
        "id": material_id,
        "duplicate": False,
        "enrichment_pending": True,
    }



def list_materials(db_path="materials.db", limit=50):
    """返回最近存入的素材列表。"""
    init_db(db_path)
    conn = _connect_db(db_path)
    rows = conn.execute(
        """
        SELECT id, title, content, tags, summary, type, source_type, url, created_at, ai_status, title_source
        FROM materials
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()

    result = []
    for row in rows:
        result.append(
            {
                "id": row[0],
                "title": row[1],
                "content": row[2],
                "tags": json.loads(row[3]) if row[3] else [],
                "summary": row[4],
                "type": row[5],
                "source_type": row[6],
                "url": row[7],
                "created_at": row[8],
                "ai_status": row[9],
                "title_source": row[10],
            }
        )
    return result


# ============================================================
# 3. 素材维护操作
# ============================================================

def delete_material(material_id, db_path="materials.db"):
    init_db(db_path)
    conn = _connect_db(db_path)
    cursor = conn.execute("DELETE FROM materials WHERE id = ?", (material_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    if deleted:
        _safe_collection_delete([material_id])
    return deleted



def delete_duplicate_materials(db_path="materials.db"):
    init_db(db_path)
    conn = _connect_db(db_path)
    rows = conn.execute(
        """
        SELECT id, title, content, created_at
        FROM materials
        ORDER BY created_at ASC, id ASC
        """
    ).fetchall()
    seen = set()
    deleted_ids = []
    for row in rows:
        key = (row[1], row[2])
        if key in seen:
            deleted_ids.append(row[0])
        else:
            seen.add(key)

    if deleted_ids:
        placeholders = ",".join("?" for _ in deleted_ids)
        conn.execute(f"DELETE FROM materials WHERE id IN ({placeholders})", deleted_ids)
        conn.commit()
    conn.close()
    _safe_collection_delete(deleted_ids)
    return len(deleted_ids)



def is_single_sentence(content: str) -> bool:
    fragments = [part.strip() for part in re.split(r"[。！？.!?]+", str(content or "").strip()) if part.strip()]
    return len(fragments) == 1



def delete_one_sentence_materials_for_date(target_date="2026-07-16", db_path="materials.db"):
    init_db(db_path)
    conn = _connect_db(db_path)
    rows = conn.execute(
        "SELECT id, content FROM materials WHERE created_at LIKE ?",
        (f"{target_date}%",),
    ).fetchall()
    deleted_ids = [row[0] for row in rows if is_single_sentence(row[1])]
    if deleted_ids:
        placeholders = ",".join("?" for _ in deleted_ids)
        conn.execute(f"DELETE FROM materials WHERE id IN ({placeholders})", deleted_ids)
        conn.commit()
    conn.close()
    _safe_collection_delete(deleted_ids)
    return len(deleted_ids)



def backfill_ai_titles(db_path="materials.db"):
    init_db(db_path)
    materials = list_materials(db_path=db_path, limit=999999)
    updated = 0
    for material in materials:
        title = generate_title_from_content(material["content"])
        if not title or title == material["title"]:
            continue
        _update_material_fields(
            material["id"],
            {"title": title, "title_source": "ai", "ai_status": "complete"},
            db_path=db_path,
        )
        _upsert_material_index(material["id"], material["tags"], material["summary"], material["content"])
        updated += 1
    return updated


# ============================================================
# 4. 🔍 向量相似检索
# ============================================================

def search_materials(keyword, top_k=5):
    """搜索关键词,返回最相似的 Top-K 条素材(按相似度排序)。"""
    try:
        collection = _get_collection()
        results = collection.query(query_texts=[keyword], n_results=top_k)
    except Exception as exc:
        return {"error": str(exc)}

    ids = results.get("ids", [[]])[0]
    distances = results.get("distances", [[]])[0]

    if not ids:
        return {"results": [], "query": keyword}

    materials = list_materials(limit=999999)
    material_map = {str(material["id"]): material for material in materials}

    matches = []
    for index, material_id in enumerate(ids):
        material = material_map.get(str(material_id))
        if not material:
            continue
        matches.append(
            {
                "id": material["id"],
                "title": material["title"],
                "tags": material["tags"],
                "summary": material["summary"],
                "type": material["type"],
                "created_at": material["created_at"],
                "content": material["content"],
                "score": round(1 - distances[index], 3) if distances else 0,
            }
        )

    return {"results": matches, "query": keyword}


# ============================================================
# 5. ✍️ AI 生成初稿
# ============================================================

def generate_draft(topic, material_ids=None, db_path="materials.db"):
    """基于素材库中指定的素材(或最新素材),生成一篇文章初稿。"""
    key = DEEPSEEK_API_KEY
    if not key or key == "请创建config.py并填入API Key":
        return {"error": "请先在 config.py 里填入你的 DeepSeek API Key"}

    client = _get_llm_client(key)
    if client is None:
        return {"error": "请先在 config.py 里填入你的 DeepSeek API Key"}

    all_materials = list_materials(db_path=db_path, limit=999999)
    if material_ids:
        selected = [material for material in all_materials if material["id"] in material_ids]
    else:
        selected = all_materials[:5]

    if not selected:
        return {"error": "没有找到相关素材,请先存入一些素材"}

    material_briefs = []
    for material in selected:
        material_briefs.append(
            f"- [{material['type']}] {material['summary']} (标签: {' '.join(material['tags'])})"
        )

    context = "\n".join(material_briefs)

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是一个专业的内容创作者。用户会给你一个主题和一组相关素材,"
                        "请基于这些素材写一篇结构清晰的文章初稿。\n"
                        "要求:\n"
                        "1. 有一个吸引人的标题\n"
                        "2. 开头简要引入主题\n"
                        "3. 正文分2-3个小标题展开\n"
                        "4. 结尾有简短总结\n"
                        "5. 如果素材不足以覆盖主题,可以适当补充常识性知识\n"
                        "总字数控制在400-800字。"
                    ),
                },
                {"role": "user", "content": f"主题: {topic}\n\n可用素材:\n{context}"},
            ],
            temperature=0.7,
            max_tokens=1500,
        )

        draft = response.choices[0].message.content.strip()
        return {
            "draft": draft,
            "topic": topic,
            "used_materials": [{"id": material["id"], "summary": material["summary"]} for material in selected],
        }
    except Exception as exc:
        return {"error": str(exc)}


# ============================================================
# 6. 重建索引
# ============================================================

def rebuild_index(db_path="materials.db"):
    """把 SQLite 里所有素材重新索引到 Chroma。"""
    materials = list_materials(db_path=db_path, limit=999999)
    count = 0
    for material in materials:
        _upsert_material_index(material["id"], material["tags"], material["summary"], material["content"])
        count += 1
    return {"indexed": count}
