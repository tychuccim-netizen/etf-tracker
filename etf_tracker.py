import pandas as pd
import streamlit as st
import requests
import datetime
import urllib3

# 關閉不必要的 SSL 警告訊息
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="日月鑫籌碼戰情室", layout="wide")

# 💼 總裁專屬戰略物資庫：API 專線網址
ETF_CONFIG = {
    "00981A": {
        "name": "主動統一台股增長",
        "url": "https://pscnetsecrwd.moneydj.com/b2brwdCommon/jsondata/8f/d7/10/twetfdata.xdjjson?x=etf-Basic0005-1&a=00981A.TW&revision=910d22a1-3e10-48a1-8144-35b8a0267f0e"
    },
    "00403A": {
        "name": "統一台股升級 50",
        "url": "https://pscnetsecrwd.moneydj.com/b2brwdCommon/jsondata/61/ff/e8/twetfdata.xdjjson?x=etf-Basic0005&a=00403A.TW&revision=910d22a1-3e10-48a1-8144-35b8a0267f0e"
    }
}

@st.cache_data(ttl=3600)
def fetch_api_data(url):
    """
    API 專線直連引擎 (JSON Parser)
    捨棄繁雜網頁解析，直接提取純淨數據庫
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        # 透過專線呼叫資料
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        response.encoding = 'utf-8'
        
        # 直接解析 JSON 核心數據
        data = response.json()
        
        # MoneyDJ 的 API 結構通常封裝在 ResultSet 的 Result 陣列中
        if 'ResultSet' in data and 'Result' in data['ResultSet']:
            records = data['ResultSet']['Result']
            df = pd.DataFrame(records)
            return df
        else:
            # 若結構有異，將整包資料轉為表格供總裁檢視
            return pd.DataFrame(data)
            
    except Exception as e:
        return f"API 連線異常：{str(e)}"

def main():
    selected_code = st.sidebar.selectbox("🎯 選擇監控標的", list(ETF_CONFIG.keys()))
    etf_name = ETF_CONFIG[selected_code]["name"]
    target_url = ETF_CONFIG[selected_code]["url"]

    st.title(f"📊 {selected_code} {etf_name} 真實籌碼探測雷達")
    st.write(f"系統更新時間：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.markdown("---")
    
    st.info(f"⚡ 正在透過 VIP 專屬 API 高速下載 {selected_code} 核心數據庫...")
    
    df = fetch_api_data(target_url)
    
    if isinstance(df, pd.DataFrame):
        if df.empty:
            st.warning("✅ 專線連線成功，但目前伺服器回傳空資料。")
        else:
            st.success(f"✅ 專線直連成功！瞬間載入 {len(df)} 筆純淨真實數據。")
            
            st.markdown("### 📡 核心數據庫原始內容 (API Raw Data)")
            st.dataframe(df, use_container_width=True)
            
    elif isinstance(df, str):
        st.error(f"⚠️ 雷達警示：{df}")

if __name__ == "__main__":
    main()
