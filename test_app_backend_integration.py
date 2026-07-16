import importlib
import subprocess
import sys
from types import ModuleType


def load_app_module():
    sys.modules.pop("app", None)
    return importlib.import_module("app")


def test_load_materials_from_backend_prefers_agent_results(monkeypatch):
    app = load_app_module()
    backend_materials = [
        {
            "id": 101,
            "title": "后端素材",
            "summary": "来自 materials.db 的真实记录",
            "tags": ["AI"],
            "type": "案例",
            "created_at": "2026-07-16 10:00:00",
        }
    ]
    fake_agent = ModuleType("agent")
    fake_agent.list_materials = lambda limit=50: backend_materials

    monkeypatch.setitem(sys.modules, "agent", fake_agent)

    materials = app.load_materials_from_backend()

    assert materials == [
        {
            "id": 101,
            "title": "后端素材",
            "summary": "来自 materials.db 的真实记录",
            "content": "",
            "tags": ["AI"],
            "type": "案例",
            "date": "2026-07-16",
            "created_at": "2026-07-16 10:00:00",
        }
    ]


def test_search_materials_timeout_falls_back_to_backend_materials(monkeypatch):
    app = load_app_module()

    monkeypatch.setattr(
        app,
        "load_materials_from_backend",
        lambda fallback_to_demo=True: [
            {
                "id": 7,
                "title": "AI 创作工作流",
                "summary": "记录 AI 内容生产流程",
                "tags": ["AI", "工作流"],
                "type": "教程",
                "date": "2026-07-16",
            }
        ],
    )
    app.st.session_state.materials = [
        {
            "title": "无关示例",
            "summary": "和查询词不匹配",
            "tags": ["日常"],
            "type": "灵感",
            "date": "2026-07-16",
        }
    ]

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=kwargs.get("args", ["python"]), timeout=20)

    monkeypatch.setattr(app.subprocess, "run", fake_run)

    results, message = app.search_materials("AI")

    assert [item["title"] for item in results] == ["AI 创作工作流"]
    assert "关键词匹配结果" in message
