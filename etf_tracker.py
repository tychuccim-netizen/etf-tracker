import pandas as pd
import streamlit as st
import requests
import datetime
import urllib3
import os
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
    if "V2" not in df.columns: return df, False, "未知"

    # 💡 提取官方資料日期 (防呆雷達)
    api_date = df['V1'].iloc[0] if 'V1' in df.columns else "未知"

    # 1. 今日數據清洗 (股轉張)
    df["今日張數"] = (pd.to_numeric(df["V5"], errors='coerce').fillna(0) / 1000).round(0).astype(int)
    df = df.rename(columns={"V2": "代號", "V3": "標的", "V4": "權重(%)"})
    df = df[["代號", "標的", "權重(%)", "今日張數"]]

    # 2. 歷史對位 (真實比對)
    df["昨日張數"] = df["今日張數"] 
    if os.path.exists(HISTORY_FILE):
        try:
            hist_df = pd.read_csv(HISTORY_FILE)
            today_str = datetime.datetime.now().strftime('%Y-%m-%d')
            # 找尋歷史檔案中小於今日的最新紀錄
            prev_data = hist_df[(hist_df['ETF'] == code) & (hist_df['日期'] < today_str)]
            if not prev_data.empty:
                latest_date = prev_data['日期'].max()
                prev_record = prev_data[prev_data['日期'] == latest_date]
                df = df.merge(prev_record[['代號', '今日張數']], on='代號', how='left', suffixes=('', '_prev'))
                # 若歷史檔案中無此檔股票，昨日張數預設與今日相同(視為建倉或持平)
                df["昨日張數"] = df["今日張數_prev"].fillna(df["今日張數"]).astype(int)
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
    
    # 排序：以變動絕對值排序
    df['abs_change'] = df['變動張數'].abs()
    df = df.sort_values('abs_change', ascending=False).drop('abs_change', axis=1)
    
    return df, True, api_date

def main():
    selected_code = st.sidebar.selectbox("🎯 選擇監控標的", list(ETF_CONFIG.keys()))
    etf_name = ETF_CONFIG[selected_code]["name"]
    target_url = ETF_CONFIG[selected_code]["url"]

    st.title(f"📊 {selected_code} {etf_name} 籌碼追蹤戰情室")
    st.write(f"系統自動更新時間：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.markdown("---")
    
    raw_df = fetch_api_data(target_url)
    
    if raw_df is not None and not raw_df.empty:
        analyzed_df, is_standard, api_date = process_and_analyze(raw_df, selected_code)
        
        if is_standard:
            # 💡 官方資料日期雷達
            st.info(f"📡 官方資料庫最新結算日期：**{api_date}**")

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("🔥 新增建倉", len(analyzed_df[analyzed_df['狀態'] == '建倉']))
            col2.metric("👁️ 持平觀望", len(analyzed_df[analyzed_df['狀態'] == '持平']))
            col3.metric("📈 加碼", len(analyzed_df[analyzed_df['狀態'] == '加碼']))
            col4.metric("📉 減碼", len(analyzed_df[analyzed_df['狀態'] == '減碼']))

            # 呈現表格
            display_df = analyzed_df[["代號", "標的", "權重(%)", "今日張數顯示", "昨日張數", "變動張數顯示", "變動幅度顯示", "狀態"]]
            display_df.columns = ["代號", "標的", "權重(%)", "今日張數", "昨日張數", "變動張數", "變動幅度", "狀態"]
            
            def highlight_status(val):
                if val in ['加碼', '建倉']: return 'color: #ff4b4b; font-weight: bold;'
                if val in ['減碼', '出清']: return 'color: #00cc96; font-weight: bold;'
                return ''
                
            def highlight_numbers(val):
                if isinstance(val, str) and '+' in val: return 'color: #ff4b4b;'
                if isinstance(val, str) and '-' in val and val != '-': return 'color: #00cc96;'
                return ''
                
            styled_df = display_df.style.map(highlight_status, subset=['狀態'])\
                                         .map(highlight_numbers, subset=['變動張數', '變動幅度'])
                                         
            st.dataframe(styled_df, use_container_width=True, height=750)
            
            if os.path.exists(HISTORY_FILE):
                st.success("✅ 系統已成功連結歷史數據庫，正在執行真實對位分析。")
            else:
                st.info("💡 系統目前尚未讀取到歷史存檔，首日變動將暫以持平顯示。")
        else:
            st.warning("⚠️ 格式異常。")
            st.dataframe(analyzed_df, use_container_width=True)
    else:
        st.error("⚠️ 數據獲取失敗。")

if __name__ == "__main__":
    main()
