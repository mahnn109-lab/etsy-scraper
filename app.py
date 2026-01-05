import streamlit as st
import pandas as pd
import random
import time
from playwright.sync_api import sync_playwright

# --- 页面基础配置 ---
st.set_page_config(page_title="外贸工艺品竞品分析", layout="wide")

# --- 模拟数据生成器 (当爬虫被封锁时使用) ---
def generate_mock_data(keyword, count=8):
    """生成模拟数据，保证演示效果"""
    mock_items = []
    base_titles = [
        f"Nordic Style {keyword} - Handmade", 
        f"Cute {keyword} Figurine for Gift", 
        f"Vintage {keyword} Sculpture", 
        f"Resin {keyword} Statue Home Decor"
    ]
    # 随机生成一些图片占位符
    mock_images = [
        "https://images.unsplash.com/photo-1581557991964-125469da3b8a?auto=format&fit=crop&w=300&q=80",
        "https://images.unsplash.com/photo-1513519245088-0e12902e5a38?auto=format&fit=crop&w=300&q=80",
        "https://images.unsplash.com/photo-1576075796033-848c2a5f3696?auto=format&fit=crop&w=300&q=80",
        "https://images.unsplash.com/photo-1515488042361-25f4682ea2dd?auto=format&fit=crop&w=300&q=80"
    ]
    
    for i in range(count):
        item = {
            "title": f"{random.choice(base_titles)} #{i+1}",
            "price": round(random.uniform(15.99, 89.99), 2),
            "image": random.choice(mock_images),
            "link": "https://www.etsy.com"
        }
        mock_items.append(item)
    return mock_items

# --- 爬虫核心逻辑 ---
def get_etsy_data(keyword):
    data = []
    url = f"https://www.etsy.com/search?q={keyword.replace(' ', '+')}"
    
    with sync_playwright() as p:
        try:
           # 智能判断：如果是云端就用系统浏览器，如果是本地就用自带的
import os
sys_browser = "/usr/bin/chromium"
launch_path = sys_browser if os.path.exists(sys_browser) else None

browser = p.chromium.launch(
    headless=True,
    executable_path=launch_path,  # 关键修复在这里
    args=['--no-sandbox', '--disable-dev-shm-usage']
)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            page = context.new_page()
            
            st.toast(f"正在访问 Etsy: {keyword}...", icon="🚀")
            page.goto(url, timeout=30000)
            
            # 随机等待，模拟人类
            time.sleep(random.uniform(2, 4))
            
            # 尝试获取商品列表 (Etsy 的结构经常变，这里用通用选择器尝试)
            # 注意：实际生产中需要定期维护 CSS 选择器
            items = page.query_selector_all('ol li.wt-list-unstyled') # 这是一个常见的列表容器
            
            # 如果没抓到或者被反爬拦截，抛出异常进入 Mock 模式
            if not items or len(items) < 2:
                raise Exception("No items found or Anti-bot triggered")

            count = 0
            for item in items[:12]: # 限制抓取前12个用于演示
                try:
                    # 提取标题
                    title_el = item.query_selector('h3')
                    title = title_el.inner_text().strip() if title_el else "Unknown Product"
                    
                    # 提取价格
                    price_el = item.query_selector('.currency-value')
                    price = float(price_el.inner_text().replace(',', '')) if price_el else 0.0
                    
                    # 提取图片
                    img_el = item.query_selector('img')
                    img_src = img_el.get_attribute('src') if img_el else ""
                    
                    # 提取链接
                    link_el = item.query_selector('a')
                    link = link_el.get_attribute('href') if link_el else ""

                    if title and price > 0:
                        data.append({
                            "title": title,
                            "price": price,
                            "image": img_src,
                            "link": link
                        })
                        count += 1
                except:
                    continue
            
            browser.close()
            
        except Exception as e:
            # 抓取失败时的处理
            st.error(f"Etsy 云端反爬虫极其严格 (Error: {e})。已切换至【演示模式】展示功能。")
            return generate_mock_data(keyword)
            
    # 如果抓取结果为空，也返回模拟数据
    if not data:
        return generate_mock_data(keyword)
        
    return data

# --- 网页界面 UI ---
st.title("🛍️ 工艺品竞品透视 (Demo版)")
st.markdown("输入关键词，快速分析 Etsy 上的竞品价格与设计风格。")

# 侧边栏
with st.sidebar:
    st.header("🔎 搜索设置")
    keyword = st.text_input("输入关键词", value="Resin Garden Gnome")
    st.info("提示：Etsy 对云服务器有严格拦截，如果抓取失败会自动展示演示数据。")
    run_btn = st.button("开始分析", type="primary")

# 主逻辑
if run_btn:
    with st.spinner('正在分析市场数据...'):
        # 获取数据
        df_list = get_etsy_data(keyword)
        df = pd.DataFrame(df_list)
        
        # 1. 显示核心指标
        col1, col2, col3 = st.columns(3)
        avg_price = df['price'].mean()
        max_price = df['price'].max()
        min_price = df['price'].min()
        
        col1.metric("市场均价", f"${avg_price:.2f}")
        col2.metric("最高价", f"${max_price:.2f}")
        col3.metric("最低价", f"${min_price:.2f}")
        
        st.divider()
        
        # 2. 图片画廊 (Visual Gallery)
        st.subheader(f"🖼️ '{keyword}' 热门款式")
        
        # 每行显示 4 张图
        cols = st.columns(4)
        for idx, row in df.iterrows():
            with cols[idx % 4]:
                st.image(row['image'], use_container_width=True)
                st.markdown(f"**${row['price']}**")
                st.caption(row['title'][:30] + "...")
                st.markdown(f"[查看原网页]({row['link']})")
        
        st.divider()
        
        # 3. 数据表格
        with st.expander("查看详细数据表"):
            st.dataframe(df)
