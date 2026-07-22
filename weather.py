import os
import json
import requests
import resend

# Configure Resend
resend.api_key = os.environ["RESEND_API_KEY"]

# Load locations
with open("locations.json", "r") as f:
    locations = json.load(f)

# Build the HTML email
html = """
<h1>🌤 Morning Weather Report</h1>
"""

for location in locations:

    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={location['latitude']}"
        f"&longitude={location['longitude']}"
        f"&daily=temperature_2m_max,temperature_2m_min"
        f"&temperature_unit=fahrenheit"
        f"&timezone=auto"
    )

    response = requests.get(url)
    data = response.json()

    high = data["daily"]["temperature_2m_max"][0]
    low = data["daily"]["temperature_2m_min"][0]

    html += f"""
    <h2>{location['name']}</h2>
    <p>
        High: <strong>{high}°F</strong><br>
        Low: <strong>{low}°F</strong>
    </p>
    """

# Send email
resend.Emails.send({
    "from": "onboarding@resend.dev",
    "to": "porterpayne04@gmail.com",
    "subject": "Morning Weather",
    "html": html
})

print("Email sent!")