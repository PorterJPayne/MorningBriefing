import os
import json
import time
import requests
import resend
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure Resend
resend.api_key = os.environ["RESEND_API_KEY"]

print("Loading locations...", flush=True)

with open("locations.json", "r") as f:
    locations = json.load(f)

print(f"Loaded {len(locations)} locations.", flush=True)

session = requests.Session()


def fetch_weather(location):
    print(f"Fetching {location['name']}...", flush=True)

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={location['latitude']}"
        f"&longitude={location['longitude']}"
        "&daily=temperature_2m_max,"
        "temperature_2m_min,"
        "precipitation_probability_max,"
        "precipitation_sum"
        "&temperature_unit=fahrenheit"
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

            high = round(data["daily"]["temperature_2m_max"][0])
            low = round(data["daily"]["temperature_2m_min"][0])
            rain_chance = round(data["daily"]["precipitation_probability_max"][0])
            rain_amount = data["daily"]["precipitation_sum"][0]

            print(f"Finished {location['name']}", flush=True)

            return {
                "success": True,
                "name": location["name"],
                "high": high,
                "low": low,
                "rain_chance": rain_chance,
                "rain_amount": rain_amount,
            }

        except Exception as e:
            last_error = e
            print(
                f"Retry {attempt + 1}/3 for {location['name']} ({e})",
                flush=True,
            )
            time.sleep(attempt + 1)

    return {
        "success": False,
        "name": location["name"],
        "error": str(last_error),
    }


results = []

with ThreadPoolExecutor(max_workers=8) as executor:
    futures = [executor.submit(fetch_weather, loc) for loc in locations]

    for future in as_completed(futures):
        results.append(future.result())

# Sort results back into the same order as locations.json
order = {loc["name"]: i for i, loc in enumerate(locations)}
results.sort(key=lambda x: order[x["name"]])

html = """
<h1>🌤 Morning Weather Report</h1>
<p>Today's forecast:</p>
<hr>
"""

for result in results:

    if result["success"]:

        html += f"""
        <h2>{result['name']}</h2>
        <ul>
            <li>🌡 High: <strong>{result['high']}°F</strong></li>
            <li>❄️ Low: <strong>{result['low']}°F</strong></li>
            <li>🌧 Chance of Rain: <strong>{result['rain_chance']}%</strong></li>
        """

        if result["rain_amount"] > 0:
            html += f"""
            <li>☔ Expected Rain: <strong>{result['rain_amount']:.2f}"</strong></li>
            """

        html += """
        </ul>
        <hr>
        """

    else:
        html += f"""
        <h2>{result['name']}</h2>
        <p><strong>Unable to retrieve weather.</strong></p>
        <hr>
        """

print("Sending email...", flush=True)

response = resend.Emails.send({
    "from": "onboarding@resend.dev",
    "to": "porterpayne04@gmail.com",
    "subject": "🌤 Morning Weather Report",
    "html": html
})

print("Email sent!", flush=True)
print(response, flush=True)