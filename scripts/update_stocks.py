"""
update_stocks.py
Fetch harga saham IDX dari Yahoo Finance (gratis, delay ~15 menit)
lalu simpan ke Supabase.
Dijalankan otomatis oleh GitHub Actions setiap 15 menit saat jam bursa.
"""

import os
import yfinance as yf
from supabase import create_client
from datetime import datetime, timezone
import time

# ─── Config ──────────────────────────────────────────────────
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SECRET_KEY"]

# 20 saham IDX paling populer (format Yahoo Finance: CODE.JK)
STOCKS = [
    "BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK", "BRIS.JK",
    "TLKM.JK", "ASII.JK", "GOTO.JK", "PGAS.JK", "INDF.JK",
    "ICBP.JK", "UNVR.JK", "KLBF.JK", "SIDO.JK", "ADRO.JK",
    "PTBA.JK", "ANTM.JK", "MDKA.JK", "SMGR.JK", "WIKA.JK",
]

# ─── Connect Supabase ─────────────────────────────────────────
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_and_save():
    print(f"[{datetime.now()}] Mulai fetch data saham IDX...")
    
    success_count = 0
    error_count = 0

    for ticker_sym in STOCKS:
        stock_code = ticker_sym.replace(".JK", "")
        
        try:
            # Ambil data dari Yahoo Finance
            ticker = yf.Ticker(ticker_sym)
            
            # Data hari ini (interval 1 menit, periode 1 hari)
            hist = ticker.history(period="1d", interval="1m")
            
            if hist.empty:
                print(f"  ⚠ {stock_code}: data kosong, skip")
                continue

            # Ambil data OHLCV terbaru (candle terakhir)
            latest = hist.iloc[-1]
            now_utc = datetime.now(timezone.utc)

            # Simpan ke tabel stock_prices
            data = {
                "stock_code": stock_code,
                "time": now_utc.isoformat(),
                "open": round(float(latest["Open"]), 2),
                "high": round(float(latest["High"]), 2),
                "low": round(float(latest["Low"]), 2),
                "close": round(float(latest["Close"]), 2),
                "volume": int(latest["Volume"]),
            }

            # Upsert (insert atau update kalau udah ada)
            supabase.table("stock_prices").upsert(
                data,
                on_conflict="stock_code,time"
            ).execute()

            print(f"  ✓ {stock_code}: {data['close']:,.0f} (vol: {data['volume']:,})")
            success_count += 1

            # Jeda singkat biar gak kena rate limit Yahoo Finance
            time.sleep(0.5)

        except Exception as e:
            print(f"  ✗ {stock_code}: Error — {e}")
            error_count += 1
            continue

    print(f"\n✅ Selesai: {success_count} berhasil, {error_count} gagal")
    print(f"Waktu: {datetime.now()}")

if __name__ == "__main__":
    fetch_and_save()
