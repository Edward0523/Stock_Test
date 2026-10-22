import os
import csv
import re
import streamlit as st
import pandas as pd

# 引入 Matplotlib 繪圖
import matplotlib.pyplot as plt

# 設定中文字型
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

try:
    import twstock
except ImportError:
    twstock = None

# 頁面標題設定
st.set_page_config(page_title="台股歷史收盤資料與圖表查詢系統", layout="wide")

st.title("📈 台股歷史收盤資料與走勢圖查詢系統")
st.markdown("輸入多檔股票代號（可以逗號或空格分隔），即可同時查詢該月份的歷史收盤資料與視覺化走勢圖！")

# --- 側邊欄或上方查詢設定 ---
with st.sidebar:
    st.header("🔍 查詢條件設定")
    
    # 預設股票代號
    default_stock = "2330, 2317"
    
    stock_input = st.text_input("股票代號 (多檔請用逗號隔開)", value=default_stock)
    year = st.number_input("年份", min_value=2015, max_value=2030, value=2026)
    month = st.number_input("月份", min_value=1, max_value=12, value=10)
    
    submitted = st.button("開始查詢", type="primary")

# 記憶查詢或初始化
if submitted or stock_input:
    stocknos = [s.strip() for s in re.split(r'[,，\s、]+', stock_input) if s.strip()]
    
    if not stocknos:
        st.warning("請至少輸入一個股票代號！")
    else:
        # 建立多個分頁 (Tabs)
        tab_titles = []
        stock_data_dict = {}
        
        for stockno in stocknos:
            stock_name = "未知股票"
            if twstock and stockno in twstock.codes:
                stock_name = twstock.codes[stockno].name
            tab_titles.append(f"{stockno} {stock_name}")
            
            filename = f"stock_{stockno}_{year}_{int(month):02d}.csv"
            stock_rows = []
            
            # 檢查本機快取
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        stock_rows.append(row)
            else:
                if twstock is None:
                    st.error("找不到 twstock 模組！")
                    break
                
                with st.spinner(f"正在從網路取得 {stockno} ({stock_name}) 資料..."):
                    stock = twstock.Stock(stockno)
                    historical_data = stock.fetch(int(year), int(month))
                    
                    if not historical_data:
                        continue
                        
                    headers = ['Date', 'Open', 'High', 'Low', 'Close', 'Capacity']
                    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                        writer = csv.writer(f)
                        writer.writerow(headers)
                        for entry in historical_data:
                            row_data = [
                                entry.date.strftime('%Y-%m-%d'),
                                entry.open,
                                entry.high,
                                entry.low,
                                entry.close,
                                entry.capacity
                            ]
                            writer.writerow(row_data)
                            stock_rows.append({
                                'Date': row_data[0],
                                'Open': row_data[1],
                                'High': row_data[2],
                                'Low': row_data[3],
                                'Close': row_data[4],
                                'Capacity': row_data[5]
                            })
            
            stock_data_dict[stockno] = {"name": stock_name, "rows": stock_rows}

        if stock_data_dict:
            # 建立 Streamlit 分頁
            tabs = st.tabs(list(stock_data_dict.keys()))
            
            for idx, (stockno, info) in enumerate(stock_data_dict.items()):
                with tabs[idx]:
                    st.subheader(f"{stockno} {info['name']} - {year}年{month}月 歷史資料與走勢")
                    
                    rows = info['rows']
                    if not rows:
                        st.info("該月份尚無交易資料。")
                        continue
                        
                    # 整理成 DataFrame 供表格顯示
                    df = pd.DataFrame(rows)
                    df.insert(0, 'StockName', info['name'])
                    df.insert(0, 'StockNo', stockno)
                    
                    # 重新命名欄位呈現
                    df_display = df.rename(columns={
                        'StockNo': '股票代號',
                        'StockName': '股票名稱',
                        'Date': '日期',
                        'Open': '開盤價',
                        'High': '最高價',
                        'Low': '最低價',
                        'Close': '收盤價',
                        'Capacity': '成交股數'
                    })
                    
                    # 左右或上下配置：上方表格，下方圖表
                    st.dataframe(df_display, use_container_width=True)
                    
                    # 繪製圖表
                    fig, ax1 = plt.subplots(figsize=(10, 4))
                    
                    dates = [r['Date'] for r in rows]
                    closes = [float(r['Close']) for r in rows]
                    capacities = [float(r['Capacity']) for r in rows]
                    
                    color = 'tab:red'
                    ax1.set_xlabel('日期')
                    ax1.set_ylabel('收盤價 (元)', color=color)
                    ax1.plot(dates, closes, color=color, marker='o', linewidth=2, label='收盤價')
                    ax1.tick_params(axis='y', labelcolor=color)
                    ax1.tick_params(axis='x', rotation=45)
                    
                    ax2 = ax1.twinx()
                    color = 'tab:blue'
                    ax2.set_ylabel('成交股數', color=color)
                    ax2.bar(dates, capacities, color=color, alpha=0.3, label='成交量')
                    ax2.tick_params(axis='y', labelcolor=color)
                    ax2.grid(False)
                    
                    plt.title(f"{stockno} {info['name']} 收盤價與成交量走勢圖")
                    fig.tight_layout()
                    
                    st.pyplot(fig)
        else:
            st.warning("查無符合條件的股票資料。")
