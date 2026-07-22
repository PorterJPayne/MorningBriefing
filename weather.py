import os
import json
import time
import requests
import resend
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# ==========================
# Configuration
# ==========================

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
    82: ("🌧️", "Heavy Showers"),
    85: ("🌨️", "Snow Showers"),
    86: ("🌨️", "Heavy Snow Showers"),
    95: ("⛈️", "Thunderstorms"),
}

print("Loading locations...", flush=True)

with open("locations.json") as f:
    locations = json.load(f)

print(f"Loaded {len(locations)} locations.", flush=True)


def state_from_name(name):
    mapping = {
        "Salt Lake City": "Utah",
        "Lehi": "Utah",
        "Park City": "Utah",
        "Provo": "Utah",
        "Holladay": "Utah",
        "St. George": "Utah",
        "Boulder": "Colorado",
        "Littleton": "Colorado",
        "Fort Collins": "Colorado",
        "Solana Beach": "California",
        "Leucadia": "California",
        "Carlsbad": "California",
        "Rancho Bernardo": "California",
        "Gilbert": "Arizona",
        "Biltmore": "Arizona",
        "Meridian": "Idaho",
        "Boise": "Idaho",
        "Las Vegas": "Nevada",
        "Reno": "Nevada",
        "Portland": "Oregon",
        "Bend": "Oregon",
        "Bozeman": "Montana",
        "Plano": "Texas",
        "Preston Hollow": "Texas",
        "Fremont": "California",
    }
    return mapping.get(name, "Other")


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
                "state": state_from_name(location["name"]),
                "high": round(data["daily"]["temperature_2m_max"][0]),
                "low": round(data["daily"]["temperature_2m_min"][0]),
                "rain": round(data["daily"]["precipitation_probability_max"][0]),
                "amount": data["daily"]["precipitation_sum"][0],
                "wind": round(data["daily"]["wind_speed_10m_max"][0]),
                "code": data["daily"]["weather_code"][0],
            }

        except Exception as e:
            last_error = e
            time.sleep(attempt + 1)

    return {
        "success": False,
        "name": location["name"],
        "state": state_from_name(location["name"]),
        "error": str(last_error),
    }


results = []

with ThreadPoolExecutor(max_workers=8) as executor:

    futures = [executor.submit(fetch_weather, l) for l in locations]

    for future in as_completed(futures):
        results.append(future.result())

order = {l["name"]: i for i, l in enumerate(locations)}
results.sort(key=lambda r: order[r["name"]])

good = [r for r in results if r["success"]]

hottest = max(good, key=lambda x: x["high"])
coolest = min(good, key=lambda x: x["low"])
rainiest = max(good, key=lambda x: x["rain"])
windiest = max(good, key=lambda x: x["wind"])

groups = defaultdict(list)

for r in results:
    groups[r["state"]].append(r)

today = datetime.now().strftime("%A, %B %d")

html = f"""
<html>
<body style="margin:0;background:#eef2f7;font-family:Arial,sans-serif;">

<div style="max-width:900px;margin:30px auto;background:white;border-radius:14px;padding:30px;box-shadow:0 2px 12px rgba(0,0,0,.12);">

<h1 style="margin-top:0;color:#1d4e89;">
🏡 HomeOS Morning Brief
</h1>

<p style="color:#666;">{today}</p>

<div style="background:#f4f8fc;padding:18px;border-radius:10px;margin-bottom:30px;">

<b>🔥 Hottest:</b> {hottest["name"]} ({hottest["high"]}°)<br>
<b>❄️ Coolest:</b> {coolest["name"]} ({coolest["low"]}°)<br>
<b>🌧 Highest Rain Chance:</b> {rainiest["name"]} ({rainiest["rain"]}%)<br>
<b>🌬 Windiest:</b> {windiest["name"]} ({windiest["wind"]} mph)

</div>
"""

for state in sorted(groups):

    html += f"""
    <h2 style="
    background:#1d4e89;
    color:white;
    padding:10px 14px;
    border-radius:8px;">
    {state}
    </h2>

    <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
    <tr style="background:#edf3fa;">
        <th align="left">City</th>
        <th>Weather</th>
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
            <td>{r['name']}</td>
            <td colspan="5">Unable to retrieve weather.</td>
            </tr>
            """
            continue

        icon, desc = WEATHER.get(r["code"], ("❔", "Unknown"))

        rain = "—"

        if r["rain"] >= 20:
            rain = f"{r['rain']}%"

        if r["amount"] > 0:
            if "Snow" in desc:
                rain += f' ({r["amount"]:.2f}" snow)'
            else:
                rain += f' ({r["amount"]:.2f}")'

        wind = "—"
        if r["wind"] >= 20:
            wind = f"{r['wind']} mph"

        html += f"""
        <tr style="border-bottom:1px solid #eee;">
            <td>{r['name']}</td>
            <td align="center">{icon}<br><small>{desc}</small></td>
            <td align="center">{r['high']}°</td>
            <td align="center">{r['low']}°</td>
            <td align="center">{rain}</td>
            <td align="center">{wind}</td>
        </tr>
        """

    html += "</table>"

html += """
<p style="text-align:center;color:#888;font-size:12px;margin-top:30px;">
Generated automatically by HomeOS
</p>

</div>
</body>
</html>
"""

print("Sending email...", flush=True)

resend.Emails.send({
    "from": "onboarding@resend.dev",
    "to": "porterpayne04@gmail.com",
    "subject": "🏡 HomeOS Morning Brief",
    "html": html,
})

print("Done!", flush=True)