import pandas as pd
import streamlit as st
import requests
import datetime
import urllib3
import numpy as np

# 關閉不必要的 SSL 警告訊息
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="日月鑫籌碼戰情室", layout="wide")

# 💼 總裁專屬戰略物資庫：強制校正 API 參數版
ETF_CONFIG = {
    "00981A": {
        "name": "主動統一台股增長",
        "url": "https://pscnetsecrwd.moneydj.com/b2brwdCommon/jsondata/8f/d7/10/twetfdata.xdjjson?x=etf-Basic0005-1&a=00981A.TW&revision=910d22a1-3e10-48a1-8144-35b8a0267f0e"
    },
    "00403A": {
        "name": "統一台股升級 50",
        # 戰略破解：強制將參數改為 etf-Basic0005-1，直搗持股明細資料夾
        "url": "https://pscnetsecrwd.moneydj.com/b2brwdCommon/jsondata/61/ff/e8/twetfdata.xdjjson?x=etf-Basic0005-1&a=00403A.TW&revision=910d22a1-3e10-48a1-8144-35b8a0267f0e"
    }
}

@st.cache_data(ttl=3600)
def fetch_api_data(url):
    """API 專線直連引擎 (JSON Parser)"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        response.encoding = 'utf-8'
        data = response.json()
        
        # 提取核心 ResultSet -> Result
        if 'ResultSet' in data and 'Result' in data['ResultSet']:
            return pd.DataFrame(data['ResultSet']['Result'])
        return pd.DataFrame()
    except Exception as e:
        return str(e)

def process_and_analyze(df):
    """資料清洗與戰情分析模組"""
    if "V2" not in df.columns:
        return df, False 
        
    df = df.rename(columns={"V2": "代號", "V3": "標的", "V4": "權重(%)", "V5": "今日張數"})
    df = df[["代號", "標的", "權重(%)", "今日張數"]]
    
    df["今日張數"] = pd.to_numeric(df["今日張數"], errors='coerce').fillna(0)
    df["權重(%)"] = pd.to_numeric(df["權重(%)"], errors='coerce').fillna(0)
    
    # 模擬 T-1 日庫存 (建立變動基準)
    np.random.seed(42) 
    mock_changes = np.random.uniform(0.95, 1.05, size=len(df))
    df["昨日張數"] = (df["今日張數"] * mock_changes).astype(int)
    
    df['變動張數'] = df['今日張數'] - df['昨日張數']
    df['變動幅度'] = np.where(df['昨日張數'] == 0, 0, (df['變動張數'] / df['昨日張數']) * 100)
    
    def get_status(row):
        if row['昨日張數'] == 0 and row['今日張數'] > 0: return "建倉"
        if row['變動張數'] > 0: return "加碼"
        if row['變動張數'] < 0: return "減碼"
        return "持平"
        
    df['狀態'] = df.apply(get_status, axis=1)
    
    df['變動幅度'] = df['變動幅度'].apply(lambda x: f"{x:+.2f}%" if x != 0 else "-")
    df['今日張數'] = df['今日張數'].apply(lambda x: f"{int(x):,}")
    df['變動張數'] = df['變動張數'].apply(lambda x: f"{int(x):+,}" if x != 0 else "-")
    
    df['abs_change'] = df['變動張數'].apply(lambda x: abs(int(str(x).replace('+','').replace(',',''))) if x != '-' else 0)
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
    
    if isinstance(raw_df, pd.DataFrame) and not raw_df.empty:
        analyzed_df, is_standard_format = process_and_analyze(raw_df)
        
        if is_standard_format:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("🔥 新增建倉 (潛力股)", len(analyzed_df[analyzed_df['狀態'] == '建倉']))
            col2.metric("👁️ 持平觀望", len(analyzed_df[analyzed_df['狀態'] == '持平']))
            col3.metric("📈 加碼 (趨勢向上)", len(analyzed_df[analyzed_df['狀態'] == '加碼']))
            col4.metric("📉 減碼 (籌碼轉弱)", len(analyzed_df[analyzed_df['狀態'] == '減碼']))

            st.markdown("### 資金交易明細")
            
            def highlight_status(val):
                if val in ['加碼', '建倉']: return 'color: #ff4b4b; font-weight: bold;'
                if val in ['減碼', '出清']: return 'color: #00cc96; font-weight: bold;'
                return ''
                
            def highlight_numbers(val):
                if isinstance(val, str) and '+' in val: return 'color: #ff4b4b;'
                if isinstance(val, str) and '-' in val and val != '-': return 'color: #00cc96;'
                return ''
                
            styled_df = analyzed_df.style.map(highlight_status, subset=['狀態'])\
                                         .map(highlight_numbers, subset=['變動張數', '變動幅度'])
                                         
            st.dataframe(styled_df, use_container_width=True, height=700)
            st.caption("備註：本系統已串接 API，目前『昨日張數』採趨勢模擬運算以展示戰情室 UI，下一階段將介接實體資料庫進行 T-1 比對。")
            
        else:
            st.warning("⚠️ 專線連線成功，但偵測到欄位格式與預期不同。")
            st.dataframe(analyzed_df, use_container_width=True)
            
    elif isinstance(raw_df, str):
        st.error(f"連線異常：{raw_df}")
    else:
        st.error("⚠️ 伺服器回傳空資料。")
        st.info("💡 總裁戰略洞察：我們已強制鎖定持股明細參數 (-1)。若依然為空，代表統一投信/證券端尚未將 00403A 的『持股明細』匯入至 MoneyDJ 的 API 系統中（新發行 ETF 常見現象）。建議後續幾日持續監控。")

if __name__ == "__main__":
    main()
