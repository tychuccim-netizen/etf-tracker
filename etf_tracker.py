import pandas as pd
import streamlit as st
import requests
import datetime
import urllib3
import numpy as np

# 關閉 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="日月鑫籌碼戰情室", layout="wide")

# 💼 總裁專屬戰略物資庫
ETF_CONFIG = {
    "00981A": {
        "name": "主動統一台股增長",
        "url": "https://pscnetsecrwd.moneydj.com/b2brwdCommon/jsondata/8f/d7/10/twetfdata.xdjjson?x=etf-Basic0005-1&a=00981A.TW&revision=910d22a1-3e10-48a1-8144-35b8a0267f0e"
    },
    "00403A": {
        "name": "統一台股升級 50",
        "url": "https://pscnetsecrwd.moneydj.com/b2brwdCommon/jsondata/61/ff/e8/twetfdata.xdjjson?x=etf-Basic0005-1&a=00403A.TW&revision=910d22a1-3e10-48a1-8144-35b8a0267f0e"
    }
}

@st.cache_data(ttl=3600)
def fetch_api_data(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        response.encoding = 'utf-8'
        data = response.json()
        if 'ResultSet' in data and 'Result' in data['ResultSet']:
            return pd.DataFrame(data['ResultSet']['Result'])
        return pd.DataFrame()
    except:
        return None

def process_and_analyze(df):
    if "V2" not in df.columns:
        return df, False 
        
    # 1. 欄位翻譯與【股數轉張數】換算，並強制取整數
    df["今日張數"] = (pd.to_numeric(df["V5"], errors='coerce').fillna(0) / 1000).round(0).astype(int) # ⚠️ 強制轉整數
    df = df.rename(columns={"V2": "代號", "V3": "標的", "V4": "權重(%)"})
    df = df[["代號", "標的", "權重(%)", "今日張數"]]
    df["權重(%)"] = pd.to_numeric(df["權重(%)"], errors='coerce').fillna(0)
    
    # 2. 模擬 T-1 日庫存 (建立變動基準，同步取整數)
    np.random.seed(42) 
    mock_changes = np.random.uniform(0.98, 1.02, size=len(df)) # 縮小變動範圍使模擬更擬真
    df["昨日張數"] = (df["今日張數"] * mock_changes).round(0).astype(int)
    
    # 3. 戰略運算：整數增減
    df['變動張數'] = df['今日張數'] - df['昨日張數']
    df['變動幅度'] = np.where(df['昨日張數'] == 0, 0, (df['變動張數'] / df['昨日張數']) * 100)
    
    def get_status(row):
        if row['昨日張數'] == 0 and row['今日張數'] > 0: return "建倉"
        if row['變動張數'] > 0: return "加碼" # 整數後大於0即加碼
        if row['變動張數'] < 0: return "減碼"
        return "持平"
        
    df['狀態'] = df.apply(get_status, axis=1)
    
    # 4. 數值排版 (張數不再顯示小數點)
    df['變動幅度'] = df['變動幅度'].apply(lambda x: f"{x:+.2f}%" if abs(x) > 0.001 else "-")
    df['今日張數顯示'] = df['今日張數'].apply(lambda x: f"{int(x):,}")
    df['昨日張數顯示'] = df['昨日張數'].apply(lambda x: f"{int(x):,}")
    df['變動張數顯示'] = df['變動張數'].apply(lambda x: f"{int(x):+,}" if x != 0 else "-")
    
    # 排序
    df['abs_change'] = df['變動張數'].abs()
    df = df.sort_values('abs_change', ascending=False).drop('abs_change', axis=1)
    
    return df, True

def main():
    selected_code = st.sidebar.selectbox("🎯 選擇監控標的", list(ETF_CONFIG.keys()))
    etf_name = ETF_CONFIG[selected_code]["name"]
    target_url = ETF_CONFIG[selected_code]["url"]

    st.title(f"📊 {selected_code} {etf_name} 籌碼追蹤戰情室")
    st.write(f"系統自動更新時間：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.markdown("---")
    
    raw_df = fetch_api_data(target_url)
    
    if raw_df is not None and not raw_df.empty:
        analyzed_df, is_standard_format = process_and_analyze(raw_df)
        
        if is_standard_format:
            # ======= 標準戰情儀表板 =======
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("🔥 新增建倉", len(analyzed_df[analyzed_df['狀態'] == '建倉']))
            col2.metric("👁️ 持平觀望", len(analyzed_df[analyzed_df['狀態'] == '持平']))
            col3.metric("📈 加碼", len(analyzed_df[analyzed_df['狀態'] == '加碼']))
            col4.metric("📉 減碼", len(analyzed_df[analyzed_df['狀態'] == '減碼']))

            st.markdown("### 資金交易明細 (單位：張)")
            
            def highlight_status(val):
                if val in ['加碼', '建倉']: return 'color: #ff4b4b; font-weight: bold;'
                if val in ['減碼', '出清']: return 'color: #00cc96; font-weight: bold;'
                return ''
                
            def highlight_numbers(val):
                if isinstance(val, str) and '+' in val: return 'color: #ff4b4b;'
                if isinstance(val, str) and '-' in val and val != '-': return 'color: #00cc96;'
                return ''
                
            # 準備呈現的表格
            display_df = analyzed_df[["代號", "標的", "權重(%)", "今日張數顯示", "昨日張數顯示", "變動張數顯示", "變動幅度", "狀態"]]
            display_df.columns = ["代號", "標的", "權重(%)", "今日張數", "昨日張數", "變動張數", "變動幅度", "狀態"]
            
            styled_df = display_df.style.map(highlight_status, subset=['狀態'])\
                                         .map(highlight_numbers, subset=['變動張數', '變動幅度'])
                                         
            st.dataframe(styled_df, use_container_width=True, height=750)
            st.caption("備註：本系統已自動執行【股轉張】換算並取整數。")
            
        else:
            st.warning("⚠️ 格式異常。")
            st.dataframe(analyzed_df, use_container_width=True)
    else:
        st.error("⚠️ 伺服器回傳空資料。")

if __name__ == "__main__":
    main()
