import json
import sqlite3
from datetime import datetime
from openai import OpenAI

# ============================================================
# 配置
# ============================================================
try:
    from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
except ImportError:
    DEEPSEEK_API_KEY = ""
    DEEPSEEK_BASE_URL = "https://api.deepseek.com"

_llm_client = None

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
import chromadb
from chromadb.utils import embedding_functions

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


def _index_to_chroma(material_id, tags, summary, content):
    """把一条素材的文本向量化后存入 Chroma,供搜索用"""
    search_text = f"{' '.join(tags)} {summary} {content[:1000]}"
    try:
        collection = _get_collection()
        collection.add(
            documents=[search_text],
            metadatas=[{"id": material_id}],
            ids=[str(material_id)],
        )
    except Exception:
        pass  # 如果已存在就跳过


# ============================================================
# 1. AI 分析素材:打标签 + 写摘要 + 分类
# ============================================================
def analyze_material(content, api_key=None):
    """输入原始文本,返回 {tags, summary, type}"""
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
                        "1. 生成一个10-20字的标题(提炼核心主题,不要用'一篇关于'开头)\n"
                        "2. 生成3-5个中文标签(以#开头,如 #用户增长 #案例分析)\n"
                        "3. 写一句50字以内的中文摘要\n"
                        "4. 判断素材类型(文章/灵感/数据/案例/教程)\n"
                        "只返回JSON格式,不要任何额外文字。\n"
                        '例: {"title":"Python列表推导式入门","tags":["#Python","#教程"],"summary":"Python列表推导式是简洁创建列表的方式","type":"教程"}'
                    ),
                },
                {"role": "user", "content": content[:4000]},
            ],
            temperature=0.3,
            max_tokens=500,
        )

        result_text = response.choices[0].message.content.strip()
        if result_text.startswith("```"):
            result_text = result_text.split("\n", 1)[1]
            if result_text.endswith("```"):
                result_text = result_text[:-3]

        return json.loads(result_text)

    except Exception as e:
        return {"error": str(e)}


# ============================================================
# 2. SQLite 数据库操作
# ============================================================
def init_db(db_path="materials.db"):
    """创建素材表(如果不存在)"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
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
    """)
    conn.commit()
    conn.close()


def save_material(data, db_path="materials.db"):
    """存入一条素材,同时索引到向量库"""
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(
        """INSERT INTO materials (title, content, tags, summary, type, source_type, url, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data.get("title", ""),
            data.get("content", ""),
            json.dumps(data.get("tags", []), ensure_ascii=False),
            data.get("summary", ""),
            data.get("type", ""),
            data.get("source_type", "text"),
            data.get("url", ""),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    material_id = c.lastrowid
    conn.commit()
    conn.close()

    _index_to_chroma(material_id, data.get("tags", []), data.get("summary", ""), data.get("content", ""))
    return material_id


def list_materials(db_path="materials.db", limit=50):
    """返回最近存入的素材列表"""
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT * FROM materials ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()

    result = []
    for r in rows:
        result.append({
            "id": r[0],
            "title": r[1],
            "content": r[2],
            "tags": json.loads(r[3]) if r[3] else [],
            "summary": r[4],
            "type": r[5],
            "source_type": r[6],
            "url": r[7],
            "created_at": r[8],
        })
    return result


def delete_material(material_id, db_path="materials.db"):
    """根据 ID 删除一条素材(SQLite + Chroma)"""
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM materials WHERE id = ?", (material_id,))
    conn.commit()
    conn.close()
    try:
        collection = _get_collection()
        collection.delete(ids=[str(material_id)])
    except Exception:
        pass
    return True


def preload():
    """预热:提前加载向量模型,让后续操作秒响应"""
    _get_collection()
    _get_llm_client()


# ============================================================
# 3. 🔍 向量相似检索(新增!)
# ============================================================
def search_materials(keyword, top_k=5):
    """搜索关键词,返回最相似的 Top-K 条素材(按相似度排序)"""
    try:
        collection = _get_collection()
        results = collection.query(query_texts=[keyword], n_results=top_k)
    except Exception as e:
        return {"error": str(e)}

    ids = results.get("ids", [[]])[0]
    distances = results.get("distances", [[]])[0]

    if not ids:
        return {"results": [], "query": keyword}

    materials = list_materials(limit=999)
    material_map = {str(m["id"]): m for m in materials}

    matches = []
    for i, mid in enumerate(ids):
        m = material_map.get(mid)
        if m:
            matches.append({
                "id": m["id"],
                "title": m["title"],
                "tags": m["tags"],
                "summary": m["summary"],
                "type": m["type"],
                "created_at": m["created_at"],
                "score": round(1 - distances[i], 3) if distances else 0,
            })

    # 过滤低相关度结果(相似度 < 0.25 的不显示)
    matches = [m for m in matches if m["score"] >= 0.25]
    matches.sort(key=lambda x: x["score"], reverse=True)

    return {"results": matches, "query": keyword}


# ============================================================
# 4. ✍️ AI 生成初稿(新增!)
# ============================================================
def generate_draft(topic, material_ids=None, db_path="materials.db"):
    """基于素材库中指定的素材(或最新素材),生成一篇文章初稿"""
    if material_ids:
        all_materials = list_materials(limit=999)
        selected = [m for m in all_materials if m["id"] in material_ids]
    else:
        selected = list_materials(limit=5)

    if not selected:
        return {"error": "没有找到相关素材,请先存入一些素材"}

    material_briefs = []
    for m in selected:
        material_briefs.append(f"- [{m['type']}] {m['summary']} (标签: {' '.join(m['tags'])})")

    context = "\n".join(material_briefs)

    llm_client = _get_llm_client()
    if llm_client is None:
        return {"error": "请先在 config.py 里填入 DeepSeek API Key"}

    try:
        response = llm_client.chat.completions.create(
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
            "used_materials": [{"id": m["id"], "summary": m["summary"]} for m in selected],
        }

    except Exception as e:
        return {"error": str(e)}


# ============================================================
# 5. 重建索引(把已有素材全同步到向量库)
# ============================================================
def rebuild_index():
    """把 SQLite 里所有素材重新索引到 Chroma"""
    materials = list_materials(limit=999)
    count = 0
    for m in materials:
        _index_to_chroma(m["id"], m["tags"], m["summary"], m["content"])
        count += 1
    return {"indexed": count}




