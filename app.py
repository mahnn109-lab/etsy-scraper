import streamlit as st
import pandas as pd
import random
import time
import os  # 把 import 移到最上面，这是最规范的写法
from playwright.sync_api import sync_playwright

# --- 页面基础配置 ---
st.set_page_config(page_title="外贸工艺品竞品分析", layout="wide")

# --- 模拟数据生成器 ---
def generate_mock_data(keyword, count=8):
    """生成模拟数据，保证演示效果"""
    mock_items = []
    base_titles = [
        f"Nordic Style {keyword} - Handmade", 
        f"Cute {keyword} Figurine for Gift", 
        f"Vintage {keyword} Sculpture", 
        f"Resin {keyword} Statue Home Decor"
    ]
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
            # --- 智能浏览器启动逻辑 (这里修复了缩进) ---
            sys_browser = "/usr/bin/chromium"
            if os.path.exists(sys_browser):
                launch_path = sys_browser
            else:
                launch_path = None

            browser = p.chromium.launch(
                headless=True,
                executable_path=launch_path,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            # ----------------------------------------

            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            page = context.new_page()
            
            st.toast(f"正在访问 Etsy: {keyword}...", icon="🚀")
            page.goto(url, timeout=30000)
            time.sleep(random.uniform(2, 4))
            
            items = page.query_selector_all('ol li.wt-list-unstyled')
            
            if not items or len(items) < 2:
                # 尝试另一种常见的选择器结构，以防 Etsy 改版
                items = page.query_selector_all('.v2-listing-card')
            
            if not items:
                raise Exception("No items found")

            for item in items[:12]: 
                try:
                    title_el = item.query_selector('h3')
                    title = title_el.inner_text().strip() if title_el else "Unknown Product"
                    
                    price_el = item.query_selector('.currency-value')
                    price = float(price_el.inner_text().replace(',', '')) if price_el else 0.0
                    
                    img_el = item.query_selector('img')
                    img_src = img_el.get_attribute('src') if img_el else ""
                    
                    link_el = item.query_selector('a')
                    link = link_el.get_attribute('href') if link_el else ""

                    if title and price > 0:
                        data.append({
                            "title": title,
                            "price": price,
                            "image": img_src,
                            "link": link
                        })
                except:
                    continue
            
            browser.close()
            
        except Exception as e:
            st.error(f"Etsy 反爬虫拦截或云端环境限制 ({e})。已自动切换至【演示模式】。")
            return generate_mock_data(keyword)
            
    if not data:
        return generate_mock_data(keyword)
        
    return data

# --- 网页界面 UI ---
st.title("🛍️ 工艺品竞品透视 (Demo版)")
st.markdown("输入关键词，快速分析 Etsy 上的竞品价格与设计风格。")

with st.sidebar:
    st.header("🔎 搜索设置")
    keyword = st.text_input("输入关键词", value="Resin Garden Gnome")
    run_btn = st.button("开始分析", type="primary")

if run_btn:
    with st.spinner('正在分析市场数据...'):
        df_list = get_etsy_data(keyword)
        df = pd.DataFrame(df_list)
        
        col1, col2, col3 = st.columns(3)
        avg_price = df['price'].mean()
        max_price = df['price'].max()
        min_price = df['price'].min()
        
        col1.metric("市场均价", f"${avg_price:.2f}")
        col2.metric("最高价", f"${max_price:.2f}")
        col3.metric("最低价", f"${min_price:.2f}")
        
        st.divider()
        st.subheader(f"🖼️ '{keyword}' 热门款式")
        
        cols = st.columns(4)
        for idx, row in df.iterrows():
            with cols[idx % 4]:
                if row['image']:
                    st.image(row['image'], use_container_width=True)
                st.markdown(f"**${row['price']}**")
                st.caption(row['title'][:30] + "...")
                if row['link']:
                    st.markdown(f"[查看原网页]({row['link']})")
        
        st.divider()
        with st.expander("查看详细数据表"):
            st.dataframe(df)
