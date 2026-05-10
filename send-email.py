import smtplib
from email.mime.text import MIMEText
from datetime import date
import os

def send_email():
    sender = os.environ["EMAIL_SENDER"]
    password = os.environ["EMAIL_PASSWORD"]
    receiver = os.environ["EMAIL_RECEIVER"]

    msg = MIMEText(f"오늘 날짜: {date.today()}\n좋은 아침입니다!")
    msg["Subject"] = "매일 아침 알림"
    msg["From"] = sender
    msg["To"] = receiver

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.send_message(msg)

send_email()