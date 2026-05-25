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
        # 💡 修正點 1：強制使用 utf-8 解碼，徹底解決標的名稱亂碼問題
        response.encoding = 'utf-8'
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
    
    # 💡 修正點 2：強制將今日代號全部轉為文字型態 (str)
    df["代號"] = df["代號"].astype(str).str.strip()
    df = df[["代號", "標的", "權重(%)", "今日張數"]]

    # 核心：強制進行跨日對位
    df["昨日張數"] = df["今日張數"]
    if os.path.exists(HISTORY_FILE):
        try:
            # 💡 修正點 3：讀取歷史檔案時，強制將代號欄位以文字型態(str)讀入，避免型態衝突
            hist_df = pd.read_csv(HISTORY_FILE, dtype={"代號": str})
            hist_df["代號"] = hist_df["代號"].astype(str).str.strip()
            
            today_str = datetime.datetime.now().strftime('%Y-%m-%d')
            prev_records = hist_df[(hist_df['ETF'] == code) & (hist_df['日期'] != today_str)]
            
            if not prev_records.empty:
                latest_date = prev_records['日期'].max()
                prev_day_data = prev_records[prev_records['日期'] == latest_date]
                
                # 執行乾淨的文字對位 merge
                df = df.merge(prev_day_data[['代號', '今日張數']], on='代號', how='left', suffixes=('', '_prev'))
                df["昨日張數"] = df["今日張數_prev"].fillna(df["今日張數"]).astype(int)
                # 移除 merge 出來的暫存欄位
                if "今日張數_prev" in df.columns:
                    df = df.drop(columns=["今日張數_prev"])
        except Exception as e:
            st.warning(f"資產庫對位提示: {e}")

    # 戰略運算
    df['變動張數'] = df['今日張數'] - df['昨日張數']
    df['變動幅度'] = np.where(df['昨日張數'] == 0, 0, (df['變動張數'] / df['昨日張數']) * 100)
    
    df['狀態'] = df.apply(lambda r: "加碼" if r['變動張數'] > 0 else ("減碼" if r['變動張數'] < 0 else "持平"), axis=1)
    
    df['變動幅度顯示'] = df['變動幅度'].apply(lambda x: f"{x:+.2f}%" if abs(x) > 0.01 else "-")
    df['今日張數顯示'] = df['今日張數'].apply(lambda x: f"{int(x):,}")
    df['變動張數顯示'] = df['變動張數'].apply(lambda x: f"{int(x):+,}" if x != 0 else "-")
    
    return df.sort_values(by='變動張數', key=abs, ascending=False), True, api_date

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
            
            col1, col2, col3 = st.columns(3)
            col1.metric("👁️ 持平觀望", len(analyzed_df[analyzed_df['狀態'] == '持平']))
            col2.metric("📈 法人加碼", len(analyzed_df[analyzed_df['狀態'] == '加碼']))
            col3.metric("📉 法人減碼", len(analyzed_df[analyzed_df['狀態'] == '減碼']))

            display_df = analyzed_df[["代號", "標的", "權重(%)", "今日張數顯示", "昨日張數", "變動張數顯示", "變動幅度顯示", "狀態"]]
            display_df.columns = ["代號", "標的", "權重(%)", "今日張數", "昨日張數", "變動張數", "變動幅度", "狀態"]
            
            styled_df = display_df.style.map(lambda v: 'color: #ff4b4b; font-weight: bold;' if v=='加碼' else ('color: #00cc96; font-weight: bold;' if v=='減碼' else ''), subset=['狀態'])\
                                         .map(lambda v: 'color: #ff4b4b;' if isinstance(v,str) and '+' in v else ('color: #00cc96;' if isinstance(v,str) and '-' in v and v!='-' else ''), subset=['變動張數', '變動幅度'])
                                         
            st.dataframe(styled_df, use_container_width=True, height=700)
    else:
        st.error("⚠️ 數據獲取失敗。")

if __name__ == "__main__":
    main()
