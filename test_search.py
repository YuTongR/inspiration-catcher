from types import SimpleNamespace

import agent


def test_search_materials_maps_collection_results_to_material_rows(monkeypatch):
    fake_collection = SimpleNamespace(
        query=lambda query_texts, n_results: {
            "ids": [["2", "1"]],
            "distances": [[0.1, 0.35]],
        }
    )
    fake_materials = [
        {
            "id": 1,
            "title": "AI 市场观察",
            "tags": ["#AI"],
            "summary": "关于 AI 市场的数据摘要",
            "type": "数据",
            "created_at": "2026-07-16 10:03:01",
        },
        {
            "id": 2,
            "title": "数据库缓存策略",
            "tags": ["#Redis", "#缓存"],
            "summary": "数据库缓存的常见设计方式",
            "type": "教程",
            "created_at": "2026-07-16 10:07:19",
        },
    ]

    monkeypatch.setattr(agent, "_get_collection", lambda: fake_collection)
    monkeypatch.setattr(agent, "list_materials", lambda limit=999: fake_materials)

    result = agent.search_materials("数据库缓存", top_k=2)

    assert result["query"] == "数据库缓存"
    assert result["results"] == [
        {
            "id": 2,
            "title": "数据库缓存策略",
            "tags": ["#Redis", "#缓存"],
            "summary": "数据库缓存的常见设计方式",
            "type": "教程",
            "created_at": "2026-07-16 10:07:19",
            "score": 0.9,
        },
        {
            "id": 1,
            "title": "AI 市场观察",
            "tags": ["#AI"],
            "summary": "关于 AI 市场的数据摘要",
            "type": "数据",
            "created_at": "2026-07-16 10:03:01",
            "score": 0.65,
        },
    ]
