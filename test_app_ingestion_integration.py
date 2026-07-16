import importlib
import sys
from pathlib import Path
from types import ModuleType


def load_app_module():
    sys.modules.pop("app", None)
    return importlib.import_module("app")


def test_save_ingested_material_builds_backend_payload(monkeypatch):
    app = load_app_module()
    captured = {}

    def fake_save_material(payload):
        captured["payload"] = payload
        return 9

    fake_agent = ModuleType("agent")
    fake_agent.save_material = fake_save_material
    fake_agent.list_materials = lambda limit=50: []
    monkeypatch.setitem(sys.modules, "agent", fake_agent)

    saved, message = app.save_ingested_material(
        {
            "title": "网页标题",
            "content": "这是一段用于测试的网页正文内容。",
            "source_type": "url",
            "url": "https://example.com/post",
        }
    )

    assert saved is True
    assert message == "已成功存入素材库。"
    assert captured["payload"] == {
        "title": "网页标题",
        "content": "这是一段用于测试的网页正文内容。",
        "tags": ["日常"],
        "summary": "这是一段用于测试的网页正文内容。",
        "type": "文章",
        "source_type": "url",
        "url": "https://example.com/post",
    }


def test_ingest_url_material_uses_fetch_url_and_persists_result(monkeypatch):
    app = load_app_module()

    monkeypatch.setattr(
        app,
        "fetch_url",
        lambda url: {
            "title": "抓取结果",
            "content": "抓取到的正文",
            "source_type": "url",
            "url": url,
        },
        raising=False,
    )
    monkeypatch.setattr(app, "save_ingested_material", lambda record: (record["title"] == "抓取结果", "已成功存入素材库。"))

    saved, message = app.ingest_url_material("https://example.com/article")

    assert saved is True
    assert message == "已成功存入素材库。"


def test_ingest_uploaded_image_calls_parse_image_with_temp_file(monkeypatch, tmp_path):
    app = load_app_module()
    observed = {}

    class FakeUpload:
        name = "note.png"

        def getvalue(self):
            return b"fake-image-bytes"

    def fake_parse_image(path, ocr_api_key=None, baidu_config=None, ali_config=None):
        observed["path"] = path
        observed["exists_during_parse"] = Path(path).exists()
        return {
            "title": "图片识别内容",
            "content": "识别出的文字",
            "source_type": "image",
        }

    monkeypatch.setattr(app, "parse_image", fake_parse_image, raising=False)
    monkeypatch.setattr(app, "save_ingested_material", lambda record: (record["content"] == "识别出的文字", "已成功存入素材库。"))
    monkeypatch.setattr(app.tempfile, "gettempdir", lambda: str(tmp_path))

    saved, message = app.ingest_uploaded_image(FakeUpload())

    assert saved is True
    assert message == "已成功存入素材库。"
    assert observed["exists_during_parse"] is True
    assert Path(observed["path"]).exists() is False
