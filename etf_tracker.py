import pandas as pd
import streamlit as st
import requests
import datetime
import urllib3
import os

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

HISTORY_FILE = "etf_history.csv"

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

def process_and_analyze(df, code):
    if "V2" not in df.columns: return df, False 
        
    # 1. 今日數據清洗 (股轉張)
    df["今日張數"] = (pd.to_numeric(df["V5"], errors='coerce').fillna(0) / 1000).round(0).astype(int)
    df = df.rename(columns={"V2": "代號", "V3": "標的", "V4": "權重(%)"})
    df = df[["代號", "標的", "權重(%)", "今日張數"]]
    
    # 2. 核心：讀取歷史存檔進行真實 T-1 比對
    # 若無歷史檔案，則暫時以今日數據作為基準
    df["昨日張數"] = df["今日張數"] 
    if os.path.exists(HISTORY_FILE):
        try:
            hist_df = pd.read_csv(HISTORY_FILE)
            # 僅篩選該 ETF 昨天的紀錄
            yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
            prev_data = hist_df[(hist_df['ETF'] == code) & (hist_df['日期'] < datetime.datetime.now().strftime('%Y-%m-%d'))]
            if not prev_data.empty:
                # 取得最近一次的紀錄進行對位
                latest_date = prev_data['日期'].max()
                prev_record = prev_data[prev_data['日期'] == latest_date]
                df = df.merge(prev_record[['代號', '今日張數']], on='代號', how='left', suffixes=('', '_prev'))
                df["昨日張數"] = df["今日張數_prev"].fillna(0).astype(int)
        except:
            pass

    # 3. 戰略運算
    df['變動張數'] = df['今日張數'] - df['昨日張數']
    df['變動幅度'] = np.where(df['昨日張數'] == 0, 0, (df['變動張數'] / df['昨日張數']) * 100)
    
    def get_status(row):
        if row['昨日張數'] == 0 and row['今日張數'] > 0: return "建倉"
        if row['變動張數'] > 0: return "加碼"
        if row['變動張數'] < 0: return "減碼"
        return "持平"
        
    df['狀態'] = df.apply(get_status, axis=1)
    
    # 4. 格式排版
    df['變動幅度顯示'] = df['變動幅度'].apply(lambda x: f"{x:+.2f}%" if abs(x) > 0.01 else "-")
    df['今日張數顯示'] = df['今日張數'].apply(lambda x: f"{int(x):,}")
    df['變動張數顯示'] = df['變動張數'].apply(lambda x: f"{int(x):+,}" if x != 0 else "-")
    
    return df.sort_values('變動張數', ascending=False), True

def main():
    selected_code = st.sidebar.selectbox("🎯 選擇監控標的", list(ETF_CONFIG.keys()))
    etf_name = ETF_CONFIG[selected_code]["name"]
    target_url = ETF_CONFIG[selected_code]["url"]

    st.title(f"📊 {selected_code} {etf_name} 籌碼追蹤戰情室")
    st.write(f"系統自動更新時間：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.markdown("---")
    
    raw_df = fetch_api_data(target_url)
    
    if raw_df is not None and not raw_df.empty:
        import numpy as np
        analyzed_df, is_standard = process_and_analyze(raw_df, selected_code)
        
        if is_standard:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("🔥 新增建倉", len(analyzed_df[analyzed_df['狀態'] == '建倉']))
            col2.metric("👁️ 持平觀望", len(analyzed_df[analyzed_df['狀態'] == '持平']))
            col3.metric("📈 加碼", len(analyzed_df[analyzed_df['狀態'] == '加碼']))
            col4.metric("📉 減碼", len(analyzed_df[analyzed_df['狀態'] == '減碼']))

            # 呈現表格
            styled_df = analyzed_df[["代號", "標的", "權重(%)", "今日張數顯示", "昨日張數", "變動張數顯示", "變動幅度顯示", "狀態"]]
            styled_df.columns = ["代號", "標的", "權重(%)", "今日張數", "昨日張數", "變動張數", "變動幅度", "狀態"]
            
            st.dataframe(styled_df, use_container_width=True, height=750)
            st.info("💡 系統已啟動歷史對位機制。若昨日數據尚未入庫，變動將顯示為持平。")
    else:
        st.error("⚠️ 數據獲取失敗。")

if __name__ == "__main__":
    main()
