"""
send_telegram_alerts.py
Kirim notifikasi Telegram untuk:
- Golden Cross (sinyal beli)
- Death Cross (sinyal jual)
- Watch Zone (sinyal waspada)
Dijalankan otomatis oleh GitHub Actions setelah calculate_ma.py
"""

import os
import requests
from supabase import create_client
from datetime import date

# ─── Config ──────────────────────────────────────────────────
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SECRET_KEY"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

STOCK_NAMES = {
    'BBCA': 'Bank Central Asia', 'BBRI': 'Bank Rakyat Indonesia',
    'BMRI': 'Bank Mandiri', 'BBNI': 'Bank Negara Indonesia',
    'BRIS': 'Bank Syariah Indonesia', 'TLKM': 'Telkom Indonesia',
    'ASII': 'Astra International', 'GOTO': 'GoTo Gojek Tokopedia',
    'PGAS': 'Perusahaan Gas Negara', 'INDF': 'Indofood Sukses Makmur',
    'ICBP': 'Indofood CBP', 'UNVR': 'Unilever Indonesia',
    'KLBF': 'Kalbe Farma', 'SIDO': 'Sido Muncul',
    'ADRO': 'Adaro Energy', 'PTBA': 'Bukit Asam',
    'ANTM': 'Aneka Tambang', 'MDKA': 'Merdeka Copper Gold',
    'SMGR': 'Semen Indonesia', 'WIKA': 'Wijaya Karya',
}

def send_telegram(message: str):
    """Kirim pesan ke Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            print(f"  ✓ Telegram terkirim")
        else:
            print(f"  ✗ Telegram error: {res.text}")
    except Exception as e:
        print(f"  ✗ Telegram exception: {e}")

def format_price(price) -> str:
    if not price:
        return "—"
    return f"Rp {float(price):,.0f}".replace(",", ".")

def main():
    today = date.today().isoformat()
    print(f"Cek sinyal MA hari ini ({today})...")

    # Ambil semua sinyal hari ini
    result = supabase.table("ma_signals")\
        .select("*")\
        .eq("detected_at", today)\
        .execute()

    signals = result.data
    if not signals:
        print("Tidak ada sinyal hari ini.")
        return

    golden_crosses = [s for s in signals if s["ma_signal"] == "golden_cross"]
    death_crosses = [s for s in signals if s["ma_signal"] == "death_cross"]
    watch_zones = [s for s in signals if s["ma_signal"] == "watch_zone"]

    print(f"Golden Cross: {len(golden_crosses)} | Death Cross: {len(death_crosses)} | Watch: {len(watch_zones)}")

    # ── Kirim Golden Cross ──────────────────────────────────
    if golden_crosses:
        lines = []
        for s in golden_crosses:
            name = STOCK_NAMES.get(s["stock_code"], s["stock_code"])
            lines.append(
                f"  • <b>{s['stock_code']}</b> — {name}\n"
                f"    💰 Harga: {format_price(s['price'])}\n"
                f"    📊 MA10: {format_price(s['ma10'])} | MA20: {format_price(s['ma20'])}"
            )

        msg = (
            f"🟢 <b>GOLDEN CROSS ALERT — IDX Smart Money</b>\n"
            f"{'─'*30}\n"
            f"MA10 memotong MA20 ke atas!\n"
            f"Sinyal <b>BELI</b> terdeteksi pada {len(golden_crosses)} saham:\n\n"
            + "\n\n".join(lines) +
            f"\n\n{'─'*30}\n"
            f"📅 Tanggal: {today}\n"
            f"⏰ Delay data: ~15 menit\n"
            f"🔗 <a href='https://idx-smart-money-app.vercel.app'>Buka Dashboard</a>"
        )
        send_telegram(msg)

    # ── Kirim Death Cross ───────────────────────────────────
    if death_crosses:
        lines = []
        for s in death_crosses:
            name = STOCK_NAMES.get(s["stock_code"], s["stock_code"])
            lines.append(
                f"  • <b>{s['stock_code']}</b> — {name}\n"
                f"    💰 Harga: {format_price(s['price'])}\n"
                f"    📊 MA10: {format_price(s['ma10'])} | MA20: {format_price(s['ma20'])}"
            )

        msg = (
            f"🔴 <b>DEATH CROSS ALERT — IDX Smart Money</b>\n"
            f"{'─'*30}\n"
            f"MA10 memotong MA20 ke bawah!\n"
            f"Sinyal <b>JUAL/WASPADA</b> pada {len(death_crosses)} saham:\n\n"
            + "\n\n".join(lines) +
            f"\n\n{'─'*30}\n"
            f"📅 Tanggal: {today}\n"
            f"⏰ Delay data: ~15 menit\n"
            f"🔗 <a href='https://idx-smart-money-app.vercel.app'>Buka Dashboard</a>"
        )
        send_telegram(msg)

    # ── Kirim Watch Zone (hanya kalau ada banyak) ──────────
    if len(watch_zones) >= 3:
        codes = ", ".join([s["stock_code"] for s in watch_zones])
        msg = (
            f"🟡 <b>WATCH ZONE — IDX Smart Money</b>\n"
            f"{'─'*30}\n"
            f"{len(watch_zones)} saham mendekati MA Cross:\n"
            f"<b>{codes}</b>\n\n"
            f"MA10 & MA20 berjarak &lt;1% — cross bisa terjadi 1-3 hari ke depan.\n\n"
            f"📅 {today}\n"
            f"🔗 <a href='https://idx-smart-money-app.vercel.app'>Buka Dashboard</a>"
        )
        send_telegram(msg)

    # ── Kirim ringkasan harian ──────────────────────────────
    summary = (
        f"📊 <b>Ringkasan MA Signals — {today}</b>\n"
        f"{'─'*30}\n"
        f"🟢 Golden Cross: {len(golden_crosses)} saham\n"
        f"🔴 Death Cross: {len(death_crosses)} saham\n"
        f"🟡 Watch Zone: {len(watch_zones)} saham\n\n"
        f"🔗 <a href='https://idx-smart-money-app.vercel.app'>Lihat Detail Dashboard</a>"
    )
    send_telegram(summary)
    print("✅ Semua notifikasi Telegram berhasil dikirim!")

if __name__ == "__main__":
    main()
