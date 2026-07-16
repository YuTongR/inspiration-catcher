"""collect.py —— 灵感捕手主流程:接收素材 → AI分析 → 存库 → 向量索引"""
import sys
from agent import analyze_material, save_material


def collect(content, source_type="text", url=""):
    """接收原始文本,AI分析后存入数据库并索引到向量库"""
    print("正在分析素材...")

    result = analyze_material(content)
    if "error" in result:
        print(f"分析失败: {result['error']}")
        return None

    data = {
        "title": content[:50].replace("\n", " "),
        "content": content,
        "tags": result.get("tags", []),
        "summary": result.get("summary", ""),
        "type": result.get("type", "未知"),
        "source_type": source_type,
        "url": url,
    }

    material_id = save_material(data)
    print(f"素材已存入! (ID: {material_id})")
    print(f"   标签: {' '.join(data['tags'])}")
    print(f"   摘要: {data['summary']}")
    print(f"   类型: {data['type']}")
    return data


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python collect.py <素材文字>")
        sys.exit(1)

    text = sys.argv[1]
    collect(text)
