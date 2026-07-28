# -*- coding: utf-8 -*-
import flet as ft
import requests, time, threading
from datetime import datetime

# --- PİYASA VE SEANS KONTROLÜ ---
def get_market_session():
    now = datetime.now()
    if now.weekday() >= 5:
        return "HAFTA SONU (KAPALI)"
    hour = now.hour
    if 11 <= hour < 16:
        return "PRE-MARKET 🌅"
    elif 16 <= hour < 23:
        return "CANLI SEANS ⚡"
    else:
        return "AFTER-HOURS 🌙"

# --- TRADINGVIEW PRE-BREAKOUT ENGINE (Yüksek Oynaklık + Direnç Kırılımı) ---
def fetch_tradingview_ext_rockets():
    url = "https://scanner.tradingview.com/america/scan"
    
    # 50M$ MAKSİMUM MARKET CAP & GÜNÜN EN YÜKSEĞİNİ KIRANLAR (DİRENÇ KIRILIMI)
    payload_strict = {
        "filter": [
            {"left": "close", "operation": "in_range", "right": [0.50, 10.00]},          # Fiyat aralığı
            {"left": "market_cap_basic", "operation": "less", "right": 50000000},        # KESİN: Max 50 Milyon $ P.Değeri
            {"left": "volume", "operation": "greater", "right": 1000000},                # KESİN: En az 1 Milyon lot hacim
            {"left": "relative_volume_10d_calc", "operation": "greater", "right": 5.0},  # KESİN: Normalin EN AZ 5 KATI hacim patlaması
            {"left": "change", "operation": "in_range", "right": [4.0, 15.00]},          # Prim aralığı
            {"left": "close", "operation": "greater_or_equal", "right": "high"}          # Direnç Kırılımı: Fiyat günün zirvesinde veya üstünde!
        ],
        "options": {"lang": "en", "active_symbol_country": "US"},
        "symbols": {"query": {"types": []}, "tickers": []},
        # 'high' sütunu eklendi (indis 8)
        "columns": ["name", "close", "change", "volume", "relative_volume_10d_calc", "description", "extended_hours_price", "extended_hours_change", "high"],
        "sort_by": "relative_volume_10d_calc", 
        "sort_order": "desc",
        "range": [0, 10]
    }

    # B-PLAN FİLTRESİ (Piyasa sakinken esnetilmiş versiyon)
    payload_fallback = {
        "filter": [
            {"left": "close", "operation": "in_range", "right": [0.50, 8.00]},
            {"left": "market_cap_basic", "operation": "less", "right": 50000000},
            {"left": "volume", "operation": "greater", "right": 750000},
            {"left": "relative_volume_10d_calc", "operation": "greater", "right": 3.5},
            {"left": "change", "operation": "in_range", "right": [3.0, 12.00]}
        ],
        "options": {"lang": "en", "active_symbol_country": "US"},
        "symbols": {"query": {"types": []}, "tickers": []},
        "columns": ["name", "close", "change", "volume", "relative_volume_10d_calc", "description", "extended_hours_price", "extended_hours_change", "high"],
        "sort_by": "change",
        "sort_order": "desc",
        "range": [0, 8]
    }

    headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json; charset=utf-8"}

    def parse_data(response):
        if response.status_code == 200:
            response.encoding = 'utf-8'
            data = response.json()
            results = []
            for item in data.get("data", []):
                d = item.get("d", [])
                if len(d) >= 5:
                    ext_price = d[6] if len(d) > 6 and d[6] is not None else d[1]
                    ext_change = d[7] if len(d) > 7 and d[7] is not None else d[2]
                    if ext_price and ext_price > 0:
                        results.append({
                            "symbol": str(d[0]),
                            "price": round(float(ext_price), 2),
                            "change": round(float(ext_change), 2),
                            "volume": int(d[3]),
                            "rel_vol": round(float(d[4]), 1) if d[4] else 1.0
                        })
            return results
        return []

    try:
        res = requests.post(url, json=payload_strict, headers=headers, timeout=8)
        parsed = parse_data(res)
        if parsed:
            return parsed
        
        res_fb = requests.post(url, json=payload_fallback, headers=headers, timeout=8)
        return parse_data(res_fb)
    except Exception:
        pass
    return []

# --- ANA FLET UYGULAMASI ---
def main(page: ft.Page):
    page.title = "EMGE TRADE - Cyberpunk Pro Tracker"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#030408"
    page.padding = 12
    page.spacing = 0

    is_running = False
    seen_signals = set()
    my_positions = {}

    # --- SİBERPUNK HEADER ---
    header = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Row([
                    ft.Container(
                        content=ft.Icon(ft.Icons.ROCKET_LAUNCH_ROUNDED, color="#00ffff", size=28),
                        gradient=ft.LinearGradient(
                            begin=ft.Alignment(-1, -1),
                            end=ft.Alignment(1, 1),
                            colors=["#ff0055", "#7928ca"]
                        ),
                        padding=10, border_radius=12,
                        shadow=ft.BoxShadow(spread_radius=1, blur_radius=12, color="#ff0055")
                    ),
                    ft.Column([
                        ft.Text("EMGE TRADE", size=22, weight=ft.FontWeight.W_900, color="#ffffff"),
                        ft.Text("Low-Float Cyber Pro Radar & Al/Sat Engine", size=10, color="#00ffff", weight=ft.FontWeight.W_500),
                    ], spacing=0)
                ], spacing=12),
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.AUTO_AWESOME, color="#ff007f", size=14),
                        ft.Text("NANO-PRO", size=10, weight=ft.FontWeight.BOLD, color="#ffffff"),
                    ], spacing=4),
                    gradient=ft.LinearGradient(colors=["#ff007f", "#7928ca"]),
                    padding=ft.Padding(8, 4, 8, 4), border_radius=20,
                    shadow=ft.BoxShadow(spread_radius=1, blur_radius=8, color="#ff007f")
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=10, color="#1f293d"),
            ft.Row([
                ft.Text("Developer: emge ✦", size=10, color="#ff88aa", italic=True, weight=ft.FontWeight.BOLD),
            ], alignment=ft.MainAxisAlignment.END)
        ], spacing=2),
        padding=14,
        bgcolor="#0a0f1d",
        border_radius=14,
        border=ft.Border(
            top=ft.BorderSide(1.5, "#ff007f"),
            bottom=ft.BorderSide(1.5, "#00ffff"),
            left=ft.BorderSide(1.5, "#7928ca"),
            right=ft.BorderSide(1.5, "#ff007f")
        ),
        shadow=ft.BoxShadow(spread_radius=2, blur_radius=20, color="#0a0f1d")
    )

    status_icon = ft.Icon(ft.Icons.RADIO_BUTTON_OFF_ROUNDED, color="#ff3366", size=16)
    status_text = ft.Text("RADAR KAPALI", size=12, color="#ff3366", weight=ft.FontWeight.BOLD)
    session_badge = ft.Text(get_market_session(), size=11, color="#ffcc00", weight=ft.FontWeight.BOLD)
    clock_text = ft.Text(datetime.now().strftime("%H:%M:%S"), size=11, color="#00ffff", weight=ft.FontWeight.BOLD)

    def update_clock():
        while True:
            try:
                clock_text.value = datetime.now().strftime("%H:%M:%S")
                session_badge.value = get_market_session()
                page.update()
            except Exception:
                pass
            time.sleep(1)

    threading.Thread(target=update_clock, daemon=True).start()

    signals_list = ft.ListView(expand=True, spacing=12)

    def update_status(text, color, icon_name):
        status_text.value = text
        status_text.color = color
        status_icon.name = icon_name
        status_icon.color = color
        page.update()

    # --- SİNYAL KARTLARI ---
    def add_signal_card(sig, current_session):
        entry = sig['price']
        stop = round(entry * 0.94, 2)
        tp1 = round(entry * 1.15, 2)
        tp2 = round(entry * 1.30, 2)
        sym = sig['symbol']

        sell_alert_box = ft.Container(visible=False)

        def buy_clicked(e):
            if sym not in my_positions:
                my_positions[sym] = {'entry': entry, 'stop': stop, 'tp1': tp1, 'tp2': tp2}
                btn_buy.content.value = "📌 POZISYONDA"
                btn_buy.gradient = ft.LinearGradient(colors=["#00ff88", "#00aa55"])
                btn_buy.on_click = None
                btn_buy.update()
                page.update()

        btn_buy = ft.Container(
            content=ft.Text("📌 ALDIM", size=11, weight=ft.FontWeight.BOLD, color="#ffffff"),
            gradient=ft.LinearGradient(colors=["#00c6ff", "#0072ff"]),
            padding=ft.Padding(12, 6, 12, 6),
            border_radius=8,
            on_click=buy_clicked,
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=8, color="#00c6ff")
        )

        card = ft.Container(
            padding=14,
            bgcolor="#0c1221",
            border_radius=12,
            border=ft.Border(
                top=ft.BorderSide(1, "#2a3b5c"),
                bottom=ft.BorderSide(1, "#2a3b5c"),
                left=ft.BorderSide(3, "#ff007f"),
                right=ft.BorderSide(1, "#2a3b5c")
            ),
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=12, color="#050811"),
            content=ft.Column([
                ft.Row([
                    ft.Row([
                        ft.Icon(ft.Icons.WHATSHOT_ROUNDED, color="#ff007f", size=22),
                        ft.Text(f"${sym}", size=22, weight=ft.FontWeight.W_900, color="#ffffff"),
                    ], spacing=6),
                    ft.Container(
                        content=ft.Text(f"⚡ +%{sig['change']:.1f}", size=11, weight=ft.FontWeight.BOLD, color="#ffffff"),
                        gradient=ft.LinearGradient(colors=["#ff0055", "#ff5500"]),
                        padding=ft.Padding(8, 4, 8, 4), border_radius=6,
                        shadow=ft.BoxShadow(spread_radius=1, blur_radius=6, color="#ff0055")
                    ),
                    btn_buy
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
                ft.Divider(height=6, color="#162238"),
                
                ft.Row([
                    ft.Column([
                        ft.Text("Giris", size=10, color="#88a0c0"),
                        ft.Text(f"${entry}", size=14, color="#00ff88", weight=ft.FontWeight.BOLD)
                    ], spacing=1),
                    ft.Column([
                        ft.Text("Stop (%6)", size=10, color="#88a0c0"),
                        ft.Text(f"${stop}", size=13, color="#ff4d4d", weight=ft.FontWeight.BOLD)
                    ], spacing=1),
                    ft.Column([
                        ft.Text("TP1 (%15)", size=10, color="#88a0c0"),
                        ft.Text(f"${tp1}", size=13, color="#00ffff", weight=ft.FontWeight.BOLD)
                    ], spacing=1),
                    ft.Column([
                        ft.Text("TP2 (%30)", size=10, color="#88a0c0"),
                        ft.Text(f"${tp2}", size=13, color="#ff00ff", weight=ft.FontWeight.BOLD)
                    ], spacing=1),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
                sell_alert_box,
                
                ft.Divider(height=4, color="transparent"),
                
                ft.Row([
                    ft.Container(
                        content=ft.Text(f"Hacim: {sig['rel_vol']}x (${sig['volume']:,} Lot)", size=10, color="#ff88aa", weight=ft.FontWeight.BOLD),
                        bgcolor="#1f0f24", padding=ft.Padding(6, 2, 6, 2), border_radius=4
                    ),
                    ft.Text(datetime.now().strftime("%H:%M:%S"), size=10, color="#506b8d", italic=True)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ], spacing=4)
        )

        def check_position_status(current_price):
            if sym in my_positions:
                pos = my_positions[sym]
                if current_price >= pos['tp2']:
                    sell_alert_box.content = ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE, color="#ffffff", size=16),
                            ft.Text(f"🚨 SAT VAKTI! TP2 ASILDI (${current_price}) - KARI AL!", size=11, weight=ft.FontWeight.BOLD, color="#ffffff"),
                        ], spacing=6),
                        gradient=ft.LinearGradient(colors=["#ff00ff", "#7928ca"]),
                        padding=8, border_radius=6, shadow=ft.BoxShadow(spread_radius=1, blur_radius=10, color="#ff00ff")
                    )
                    sell_alert_box.visible = True
                    sell_alert_box.update()
                elif current_price >= pos['tp1']:
                    sell_alert_box.content = ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.MONEY_ROUNDED, color="#000000", size=16),
                            ft.Text(f"💰 KAR AL SINYALI! TP1 ULASILDI (${current_price})", size=11, weight=ft.FontWeight.BOLD, color="#000000"),
                        ], spacing=6),
                        gradient=ft.LinearGradient(colors=["#00ff88", "#00ffff"]),
                        padding=8, border_radius=6, shadow=ft.BoxShadow(spread_radius=1, blur_radius=10, color="#00ff88")
                    )
                    sell_alert_box.visible = True
                    sell_alert_box.update()
                elif current_price <= pos['stop']:
                    sell_alert_box.content = ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.WARNING_ROUNDED, color="#ffffff", size=16),
                            ft.Text(f"⚠️ STOP SINYALI! (${current_price}) - POZISYONDAN CIK!", size=11, weight=ft.FontWeight.BOLD, color="#ffffff"),
                        ], spacing=6),
                        gradient=ft.LinearGradient(colors=["#ff3366", "#990022"]),
                        padding=8, border_radius=6, shadow=ft.BoxShadow(spread_radius=1, blur_radius=10, color="#ff3366")
                    )
                    sell_alert_box.visible = True
                    sell_alert_box.update()

        card.check_pos = check_position_status
        signals_list.controls.insert(0, card)
        page.update()

    def scanner_loop():
        nonlocal is_running
        while is_running:
            try:
                curr_session = get_market_session()
                update_status("TARANIYOR...", "#00ffff", ft.Icons.SYNC_ROUNDED)
                rockets = fetch_tradingview_ext_rockets()

                if rockets:
                    update_status(f"CANLI TARAMA AKTIF ({len(rockets)} ROKET)", "#00ff88", ft.Icons.CHECK_CIRCLE_ROUNDED)
                    
                    for card in list(signals_list.controls):
                        if hasattr(card, 'check_pos'):
                            for r in rockets:
                                card.check_pos(r['price'])

                    for r in rockets:
                        sig_key = f"{r['symbol']}_{r['price']}"
                        if sig_key not in seen_signals:
                            seen_signals.add(sig_key)
                            add_signal_card(r, curr_session)
                else:
                    update_status("Kivilcim Bekleniyor...", "#ffcc00", ft.Icons.SEARCH_ROUNDED)

            except Exception:
                pass
            
            time.sleep(3)

    def toggle_scanner(e):
        nonlocal is_running
        if not is_running:
            is_running = True
            btn_start.content.value = "Taramayi Durdur"
            btn_start.gradient = ft.LinearGradient(colors=["#ff3366", "#990022"])
            btn_start.update()
            threading.Thread(target=scanner_loop, daemon=True).start()
        else:
            is_running = False
            btn_start.content.value = "Pre-Breakout Taramasini Baslat"
            btn_start.gradient = ft.LinearGradient(colors=["#ff0055", "#7928ca"])
            btn_start.update()
            update_status("RADAR KAPALI", "#ff3366", ft.Icons.RADIO_BUTTON_OFF_ROUNDED)

    btn_start = ft.Container(
        content=ft.Text("Pre-Breakout Taramasini Baslat", size=14, weight=ft.FontWeight.BOLD, color="#ffffff"),
        gradient=ft.LinearGradient(colors=["#ff0055", "#7928ca"]),
        alignment=ft.Alignment(0, 0),
        height=50,
        border_radius=12,
        on_click=toggle_scanner,
        shadow=ft.BoxShadow(spread_radius=2, blur_radius=12, color="#ff0055")
    )

    radar_view = ft.Column([
        ft.Container(
            content=ft.Row([
                ft.Row([status_icon, status_text], spacing=8),
                ft.Row([session_badge, clock_text], spacing=10)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=12, bgcolor="#0a0f1d", border_radius=10,
            border=ft.Border(ft.BorderSide(1, "#1a273d"))
        ),
        btn_start,
        ft.Divider(color="#1a273d", height=4),
        signals_list
    ], expand=True, spacing=10)

    page.add(
        ft.Column([
            header,
            ft.Container(height=10),
            radar_view
        ], expand=True, spacing=0)
    )

if __name__ == "__main__":
    ft.app(target=main)
