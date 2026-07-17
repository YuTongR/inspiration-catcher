import sqlite3
from pathlib import Path
from uuid import uuid4

import agent


ROOT_DIR = Path(r"D:\48")


def create_db(db_path: Path, rows: list[tuple]) -> None:
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            tags TEXT,
            summary TEXT,
            type TEXT,
            source_type TEXT,
            url TEXT,
            created_at TEXT,
            ai_status TEXT DEFAULT 'complete',
            title_source TEXT DEFAULT 'user'
        )
        """
    )
    conn.executemany(
        """
        INSERT INTO materials (title, content, tags, summary, type, source_type, url, created_at, ai_status, title_source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'complete', 'user')
        """,
        rows,
    )
    conn.commit()
    conn.close()


def build_db_path(name: str) -> Path:
    return ROOT_DIR / f"{name}-{uuid4().hex}.db"


def test_save_material_rejects_duplicate_title_and_content(monkeypatch):
    db_path = build_db_path("materials-duplicate")
    try:
        create_db(
            db_path,
            [
                ("婚礼回忆", "今天想起婚礼那天的光。", "[]", "", "灵感", "text", "", "2026-07-16 09:00:00"),
            ],
        )
        monkeypatch.setattr(agent, "_schedule_material_enrichment", lambda *args, **kwargs: None)

        result = agent.save_material(
            {
                "title": "婚礼回忆",
                "content": "今天想起婚礼那天的光。",
                "tags": [],
                "summary": "",
                "type": "灵感",
                "source_type": "text",
                "url": "",
            },
            db_path=str(db_path),
        )

        assert result["duplicate"] is True
        assert len(agent.list_materials(db_path=str(db_path), limit=20)) == 1
    finally:
        db_path.unlink(missing_ok=True)


def test_delete_duplicate_materials_keeps_earliest_record(monkeypatch):
    db_path = build_db_path("materials-dedup")
    try:
        create_db(
            db_path,
            [
                ("同名素材", "完全相同的正文", "[]", "", "灵感", "text", "", "2026-07-16 09:00:00"),
                ("同名素材", "完全相同的正文", "[]", "", "灵感", "text", "", "2026-07-16 10:00:00"),
                ("不同标题", "完全相同的正文", "[]", "", "灵感", "text", "", "2026-07-16 11:00:00"),
            ],
        )
        monkeypatch.setattr(agent, "_safe_collection_delete", lambda material_ids: None)

        deleted = agent.delete_duplicate_materials(db_path=str(db_path))
        materials = agent.list_materials(db_path=str(db_path), limit=20)

        assert deleted == 1
        assert [(item["title"], item["content"], item["created_at"]) for item in materials] == [
            ("不同标题", "完全相同的正文", "2026-07-16 11:00:00"),
            ("同名素材", "完全相同的正文", "2026-07-16 09:00:00"),
        ]
    finally:
        db_path.unlink(missing_ok=True)


def test_delete_one_sentence_materials_for_2026_07_16_only_removes_matching_rows(monkeypatch):
    db_path = build_db_path("materials-cleanup")
    try:
        create_db(
            db_path,
            [
                ("测试一句话", "这是一句测试。", "[]", "", "灵感", "text", "", "2026-07-16 10:00:00"),
                ("旧一句话", "这是一句旧记录。", "[]", "", "灵感", "text", "", "2026-07-15 10:00:00"),
                ("今天多句", "第一句。第二句。", "[]", "", "灵感", "text", "", "2026-07-16 10:00:00"),
            ],
        )
        monkeypatch.setattr(agent, "_safe_collection_delete", lambda material_ids: None)

        deleted = agent.delete_one_sentence_materials_for_date("2026-07-16", db_path=str(db_path))
        materials = agent.list_materials(db_path=str(db_path), limit=20)

        assert deleted == 1
        assert [(item["title"], item["created_at"]) for item in materials] == [
            ("今天多句", "2026-07-16 10:00:00"),
            ("旧一句话", "2026-07-15 10:00:00"),
        ]
    finally:
        db_path.unlink(missing_ok=True)


def test_delete_material_removes_sqlite_row_and_chroma_document(monkeypatch):
    db_path = build_db_path("materials-delete")
    try:
        create_db(
            db_path,
            [
                ("要删除的素材", "正文", "[]", "", "灵感", "text", "", "2026-07-16 10:00:00"),
            ],
        )
        deleted_ids = []
        monkeypatch.setattr(agent, "_safe_collection_delete", lambda ids: deleted_ids.extend([str(item) for item in ids]))

        deleted = agent.delete_material(1, db_path=str(db_path))

        assert deleted is True
        assert deleted_ids == ["1"]
        assert agent.list_materials(db_path=str(db_path), limit=20) == []
    finally:
        db_path.unlink(missing_ok=True)


def test_backfill_ai_titles_updates_existing_titles(monkeypatch):
    db_path = build_db_path("materials-titles")
    try:
        create_db(
            db_path,
            [
                ("今天想起奶奶在院子里", "今天想起奶奶在院子里等家人回来的样子。", "[]", "", "灵感", "text", "", "2026-07-15 10:00:00"),
            ],
        )
        monkeypatch.setattr(agent, "generate_title_from_content", lambda content, api_key=None: "奶奶在院子里等家人")
        monkeypatch.setattr(agent, "_upsert_material_index", lambda material_id, tags, summary, content: None)

        updated = agent.backfill_ai_titles(db_path=str(db_path))
        materials = agent.list_materials(db_path=str(db_path), limit=20)

        assert updated == 1
        assert materials[0]["title"] == "奶奶在院子里等家人"
    finally:
        db_path.unlink(missing_ok=True)
