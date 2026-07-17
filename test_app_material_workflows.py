import importlib
import sys
from pathlib import Path
from types import ModuleType


def load_app_module():
    sys.modules.pop("app", None)
    return importlib.import_module("app")


def test_save_material_uses_explicit_title_and_preserves_it(monkeypatch):
    app = load_app_module()
    captured = {}

    def fake_persist(payload):
        captured["payload"] = payload
        return True, "ok"

    monkeypatch.setattr(app, "persist_material_payload", fake_persist)

    saved, message = app.save_material("婚礼当天", "婚礼当天我突然想起外婆说的话。")

    assert saved is True
    assert message == "ok"
    assert captured["payload"]["title"] == "婚礼当天"
    assert captured["payload"]["content"] == "婚礼当天我突然想起外婆说的话。"


def test_save_material_without_title_uses_placeholder_instead_of_content_prefix(monkeypatch):
    app = load_app_module()
    captured = {}

    def fake_persist(payload):
        captured["payload"] = payload
        return True, "ok"

    monkeypatch.setattr(app, "persist_material_payload", fake_persist)

    saved, _ = app.save_material("", "这是一个很长的正文内容，不应该再被前十六个字拿去当正式标题。")

    assert saved is True
    assert captured["payload"]["title"].startswith("未命名素材")
    assert "这是一个很长的正文内容" not in captured["payload"]["title"]


def test_resolve_draft_candidates_prefers_topic_relevant_materials(monkeypatch):
    app = load_app_module()
    fake_agent = ModuleType("agent")
    fake_agent.search_materials = lambda topic, top_k=8: {
        "results": [
            {
                "id": 2,
                "title": "AI 教育案例",
                "summary": "关于 AI 改变课堂反馈的案例",
                "tags": ["#AI", "#教育"],
                "type": "案例",
                "created_at": "2026-07-16 09:00:00",
                "score": 0.95,
            }
        ]
    }
    monkeypatch.setitem(sys.modules, "agent", fake_agent)

    candidates, error = app.resolve_draft_candidates("AI 教育")

    assert error == ""
    assert [item["title"] for item in candidates] == ["AI 教育案例"]


def test_app_source_contains_title_input_and_library_actions():
    source = Path(__file__).with_name("app.py").read_text(encoding="utf-8")

    assert "素材标题" in source
    assert "查看详情" in source
    assert "确认删除" in source
    assert "删除" in source


def test_text_capture_uses_single_top_level_material_title_field():
    source = Path(__file__).with_name("app.py").read_text(encoding="utf-8")

    assert '<div class="quick-capture-input">素材标题</div>' in source
    assert '"快速定位"' not in source
    assert 'st.text_input(\n                "素材标题",\n                key="material_title",\n                placeholder="例如：奶奶在院子门口等家人回来",\n            )' not in source
    assert 'height=368' in source