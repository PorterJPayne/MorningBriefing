import os
import json
import time
import requests
import resend

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# ============================================
# HomeOS Morning Brief
# ============================================

resend.api_key = os.environ["RESEND_API_KEY"]

session = requests.Session()

WEATHER = {
    0: ("☀️", "Clear"),
    1: ("🌤️", "Mostly Clear"),
    2: ("⛅", "Partly Cloudy"),
    3: ("☁️", "Cloudy"),
    45: ("🌫️", "Fog"),
    48: ("🌫️", "Fog"),
    51: ("🌦️", "Light Drizzle"),
    53: ("🌦️", "Drizzle"),
    55: ("🌧️", "Heavy Drizzle"),
    61: ("🌦️", "Rain"),
    63: ("🌧️", "Rain"),
    65: ("🌧️", "Heavy Rain"),
    71: ("❄️", "Snow"),
    73: ("❄️", "Snow"),
    75: ("❄️", "Heavy Snow"),
    80: ("🌦️", "Rain Showers"),
    81: ("🌧️", "Rain Showers"),
    82: ("🌧️", "Heavy Rain Showers"),
    85: ("🌨️", "Snow Showers"),
    86: ("🌨️", "Heavy Snow Showers"),
    95: ("⛈️", "Thunderstorms"),
}

print("Loading locations...", flush=True)

with open("locations.json", "r") as f:
    locations = json.load(f)

print(f"Loaded {len(locations)} locations.", flush=True)


def fetch_weather(location):

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={location['latitude']}"
        f"&longitude={location['longitude']}"
        "&daily="
        "weather_code,"
        "temperature_2m_max,"
        "temperature_2m_min,"
        "precipitation_probability_max,"
        "precipitation_sum,"
        "wind_speed_10m_max"
        "&temperature_unit=fahrenheit"
        "&wind_speed_unit=mph"
        "&precipitation_unit=inch"
        "&timezone=auto"
        "&forecast_days=1"
    )

    last_error = None

    for attempt in range(3):

        try:

            response = session.get(url, timeout=20)
            response.raise_for_status()

            data = response.json()

            return {
                "success": True,
                "name": location["name"],
                "state": location["state"],
                "high": round(data["daily"]["temperature_2m_max"][0]),
                "low": round(data["daily"]["temperature_2m_min"][0]),
                "rain": round(data["daily"]["precipitation_probability_max"][0]),
                "amount": data["daily"]["precipitation_sum"][0],
                "wind": round(data["daily"]["wind_speed_10m_max"][0]),
                "code": data["daily"]["weather_code"][0],
            }

        except Exception as e:
            last_error = e
            print(
                f"Retry {attempt+1}/3 for {location['name']} ({e})",
                flush=True,
            )
            time.sleep(attempt + 1)

    return {
        "success": False,
        "name": location["name"],
        "state": location["state"],
        "error": str(last_error),
    }


print("Fetching forecasts...", flush=True)

results = []

with ThreadPoolExecutor(max_workers=8) as executor:

    futures = [executor.submit(fetch_weather, l) for l in locations]

    for future in as_completed(futures):
        results.append(future.result())

order = {l["name"]: i for i, l in enumerate(locations)}
results.sort(key=lambda r: order[r["name"]])

good = [r for r in results if r["success"]]

groups = defaultdict(list)

for r in results:
    groups[r["state"]].append(r)

hottest = max(good, key=lambda x: x["high"])
coolest = min(good, key=lambda x: x["low"])
rainiest = max(good, key=lambda x: x["rain"])
windiest = max(good, key=lambda x: x["wind"])

today = datetime.now().strftime("%A, %B %d, %Y")

state_order = [
    "Utah",
    "California",
    "Colorado",
    "Arizona",
    "Idaho",
    "Nevada",
    "Oregon",
    "Montana",
    "Texas",
]

html = f"""
<html>
<head>
<style>
body {{
    background:#eef3f8;
    font-family:Arial,Helvetica,sans-serif;
    margin:0;
}}

.container {{
    max-width:900px;
    margin:30px auto;
    background:white;
    border-radius:14px;
    overflow:hidden;
    box-shadow:0 2px 12px rgba(0,0,0,.15);
}}

.header {{
    background:#194f90;
    color:white;
    padding:30px;
}}

.header h1 {{
    margin:0;
}}

.summary {{
    padding:20px 30px;
    background:#f5f9fd;
    line-height:1.8;
}}

.state {{
    background:#194f90;
    color:white;
    padding:10px 20px;
    font-size:20px;
    font-weight:bold;
    margin-top:20px;
}}

table {{
    width:100%;
    border-collapse:collapse;
}}

th {{
    background:#edf3fa;
    padding:10px;
}}

td {{
    padding:10px;
    border-bottom:1px solid #ececec;
    text-align:center;
}}

td:first-child,
th:first-child {{
    text-align:left;
}}

.footer {{
    text-align:center;
    color:#888;
    padding:25px;
    font-size:12px;
}}
</style>
</head>

<body>

<div class="container">

<div class="header">
<h1>Kiln Weather Report</h1>
<div>{today}</div>
</div>

<div class="summary">

<b>🔥 Hottest:</b> {hottest["name"]} ({hottest["high"]}°F)<br>
<b>❄️ Coolest:</b> {coolest["name"]} ({coolest["low"]}°F)<br>
<b>🌧 Highest Rain Chance:</b> {rainiest["name"]} ({rainiest["rain"]}%)<br>
<b>🌬 Windiest:</b> {windiest["name"]} ({windiest["wind"]} mph)

</div>
"""
for state in state_order:

    if state not in groups:
        continue

    html += f"""
    <div class="state">{state}</div>

    <table>

    <tr>
        <th>City</th>
        <th>Conditions</th>
        <th>High</th>
        <th>Low</th>
        <th>Rain</th>
        <th>Wind</th>
    </tr>
    """

    for r in groups[state]:

        if not r["success"]:

            html += f"""
            <tr>
                <td>{r["name"]}</td>
                <td colspan="5">❌ Unable to retrieve weather</td>
            </tr>
            """

            continue

        icon, desc = WEATHER.get(
            r["code"],
            ("❔", "Unknown")
        )

        rain = "—"

        if r["rain"] >= 20:
            rain = f"{r['rain']}%"

        if r["amount"] > 0:

            if "Snow" in desc:

                if rain == "—":
                    rain = ""

                rain += f' {r["amount"]:.2f}" snow'

            else:

                if rain == "—":
                    rain = ""

                rain += f' {r["amount"]:.2f}"'

        if rain == "":
            rain = "—"

        wind = "—"

        if r["wind"] >= 20:
            wind = f'{r["wind"]} mph'

        high = f'{r["high"]}°'
        low = f'{r["low"]}°'

        if r["high"] >= 100:
            high = f'🔥 {high}'
        elif r["high"] >= 90:
            high = f'🟠 {high}'

        if r["low"] <= 32:
            low = f'❄️ {low}'

        html += f"""
        <tr>
            <td><b>{r["name"]}</b></td>
            <td>{icon}<br><small>{desc}</small></td>
            <td>{high}</td>
            <td>{low}</td>
            <td>{rain}</td>
            <td>{wind}</td>
        </tr>
        """

    html += "</table>"

html += """

</div>

</body>
</html>
"""

print("Sending email...", flush=True)

response = resend.Emails.send({

    "from": "onboarding@resend.dev",

    "to": "porterpayne04@gmail.com", "porter.p@kiln.com",

    "subject": "Kiln Weather Report",

    "html": html,

})

print(response)
print("Done!", flush=True)