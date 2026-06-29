import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="Rekomendasi Saham Alpha Vantage", layout="wide")
st.title("📈 Aplikasi Analisis Saham (Alpha Vantage)")
st.markdown("Aplikasi ini menggunakan data resmi dari Alpha Vantage API dan indikator RSI.")

# --- Ambil API Key dari Streamlit Secrets ---
# Jangan tulis API Key langsung di sini agar aman!
try:
    API_KEY = st.secrets["ALPHA_VANTAGE_KEY"]
except:
    st.error("API Key belum dikonfigurasi di Streamlit Cloud Secrets.")
    st.stop()

# --- Fungsi Mengambil Data dari Alpha Vantage ---
def get_stock_data(symbol, api_key):
    # Menggunakan fungsi TIME_SERIES_DAILY untuk data harian
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={api_key}"
    response = requests.get(url)
    data = response.json()
    
    # Validasi jika terjadi error atau batasan limit API gratis harian tercapai
    if "Time Series (Daily)" not in data:
        return pd.DataFrame()
        
    # Mengubah JSON menjadi DataFrame Pandas
    df = pd.DataFrame.from_dict(data["Time Series (Daily)"], orient="index")
    
    # Membersihkan nama kolom (Alpha Vantage menggunakan awalan angka seperti '1. open')
    df = df.rename(columns={
        "1. open": "Open",
        "2. high": "High",
        "3. low": "Low",
        "4. close": "Close",
        "5. volume": "Volume"
    })
    
    # Mengubah tipe data menjadi float dan mengurutkan dari tanggal terlama
    df = df.astype(float)
    df = df.sort_index(ascending=True)
    return df

# --- Fungsi Menghitung RSI ---
def calculate_rsi(data, window=14):
    delta = data['Close'].diff(1)
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    
    avg_gain = pd.Series(gain).rolling(window=window, min_periods=1).mean()
    avg_loss = pd.Series(loss).rolling(window=window, min_periods=1).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# --- Sidebar Input ---
st.sidebar.header("Pengaturan")
# Catatan: Untuk Alpha Vantage, saham Indonesia biasanya menggunakan akhiran .JKT (contoh: BBCA.JKT)
ticker_symbol = st.sidebar.text_input("Masukkan Kode Saham (Contoh: BBCA.JKT, AAPL, TSLA)", "BBCA.JKT")

if st.sidebar.button("Analisis Sekarang"):
    with st.spinner(f'Mengambil data dari Alpha Vantage untuk {ticker_symbol}...'):
        df = get_stock_data(ticker_symbol, API_KEY)
        
        if df.empty:
            st.error("Gagal mengambil data. Pastikan kode saham benar atau limit API gratis Anda belum habis (5 requests per menit).")
        else:
            # Hitung RSI
            df['RSI'] = calculate_rsi(df)
            
            # Data terbaru
            latest_close = df['Close'].iloc[-1]
            latest_rsi = df['RSI'].iloc[-1]
            
            # Logika Rekomendasi
            if latest_rsi < 30:
                recommendation = "🟢 BELI (Oversold)"
            elif latest_rsi > 70:
                recommendation = "🔴 JUAL (Overbought)"
            else:
                recommendation = "🟡 TAHAN (Netral)"
                
            # Menampilkan Metrik
            col1, col2, col3 = st.columns(3)
            col1.metric("Harga Terakhir", f"{latest_close:,.2f}")
            col2.metric("Nilai RSI (14)", f"{latest_rsi:.2f}")
            col3.metric("Rekomendasi Sistem", recommendation)
            
            st.divider()
            
            # Visualisasi Grafik
            st.subheader(f"Grafik Harga Harian: {ticker_symbol}")
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df.index,
                            open=df['Open'],
                            high=df['High'],
                            low=df['Low'],
                            close=df['Close'],
                            name='Market Data'))
            
            fig.update_layout(xaxis_rangeslider_visible=False, height=500)
            st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("Lihat Data Mentah"):
                st.dataframe(df.tail(10))
