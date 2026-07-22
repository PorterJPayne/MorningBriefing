import os
import resend

resend.api_key = os.environ["RESEND_API_KEY"]

response = resend.Emails.send({
    "from": "onboarding@resend.dev",
    "to": "porterpayne04@gmail.com",
    "subject": "My first GitHub email",
    "html": "<h1>🎉 It worked!</h1><p>This email was sent using GitHub Actions and Resend.</p>"
})

print(response)
