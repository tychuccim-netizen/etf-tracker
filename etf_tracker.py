import pandas as pd
import streamlit as st
import datetime

# 定義目標 ETF 的標準代號與名稱常數字典
TARGET_ETFS = {
    "00981A": "主動統一台股增長",
    "00403A": "統一台股升級 50 主動式 ETF"
}

def fetch_and_verify_holdings(target_code):
    """
    抓取並雙重核對 ETF 代號與名稱
    """
    expected_name = TARGET_ETFS.get(target_code)
    
    # --- 模擬爬蟲抓取網頁標題與代號的過程 ---
    # 實務上，這裡會使用 requests 搭配 BeautifulSoup 抓取官網的 <h1> 或特定 class 內容
    # 這裡我們模擬爬蟲成功抓到正確網頁的情境
    scraped_code = target_code 
    scraped_name = expected_name 
    
    # 🛡️ 核心防呆機制：雙重核對
    if scraped_code != target_code or scraped_name != expected_name:
        # 若資料不符，拋出例外錯誤，阻斷錯誤資料流入戰情室
        raise ValueError(f"⚠️ 資料源核對失敗！預期擷取：{target_code} {expected_name}，但實際網頁顯示為：{scraped_code} {scraped_name}。請確認官網網址或網頁結構是否異動。")
    
    # 核對成功後，才繼續抓取成分股明細（以下為模擬數據）
    data = {
        "標的": ["健鼎", "旺宏", "台積電", "聯發科"],
        "代號": ["3044", "2337", "2330", "2454"],
        "今日張數": [3500, 21000, 5000, 1200],
        "昨日張數": [3407, 10468, 5000, 1500],
        "股價": [529.0, 168.0, 800.0, 1100.0],
        "漲跌幅": [9.98, 9.80, 1.2, -2.5]
    }
    return pd.DataFrame(data), expected_name

def analyze_movements(df):
    """計算籌碼變動幅度與判定狀態"""
    df['變動張數'] = df['今日張數'] - df['昨日張數']
    df['變動幅度'] = (df['變動張數'] / df['昨日張數']) * 100
    
    def get_status(row):
        if row['昨日張數'] == 0 and row['今日張數'] > 0: return "新進"
        if row['今日張數'] == 0 and row['昨日張數'] > 0: return "出清"
        if row['變動張數'] > 0: return "加碼"
        if row['變動張數'] < 0: return "減碼"
        return "持平"
    
    df['狀態'] = df.apply(get_status, axis=1)
    return df

def main():
    st.set_page_config(page_title="籌碼追蹤戰情室", layout="wide")
    
    # 透過側邊欄選擇要監控的標的
    selected_code = st.sidebar.selectbox("選擇監控標的", list(TARGET_ETFS.keys()))
    
    try:
        # 執行抓取與雙重核對
        df_raw, etf_name = fetch_and_verify_holdings(selected_code)
        df_result = analyze_movements(df_raw)
        
        st.title(f"📊 {selected_code} {etf_name} 籌碼監控")
        st.write(f"資料核對狀態：✅ 雙重驗證通過 | 更新時間：{datetime.datetime.now().strftime('%Y-%m-%d 17:30')}")

        # 頂部戰略儀表板
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("新增 (潛力建倉)", len(df_result[df_result['狀態'] == '新進']))
        col2.metric("出清 (重點警示)", len(df_result[df_result['狀態'] == '出清']))
        col3.metric("加碼 (趨勢向上)", len(df_result[df_result['狀態'] == '加碼']))
        col4.metric("減碼 (籌碼轉弱)", len(df_result[df_result['狀態'] == '減碼']))

        # 呈現明細表格
        st.markdown("### 資金交易明細")
        
        # 為了視覺化更容易判讀，針對加減碼加上顏色標示 (Streamlit style)
        def highlight_status(val):
            color = '#ff4b4b' if val in ['加碼', '新進'] else '#00cc96' if val in ['減碼', '出清'] else ''
            return f'color: {color}'
            
        st.dataframe(df_result[['標的', '代號', '股價', '狀態', '變動張數', '變動幅度']].style.map(highlight_status, subset=['狀態']), use_container_width=True)

    except Exception as e:
        # 捕捉核對失敗或其他例外錯誤
        st.error(str(e))
        st.warning("系統已啟動防護機制，暫停顯示該檔 ETF 資訊。請通知管理員進行網頁結構排查。")

if __name__ == "__main__":
    main()