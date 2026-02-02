import requests
from jinja2 import Template
from datetime import datetime
import random
import os
import google.generativeai as genai
import time
import json # 引入 JSON 库来解析 AI 的结构化输出

# --- 1. 配置 Gemini ---
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    # 使用支持 JSON 模式的最新模型
    model = genai.GenerativeModel('gemini-1.5-pro-latest', generation_config={"response_mime_type": "application/json"})
else:
    print("警告: 未找到 GEMINI_API_KEY，将使用静态占位符。")
    model = None

# --- 图片库 (保持不变) ---
AI_IMAGES = [
    "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=600&q=80",
    "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=600&q=80",
    "https://images.unsplash.com/photo-1531746790731-6c087fecd65a?w=600&q=80",
    "https://images.unsplash.com/photo-1555255707-c07966088b7b?w=600&q=80",
]
SEC_IMAGES = [
    "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=600&q=80",
    "https://images.unsplash.com/photo-1563986768609-322da13575f3?w=600&q=80",
    "https://images.unsplash.com/photo-1614064641938-3bbee52942c7?w=600&q=80",
    "https://images.unsplash.com/photo-1510511459019-5dda7724fd82?w=600&q=80",
]

def generate_bilingual_summary(text_list):
    """让 AI 一次性生成结构化的中英文标题和摘要"""
    if not model or not text_list:
        return []
    
    # 构造高级 Prompt：要求返回 JSON 格式
    prompt = """
    You are an expert tech news editor. For each of the following English news titles, provide a structured summary in JSON format.
    For each title, generate:
    1. "title_zh": Translate the title into clear Chinese.
    2. "title_en": Keep the original English title (clean it up if necessary).
    3. "summary_zh": A concise Chinese summary (around 50-80 characters) capturing the core value or impact.
    4. "summary_en": A concise English summary (around 30-50 words).

    Input Titles:
    """
    for i, title in enumerate(text_list):
        prompt += f"{i+1}. {title}\n"
        
    prompt += """
    \nOutput Requirement:
    Return a JSON array of objects, where each object corresponds to an input title in order. Example format:
    [
        {
            "title_zh": "...",
            "title_en": "...",
            "summary_zh": "...",
            "summary_en": "..."
        },
        ...
    ]
    """
    
    try:
        print(f"Sending Request to Gemini for {len(text_list)} items...")
        response = model.generate_content(prompt)
        # 解析返回的 JSON 数据
        structured_data = json.loads(response.text)
        return structured_data
    except Exception as e:
        print(f"AI 调用或解析失败: {e}")
        # 出错时返回空字典列表作为兜底
        return [{} for _ in text_list]

def fetch_hn_topic(query, label, image_pool, limit=4):
    print(f"正在抓取 {label} ...")
    # 搜索过去 48 小时以获取更多高质量内容
    url = f"https://hn.algolia.com/api/v1/search_by_date?query={query}&tags=story&numericFilters=created_at_i>{int(time.time())-172800}&hitsPerPage={limit*2}"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        raw_items = []
        titles_to_summarize = []
        
        # 1. 筛选数据
        for hit in data['hits']:
            title = hit.get('title', '')
            if not title or len(title) < 10: continue # 过滤太短的标题
            # 简单去重
            if any(item['objectID'] == hit['objectID'] for item in raw_items): continue
            
            raw_items.append(hit)
            titles_to_summarize.append(title)
            if len(raw_items) >= limit: break
            
        if not titles_to_summarize:
            return []

        # 2. 调用 AI 生成双语数据
        bilingual_data = generate_bilingual_summary(titles_to_summarize)
        
        # 3. 组装最终数据
        final_items = []
        for i, hit in enumerate(raw_items):
            # 获取 AI 数据，如果没有则使用默认值
            ai_content = bilingual_data[i] if i < len(bilingual_data) else {}
            
            final_items.append({
                # 核心数据：中英文标题和摘要
                "title_zh": ai_content.get("title_zh", hit.get('title')),
                "title_en": ai_content.get("title_en", hit.get('title')),
                "summary_zh": ai_content.get("summary_zh", "AI摘要生成中，请稍后查看... (请确保API Key配置正确)"),
                "summary_en": ai_content.get("summary_en", "AI summary generating..."),
                
                "link": hit.get('url', f"https://news.ycombinator.com/item?id={hit['objectID']}"),
                "source": label,
                "date": datetime.now().strftime("%m-%d"),
                "image_url": random.choice(image_pool)
            })
            
        return final_items
    except Exception as e:
        print(f"抓取 {label} 失败: {e}")
        return []

def main():
    # 抓取数据
    ai_news = fetch_hn_topic("AI OR LLM OR GPT", "AI Trend", AI_IMAGES, limit=5)
    time.sleep(2) # 避免请求过快
    sec_news = fetch_hn_topic("Cyber Security OR Vulnerability OR Exploit", "CyberSec", SEC_IMAGES, limit=5)
    
    all_news = ai_news + sec_news
    
    if not all_news:
        print("未抓取到有效数据。")
        # 可以选择生成一个空页面或者保留旧页面
        return

    # 渲染
    try:
        with open('template.html', 'r', encoding='utf-8') as f:
            template_text = f.read()

        template = Template(template_text)
        current_date = datetime.now().strftime("%Y-%m-%d")
        html_output = template.render(news_list=all_news, date_str=current_date)

        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(html_output)
        print(f"成功生成 index.html，包含 {len(all_news)} 条新闻。")
        
    except FileNotFoundError:
        print("错误：找不到 template.html")

if __name__ == "__main__":
    main()
