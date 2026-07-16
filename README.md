# 🎨 灵感捕手 (Inspiration Catcher)

> 创作者的 AI 素材管家 —— 让收藏夹从"吃灰"变成"第二大脑"

## 💢 痛点

写作者、设计师、UP 主、学生写论文：看到好内容随手截图/收藏，但从不整理，要用时找不到；灵感转瞬即逝来不及记录。

## 🛠️ 解决方案

一个全平台素材收集 + AI 自动整理工具：存入文字/链接/截图，AI 自动打标签、写摘要、关联已有素材，形成个人知识网络。写作时输入关键词，AI 推荐相关素材并生成初稿框架。

## 🧱 技术架构

| 层 | 技术 |
|---|---|
| 前端 | Streamlit |
| AI 引擎 | DeepSeek API (标签/摘要/Embedding/生成) |
| 向量检索 | ChromaDB |
| 数据存储 | SQLite |
| 素材接入 | requests + BeautifulSoup + OCR |

## 👥 团队分工

| 成员 | 角色 |
|---|---|
| A | 素材接入 (文字/URL/图片解析) |
| B | Agent 核心 (AI 标签+摘要+向量检索+生成初稿) |
| C | Streamlit 界面 + PPT + Demo |

## 🚀 快速启动

```bash
# 1. 克隆仓库
git clone https://github.com/your-team/inspiration-catcher.git
cd inspiration-catcher

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置 API Key
# 复制 config.example.py 为 config.py
# 然后在 config.py 中填入你自己的 DeepSeek API Key

# 5. 启动
streamlit run app.py
```

## 📅 项目周期

2026 年 7 月 14 日 - 17 日（上海电力大学《Cloud Native & AI Coding 技术》微课程实训项目）



