import flet as ft
import requests
from datetime import datetime

# 天気の文字列に対応するアイコンのマッピング（ご提供いただいたものを統合）
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
    # 必要に応じて他の天気も追加可能
}

def main(page: ft.Page):
    page.title = "日本の天気予報アプリ"

    # 地域と都道府県のデータを取得
    def get_regions_and_prefectures():
        # area.jsonからデータを取得
        url = "https://www.jma.go.jp/bosai/common/const/area.json"
        response = requests.get(url)
        area_data = response.json()

        # 地方（region）のコードと名前を取得
        regions = {}
        for code, info in area_data['offices'].items():
            region_code = info['parent']
            region_name = area_data['centers'][region_code]['name']
            prefecture_name = info['name']
            if region_name not in regions:
                regions[region_name] = []
            regions[region_name].append({
                'code': code,
                'name': prefecture_name
            })
        return regions

    # 天気予報を取得する
    def get_weather_forecast(area_code):
        url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"
        response = requests.get(url)
        data = response.json()
        return data

    # 地方選択時に都道府県のドロップダウンを更新
    def on_region_change(e):
        selected_region = region_dropdown.value
        prefecture_dropdown.options = [
            ft.dropdown.Option(pref['name']) for pref in regions[selected_region]
        ]
        prefecture_dropdown.value = None  # 初期化
        prefecture_dropdown.update()
        # 天気情報をクリア
        weather_info.controls.clear()
        page.update()

    # 都道府県選択時に天気情報を取得して表示
    def display_weather(e):
        selected_region = region_dropdown.value
        selected_prefecture = prefecture_dropdown.value

        # 選択された都道府県のコードを取得
        for pref in regions[selected_region]:
            if pref['name'] == selected_prefecture:
                area_code = pref['code']
                break
        else:
            return

        # 天気予報データを取得
        forecast_data = get_weather_forecast(area_code)

        # エリアコードを取得（市区町村のコード）
        area_codes = []

        # 気温情報を取得するために、エリアコードを取得
        # 今回は最初のエリアコードを使用
        area_json = forecast_data[0]
        time_series = area_json.get("timeSeries", [])
        for ts in time_series:
            areas = ts.get("areas", [])
            for area in areas:
                if "weathers" in area or "temps" in area or "pops" in area:
                    area_code_temp = area["area"]["code"]
                    area_name = area["area"]["name"]
                    area_codes.append((area_code_temp, area_name))
                    break
            if area_codes:
                break

        # 天気情報を解析して表示
        weather_info.controls.clear()

        # データを格納するリスト
        table_rows = []

        # データを一時的に格納する辞書
        data_dict = {}

        # 時系列のデータをまとめる
        for ts in forecast_data[0]["timeSeries"]:
            timeDefines = ts["timeDefines"]
            areas = ts["areas"]
            for area in areas:
                if area["area"]["code"] == area_codes[0][0]:
                    for i, time in enumerate(timeDefines):
                        time_fmt = datetime.fromisoformat(time).strftime("%Y-%m-%d %H:%M")
                        if time_fmt not in data_dict:
                            data_dict[time_fmt] = {}
                        if "weathers" in area:
                            weather = area["weathers"][i] if i < len(area["weathers"]) else ""
                            # 天気アイコンを取得
                            weather_icon = ""
                            for key in weather_icons:
                                if key in weather:
                                    weather_icon = weather_icons[key]
                                    break
                            data_dict[time_fmt]["weather"] = weather
                            data_dict[time_fmt]["weather_icon"] = weather_icon
                        if "temps" in area:
                            temp = area["temps"][i] if i < len(area["temps"]) else ""
                            data_dict[time_fmt]["temp"] = temp
                        if "pops" in area:
                            pop = area["pops"][i] if i < len(area["pops"]) else ""
                            data_dict[time_fmt]["pop"] = pop

        # データをテーブルに追加
        for time_fmt in sorted(data_dict.keys()):
            date_str, time_str = time_fmt.split(' ')
            weather_icon = data_dict[time_fmt].get("weather_icon", "")
            weather = data_dict[time_fmt].get("weather", "")
            temp = data_dict[time_fmt].get("temp", "")
            pop = data_dict[time_fmt].get("pop", "")

            table_rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(date_str)),
                    ft.DataCell(ft.Text(time_str)),
                    ft.DataCell(ft.Text(weather_icon)),
                    ft.DataCell(ft.Text(weather)),
                    ft.DataCell(ft.Text(f"{temp}℃" if temp else "")),
                    ft.DataCell(ft.Text(f"{pop}%" if pop else "")),
                ])
            )

        # データテーブルを作成
        data_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("日付")),
                ft.DataColumn(ft.Text("時刻")),
                ft.DataColumn(ft.Text("天気")),
                ft.DataColumn(ft.Text("詳細")),
                ft.DataColumn(ft.Text("気温")),
                ft.DataColumn(ft.Text("降水確率")),
            ],
            rows=table_rows
        )

        weather_info.controls.append(ft.Text(f"{selected_prefecture} ({area_codes[0][1]})の天気予報：", size=20, weight=ft.FontWeight.BOLD))
        weather_info.controls.append(data_table)
        page.update()

    # 地域と都道府県のデータを取得
    regions = get_regions_and_prefectures()

    # 地域名のリスト
    region_names = list(regions.keys())

    # 地域のドロップダウンメニュー
    region_dropdown = ft.Dropdown(
        options=[ft.dropdown.Option(name) for name in region_names],
        on_change=on_region_change
    )

    # 都道府県のドロップダウンメニュー
    prefecture_dropdown = ft.Dropdown(
        options=[],
        on_change=display_weather
    )

    weather_info = ft.Column()

    page.add(
        ft.Column(
            [
                ft.Text("地域を選択してください："),
                region_dropdown,
                ft.Text("都道府県を選択してください："),
                prefecture_dropdown,
                weather_info,
            ],
            alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.START
        )
    )

ft.app(target=main)