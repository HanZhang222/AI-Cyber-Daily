import requests
from jinja2 import Template
from datetime import datetime
import random

# --- 1. 配置图片库 (区分 AI 和 安全) ---
# Unsplash 随机图源，为了配合手绘风，我们选了一些更有质感的图

# AI 主题图片 (大脑, 芯片, 机器人)
AI_IMAGES = [
    "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=500&auto=format&fit=crop&q=60",
    "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=500&auto=format&fit=crop&q=60",
    "https://images.unsplash.com/photo-1531746790731-6c087fecd65a?w=500&auto=format&fit=crop&q=60",
    "https://images.unsplash.com/photo-1555255707-c07966088b7b?w=500&auto=format&fit=crop&q=60",
]

# 网络安全主题图片 (锁, 代码, 矩阵, 盾牌)
SEC_IMAGES = [
    "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=500&auto=format&fit=crop&q=60", # Cyber lock
    "https://images.unsplash.com/photo-1563986768609-322da13575f3?w=500&auto=format&fit=crop&q=60", # Matrix code
    "https://images.unsplash.com/photo-1614064641938-3bbee52942c7?w=500&auto=format&fit=crop&q=60", # Hacker hoodie
    "https://images.unsplash.com/photo-1510511459019-5dda7724fd82?w=500&auto=format&fit=crop&q=60", # Shield/Data
]

# --- 2. 通用抓取函数 ---
def fetch_hn_topic(query, label, image_pool, limit=5):
    """
    query: 搜索关键词 (如 'AI' 或 'Security')
    label: 显示在卡片上的标签 (如 'AI Trend' 或 'Cyber Alert')
    image_pool: 对应的图片列表
    limit: 抓取数量
    """
    print(f"正在抓取主题: {label} ...")
    # 搜索过去 24 小时的高热度文章
    url = f"https://hn.algolia.com/api/v1/search_by_date?query={query}&tags=story&hitsPerPage={limit}"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        items = []
        for hit in data['hits']:
            title = hit.get('title', '')
            if not title or len(title) < 5: continue
            
            # 构建新闻对象
            item = {
                "title": title,
                "link": hit.get('url', f"https://news.ycombinator.com/item?id={hit['objectID']}"),
                # 暂时用静态摘要，部署好 Gemini Key 后可以在这里接入 AI
                "summary": f"Latest update on {label}. Click to read the full discussion on Hacker News.",
                "source": label, # 这里决定了卡片右上角显示什么
                "date": datetime.now().strftime("%m-%d"),
                "image_url": random.choice(image_pool) # 从对应主题池里随机选图
            }
            items.append(item)
        return items
    except Exception as e:
        print(f"抓取 {label} 失败: {e}")
        return []

def main():
    # --- 3. 分别抓取两类新闻 ---
    
    # 抓取 5 条 AI 新闻
    # 关键词包含: AI, LLM, GPT, Transformer
    ai_news = fetch_hn_topic("AI OR LLM OR GPT", "AI Trend", AI_IMAGES, limit=5)
    
    # 抓取 5 条 安全 新闻
    # 关键词包含: Security, Malware, Vulnerability, Exploit
    sec_news = fetch_hn_topic("Cyber Security OR Vulnerability OR Malware", "CyberSec", SEC_IMAGES, limit=5)
    
    # --- 4. 合并数据 ---
    # 你可以选择直接相加，或者交替合并。这里我们简单合并。
    all_news = ai_news + sec_news
    
    # 如果一条都没抓到（API挂了），放一条假数据防止页面空白
    if not all_news:
        all_news = [{
            "title": "System Update: No news fetched properly",
            "summary": "Check GitHub Actions logs for details.",
            "link": "#",
            "source": "System",
            "date": datetime.now().strftime("%m-%d"),
            "image_url": ""
        }]

    # --- 5. 渲染网页 ---
    try:
        with open('template.html', 'r', encoding='utf-8') as f:
            template_text = f.read()

        template = Template(template_text)
        current_date = datetime.now().strftime("%Y-%m-%d")
        html_output = template.render(news_list=all_news, date_str=current_date)

        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(html_output)
        
        print(f"网页生成完毕! 共包含 {len(all_news)} 条新闻。")
        
    except FileNotFoundError:
        print("错误：找不到 template.html 文件！")

if __name__ == "__main__":
    main()
