import pandas as pd
import streamlit as st
import requests
import datetime

# 設定網頁標題與寬版顯示
st.set_page_config(page_title="日月鑫籌碼戰情室", layout="wide")

# 💼 總裁專屬戰略物資庫：雙軌 ETF 網址設定
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

@st.cache_data(ttl=3600) # 快取機制：避免頻繁切換時重複抓取被封鎖
def fetch_real_market_data(url):
    """
    資料採集引擎 (Web Crawler)
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        # 加入 verify=False，指示系統略過嚴格的 SSL 憑證檢查
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        response.encoding = 'utf-8' # 確保繁體中文不亂碼
        
        # 尋找網頁中的所有表格
        tables = pd.read_html(response.text)
        return tables if tables else None
            
    except ValueError:
        return "解析失敗：該網頁沒有標準的 HTML 表格，可能需要更深層的技術突破。"
    except Exception as e:
        return f"連線異常：{str(e)}"

def main():
    # 🎛️ 側邊欄：戰略切換器
    selected_code = st.sidebar.selectbox("🎯 選擇監控標的", list(ETF_CONFIG.keys()))
    etf_name = ETF_CONFIG[selected_code]["name"]
    target_url = ETF_CONFIG[selected_code]["url"]

    st.title(f"📊 {selected_code} {etf_name} 真實籌碼探測雷達")
    st.write(f"系統更新時間：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.markdown("---")
    
    st.info(f"🔄 正在向統一證券官網調度資源，解析 {selected_code} 完整持股名單...")
    
    # 啟動採集引擎，並帶入對應的網址
    extracted_data = fetch_real_market_data(target_url)
    
    if isinstance(extracted_data, list):
        st.success(f"✅ 成功突破防線！系統在該網址中掃描到 {len(extracted_data)} 個資料表。")
        
        st.markdown("### 📡 原始數據截獲清單 (Raw Data)")
        for i, df in enumerate(extracted_data):
            st.write(f"**表格 {i+1}** (共 {len(df)} 筆資料)")
            st.dataframe(df, use_container_width=True)
            
    elif isinstance(extracted_data, str):
        st.error(f"⚠️ 雷達警示：{extracted_data}")
    else:
        st.warning("網頁連線成功，但未能辨識出標準的表格結構。")

if __name__ == "__main__":
    main()
