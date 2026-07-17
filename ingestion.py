#test
import requests
from bs4 import BeautifulSoup
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def fetch_url(url: str) -> dict:
    try:
        if not url.lower().startswith(('http://', 'https://')):
            return {'error': '抓取失败: URL格式不正确'}

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0'
        }

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        content_type = response.headers.get('Content-Type', '').lower()
        if 'text/html' not in content_type:
            if 'application/pdf' in content_type:
                return {'error': '抓取失败: 不支持PDF文件，请使用其他工具处理'}
            if 'image/' in content_type:
                return {'error': '抓取失败: 不支持图片链接，请使用parse_image处理'}
            return {'error': f'抓取失败: 非HTML内容 ({content_type})'}

        try:
            html_text = response.content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                html_text = response.content.decode('gbk')
            except UnicodeDecodeError:
                try:
                    html_text = response.content.decode('gb2312')
                except UnicodeDecodeError:
                    html_text = response.content.decode(response.apparent_encoding or 'utf-8', errors='replace')
        
        soup = BeautifulSoup(html_text, 'html.parser')

        title = ''
        if soup.title:
            title = soup.title.string.strip() if soup.title.string else ''
        else:
            og_title = soup.find('meta', property='og:title')
            if og_title:
                title = og_title.get('content', '').strip()

        content_parts = []
        for p in soup.find_all('p'):
            text = p.get_text(strip=True)
            if text:
                content_parts.append(text)

        if not content_parts:
            article_tag = soup.find('article')
            if article_tag:
                for tag in article_tag.find_all(['p', 'h1', 'h2', 'h3', 'div']):
                    text = tag.get_text(strip=True)
                    if text and len(text) > 5:
                        content_parts.append(text)

        if not content_parts:
            body_tag = soup.find('body')
            if body_tag:
                for tag in body_tag.find_all(['p', 'div', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                    text = tag.get_text(strip=True)
                    if text and len(text) > 5:
                        content_parts.append(text)

        if not content_parts:
            text_content = soup.get_text(separator='\n')
            lines = [line.strip() for line in text_content.split('\n') if line.strip()]
            content_parts = lines

        content = '\n\n'.join(content_parts)

        return {
            'title': title,
            'content': content,
            'source_type': 'url',
            'url': url
        }

    except requests.exceptions.Timeout:
        return {'error': '抓取失败: 请求超时，请稍后重试'}
    except requests.exceptions.ConnectionError:
        return {'error': '抓取失败: 网络连接失败，请检查网络'}
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else 0
        if status_code == 403:
            return {'error': '抓取失败: 403禁止访问，可能被反爬机制拦截'}
        elif status_code == 404:
            return {'error': '抓取失败: 404页面不存在'}
        elif 500 <= status_code < 600:
            return {'error': f'抓取失败: 服务器错误 ({status_code})'}
        else:
            return {'error': f'抓取失败: HTTP错误 ({status_code})'}
    except requests.exceptions.RequestException as e:
        return {'error': f'抓取失败: 请求异常 ({str(e)})'}
    except Exception as e:
        return {'error': f'抓取失败: {str(e)}'}


def parse_text(text: str) -> dict:
    lines = text.split('\n')
    cleaned_lines = [line.strip() for line in lines]
    filtered_lines = [line for line in cleaned_lines if line]
    content = '\n'.join(filtered_lines)
    return {
        'title': '用户输入的素材',
        'content': content,
        'source_type': 'text'
    }


def preprocess_image(image):
    from PIL import Image, ImageEnhance, ImageFilter

    img = image.convert('L')

    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)

    img = img.filter(ImageFilter.SHARPEN)

    threshold = 128
    img = img.point(lambda x: 255 if x > threshold else 0)

    return img


def baidu_ocr(image_path: str, api_key: str, secret_key: str) -> str:
    import base64
    import json

    token_url = 'https://aip.baidubce.com/oauth/2.0/token'
    token_params = {
        'grant_type': 'client_credentials',
        'client_id': api_key,
        'client_secret': secret_key
    }
    token_response = requests.post(token_url, data=token_params, timeout=30)
    token_result = token_response.json()
    if 'access_token' not in token_result:
        raise Exception(f'获取token失败: {token_result.get("error_description", "未知错误")}')
    access_token = token_result['access_token']

    ocr_url = 'https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic'
    with open(image_path, 'rb') as f:
        base64_image = base64.b64encode(f.read()).decode('utf-8')

    ocr_params = {
        'image': base64_image,
        'language_type': 'CHN_ENG',
        'detect_direction': 'true',
        'detect_language': 'true'
    }
    ocr_response = requests.post(ocr_url, data=ocr_params, params={'access_token': access_token}, timeout=30)
    ocr_result = ocr_response.json()

    if 'words_result' not in ocr_result:
        raise Exception(f'OCR识别失败: {ocr_result.get("error_msg", "未知错误")}')

    return '\n'.join(item['words'] for item in ocr_result['words_result'])


def ali_ocr(image_path: str, access_key_id: str, access_key_secret: str) -> str:
    import base64
    import json
    from datetime import datetime
    import hmac
    import hashlib
    import urllib.parse

    with open(image_path, 'rb') as f:
        base64_image = base64.b64encode(f.read()).decode('utf-8')

    now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    endpoint = 'ocr.cn-hangzhou.aliyuncs.com'
    api_version = '2019-12-30'
    api_action = 'RecognizeText'

    params = {
        'Format': 'JSON',
        'Version': api_version,
        'AccessKeyId': access_key_id,
        'SignatureMethod': 'HMAC-SHA256',
        'Timestamp': now,
        'SignatureVersion': '1.0',
        'Action': api_action,
        'ImageURL': f'data:image/jpeg;base64,{base64_image}'
    }

    query_string = '&'.join(f'{k}={urllib.parse.quote(str(v), safe="")}' for k, v in sorted(params.items()))
    string_to_sign = f'POST&%2F&{urllib.parse.quote(query_string, safe="")}'
    secret = f'{access_key_secret}&'
    signature = hmac.new(secret.encode('utf-8'), string_to_sign.encode('utf-8'), hashlib.sha256).digest()
    signature_base64 = base64.b64encode(signature).decode('utf-8')

    url = f'https://{endpoint}/?{query_string}&Signature={urllib.parse.quote(signature_base64)}'
    response = requests.post(url, timeout=30)
    result = response.json()

    if 'Data' not in result or 'TextDetections' not in result['Data']:
        raise Exception(f'OCR识别失败: {result.get("Message", "未知错误")}')

    return '\n'.join(item['DetectedText'] for item in result['Data']['TextDetections'])


def clean_ocr_text(text: str) -> str:
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        filtered = []
        for char in stripped:
            if '\u4e00' <= char <= '\u9fff' or char.isalnum() or char in '，。！？；：、""''（）[]{}《》<>·—…\n\r\t ':
                filtered.append(char)
        cleaned_line = ''.join(filtered)
        if cleaned_line:
            cleaned_lines.append(cleaned_line)
    return '\n'.join(cleaned_lines)


def parse_image(image_path: str, ocr_api_key: str = None, baidu_config: dict = None, ali_config: dict = None) -> dict:
    import time
    start_time = time.time()

    if not os.path.exists(image_path):
        return {'error': '图片文件不存在'}

    if not os.path.isfile(image_path):
        return {'error': '路径不是文件'}

    ext = os.path.splitext(image_path)[1].lower()
    if ext not in ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.webp'):
        return {'error': '不支持的图片格式，请使用PNG/JPG/BMP等格式'}

    try:
        if baidu_config and 'api_key' in baidu_config and 'secret_key' in baidu_config:
            try:
                text = baidu_ocr(image_path, baidu_config['api_key'], baidu_config['secret_key'])
                text = clean_ocr_text(text)
                if text.strip():
                    time_used = round(time.time() - start_time, 2)
                    return {
                        'title': '图片识别内容',
                        'content': text.strip(),
                        'source_type': 'image',
                        'ocr_method': 'baidu_ocr',
                        'time_used': time_used
                    }
            except Exception:
                pass

        if ali_config and 'access_key_id' in ali_config and 'access_key_secret' in ali_config:
            try:
                text = ali_ocr(image_path, ali_config['access_key_id'], ali_config['access_key_secret'])
                text = clean_ocr_text(text)
                if text.strip():
                    time_used = round(time.time() - start_time, 2)
                    return {
                        'title': '图片识别内容',
                        'content': text.strip(),
                        'source_type': 'image',
                        'ocr_method': 'ali_ocr',
                        'time_used': time_used
                    }
            except Exception:
                pass

        try:
            import base64
            with open(image_path, 'rb') as f:
                base64_image = base64.b64encode(f.read()).decode('utf-8')

            url = 'https://api.ocr.space/parse/image'
            payload = {
                'base64Image': f'data:image/{ext[1:]};base64,{base64_image}',
                'language': 'chs',
                'isOverlayRequired': 'false'
            }
            headers = {'apikey': ocr_api_key or ''}

            response = requests.post(url, data=payload, headers=headers, timeout=60)
            response.raise_for_status()
            result = response.json()

            if not result.get('IsErroredOnProcessing') and 'ParsedResults' in result and len(result['ParsedResults']) > 0:
                parsed_text = result['ParsedResults'][0].get('ParsedText', '')
                parsed_text = clean_ocr_text(parsed_text)
                if parsed_text.strip():
                    time_used = round(time.time() - start_time, 2)
                    return {
                        'title': '图片识别内容',
                        'content': parsed_text.strip(),
                        'source_type': 'image',
                        'ocr_method': 'ocr.space',
                        'time_used': time_used
                    }
        except Exception:
            pass

        try:
            import pytesseract
            from PIL import Image

            img = Image.open(image_path)
            processed_img = preprocess_image(img)
            text = pytesseract.image_to_string(processed_img, lang='chi_sim+eng', config='--oem 3 --psm 6')
            text = clean_ocr_text(text)

            if text.strip():
                time_used = round(time.time() - start_time, 2)
                return {
                    'title': '图片识别内容',
                    'content': text.strip(),
                    'source_type': 'image',
                    'ocr_method': 'pytesseract',
                    'time_used': time_used
                }
        except Exception:
            pass

        time_used = round(time.time() - start_time, 2)
        return {
            'error': '请手动输入图片中的文字',
            'ocr_method': 'failed',
            'time_used': time_used
        }

    except Exception as e:
        time_used = round(time.time() - start_time, 2)
        return {
            'error': f'请手动输入图片中的文字',
            'ocr_method': 'failed',
            'time_used': time_used
        }


def export_to_md(
    materials: list,
    draft: str = '',
    output_file: str = 'output.md',
    title: str = '素材整理'
) -> dict:
    """
    将素材和初稿导出为Markdown文件
    
    Args:
        materials: 素材列表，每个元素是 fetch_url/parse_text/parse_image 的返回结果
        draft: 生成的初稿内容
        output_file: 输出文件路径
        title: Markdown文件标题
        
    Returns:
        {'success': True, 'file_path': ...} 或 {'error': ...}
    """
    try:
        md_parts = [f'# {title}\n']

        if materials:
            md_parts.append('\n## 一、原始素材\n')

            for i, material in enumerate(materials, 1):
                if 'error' in material:
                    md_parts.append(f'\n### {i}. 素材（获取失败）\n')
                    md_parts.append(f'> {material["error"]}\n')
                    continue

                material_title = material.get('title', f'素材{i}')
                source_type = material.get('source_type', 'unknown')
                url = material.get('url', '')
                content = material.get('content', '')

                md_parts.append(f'\n### {i}. {material_title}\n')
                md_parts.append(f'**来源类型**: {source_type}\n')
                if url:
                    md_parts.append(f'**来源链接**: [{url}]({url})\n')

                ocr_method = material.get('ocr_method', '')
                if ocr_method:
                    md_parts.append(f'**OCR方法**: {ocr_method}\n')

                md_parts.append('\n')
                md_parts.append(content)
                md_parts.append('\n')

        if draft:
            md_parts.append('\n---\n')
            md_parts.append('\n## 二、生成初稿\n')
            md_parts.append(draft)
            md_parts.append('\n')

        md_content = '\n'.join(md_parts)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(md_content)

        return {
            'success': True,
            'file_path': output_file,
            'materials_count': len(materials),
            'draft_length': len(draft)
        }
    except Exception as e:
        return {'error': f'导出失败: {str(e)}'}


def ingest_batch(inputs: list) -> list:
    """
    批量处理输入列表，根据类型自动调用对应函数
    
    Args:
        inputs: 列表，每项格式为 {"type": "text"|"url"|"image", "value": "..."}
    
    Returns:
        处理结果列表，失败的项标记 error
    """
    results = []
    
    for idx, item in enumerate(inputs):
        item_type = item.get('type', '').lower()
        value = item.get('value', '')
        
        try:
            if item_type == 'text':
                result = parse_text(value)
            elif item_type == 'url':
                result = fetch_url(value)
            elif item_type == 'image':
                result = parse_image(value)
            else:
                result = {'error': f'不支持的类型: {item_type}', 'type': item_type}
            
            result['index'] = idx
            results.append(result)
        except Exception as e:
            results.append({
                'index': idx,
                'type': item_type,
                'error': f'处理失败: {str(e)}'
            })
    
    return results


if __name__ == '__main__':
    print("=" * 60)
    print("测试1: fetch_url (抓取网页)")
    print("=" * 60)
    url_result = fetch_url('https://example.com')
    if 'error' in url_result:
        print(f"错误: {url_result['error']}")
    else:
        print(f"标题: {url_result['title']}")
        print("-" * 50)
        print(f"正文前200字: {url_result['content'][:200]}...")

    print("\n" + "=" * 60)
    print("测试2: parse_text (清洗文本)")
    print("=" * 60)
    raw_text = """
        这是一段测试文本。

        包含多余的空行和首尾空白。


        第二段落内容。
        """
    text_result = parse_text(raw_text)
    print(f"标题: {text_result['title']}")
    print("-" * 50)
    print(f"清洗后内容:\n{text_result['content']}")

    print("\n" + "=" * 60)
    print("测试3: parse_image (图片OCR)")
    print("=" * 60)
    print("请将测试图片放入当前目录并命名为 test.png 或 test.jpg")
    for test_file in ['test.png', 'test.jpg', 'test.jpeg']:
        if os.path.exists(test_file):
            image_result = parse_image(test_file)
            if 'error' in image_result:
                print(f"错误: {image_result['error']}")
            else:
                print(f"标题: {image_result['title']}")
                print(f"OCR方法: {image_result['ocr_method']}")
                print("-" * 50)
                print(f"识别内容:\n{image_result['content']}")
            break
    else:
        print("未找到测试图片，请放入 test.png 或 test.jpg 后重新运行")
