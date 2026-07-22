import os
import json
import requests
import resend

# Configure Resend
resend.api_key = os.environ["RESEND_API_KEY"]

print("Loading locations...", flush=True)

with open("locations.json", "r") as f:
    locations = json.load(f)

print(f"Loaded {len(locations)} locations.", flush=True)

html = """
<h1>🌤 Morning Weather Report</h1>
<p>Today's forecast:</p>
<hr>
"""

for location in locations:

    print(f"Fetching {location['name']}...", flush=True)

    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={location['latitude']}"
            f"&longitude={location['longitude']}"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum"
            f"&temperature_unit=fahrenheit"
            f"&precipitation_unit=inch"
            f"&timezone=auto"
            f"&forecast_days=1"
        )

        response = requests.get(url, timeout=10)
        response.raise_for_status()

        print(f"Received response for {location['name']}", flush=True)

        data = response.json()

        high = round(data["daily"]["temperature_2m_max"][0])
        low = round(data["daily"]["temperature_2m_min"][0])
        rain_chance = round(data["daily"]["precipitation_probability_max"][0])
        rain_amount = data["daily"]["precipitation_sum"][0]

        html += f"""
        <h2>{location['name']}</h2>
        <ul>
            <li>🌡 High: <strong>{high}°F</strong></li>
            <li>❄️ Low: <strong>{low}°F</strong></li>
            <li>🌧 Chance of Rain: <strong>{rain_chance}%</strong></li>
        """

        if rain_amount > 0:
            html += f"""
            <li>☔ Expected Rain: <strong>{rain_amount:.2f}"</strong></li>
            """

        html += """
        </ul>
        <hr>
        """

        print(f"Finished {location['name']}", flush=True)

    except Exception as e:
        print(f"ERROR for {location['name']}: {e}", flush=True)

        html += f"""
        <h2>{location['name']}</h2>
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