import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# 이 설정을 별도 .env 파일에 두는 것이 안전합니다.
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

def send_verification_email(target_email: str, code: str):
    msg = EmailMessage()
    msg.set_content(f"안녕하세요! 인증번호는 [{code}] 입니다. 3분 이내에 입력해주세요.")
    msg["Subject"] = "[Stock Analysis] 회원가입 인증번호"
    msg["From"] = SMTP_USER
    msg["To"] = target_email

    try:
        # SSL 보안 연결로 메일 발송
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(msg)
        return True
    except Exception as e:
        print(f"메일 발송 실패: {e}")
        return False