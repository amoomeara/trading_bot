import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

def send_sms_test():
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_num = os.getenv("TWILIO_PHONE_NUMBER")
    my_num = os.getenv("MY_PHONE_NUMBER")

    client = Client(sid, token)
    body = "🚨 Test Alert: Your bot's SMS system is working!"

    try:
        message = client.messages.create(
            body=body,
            from_=twilio_num,
            to=my_num
        )
        print("✅ SMS sent successfully!")
    except Exception as e:
        print(f"❌ Error sending SMS: {e}")

send_sms_test()
