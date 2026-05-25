import pandas as pd
import streamlit as st
import requests
import datetime
import urllib3
import os
import numpy as np

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="日月鑫籌碼戰情室", layout="wide")

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

@st.cache_data(ttl=60)
def fetch_api_data(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        response.encoding = 'utf-8' # 澈底解決繁體中文亂碼
        data = response.json()
        return pd.DataFrame(data['ResultSet']['Result'])
    except:
        return pd.DataFrame()

def process_and_analyze(df, code):
    if "V2" not in df.columns: return df, False, "未知"
    api_date = df['V1'].iloc[0] if 'V1' in df.columns else "未知"

    # 今日數據清洗
    df["今日張數"] = (pd.to_numeric(df["V5"], errors='coerce').fillna(0) / 1000).round(0).astype(int)
    df = df.rename(columns={"V2": "代號", "V3": "標的", "V4": "權重(%)"})
    
    df["代號"] = df["代號"].astype(str).str.strip()
    df = df[["代號", "標的", "權重(%)", "今日張數"]]

    # 核心：強制進行跨日對位 (導入建倉偵測邏輯)
    df["昨日張數"] = np.nan # 初始預設為空值，用來精準抓出「歷史上不存在」的標的
    
    if os.path.exists(HISTORY_FILE):
        try:
            hist_df = pd.read_csv(HISTORY_FILE, dtype={"代號": str})
            hist_df["代號"] = hist_df["代號"].astype(str).str.strip()
            
            today_str = datetime.datetime.now().strftime('%Y-%m-%d')
            prev_records = hist_df[(hist_df['ETF'] == code) & (hist_df['日期'] != today_str)]
            
            if not prev_records.empty:
                latest_date = prev_records['日期'].max()
                prev_day_data = prev_records[prev_records['日期'] == latest_date]
                
                df = df.merge(prev_day_data[['代號', '今日張數']], on='代號', how='left', suffixes=('', '_prev'))
                # 如果歷史檔案有這檔股票，帶入歷史張數；如果歷史檔案完全沒這檔股票，帶入 0 (代表新進建倉)
                df["昨日張數"] = df["今日張數_prev"].fillna(0).astype(int)
                
                if "今日張數_prev" in df.columns:
                    df = df.drop(columns=["今日張數_prev"])
        except Exception as e:
            st.warning(f"資產庫對位提示: {e}")

    # 如果歷史檔案不存在，昨日張數比照今日 (防呆)
    if df["昨日張數"].isnull().all():
        df["昨日張數"] = df["今日張數"]

    # 🎯 戰略運算：精準判定加碼、減碼與【新進建倉】
    df['變動張數'] = df['今日張數'] - df['昨日張數']
    df['變動幅度'] = np.where(df['開盤前基數'] == 0, 0, (df['變動張數'] / df['昨日張數']) * 100) # 防除以0
    df['變動幅度'] = np.where((df['昨日張數'] == 0) & (df['今日張數'] > 0), 100.0, df['變動幅度']) # 建倉定義為 100% 噴出
    
    # 判斷狀態
    def judge_status(row):
        if row['昨日張數'] == 0 and row['今日張數'] > 0:
            return "💥 新進建倉"
        elif row['變動張數'] > 0:
            return "加碼"
        elif row['變動張數'] < 0:
            return "減碼"
        else:
            return "持平"
            
    df['狀態'] = df.apply(judge_status, axis=1)
    
    df['變動幅度顯示'] = df['變動幅度'].apply(lambda x: f"{x:+.2f}%" if abs(x) > 0.01 else "-")
    df['今日張數顯示'] = df['今日張數'].apply(lambda x: f"{int(x):,}")
    df['變動張數顯示'] = df['變動張數'].apply(lambda x: f"{int(x):+,}" if x != 0 else "-")
    
    # 讓「新進建倉」和「大變動」的股票強制排在最前面
    df['排序權重'] = np.where(df['狀態'] == '💥 新進建倉', 999999, df['變動張數'].abs())
    return df.sort_values(by='排序權重', ascending=False).drop(columns=['排序權重']), True, api_date

def main():
    selected_code = st.sidebar.selectbox("🎯 選擇監控標的", list(ETF_CONFIG.keys()))
    etf_name = ETF_CONFIG[selected_code]["name"]
    target_url = ETF_CONFIG[selected_code]["url"]

    st.title(f"📊 {selected_code} {etf_name} 籌碼追蹤戰情室")
    st.write(f"系統即時同步時間：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.markdown("---")
    
    raw_df = fetch_api_data(target_url)
    
    if raw_df is not None and not raw_df.empty:
        analyzed_df, is_standard, api_date = process_and_analyze(raw_df, selected_code)
        
        if is_standard:
            st.info(f"📡 官方資料庫最新結算日期：**{api_date}**")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("👁️ 持平觀望", len(analyzed_df[analyzed_df['狀態'] == '持平']))
            col2.metric("📈 法人加碼", len(analyzed_df[analyzed_df['狀態'] == '加碼']))
            col3.metric("📉 法人減碼", len(analyzed_df[analyzed_df['狀態'] == '減碼']))
            col4.metric("💥 新進建倉", len(analyzed_df[analyzed_df['狀態'] == '💥 新進建倉']))

            display_df = analyzed_df[["代號", "標的", "權重(%)", "今日張數顯示", "昨日張數", "變動張數顯示", "變動幅度顯示", "狀態"]]
            display_df.columns = ["代號", "標的", "權重(%)", "今日張數", "昨日張數", "變動張數", "變動幅度", "狀態"]
            
            # 視覺化紅綠燈增強版
            def style_status(v):
                if v == '💥 新進建倉': return 'background-color: #ffe6e6; color: #ff4b4b; font-weight: bold; border: 1px solid #ff4b4b;'
                if v == '加碼': return 'color: #ff4b4b; font-weight: bold;'
                if v == '減碼': return 'color: #00cc96; font-weight: bold;'
                return ''
                
            styled_df = display_df.style.map(style_status, subset=['狀態'])\
                                         .map(lambda v: 'color: #ff4b4b;' if isinstance(v,str) and '+' in v else ('color: #00cc96;' if isinstance(v,str) and '-' in v and v!='-' else ''), subset=['變動張數', '變動幅度'])
                                         
            st.dataframe(styled_df, use_container_width=True, height=700)
    else:
        st.error("⚠️ 數據獲取失敗。")

if __name__ == "__main__":
    main()
