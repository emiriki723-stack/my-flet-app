import flet as ft
import json, ssl, time, threading, sqlite3
from collections import defaultdict, deque
from datetime import datetime

def is_market_open():
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    return True

def main(page: ft.Page):
    page.title = "EMGE TRADE Terminal PRO"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0b0d14"
    page.padding = 8
    page.spacing = 0

    config = {"api_key": "", "secret_key": "", "min_price": 0.50, "max_price": 25.00, "min_volume": 100000.0, "is_running": False}

    # --- GRAFİK SÜSLERİ (Görünür & Kalınlaştırılmış) ---
    chart_decorations = ft.Row([
        ft.Container(bgcolor="#00ffcc", width=16, height=6, border_radius=2),
        ft.Container(bgcolor="#00ffcc", width=30, height=6, border_radius=2),
        ft.Container(bgcolor="#ff4d4d", width=12, height=6, border_radius=2),
        ft.Container(bgcolor="#00ffcc", width=42, height=6, border_radius=2),
        ft.Container(bgcolor="#ff3399", width=20, height=6, border_radius=2),
    ], spacing=6)

    # --- ÜST HEADER ---
    header = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Row([
                    ft.Container(
                        content=ft.Icon(ft.Icons.SHOW_CHART, color="#00ffcc", size=22),
                        bgcolor="#1a2634", padding=6, border_radius=8
                    ),
                    ft.Column([
                        ft.Text("EMGE TRADE", size=18, weight=ft.FontWeight.BOLD, color="#ffffff"),
                        ft.Text("Algorithmic Scalp & Halt Radar", size=9, color="#8b9bb4"),
                    ], spacing=1)
                ], spacing=10),
                ft.Container(
                    content=ft.Text("PRO v2.5", size=10, weight=ft.FontWeight.BOLD, color="#00ffcc"),
                    bgcolor="#1a2634", padding=6, border_radius=4
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=4, color="transparent"),
            chart_decorations,
            ft.Row([
                ft.Text("Created by emge ✦", size=9, color="#00ffcc", italic=True),
            ], alignment=ft.MainAxisAlignment.END)
        ], spacing=4),
        padding=10,
        bgcolor="#161922",
        border_radius=8
    )

    # --- RADAR CANLI DURUM & SAAT ---
    status_icon = ft.Icon(ft.Icons.RADIO_BUTTON_OFF, color="#ff4d4d", size=14)
    status_text = ft.Text("SİSTEM ÇEVRİMDIŞI", size=11, color="#ff4d4d", weight=ft.FontWeight.BOLD)
    clock_text = ft.Text(datetime.now().strftime("%d.%m.%Y - %H:%M:%S"), size=10, color="#8b9bb4")

    def update_clock():
        while True:
            try:
                clock_text.value = datetime.now().strftime("%d.%m.%Y - %H:%M:%S")
                page.update()
            except:
                pass
            time.sleep(1)

    threading.Thread(target=update_clock, daemon=True).start()

    signals_list = ft.ListView(expand=True, spacing=8)

    # HAFTA SONU UYARI BANTU
    market_closed_banner = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.WARNING_ROUNDED, color="#ffaa00", size=18),
            ft.Column([
                ft.Text("PİYASALAR KAPALI (HAFTA SONU)", size=11, weight=ft.FontWeight.BOLD, color="#ffaa00"),
                ft.Text("Canlı veri akışı Pazartesi ABD borsa açılışında aktifleşecektir.", size=9, color="#8b9bb4")
            ], spacing=1)
        ], spacing=10),
        bgcolor="#1c1811",
        padding=10,
        border_radius=6,
        visible=not is_market_open()
    )

    # INPUT KUTULARI
    api_key_input = ft.TextField(
        label="Alpaca API Key", password=True, can_reveal_password=True,
        bgcolor="#161922", label_style=ft.TextStyle(color="#8b9bb4", size=12), text_style=ft.TextStyle(color="#ffffff", size=13)
    )
    secret_key_input = ft.TextField(
        label="Alpaca Secret Key", password=True, can_reveal_password=True,
        bgcolor="#161922", label_style=ft.TextStyle(color="#8b9bb4", size=12), text_style=ft.TextStyle(color="#ffffff", size=13)
    )

    def update_status(text, color, icon_name):
        status_text.value = text
        status_text.color = color
        status_icon.name = icon_name
        status_icon.color = color
        page.update()

    def init_db_and_add(symbol, sig_type, price, stop, tp1, tp2, dollar_vol, is_halt=False):
        try:
            conn = sqlite3.connect("signals.db", check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT, symbol TEXT, type TEXT, price REAL, stop REAL, tp1 REAL, tp2 REAL, volume REAL
                )
            ''')
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO signals (timestamp, symbol, type, price, stop, tp1, tp2, volume) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                           (now, symbol, sig_type, price, stop, tp1, tp2, dollar_vol))
            conn.commit()
            conn.close()
        except:
            pass

        card_bg = "#1f1810" if is_halt else "#10201a"
        tag_bg = "#332200" if is_halt else "#003322"
        tag_fg = "#ffaa00" if is_halt else "#00ffcc"

        card = ft.Container(
            padding=10,
            bgcolor=card_bg,
            border_radius=6,
            content=ft.Column([
                ft.Row([
                    ft.Row([
                        ft.Icon(ft.Icons.CANDLESTICK_CHART, color=tag_fg, size=16),
                        ft.Text(f"${symbol}", size=15, weight=ft.FontWeight.BOLD, color="#ffffff"),
                    ], spacing=4),
                    ft.Container(
                        content=ft.Text(sig_type, size=9, weight=ft.FontWeight.BOLD, color=tag_fg),
                        bgcolor=tag_bg, padding=6, border_radius=3
                    ),
                    ft.Text(datetime.now().strftime("%H:%M:%S"), size=10, color="#8b9bb4")
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(height=2, color="#2a3447"),
                ft.Row([
                    ft.Text(f"Giriş: ${price}", size=11, color="#ffffff", weight=ft.FontWeight.BOLD),
                    ft.Text(f"Stop: ${stop}", size=11, color="#ff4d4d"),
                    ft.Text(f"TP1: ${tp1}", size=11, color="#00ffcc"),
                    ft.Text(f"TP2: ${tp2}", size=11, color="#3399ff"),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(height=2, color="transparent"),
                ft.Row([
                    ft.Text(f"Hacim: ${int(dollar_vol):,}", size=9, color="#8b9bb4"),
                    ft.Text("EMGE ALGO ✦", size=9, color="#00ffcc", italic=True)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ], spacing=2)
        )
        signals_list.controls.insert(0, card)
        page.update()

    def start_scanner():
        import websocket
        history = defaultdict(lambda: deque(maxlen=10))
        last_seen = {}
        ws_url = "wss://stream.data.alpaca.markets/v2/iex"

        def on_message(ws, msg):
            try:
                data = json.loads(msg)
                if not isinstance(data, list):
                    data = [data]

                for item in data:
                    if not isinstance(item, dict):
                        continue

                    msg_type = item.get("T")
                    if msg_type == "success" and item.get("msg") == "authenticated":
                        update_status("BAĞLANTI BAŞARILI", "#00ffcc", ft.Icons.CHECK_CIRCLE)
                        ws.send(json.dumps({"action": "subscribe", "bars": ["*"]}))
                    elif msg_type == "error":
                        err_msg = item.get('msg', 'Bilinmeyen Hata')
                        update_status(f"API HATASI: {err_msg}", "#ff4d4d", ft.Icons.ERROR)
                    elif msg_type == "b":
                        update_status("CANLI AKIŞ AKTİF ⚡", "#00ffcc", ft.Icons.RADIO_BUTTON_CHECKED)
                        symbol = item.get("S")
                        vol = int(item.get("v", 0))
                        open_p = float(item.get("o", 0.0))
                        close_p = float(item.get("c", 0.0))
                        dollar_vol = vol * close_p
                        curr_time = time.time()

                        if config["min_price"] <= close_p <= config["max_price"] and dollar_vol >= config["min_volume"] and open_p > 0:
                            is_unhalted = False
                            if symbol in last_seen and (curr_time - last_seen[symbol] >= 240):
                                is_unhalted = True
                            last_seen[symbol] = curr_time

                            hist = list(history[symbol])

                            if is_unhalted and close_p > open_p:
                                entry = round(close_p, 2)
                                init_db_and_add(symbol, "⚡ HALT UNHALT", entry, round(entry*0.96,2), round(entry*1.05,2), round(entry*1.10,2), dollar_vol, is_halt=True)
                            elif len(hist) >= 4:
                                avg_v = sum(b.get("v", 0) for b in hist) / len(hist)
                                if avg_v > 0 and vol >= avg_v * 6.0:
                                    entry = round(close_p, 2)
                                    init_db_and_add(symbol, "🔥 SCALP SİNYAL", entry, round(entry*0.975,2), round(entry*1.035,2), round(entry*1.07,2), dollar_vol, is_halt=False)

                        history[symbol].append({"v": vol})
            except Exception as ex:
                pass

        def on_open(ws):
            try:
                update_status("KİMLİK DOĞRULANIYOR...", "#ffaa00", ft.Icons.SYNC)
                ws.send(json.dumps({"action": "auth", "key": config["api_key"], "secret": config["secret_key"]}))
            except Exception as ex:
                pass

        def on_error(ws, error):
            update_status("BAĞLANTI HATASI!", "#ff4d4d", ft.Icons.WARNING)

        while config["is_running"]:
            try:
                ws = websocket.WebSocketApp(ws_url, on_open=on_open, on_message=on_message, on_error=on_error)
                ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
            except Exception as e:
                time.sleep(3)

    def toggle_scanner(e):
        if not api_key_input.value or not secret_key_input.value:
            update_status("API KEY BOŞ OLAMAZ!", "#ff4d4d", ft.Icons.WARNING)
            return

        config["api_key"] = api_key_input.value.strip()
        config["secret_key"] = secret_key_input.value.strip()

        if not config["is_running"]:
            config["is_running"] = True
            btn_start.text = "Taramayı Durdur"
            btn_start.bgcolor = "#ff4d4d"
            
            update_status("SUNUCUYA BAĞLANILIYOR...", "#ffaa00", ft.Icons.SYNC)
            threading.Thread(target=start_scanner, daemon=True).start()
        else:
            config["is_running"] = False
            btn_start.text = "Taramayı Başlat"
            btn_start.bgcolor = "#00ffcc"
            update_status("SİSTEM ÇEVRİMDIŞI", "#ff4d4d", ft.Icons.RADIO_BUTTON_OFF)

    btn_start = ft.ElevatedButton(
        "Taramayı Başlat", on_click=toggle_scanner, 
        bgcolor="#00ffcc", color="#0f111a", width=200
    )

    # İÇERİK ALANLARI
    radar_view = ft.Column([
        ft.Container(
            content=ft.Row([
                ft.Row([status_icon, status_text], spacing=6),
                clock_text
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=8, bgcolor="#161922", border_radius=6
        ),
        market_closed_banner,
        ft.Divider(color="#1f293d", height=2),
        signals_list
    ], expand=True, spacing=6)

    settings_view = ft.Column([
        ft.Text("🔑 ALPACA API BAĞLANTI AYARLARI", size=12, weight=ft.FontWeight.BOLD, color="#00ffcc"),
        api_key_input,
        secret_key_input,
        ft.Divider(color="#1f293d"),
        ft.Row([btn_start], alignment=ft.MainAxisAlignment.CENTER)
    ], expand=True, spacing=12)

    body_container = ft.Container(content=radar_view, expand=True)

    def switch_tab(tab_name):
        if tab_name == "radar":
            body_container.content = radar_view
            btn_radar_nav.bgcolor = "#1a2634"
            btn_radar_nav.color = "#00ffcc"
            btn_settings_nav.bgcolor = "#161922"
            btn_settings_nav.color = "#8b9bb4"
        else:
            body_container.content = settings_view
            btn_radar_nav.bgcolor = "#161922"
            btn_radar_nav.color = "#8b9bb4"
            btn_settings_nav.bgcolor = "#1a2634"
            btn_settings_nav.color = "#00ffcc"
        page.update()

    btn_radar_nav = ft.ElevatedButton("📡 RADAR", on_click=lambda e: switch_tab("radar"), bgcolor="#1a2634", color="#00ffcc", expand=True)
    btn_settings_nav = ft.ElevatedButton("⚙️ AYARLAR", on_click=lambda e: switch_tab("settings"), bgcolor="#161922", color="#8b9bb4", expand=True)

    nav_row = ft.Container(
        content=ft.Row([btn_radar_nav, btn_settings_nav], spacing=8),
        padding=ft.Padding(0, 4, 0, 4)
    )

    page.add(
        ft.Column([
            header,
            ft.Container(height=6),
            body_container,
            ft.Divider(color="#1f293d", height=2),
            nav_row
        ], expand=True, spacing=0)
    )

ft.app(target=main)
