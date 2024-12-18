import flet as ft
import requests
import sqlite3
from datetime import datetime, timedelta

# 天気アイコンの定義
weather_icons = {
    "晴れ": "☀️",
    "晴": "☀️",
    "雨": "🌧️", 
    "大雨": "🌧️",
    "小雨": "🌦️",
    "曇り": "☁️",
    "曇": "☁️",
    "くもり": "☁️",
    "雪": "❄️",
    "雷": "⚡",
    "霧": "🌫️",
    "みぞれ": "🌨️",
    "暴風雨": "🌪️",
}

# データベース初期化
def init_db():
    conn = sqlite3.connect('weather_forecast.db')
    c = conn.cursor()
    
    # 地域テーブル
    c.execute('''
        CREATE TABLE IF NOT EXISTS regions (
            region_code TEXT PRIMARY KEY,
            region_name TEXT NOT NULL
        )
    ''')
    
    # 都道府県テーブル
    c.execute('''
        CREATE TABLE IF NOT EXISTS prefectures (
            prefecture_code TEXT PRIMARY KEY,
            prefecture_name TEXT NOT NULL,
            region_code TEXT,
            FOREIGN KEY (region_code) REFERENCES regions(region_code)
        )
    ''')
    
    # 天気予報テーブル
    c.execute('''
        CREATE TABLE IF NOT EXISTS weather_forecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prefecture_code TEXT,
            area_code TEXT,
            area_name TEXT,
            forecast_date TEXT,
            forecast_time TEXT,
            weather TEXT,
            weather_icon TEXT,
            temperature TEXT,
            precipitation_probability TEXT,
            created_at TEXT,
            FOREIGN KEY (prefecture_code) REFERENCES prefectures(prefecture_code),
            UNIQUE(prefecture_code, area_code, forecast_date, forecast_time)
        )
    ''')
    
    conn.commit()
    conn.close()

# 地域と都道府県データをDBに保存
def save_area_data():
    conn = sqlite3.connect('weather_forecast.db')
    c = conn.cursor()
    
    url = "https://www.jma.go.jp/bosai/common/const/area.json"
    response = requests.get(url)
    area_data = response.json()
    
    # 地域データを保存
    for code, info in area_data['centers'].items():
        c.execute('INSERT OR REPLACE INTO regions (region_code, region_name) VALUES (?, ?)',
                 (code, info['name']))
    
    # 都道府県データを保存
    for code, info in area_data['offices'].items():
        c.execute('INSERT OR REPLACE INTO prefectures (prefecture_code, prefecture_name, region_code) VALUES (?, ?, ?)',
                 (code, info['name'], info['parent']))
    
    conn.commit()
    conn.close()

# 天気予報を取得する
def get_weather_forecast(area_code):
    url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"
    response = requests.get(url)
    return response.json()

def main(page: ft.Page):
    page.title = "日本の天気予報アプリ"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 1000
    page.window_height = 800
    weather_info = ft.Column()

    # DB初期化とエリアデータの保存
    init_db()
    save_area_data()

    # DBから地域データを取得
    def get_regions():
        conn = sqlite3.connect('weather_forecast.db')
        c = conn.cursor()
        c.execute('SELECT DISTINCT region_name FROM regions')
        regions = [row[0] for row in c.fetchall()]
        conn.close()
        return regions
    # 天気予報をDBに保存
    def save_weather_forecast(prefecture_code, forecast_data):
        conn = sqlite3.connect('weather_forecast.db')
        c = conn.cursor()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for area_data in forecast_data[0]["timeSeries"]:
            timeDefines = area_data["timeDefines"]
            areas = area_data["areas"]
            
            for area in areas:
                area_code = area["area"]["code"]
                area_name = area["area"]["name"]
                
                for i, time in enumerate(timeDefines):
                    dt = datetime.fromisoformat(time)
                    forecast_date = dt.strftime("%Y-%m-%d")
                    forecast_time = dt.strftime("%H:%M")
                    
                    weather = area.get("weathers", [""])[i] if "weathers" in area else ""
                    temp = area.get("temps", [""])[i] if "temps" in area else ""
                    pop = area.get("pops", [""])[i] if "pops" in area else ""
                    
                    weather_icon = ""
                    for key in weather_icons:
                        if key in weather:
                            weather_icon = weather_icons[key]
                            break
                    
                    c.execute('''
                        INSERT OR REPLACE INTO weather_forecasts 
                        (prefecture_code, area_code, area_name, forecast_date, forecast_time,
                         weather, weather_icon, temperature, precipitation_probability, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (prefecture_code, area_code, area_name, forecast_date, forecast_time,
                          weather, weather_icon, temp, pop, current_time))
        
        conn.commit()
        conn.close()

    # 地域選択時の処理
    def on_region_change(e):
        conn = sqlite3.connect('weather_forecast.db')
        c = conn.cursor()
        c.execute('''
            SELECT prefecture_name 
            FROM prefectures p
            JOIN regions r ON p.region_code = r.region_code
            WHERE r.region_name = ?
        ''', (region_dropdown.value,))
        prefectures = [row[0] for row in c.fetchall()]
        conn.close()

        prefecture_dropdown.options = [
            ft.dropdown.Option(name) for name in prefectures
        ]
        prefecture_dropdown.value = None
        prefecture_dropdown.update()
        
        weather_info.controls.clear()
        page.update()

    # 天気予報表示の処理
    def display_weather(e):
        weather_info.controls.clear()
        
        if not prefecture_dropdown.value:
            return

        conn = sqlite3.connect('weather_forecast.db')
        c = conn.cursor()
        
        c.execute('SELECT prefecture_code FROM prefectures WHERE prefecture_name = ?',
                 (prefecture_dropdown.value,))
        prefecture_code = c.fetchone()[0]
        
        try:
            forecast_data = get_weather_forecast(prefecture_code)
            save_weather_forecast(prefecture_code, forecast_data)
        except Exception as e:
            print(f"forecast data update error: {e}")

        # 日付ごとにグループ化されたデータを取得
        c.execute('''
            SELECT DISTINCT forecast_date,
                   MAX(CASE WHEN forecast_time LIKE '09%' THEN temperature END) as temp_min,
                   MAX(CASE WHEN forecast_time LIKE '15%' THEN temperature END) as temp_max,
                   MAX(weather) as weather,
                   MAX(weather_icon) as weather_icon,
                   MAX(area_name) as area_name,
                   MAX(precipitation_probability) as precipitation_probability
            FROM weather_forecasts
            WHERE prefecture_code = ?
            GROUP BY forecast_date
            ORDER BY forecast_date
            LIMIT 7
        ''', (prefecture_code,))
        
        forecast_results = c.fetchall()
        conn.close()

        # カードを横に並べるための行を作成
        forecast_row = ft.Row(
            controls=[],
            scroll=ft.ScrollMode.AUTO
        )

        # 各日付のカードを作成
        for result in forecast_results:
            forecast_date, temp_min, temp_max, weather, weather_icon, area_name, pop = result
            
            # 日付のフォーマット
            date_obj = datetime.strptime(forecast_date, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%m/%d')
            day_of_week = date_obj.strftime('%a')
            
            # カードの作成
            card = ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(f"{formatted_date} ({day_of_week})", 
                                  size=16, 
                                  weight=ft.FontWeight.BOLD,
                                  text_align=ft.TextAlign.CENTER),
                            ft.Text(weather_icon, size=40, text_align=ft.TextAlign.CENTER),
                            ft.Text(weather, 
                                  size=14, 
                                  text_align=ft.TextAlign.CENTER),
                            ft.Row(
                                [
                                    ft.Text(f"最低 {temp_min}℃", 
                                          size=14, 
                                          color=ft.colors.BLUE,
                                          weight=ft.FontWeight.BOLD),
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                            ),
                            ft.Row(
                                [
                                    ft.Text(f"最高 {temp_max}℃", 
                                          size=14, 
                                          color=ft.colors.RED,
                                          weight=ft.FontWeight.BOLD),
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                            ),
                            ft.Text(f"降水確率 {pop}%", 
                                  size=14, 
                                  text_align=ft.TextAlign.CENTER),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    padding=15,
                    width=150,
                )
            )
            forecast_row.controls.append(card)

        # タイトルと予報カードを表示
        weather_info.controls.extend([
            ft.Text(
                f"{prefecture_dropdown.value}の天気予報",
                size=24,
                weight=ft.FontWeight.BOLD,
                text_align=ft.TextAlign.CENTER,
            ),
            forecast_row,
        ])
        
        page.update()

    # ドロップダウンメニューの作成
    region_dropdown = ft.Dropdown(
        width=200,
        options=[ft.dropdown.Option(name) for name in get_regions()],
        label="地域を選択",
    )

    prefecture_dropdown = ft.Dropdown(
        width=200,
        options=[],
        label="都道府県を選択",
    )

    # イベントハンドラの設定
    region_dropdown.on_change = on_region_change
    prefecture_dropdown.on_change = display_weather

    # レイアウトの設定
    page.add(
        ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [region_dropdown, prefecture_dropdown],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    weather_info,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=20,
        )
    )

if __name__ == '__main__':
    ft.app(target=main)