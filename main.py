import flet as ft
import json, ssl, time, threading, sqlite3
from collections import defaultdict, deque
from datetime import datetime

# Veritabanı
conn = sqlite3.connect("signals.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT, symbol TEXT, type TEXT, price REAL, stop REAL, tp1 REAL, tp2 REAL, volume REAL
    )
''')
conn.commit()

def save_to_db(symbol, sig_type, price, stop, tp1, tp2, volume):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO signals (timestamp, symbol, type, price, stop, tp1, tp2, volume) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   (now, symbol, sig_type, price, stop, tp1, tp2, volume))
    conn.commit()

def main(page: ft.Page):
    page.title = "Trading & Halt Radar PRO"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 10

    config = {"api_key": "", "secret_key": "", "min_price": 0.50, "max_price": 25.00, "min_volume": 100000.0, "is_running": False}

    status_icon = ft.Icon(name="wifi_off", color=ft.colors.RED)
    status_text = ft.Text("Bağlantı Kapalı", size=12, color=ft.colors.RED)
    signals_list = ft.ListView(expand=True, spacing=10)

    api_key_input = ft.TextField(label="Alpaca API Key", password=True, can_reveal_password=True)
    secret_key_input = ft.TextField(label="Alpaca Secret Key", password=True, can_reveal_password=True)

    def add_signal_card(symbol, sig_type, price, stop, tp1, tp2, dollar_vol, is_halt=False):
        save_to_db(symbol, sig_type, price, stop, tp1, tp2, dollar_vol)
        border_color = ft.colors.YELLOW_ACCENT if is_halt else ft.colors.GREEN_ACCENT
        tag_color = ft.colors.ORANGE_400 if is_halt else ft.colors.GREEN_400

        card = ft.Card(
            content=ft.Container(
                padding=12,
                border=ft.border.all(1, border_color),
                border_radius=8,
                content=ft.Column([
                    ft.Row([
                        ft.Text(f"${symbol}", size=16, weight=ft.FontWeight.BOLD, color=ft.colors.CYAN_300),
                        ft.Container(content=ft.Text(sig_type, size=10, weight=ft.FontWeight.BOLD, color=ft.colors.BLACK), bgcolor=tag_color, padding=4, border_radius=4),
                        ft.Text(datetime.now().strftime("%H:%M:%S"), size=10, color=ft.colors.GREY_500)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(height=5, color=ft.colors.TRANSPARENT),
                    ft.Row([
                        ft.Text(f"Giriş: ${price}", color=ft.colors.WHITE),
                        ft.Text(f"Stop: ${stop}", color=ft.colors.RED_ACCENT),
                        ft.Text(f"TP1: ${tp1}", color=ft.colors.GREEN_ACCENT),
                        ft.Text(f"TP2: ${tp2}", color=ft.colors.BLUE_ACCENT),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(height=5, color=ft.colors.TRANSPARENT),
                    ft.Text(f"💰 Dakikalık Hacim: ${int(dollar_vol):,}", size=10, color=ft.colors.GREY_400)
                ])
            ),
            color="#181825"
        )
        signals_list.controls.insert(0, card)
        page.update()

    def start_scanner():
        import websocket
        history = defaultdict(lambda: deque(maxlen=10))
        last_seen = {}
        ws_url = "wss://stream.data.alpaca.markets/v2/iex"

        def on_message(ws, msg):
            for item in json.loads(msg):
                if item.get("T") == "success" and item.get("msg") == "authenticated":
                    status_icon.name = "check_circle"
                    status_icon.color = ft.colors.GREEN
                    status_text.value = "Canlı Akış Aktif"
                    status_text.color = ft.colors.GREEN
                    page.update()
                    ws.send(json.dumps({"action": "subscribe", "bars": ["*"]}))
                elif item.get("T") == "b":
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
                            add_signal_card(symbol, "⚡ HALT UNHALT", entry, round(entry*0.96,2), round(entry*1.05,2), round(entry*1.10,2), dollar_vol, is_halt=True)
                        elif len(hist) >= 4:
                            avg_v = sum(b["v"] for b in hist) / len(hist)
                            if avg_v > 0 and vol >= avg_v * 6.0:
                                entry = round(close_p, 2)
                                add_signal_card(symbol, "🔥 SCALP SİNYAL", entry, round(entry*0.975,2), round(entry*1.035,2), round(entry*1.07,2), dollar_vol, is_halt=False)

                    history[symbol].append({"v": vol})

        def on_open(ws):
            ws.send(json.dumps({"action": "auth", "key": config["api_key"], "secret": config["secret_key"]}))

        while config["is_running"]:
            try:
                ws = websocket.WebSocketApp(ws_url, on_open=on_open, on_message=on_message)
                ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
            except:
                time.sleep(3)

    def toggle_scanner(e):
        if not api_key_input.value or not secret_key_input.value:
            page.snack_bar = ft.SnackBar(ft.Text("Lütfen API Key ve Secret Key girin!"))
            page.snack_bar.open = True
            page.update()
            return

        config["api_key"] = api_key_input.value
        config["secret_key"] = secret_key_input.value

        if not config["is_running"]:
            config["is_running"] = True
            btn_start.text = "Taramayı Durdur"
            btn_start.bgcolor = ft.colors.RED_600
            threading.Thread(target=start_scanner, daemon=True).start()
        else:
            config["is_running"] = False
            btn_start.text = "Taramayı Başlat"
            btn_start.bgcolor = ft.colors.GREEN_600
            status_icon.name = "wifi_off"
            status_icon.color = ft.colors.RED
            status_text.value = "Bağlantı Kapalı"
            status_text.color = ft.colors.RED

        page.update()

    btn_start = ft.ElevatedButton("Taramayı Başlat", on_click=toggle_scanner, bgcolor=ft.colors.GREEN_600, color=ft.colors.WHITE)

    radar_tab = ft.Column([
        ft.Row([status_icon, status_text], alignment=ft.MainAxisAlignment.START),
        ft.Divider(color=ft.colors.GREY_800),
        signals_list
    ])

    settings_tab = ft.Column([
        ft.Text("🔑 API Ayarları", size=16, weight=ft.FontWeight.BOLD),
        api_key_input,
        secret_key_input,
        ft.Divider(color=ft.colors.GREY_800),
        btn_start
    ])

    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(text="📡 Canlı Radar", content=radar_tab),
            ft.Tab(text="⚙️ Ayarlar", content=settings_tab),
        ],
        expand=True
    )

    page.add(tabs)

ft.app(target=main)
