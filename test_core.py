#!/usr/bin/env python3
import sys
sys.path.append('..')
from ingestion import fetch_url, parse_text, parse_image, ingest_batch

print("=" * 60)
print("核心功能测试")
print("=" * 60)

print("\n1. 测试 fetch_url (网页抓取)")
print("-" * 40)
try:
    result = fetch_url("https://example.com")
    if 'error' in result:
        print(f"✗ 失败: {result['error']}")
    else:
        print(f"✓ 成功获取网页")
        print(f"  标题: {result['title'][:50]}...")
        print(f"  正文长度: {len(result['content'])} 字符")
        print(f"  来源类型: {result['source_type']}")
except Exception as e:
    print(f"✗ 异常: {e}")

print("\n2. 测试 parse_text (文本清洗)")
print("-" * 40)
try:
    test_text = "  这是一段测试文本，包含各种符号！@#$%^&*()。\n\n还有换行符和多余空格。  "
    result = parse_text(test_text)
    if 'error' in result:
        print(f"✗ 失败: {result['error']}")
    else:
        print(f"✓ 成功清洗文本")
        print(f"  原始长度: {len(test_text)}")
        print(f"  清洗后长度: {len(result['content'])}")
        print(f"  标题: {result['title']}")
except Exception as e:
    print(f"✗ 异常: {e}")

print("\n3. 测试 ingest_batch (批量处理)")
print("-" * 40)
try:
    inputs = [
        {"type": "text", "value": "这是一段测试文本内容"},
        {"type": "url", "value": "https://example.com"}
    ]
    results = ingest_batch(inputs)
    print(f"✓ 成功处理 {len(results)} 个输入")
    for i, r in enumerate(results):
        if 'error' in r:
            print(f"  输入 {i+1}: 类型={r.get('type', 'unknown')}, 错误={r['error']}")
        else:
            print(f"  输入 {i+1}: 类型={r.get('source_type', 'unknown')}, 标题={r.get('title', '')[:30]}...")
except Exception as e:
    print(f"✗ 异常: {e}")

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
