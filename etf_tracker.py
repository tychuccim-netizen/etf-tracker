import pandas as pd
import streamlit as st
import requests
from bs4 import BeautifulSoup
import datetime
import urllib3

# 關閉不必要的 SSL 警告訊息
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="日月鑫籌碼戰情室", layout="wide")

ETF_CONFIG = {
    "00981A": {
        "name": "主動統一台股增長",
        "url": "https://www.pscnet.com.tw/pscnetStock/menuContent.do?main_id=38b3f10a07000000083acb70970ca6cb&sub_id=38d1d31174000000ce140c65c110c18122"
    },
    "00403A": {
        "name": "統一台股升級 50",
        "url": "https://www.pscnet.com.tw/pscnetStock/menuContent.do?main_id=38b3f10a07000000083acb70970ca6cb&sub_id=38d1d31174000000ce140c65c110c181"
    }
}

@st.cache_data(ttl=3600)
def fetch_real_market_data(url):
    """
    終極深度解析引擎 (Deep Crawler)
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        # 強制突破防線，取得原始網頁代碼
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        response.encoding = 'utf-8'
        
        # 啟動 BeautifulSoup 深度清洗網頁
        soup = BeautifulSoup(response.text, 'html5lib') # 使用最強的 html5lib 容錯解析器
        
        # 鎖定網頁中所有的 <table> 標籤
        tables = soup.find_all('table')
        
        if not tables:
            return "解析失敗：雖然連線成功，但無法在該網頁的結構中找到任何標準的 <table> 標籤。"
            
        # 將找到的 HTML 表格轉為 Pandas DataFrame
        df_list = []
        for table in tables:
            try:
                df = pd.read_html(str(table))[0]
                # 排除完全空白的無效表格
                if not df.empty and len(df.columns) > 1:
                    df_list.append(df)
            except:
                continue
                
        if df_list:
             return df_list
        else:
             return "解析異常：找到表格標籤，但內容為空或無法轉換。"
             
    except Exception as e:
        return f"深度連線異常：{str(e)}"

def main():
    selected_code = st.sidebar.selectbox("🎯 選擇監控標的", list(ETF_CONFIG.keys()))
    etf_name = ETF_CONFIG[selected_code]["name"]
    target_url = ETF_CONFIG[selected_code]["url"]

    st.title(f"📊 {selected_code} {etf_name} 真實籌碼探測雷達")
    st.write(f"系統更新時間：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.markdown("---")
    
    st.info(f"🔄 深度解析晶片啟動，正在過濾 {selected_code} 官網原始代碼...")
    
    extracted_data = fetch_real_market_data(target_url)
    
    if isinstance(extracted_data, list):
        st.success(f"✅ 深度解析成功！系統成功從亂碼中提煉出 {len(extracted_data)} 個有效資料表。")
        
        st.markdown("### 📡 提煉後之真實數據 (Cleaned Data)")
        for i, df in enumerate(extracted_data):
            st.write(f"**資料庫 {i+1}** (共 {len(df)} 筆持股紀錄)")
            st.dataframe(df, use_container_width=True)
            
    elif isinstance(extracted_data, str):
        st.error(f"⚠️ 雷達警示：{extracted_data}")

if __name__ == "__main__":
    main()
