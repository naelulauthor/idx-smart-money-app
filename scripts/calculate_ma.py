"""
calculate_ma.py
Hitung MA10, MA20, MA50 dari data harga historis di Supabase,
lalu deteksi Golden Cross dan Death Cross,
lalu simpan hasilnya ke tabel ma_signals.
"""

import os
from supabase import create_client
from datetime import date, timedelta

# ─── Config ──────────────────────────────────────────────────
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SECRET_KEY"]

STOCKS = [
    "BBCA", "BBRI", "BMRI", "BBNI", "BRIS",
    "TLKM", "ASII", "GOTO", "PGAS", "INDF",
    "ICBP", "UNVR", "KLBF", "SIDO", "ADRO",
    "PTBA", "ANTM", "MDKA", "SMGR", "WIKA",
]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def calculate_ma(prices: list, period: int) -> float | None:
    """Hitung simple moving average dari list harga."""
    if len(prices) < period:
        return None
    return round(sum(prices[-period:]) / period, 2)

def detect_signal(ma10_prev, ma20_prev, ma10_curr, ma20_curr) -> tuple:
    """
    Deteksi Golden Cross / Death Cross.
    Returns: (signal_type, ma_signal)
    """
    if None in [ma10_prev, ma20_prev, ma10_curr, ma20_curr]:
        return "watch", "watch_zone"

    # Golden Cross: MA10 tadi di bawah MA20, sekarang di atas
    if ma10_prev <= ma20_prev and ma10_curr > ma20_curr:
        return "buy", "golden_cross"

    # Death Cross: MA10 tadi di atas MA20, sekarang di bawah
    if ma10_prev >= ma20_prev and ma10_curr < ma20_curr:
        return "sell", "death_cross"

    # Watch Zone: MA10 mendekati MA20 (selisih < 1%)
    if ma10_curr and ma20_curr:
        diff_pct = abs(ma10_curr - ma20_curr) / ma20_curr * 100
        if diff_pct < 1.0:
            return "watch", "watch_zone"

    # MA10 di atas MA20 tapi belum cross → potential buy
    if ma10_curr > ma20_curr:
        return "buy", "bounce_ma"

    return "sell", "bounce_ma"

def process_stock(code: str):
    try:
        # Ambil 60 hari data terakhir (butuh minimal 50 buat MA50)
        since = (date.today() - timedelta(days=90)).isoformat()

        result = supabase.table("stock_prices")\
            .select("close, time")\
            .eq("stock_code", code)\
            .gte("time", since)\
            .order("time", desc=False)\
            .execute()

        rows = result.data
        if len(rows) < 10:
            print(f"  ⚠ {code}: data terlalu sedikit ({len(rows)} baris), skip")
            return

        # Ambil list harga close
        closes = [float(r["close"]) for r in rows]
        current_price = closes[-1]

        # Hitung MA
        ma10 = calculate_ma(closes, 10)
        ma20 = calculate_ma(closes, 20)
        ma50 = calculate_ma(closes, 50)

        # Untuk deteksi cross, butuh MA dari kemarin juga
        ma10_prev = calculate_ma(closes[:-1], 10)
        ma20_prev = calculate_ma(closes[:-1], 20)

        # Deteksi sinyal
        signal_type, ma_signal = detect_signal(ma10_prev, ma20_prev, ma10, ma20)

        # Simpan ke Supabase
        data = {
            "stock_code": code,
            "signal_type": signal_type,
            "ma_signal": ma_signal,
            "price": round(current_price, 2),
            "ma10": ma10,
            "ma20": ma20,
            "ma50": ma50,
            "detected_at": date.today().isoformat(),
        }

        supabase.table("ma_signals").upsert(
            data,
            on_conflict="stock_code,detected_at"
        ).execute()

        signal_label = {
            "golden_cross": "🟢 Golden Cross",
            "death_cross": "🔴 Death Cross",
            "watch_zone": "🟡 Watch Zone",
            "bounce_ma": "⚪ Bounce MA",
        }.get(ma_signal, ma_signal)

        print(f"  ✓ {code}: {signal_label} | MA10={ma10} MA20={ma20} MA50={ma50}")

    except Exception as e:
        print(f"  ✗ {code}: Error — {e}")

def main():
    print(f"Mulai kalkulasi MA signals...")
    for code in STOCKS:
        process_stock(code)
    print(f"✅ Kalkulasi MA selesai untuk {len(STOCKS)} saham")

if __name__ == "__main__":
    main()
