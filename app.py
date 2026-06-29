import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import yfinance as yf

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Rekomendasi Saham & Robo-Advisor", layout="wide")
st.title("📈 Asisten Investasi Pribadi & Analisis Saham")
st.markdown("Aplikasi ini membantu Anda menganalisis saham dan merencanakan alokasi aset dengan mudah.")

# --- 2. PERSIAPAN API KEY ---
try:
    API_KEY = st.secrets["ALPHA_VANTAGE_KEY"]
except:
    st.error("API Key belum dikonfigurasi di Streamlit Cloud Secrets.")
    st.stop()

# --- 3. FUNGSI PENGAMBILAN & PEMROSESAN DATA ---

@st.cache_data(ttl=3600) # Cache kurs selama 1 jam agar lebih cepat
def get_usd_to_idr():
    """Mengambil kurs USD ke IDR terbaru menggunakan Yahoo Finance"""
    try:
        ticker = yf.Ticker("USDIDR=X")
        df = ticker.history(period="1d")
        return float(df['Close'].iloc[-1])
    except:
        st.warning("Gagal mengambil kurs terbaru. Menggunakan kurs estimasi (Rp 15.500).")
        return 15500.0

def get_stock_data(symbol, api_key):
    """Mengambil data riwayat harga harian dari Alpha Vantage"""
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={api_key}"
    response = requests.get(url)
    data = response.json()
    
    if "Time Series (Daily)" not in data:
        st.warning(f"Pesan asli dari server Alpha Vantage: {data}")
        return pd.DataFrame()
        
    df = pd.DataFrame.from_dict(data["Time Series (Daily)"], orient="index")
    
    df = df.rename(columns={
        "1. open": "Open",
        "2. high": "High",
        "3. low": "Low",
        "4. close": "Close",
        "5. volume": "Volume"
    })
    
    df = df.astype(float)
    df = df.sort_index(ascending=True)
    return df

def calculate_rsi(data, window=14):
    """Menghitung indikator Relative Strength Index (RSI)"""
    delta = data['Close'].diff(1)
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    
    avg_gain = pd.Series(gain).rolling(window=window, min_periods=1).mean()
    avg_loss = pd.Series(loss).rolling(window=window, min_periods=1).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def get_asset_allocation(risk_profile, total_capital):
    """Logika Konsultan (Robo-Advisor) berdasarkan profil risiko"""
    if risk_profile == "Konservatif (Cari Aman)":
        alloc = {"Pasar Uang (Risiko Rendah)": 0.60, "Obligasi (Risiko Menengah)": 0.30, "Saham (Risiko Tinggi)": 0.10}
        desc = "Karena Anda memilih jalur aman, kami menyarankan sebagian besar uang Anda disimpan di instrumen yang stabil seperti Deposito atau Reksadana Pasar Uang agar tidak tergerus saat pasar saham sedang turun."
    elif risk_profile == "Moderat (Seimbang)":
        alloc = {"Pasar Uang (Risiko Rendah)": 0.20, "Obligasi (Risiko Menengah)": 0.40, "Saham (Risiko Tinggi)": 0.40}
        desc = "Strategi yang seimbang. Anda siap menerima sedikit risiko penurunan nilai demi mendapatkan keuntungan yang lebih besar daripada sekadar menabung di bank."
    else: # Agresif
        alloc = {"Pasar Uang (Risiko Rendah)": 0.10, "Obligasi (Risiko Menengah)": 0.20, "Saham (Risiko Tinggi)": 0.70}
        desc = "Strategi agresif! Anda fokus pada pertumbuhan kekayaan jangka panjang dan siap melihat uang Anda naik-turun dengan tajam dalam jangka pendek. Sebagian besar dana masuk ke pasar saham."
        
    nominal = {k: v * total_capital for k, v in alloc.items()}
    return alloc, nominal, desc

# --- 4. BAGIAN UTAMA: ANALISIS SAHAM ---
st.sidebar.header("Pengaturan Analisis")
ticker_symbol = st.sidebar.text_input("Masukkan Kode Saham (Contoh: AAPL, BBCA)", "AAPL")

if st.sidebar.button("Analisis Saham Sekarang"):
    with st.spinner(f'Mengambil data untuk {ticker_symbol} dan mengonversi kurs...'):
        # 1. Ambil Data Kurs & Saham
        kurs_idr = get_usd_to_idr()
        df = get_stock_data(ticker_symbol, API_KEY)
        
        if df.empty:
            st.error("Gagal memproses data. Silakan periksa kembali kode saham atau tunggu sebentar jika terkena limit API.")
        else:
            # 2. Konversi Harga USD ke IDR
            kolom_harga = ['Open', 'High', 'Low', 'Close']
            df[kolom_harga] = df[kolom_harga] * kurs_idr
            
            # 3. Hitung Indikator
            df['RSI'] = calculate_rsi(df)
            
            # 4. Ambil Angka Terbaru
            latest_close = df['Close'].iloc[-1]
            latest_rsi = df['RSI'].iloc[-1]
            
            # 5. Logika Rekomendasi
            if latest_rsi < 30:
                recommendation = "🟢 BELI (Harga Sedang Murah/Oversold)"
            elif latest_rsi > 70:
                recommendation = "🔴 JUAL (Harga Sedang Mahal/Overbought)"
            else:
                recommendation = "🟡 TAHAN (Kondisi Pasar Normal)"
                
            # 6. Tampilkan Papan Informasi Utama
            st.subheader(f"Ringkasan Saham: {ticker_symbol}")
            st.caption(f"*Harga sudah dikonversi ke Rupiah (Estimasi Kurs: 1 USD = Rp {kurs_idr:,.0f})*")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Harga Terakhir (IDR)", f"Rp {latest_close:,.0f}")
            col2.metric("Nilai RSI (14 Hari)", f"{latest_rsi:.2f}")
            col3.metric("Rekomendasi Mesin", recommendation)
            
            # 7. Visualisasi Grafik Interaktif
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df.index,
                            open=df['Open'],
                            high=df['High'],
                            low=df['Low'],
                            close=df['Close'],
                            name='Pergerakan Harga'))
            
            fig.update_layout(
                title=f"Grafik Pergerakan Harga {ticker_symbol} (dalam Rupiah)",
                yaxis_title="Harga (IDR)",
                xaxis_rangeslider_visible=False, 
                height=500
            )
            st.plotly_chart(fig, use_container_width=True)

# --- 5. BAGIAN KONSULTAN INVESTASI (ROBO-ADVISOR) ---
st.divider()
st.header("💼 Konsultan Investasi Pribadi")
st.markdown("Tidak yakin harus mulai dari mana? Mari kita atur strategi investasi yang paling cocok untuk Anda berdasarkan modal yang Anda miliki.")

col_input1, col_input2 = st.columns(2)

with col_input1:
    modal_awal = st.number_input("Berapa total dana yang ingin Anda investasikan? (Rp)", min_value=1000000, value=10000000, step=1000000)
    tujuan_finansial = st.selectbox("Apa tujuan utama investasi ini?", 
                                    ["Dana Pensiun (> 10 Tahun)", 
                                     "Beli Rumah/Kendaraan (3-5 Tahun)", 
                                     "Dana Darurat (Kapan saja bisa dicairkan)"])

with col_input2:
    profil_risiko = st.radio("Bagaimana perasaan Anda jika investasi Anda tiba-tiba turun 15% dalam sebulan?",
                             ["Panik dan langsung jual semua (Konservatif/Cari Aman)",
                              "Sedikit cemas, tapi akan menunggu pasar pulih (Moderat/Seimbang)",
                              "Biasa saja, malah itu kesempatan beli lebih banyak! (Agresif/Tinggi Risiko)"])

# Terjemahkan jawaban profil risiko
if "Panik" in profil_risiko:
    profil = "Konservatif (Cari Aman)"
elif "cemas" in profil_risiko:
    profil = "Moderat (Seimbang)"
else:
    profil = "Agresif (Tinggi Risiko)"

if st.button("Buat Rencana Strategi Saya"):
    alloc, nominal, desc = get_asset_allocation(profil, modal_awal)
    
    st.success(f"Berdasarkan jawaban Anda, karakter investasi Anda adalah **{profil}**.")
    st.info(f"**Analisis Konsultan:** {desc}")
    
    col_chart, col_text = st.columns([1, 1])
    
    with col_chart:
        fig_pie = go.Figure(data=[go.Pie(labels=list(alloc.keys()), 
                                         values=list(alloc.values()), 
                                         hole=.4,
                                         marker_colors=['#2ecc71', '#f1c40f', '#e74c3c'])])
        fig_pie.update_layout(title_text="Rekomendasi Pembagian Dana Anda", margin=dict(t=40, b=0, l=0, r=0))
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col_text:
        st.subheader("Rincian Eksekusi Dana:")
        st.markdown("Jika Anda memiliki modal **Rp {:,.0f}**, begini cara membaginya:".format(modal_awal).replace(',', '.'))
        
        for aset, nilai in nominal.items():
            st.markdown(f"- **{aset}:** Rp {:,.0f}".format(nilai).replace(',', '.'))
            
        st.markdown("*Catatan: Lakukan pembelian aset secara bertahap (rutin tiap bulan) untuk hasil yang lebih maksimal.*")
