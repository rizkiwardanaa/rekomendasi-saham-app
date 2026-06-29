import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="Rekomendasi Saham Real-Time", layout="wide")
st.title("📈 Aplikasi Analisis & Rekomendasi Saham")
st.markdown("Aplikasi ini menggunakan data Yahoo Finance dan indikator RSI untuk memberikan sinyal Beli/Jual.")

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

# --- Sidebar Input User ---
st.sidebar.header("Pengaturan")
# Catatan: Untuk saham Indonesia di Yahoo Finance, gunakan akhiran .JK (contoh: BBCA.JK, GOTO.JK)
ticker_symbol = st.sidebar.text_input("Masukkan Kode Saham (Contoh: BBCA.JK, AAPL, TSLA)", "BBCA.JK")
time_interval = st.sidebar.selectbox("Pilih Interval Waktu", ["1m", "5m", "15m", "1d"])
period = st.sidebar.selectbox("Pilih Periode Data", ["1d", "5d", "1mo", "3mo", "1y"])

# --- Proses Pengambilan Data ---
if st.sidebar.button("Analisis Sekarang"):
    with st.spinner(f'Mengambil data untuk {ticker_symbol}...'):
        # Mengambil data dari Yahoo Finance
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period=period, interval=time_interval)
        
        if df.empty:
            st.error("Data tidak ditemukan. Pastikan kode saham dan kombinasi interval/periode benar.")
        else:
            # Hitung RSI
            df['RSI'] = calculate_rsi(df)
            
            # Ambil data terbaru (baris terakhir)
            latest_close = df['Close'].iloc[-1]
            latest_rsi = df['RSI'].iloc[-1]
            
            # --- Logika Rekomendasi ---
            if latest_rsi < 30:
                recommendation = "🟢 BELI (Oversold)"
            elif latest_rsi > 70:
                recommendation = "🔴 JUAL (Overbought)"
            else:
                recommendation = "🟡 TAHAN (Netral)"
                
            # --- Tampilan Metrik ---
            col1, col2, col3 = st.columns(3)
            col1.metric("Harga Terakhir", f"{latest_close:,.2f}")
            col2.metric("Nilai RSI (14)", f"{latest_rsi:.2f}")
            col3.metric("Rekomendasi Sistem", recommendation)
            
            st.divider()
            
            # --- Visualisasi Grafik Interaktif ---
            st.subheader(f"Grafik Pergerakan Harga: {ticker_symbol}")
            fig = go.Figure()
            
            # Candlestick chart
            fig.add_trace(go.Candlestick(x=df.index,
                            open=df['Open'],
                            high=df['High'],
                            low=df['Low'],
                            close=df['Close'],
                            name='Market Data'))
            
            fig.update_layout(xaxis_rangeslider_visible=False, height=500)
            st.plotly_chart(fig, use_container_width=True)
            
            # Menampilkan tabel data mentah
            with st.expander("Lihat Data Mentah"):
                st.dataframe(df.tail(10))
