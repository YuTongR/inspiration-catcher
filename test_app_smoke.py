from pathlib import Path


def test_app_contains_new_dashboard_copy():
    source = Path("app.py").read_text(encoding="utf-8")

    assert "灵感捕手" in source
    assert "Inspiration Catcher" in source
    assert '创作者的 AI 素材管家 —— 让收藏夹从"吃灰"变成"第二大脑"' in source
    assert "存入一段灵感碎片" in source
    assert "输入建议" in source
    assert "推荐素材" in source
    assert "当前预览" in source
    assert "素材知识库" in source
    assert "存入素材库" in source


def test_app_contains_new_sidebar_and_warm_ui_classes():
    source = Path("app.py").read_text(encoding="utf-8")

    assert "sidebar-nav" in source
    assert "nav-indicator" in source
    assert "quick-capture-input" in source
    assert "info-panel" in source
    assert "library-card" in source
    assert "sample_materials" in source


def test_app_drops_old_copy_and_keeps_clean_demo_language():
    source = Path("app.py").read_text(encoding="utf-8")

    assert "今天先收下一段回忆碎片" not in source
    assert "A/B" not in source
    assert "Memory Intake · Day 1" not in source


def test_app_contains_search_page_markers():
    source = Path("app.py").read_text(encoding="utf-8")

    assert "智能检索" in source
    assert "搜索" in source
    assert "搜索结果" in source
    assert "search_materials" in source


def test_app_contains_draft_page_markers():
    source = Path("app.py").read_text(encoding="utf-8")

    assert "生成初稿" in source
    assert "初稿主题" in source
    assert "generate_draft" in source
    assert "使用了哪些素材" in source
    assert "复制初稿" in source
