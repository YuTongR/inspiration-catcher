import importlib
import subprocess
import sys
from types import ModuleType

from streamlit.testing.v1 import AppTest


def build_fake_agent():
    fake_agent = ModuleType("agent")
    fake_agent.list_materials = lambda limit=50: [
        {
            "id": 1,
            "title": "AI 市场观察",
            "summary": "关于 AI 市场的数据摘要",
            "tags": ["#AI", "#市场"],
            "type": "数据",
            "created_at": "2026-07-16 10:03:01",
        },
        {
            "id": 2,
            "title": "数据库缓存策略",
            "summary": "数据库缓存的常见设计方式",
            "tags": ["#缓存", "#数据库"],
            "type": "教程",
            "created_at": "2026-07-16 10:07:19",
        },
    ]
    fake_agent.save_material = lambda data: 3
    fake_agent.search_materials = lambda keyword, top_k=5: {"results": [], "query": keyword}
    fake_agent.generate_draft = lambda topic, material_ids=None: {
        "draft": "示例初稿",
        "used_materials": [{"id": 1, "summary": "关于 AI 市场的数据摘要"}],
    }
    return fake_agent


def load_app_module():
    sys.modules.pop("app", None)
    return importlib.import_module("app")


def test_library_filters_do_not_reset_current_page(monkeypatch):
    monkeypatch.setitem(sys.modules, "agent", build_fake_agent())

    app_test = AppTest.from_file("app.py")
    app_test.run()
    app_test.radio[0].set_value("素材知识库").run()

    app_test.multiselect[0].set_value(["#AI"]).run()

    assert app_test.session_state["page"] == "素材知识库"
    assert app_test.radio[0].value == "素材知识库"


def test_draft_material_picker_does_not_reset_current_page(monkeypatch):
    monkeypatch.setitem(sys.modules, "agent", build_fake_agent())

    app_test = AppTest.from_file("app.py")
    app_test.run()
    app_test.radio[0].set_value("生成初稿").run()

    first_option = list(app_test.multiselect[0].options)[:1]
    app_test.multiselect[0].set_value(first_option).run()

    assert app_test.session_state["page"] == "生成初稿"
    assert app_test.radio[0].value == "生成初稿"


def test_search_materials_limits_backend_wait_before_fallback(monkeypatch):
    app = load_app_module()

    monkeypatch.setattr(
        app,
        "load_materials_from_backend",
        lambda fallback_to_demo=False: [
            {
                "id": 1,
                "title": "AI 市场观察",
                "summary": "关于 AI 市场的数据摘要",
                "tags": ["#AI"],
                "type": "数据",
                "date": "2026-07-16",
            }
        ],
    )

    captured = {}

    def fake_run(*args, **kwargs):
        captured["timeout"] = kwargs["timeout"]
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs["timeout"])

    monkeypatch.setattr(app.subprocess, "run", fake_run)
    app.st.session_state.search_backend_retry_after = 0.0

    results, message = app.search_materials("AI")

    assert captured["timeout"] <= 2
    assert results
    assert "关键词匹配结果" in message


def test_search_materials_fallback_matches_content_text(monkeypatch):
    app = load_app_module()

    monkeypatch.setattr(
        app,
        "load_materials_from_backend",
        lambda fallback_to_demo=False: [
            {
                "id": 3,
                "title": "图片识别内容",
                "summary": "这是一段摘要，不包含关键词。",
                "content": "傍晚的风穿过楼宇之间，带走白日积攒的燥热。",
                "tags": ["日常"],
                "type": "图片",
                "date": "2026-07-16",
            }
        ],
    )

    monkeypatch.setattr(
        app.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs["timeout"])),
    )
    app.st.session_state.search_backend_retry_after = 0.0

    results, message = app.search_materials("傍晚")

    assert [item["title"] for item in results] == ["图片识别内容"]
    assert "关键词匹配结果" in message


def test_resolve_search_state_treats_fallback_message_as_notice(monkeypatch):
    app = load_app_module()

    monkeypatch.setattr(
        app,
        "search_materials",
        lambda query: ([{"title": "AI 市场观察", "tags": ["#AI"], "summary": "摘要", "type": "数据", "score": 117}], "向量检索仍在初始化，当前先展示本地关键词匹配结果。"),
    )

    results, error, notice = app.resolve_search_state("AI")

    assert [item["title"] for item in results] == ["AI 市场观察"]
    assert error == ""
    assert "关键词匹配结果" in notice


def test_resolve_search_state_keeps_message_as_error_without_results(monkeypatch):
    app = load_app_module()

    monkeypatch.setattr(app, "search_materials", lambda query: ([], "没有找到相关素材。你可以换一个关键词试试。"))

    results, error, notice = app.resolve_search_state("不存在")

    assert results == []
    assert "没有找到相关素材" in error
    assert notice == ""

def test_library_detail_state_clears_after_leaving_library_page(monkeypatch):
    monkeypatch.setitem(sys.modules, "agent", build_fake_agent())

    app = load_app_module()
    app.st.session_state.library_detail_material_id = "1"

    app.sync_library_detail_state("智能检索")

    assert app.st.session_state.library_detail_material_id is None


def test_delete_dialog_state_suppresses_detail_dialog_state(monkeypatch):
    monkeypatch.setitem(sys.modules, "agent", build_fake_agent())

    app = load_app_module()

    detail_id, delete_id = app.resolve_library_modal_state("素材知识库", "1", "2")

    assert detail_id is None
    assert delete_id == "2"