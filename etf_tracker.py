import pandas as pd
import streamlit as st
import requests
import datetime
import urllib3
import numpy as np

# 關閉不必要的 SSL 警告訊息
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="日月鑫籌碼戰情室", layout="wide")

# 💼 總裁專屬戰略物資庫：最終版 API 專線
ETF_CONFIG = {
    "00981A": {
        "name": "主動統一台股增長",
        "url": "https://pscnetsecrwd.moneydj.com/b2brwdCommon/jsondata/8f/d7/10/twetfdata.xdjjson?x=etf-Basic0005-1&a=00981A.TW&revision=910d22a1-3e10-48a1-8144-35b8a0267f0e"
    },
    "00403A": {
        "name": "統一台股升級 50",
        # 總裁最新截獲之專線
        "url": "https://pscnetsecrwd.moneydj.com/b2brwdCommon/jsondata/61/ff/e8/twetfdata.xdjjson?x=etf-Basic0005&a=00403A.TW&revision=2018_07_31_1"
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
    # 智慧防呆：確認資料庫是否有 V2 (股票代號) 欄位
    if "V2" not in df.columns:
        return df, False # 回傳 False 代表格式不符，直接顯示原始資料
        
    # 1. 欄位翻譯與精煉
    df = df.rename(columns={"V2": "代號", "V3": "標的", "V4": "權重(%)", "V5": "今日張數"})
    df = df[["代號", "標的", "權重(%)", "今日張數"]]
    
    df["今日張數"] = pd.to_numeric(df["今日張數"], errors='coerce').fillna(0)
    df["權重(%)"] = pd.to_numeric(df["權重(%)"], errors='coerce').fillna(0)
    
    # 2. 模擬 T-1 日庫存 (建立變動基準)
    np.random.seed(42) # 固定亂數種子讓模擬結果穩定
    mock_changes = np.random.uniform(0.95, 1.05, size=len(df))
    df["昨日張數"] = (df["今日張數"] * mock_changes).astype(int)
    
    # 3. 戰略運算：找出建倉與加減碼
    df['變動張數'] = df['今日張數'] - df['昨日張數']
    df['變動幅度'] = np.where(df['昨日張數'] == 0, 0, (df['變動張數'] / df['昨日張數']) * 100)
    
    def get_status(row):
        if row['昨日張數'] == 0 and row['今日張數'] > 0: return "建倉"
        if row['變動張數'] > 0: return "加碼"
        if row['變動張數'] < 0: return "減碼"
        return "持平"
        
    df['狀態'] = df.apply(get_status, axis=1)
    
    # 4. 數值排版優化 (千分位與正負號)
    df['變動幅度'] = df['變動幅度'].apply(lambda x: f"{x:+.2f}%" if x != 0 else "-")
    df['今日張數'] = df['今日張數'].apply(lambda x: f"{int(x):,}")
    df['變動張數'] = df['變動張數'].apply(lambda x: f"{int(x):+,}" if x != 0 else "-")
    
    # 以變動張數絕對值排序，把最需要關注的飆股排在最前面
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
            # ======= 標準戰情儀表板 =======
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("🔥 新增建倉 (潛力股)", len(analyzed_df[analyzed_df['狀態'] == '建倉']))
            col2.metric("👁️ 持平觀望", len(analyzed_df[analyzed_df['狀態'] == '持平']))
            col3.metric("📈 加碼 (趨勢向上)", len(analyzed_df[analyzed_df['狀態'] == '加碼']))
            col4.metric("📉 減碼 (籌碼轉弱)", len(analyzed_df[analyzed_df['狀態'] == '減碼']))

            st.markdown("### 資金交易明細")
            
            # 設定視覺化紅綠燈邏輯
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
            # ======= 格式異常診斷面板 =======
            st.warning("⚠️ 專線連線成功，但偵測到欄位格式與預期不同 (可能是產業比例而非持股明細)。")
            st.markdown("### 📡 原始 API 數據庫內容")
            st.dataframe(analyzed_df, use_container_width=True)
            st.info("💡 總裁提示：若此為 00403A，請檢查網址參數是否應加上 '-1' (即 etf-Basic0005-1)。")
            
    elif isinstance(raw_df, str):
        st.error(f"連線異常：{raw_df}")
    else:
        st.error("⚠️ 伺服器回傳空資料。")

if __name__ == "__main__":
    main()
