from ingestion import fetch_url, parse_text, parse_image

print("=" * 60)
print("测试1: fetch_url (抓取网页)")
print("=" * 60)
result = fetch_url('https://example.com')
if 'error' in result:
    print(f"错误: {result['error']}")
else:
    print(f"标题: {result['title']}")
    print(f"来源: {result['url']}")
    print("-" * 50)
    print(f"正文: {result['content']}")

print("\n" + "=" * 60)
print("测试2: parse_text (清洗文本)")
print("=" * 60)
result = parse_text('  用户粘贴的文字\n\n包含多余空行  ')
print(f"标题: {result['title']}")
print("-" * 50)
print(f"清洗后内容:\n{result['content']}")

print("\n" + "=" * 60)
print("测试3: parse_image (图片OCR)")
print("=" * 60)

baidu_config = {
    'api_key': '',
    'secret_key': ''
}

ali_config = {
    'access_key_id': '',
    'access_key_secret': ''
}

result = parse_image('test.jpg', baidu_config=baidu_config, ali_config=ali_config)
if 'error' in result:
    print(f"错误: {result['error']}")
else:
    print(f"标题: {result['title']}")
    print(f"OCR方法: {result['ocr_method']}")
    print("-" * 50)
    print(f"识别内容:\n{result['content']}")