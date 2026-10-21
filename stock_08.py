import os
import csv
import re
import tkinter as tk
from tkinter import messagebox, ttk
try:
    import twstock
except ImportError:
    twstock = None

# 引入 Matplotlib 用於繪製圖表
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# 設定中文字型以避免亂碼
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

LAST_QUERY_FILE = "last_query.txt"

def load_last_query():
    if os.path.exists(LAST_QUERY_FILE):
        try:
            with open(LAST_QUERY_FILE, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception:
            pass
    return "2330, 2317" # 預設值

def save_last_query(text):
    try:
        with open(LAST_QUERY_FILE, 'w', encoding='utf-8') as f:
            f.write(text)
    except Exception:
        pass

def query_stocks():
    raw_input_text = entry_stock.get().strip()
    if not raw_input_text:
        messagebox.showerror("錯誤", "請至少輸入一個股票代號！")
        return
        
    # 記錄最後一次查詢的股票代號到檔案
    save_last_query(raw_input_text)
        
    stocknos = [s.strip() for s in re.split(r'[,，\s、]+', raw_input_text) if s.strip()]
    
    year_str = entry_year.get().strip()
    month_str = entry_month.get().strip()
    
    if not year_str or not month_str:
        messagebox.showerror("錯誤", "請完整輸入年份與月份！")
        return
    
    try:
        year = int(year_str)
        month = int(month_str)
    except ValueError:
        messagebox.showerror("錯誤", "年份與月份必須為數字！")
        return
        
    # 清除現有的所有分頁
    for tab in notebook.tabs():
        notebook.forget(tab)
        
    status_messages = []
    
    for stockno in stocknos:
        stock_name = "未知股票"
        if twstock and stockno in twstock.codes:
            stock_name = twstock.codes[stockno].name
            
        filename = f"stock_{stockno}_{year}_{month:02d}.csv"
        stock_rows = []
        
        if os.path.exists(filename):
            status_messages.append(f"{stockno}(本機)")
            with open(filename, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    stock_rows.append(row)
        else:
            if twstock is None:
                messagebox.showerror("錯誤", "找不到 twstock 模組，無法連線取得股票資料！")
                return
                
            lbl_status.config(text=f"狀態：正在從網路取得 {stockno} ({stock_name}) 資料...")
            root.update()
            
            stock = twstock.Stock(stockno)
            historical_data = stock.fetch(year, month)
            
            if not historical_data:
                status_messages.append(f"{stockno}(無資料)")
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
            status_messages.append(f"{stockno}(網路抓取並存檔)")

        if not stock_rows:
            continue

        tab_frame = ttk.Frame(notebook)
        tab_title = f"{stockno} {stock_name}"
        notebook.add(tab_frame, text=tab_title)
        
        pane = ttk.PanedWindow(tab_frame, orient=tk.VERTICAL)
        pane.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 上半部：表格
        frame_table = ttk.Frame(pane)
        pane.add(frame_table, weight=1)
        
        columns = ("StockNo", "StockName", "Date", "Open", "High", "Low", "Close", "Capacity")
        tree = ttk.Treeview(frame_table, columns=columns, show="headings", height=8)
        
        tree.heading("StockNo", text="股票代號")
        tree.heading("StockName", text="股票名稱")
        tree.heading("Date", text="日期")
        tree.heading("Open", text="開盤價")
        tree.heading("High", text="最高價")
        tree.heading("Low", text="最低價")
        tree.heading("Close", text="收盤價")
        tree.heading("Capacity", text="成交股數")
        
        tree.column("StockNo", width=80, anchor="center")
        tree.column("StockName", width=100, anchor="center")
        tree.column("Date", width=100, anchor="center")
        tree.column("Open", width=80, anchor="e")
        tree.column("High", width=80, anchor="e")
        tree.column("Low", width=80, anchor="e")
        tree.column("Close", width=80, anchor="e")
        tree.column("Capacity", width=120, anchor="e")
        
        scrollbar = ttk.Scrollbar(frame_table, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        for row in stock_rows:
            tree.insert("", "end", values=(stockno, stock_name, row['Date'], row['Open'], row['High'], row['Low'], row['Close'], row['Capacity']))

        # 下半部：圖表
        frame_chart = ttk.Frame(pane)
        pane.add(frame_chart, weight=2)
        
        dates = [r['Date'] for r in stock_rows]
        closes = [float(r['Close']) for r in stock_rows]
        capacities = [float(r['Capacity']) for r in stock_rows]
        
        fig, ax1 = plt.subplots(figsize=(9, 4), dpi=100)
        
        color = 'tab:red'
        ax1.set_xlabel('日期', fontsize=10)
        ax1.set_ylabel('收盤價 (元)', color=color, fontsize=10)
        ax1.plot(dates, closes, color=color, marker='o', linewidth=2, label='收盤價')
        ax1.tick_params(axis='y', labelcolor=color)
        ax1.tick_params(axis='x', rotation=45)
        
        ax2 = ax1.twinx()  
        color = 'tab:blue'
        ax2.set_ylabel('成交股數', color=color, fontsize=10)
        ax2.bar(dates, capacities, color=color, alpha=0.3, label='成交量')
        ax2.tick_params(axis='y', labelcolor=color)
        ax2.grid(False)
        
        plt.title(f"{stockno} {stock_name} - {year}年{month}月 收盤價與成交量走勢圖", fontsize=12, pad=10)
        fig.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=frame_chart)
        canvas.draw()
        canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

    summary_status = " | ".join(status_messages)
    lbl_status.config(text=f"查詢完畢 (已記錄查詢代號)：{summary_status}")

# 主視窗
root = tk.Tk()
root.title("多股台股歷史收盤資料與圖表系統（具備記憶上次查詢功能）")
root.geometry("900x750")

frame_top = tk.LabelFrame(root, text="查詢條件設定 (支援多檔股票，自動記憶上次輸入)", padx=10, pady=10)
frame_top.pack(fill="x", padx=10, pady=10)

tk.Label(frame_top, text="股票代號:").grid(row=0, column=0, sticky="w", padx=5)
entry_stock = tk.Entry(frame_top, width=22)
entry_stock.grid(row=0, column=1, padx=5)
entry_stock.insert(0, load_last_query())

tk.Label(frame_top, text="年份:").grid(row=0, column=2, sticky="w", padx=5)
entry_year = tk.Entry(frame_top, width=6)
entry_year.grid(row=0, column=3, padx=5)
entry_year.insert(0, "2026")

tk.Label(frame_top, text="月份:").grid(row=0, column=4, sticky="w", padx=5)
entry_month = tk.Entry(frame_top, width=4)
entry_month.grid(row=0, column=5, padx=5)
entry_month.insert(0, "10")

btn_query = tk.Button(frame_top, text="查詢 / 載入資料與圖表", command=query_stocks, bg="#4CAF50", fg="white", padx=10)
btn_query.grid(row=0, column=6, padx=10)

lbl_status = tk.Label(root, text="狀態：已自動載入上次查詢的股票代號紀錄", fg="blue")
lbl_status.pack(anchor="w", padx=15)

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, padx=10, pady=10)

root.mainloop()
