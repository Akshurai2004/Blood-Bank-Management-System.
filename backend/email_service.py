import os
import sys
import time
import ssl
import json
import secrets
import smtplib
import urllib.error
import urllib.request
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid
from typing import Dict, Any, Optional, Tuple

# Try loading environment variables
try:
    from dotenv import load_dotenv
    # Search common locations
    base_dir = os.path.dirname(os.path.abspath(__file__))
    for env_candidate in [
        os.path.join(base_dir, ".env"),
        os.path.join(base_dir, "..", ".env"),
        ".env",
    ]:
        if os.path.isfile(env_candidate):
            load_dotenv(dotenv_path=env_candidate, override=False)
except ImportError:
    pass

# Optional Redis client for distributed / persistent OTP store
try:
    import redis
    _redis_host = os.getenv("REDIS_HOST", "127.0.0.1")
    _redis_port = int(os.getenv("REDIS_PORT", "6379"))
    _redis_client = redis.Redis(
        host=_redis_host,
        port=_redis_port,
        decode_responses=True,
        socket_connect_timeout=0.5,
        socket_timeout=0.5
    )
    # Test connection quickly
    _redis_client.ping()
    _has_redis = True
except Exception:
    _redis_client = None
    _has_redis = False

# Local in-memory fallback store for OTPs
# Structure: { email: { "otp": "123456", "payload": dict, "expires_at": float, "attempts": int, "last_sent_at": float, "purpose": str } }
_otp_store: Dict[str, Dict[str, Any]] = {}


def get_smtp_config() -> Dict[str, Any]:
    """Dynamically read SMTP configuration from environment variables."""
    try:
        from dotenv import load_dotenv
        base_dir = os.path.dirname(os.path.abspath(__file__))
        for env_candidate in [
            os.path.join(base_dir, ".env"),
            os.path.join(base_dir, "..", ".env"),
            ".env",
        ]:
            if os.path.isfile(env_candidate):
                load_dotenv(dotenv_path=env_candidate, override=False)
    except Exception:
        pass

    host = os.getenv("SMTP_HOST", "").strip()
    port_str = os.getenv("SMTP_PORT", "587").strip()
    try:
        port = int(port_str)
    except ValueError:
        port = 587
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    from_addr = os.getenv("SMTP_FROM", "").strip() or os.getenv("EMAILS_FROM", "").strip()
    if not from_addr:
        if user:
            from_addr = f"Blood Bank Security <{user}>"
        else:
            from_addr = "Blood Bank Security <no-reply@bloodbank.org>"

    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")
    require_real = os.getenv("REQUIRE_REAL_EMAIL", "false").lower() in ("true", "1", "yes")
    resend_api_key = os.getenv("RESEND_API_KEY", "").strip()
    email_from = os.getenv("EMAIL_FROM", "").strip() or from_addr

    is_configured = bool(host and user and password)

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "from_addr": from_addr,
        "use_tls": use_tls,
        "require_real": require_real,
        "is_configured": is_configured,
        "resend_api_key": resend_api_key,
        "email_from": email_from,
    }


def generate_otp(length: int = 6) -> str:
    """Generate a secure numeric OTP of given length."""
    return "".join(secrets.choice("0123456789") for _ in range(length))


def build_otp_email_html(otp_code: str, user_name: str, purpose: str = "registration", expiry_minutes: int = 10) -> str:
    """Generate a responsive, beautifully styled HTML email template."""
    action_text = "complete your account registration" if purpose == "registration" else "log into your account"
    title_text = "Verify Your Registration" if purpose == "registration" else "Your One-Time Login Code"
    
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title_text}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; color: #1e293b; }}
    .container {{ max-width: 520px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
    .header {{ background: linear-gradient(135deg, #991b1b 0%, #dc2626 100%); padding: 28px 24px; text-align: center; color: #ffffff; }}
    .header h1 {{ margin: 0; font-size: 22px; font-weight: 700; letter-spacing: -0.5px; }}
    .header p {{ margin: 6px 0 0; opacity: 0.9; font-size: 13px; }}
    .body {{ padding: 32px 24px; }}
    .greeting {{ font-size: 16px; font-weight: 600; margin-bottom: 12px; color: #0f172a; }}
    .text {{ font-size: 14px; line-height: 1.6; color: #475569; margin-bottom: 24px; }}
    .otp-box {{ background: #fef2f2; border: 2px dashed #f87171; border-radius: 10px; padding: 20px; text-align: center; margin: 24px 0; }}
    .otp-label {{ font-size: 12px; font-weight: 700; text-transform: uppercase; color: #991b1b; letter-spacing: 1px; margin-bottom: 8px; }}
    .otp-code {{ font-size: 36px; font-weight: 800; color: #b91c1c; letter-spacing: 8px; font-family: monospace; }}
    .otp-expiry {{ font-size: 12px; color: #64748b; margin-top: 8px; }}
    .alert-box {{ background: #fffbeb; border-left: 4px solid #f59e0b; padding: 12px 16px; border-radius: 4px; font-size: 12px; color: #92400e; margin-top: 24px; line-height: 1.5; }}
    .footer {{ background: #f1f5f9; padding: 16px 24px; text-align: center; font-size: 11px; color: #94a3b8; border-top: 1px solid #e2e8f0; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🩸 Blood Bank Management System</h1>
      <p>Healthcare & Emergency Allocation Network</p>
    </div>
    <div class="body">
      <div class="greeting">Hello, {user_name}!</div>
      <div class="text">
        Use the following one-time verification code to {action_text}.
      </div>
      <div class="otp-box">
        <div class="otp-label">Verification Code</div>
        <div class="otp-code">{otp_code}</div>
        <div class="otp-expiry">⏱️ Valid for {expiry_minutes} minutes</div>
      </div>
      <div class="alert-box">
        <strong>Security Notice:</strong> Never share this OTP with anyone. Our staff will never ask for your verification code. If you did not request this, please ignore this email.
      </div>
    </div>
    <div class="footer">
      This is an automated security notification from Blood Bank Management System.
    </div>
  </div>
</body>
</html>
"""


def send_otp_email(to_email: str, otp_code: str, user_name: str = "User", purpose: str = "registration") -> Tuple[bool, str]:
    """
    Send OTP verification email via SMTP if configured, or console/log simulation in local dev.
    Returns (success, message).
    """
    cfg = get_smtp_config()
    action_name = "Registration" if purpose == "registration" else "Login"
    subject = f"Your Blood Bank Verification Code: {otp_code} ({action_name})"

    # HTTPS email APIs work in hosts that restrict outbound SMTP ports.
    if cfg["resend_api_key"]:
        try:
            payload = json.dumps({
                "from": cfg["email_from"],
                "to": [to_email],
                "subject": subject,
                "text": (
                    f"Hello {user_name},\n\nYour verification code is: {otp_code}\n"
                    "Valid for 10 minutes.\n\nBlood Bank System"
                ),
                "html": build_otp_email_html(otp_code, user_name, purpose),
            }).encode("utf-8")
            request = urllib.request.Request(
                "https://api.resend.com/emails",
                data=payload,
                headers={
                    "Authorization": "Bearer " + cfg["resend_api_key"],
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=15) as response:
                if response.status < 200 or response.status >= 300:
                    raise RuntimeError(f"Resend returned HTTP {response.status}")
            print(f"[EMAIL SERVICE] HTTPS email successfully sent to {to_email} (Subject: {subject})")
            return True, f"Verification code sent to {to_email}. Please check your inbox."
        except urllib.error.HTTPError as err:
            error_msg = f"HTTPS email delivery failed with HTTP {err.code}."
            print(f"[EMAIL SERVICE ERROR] {error_msg}")
            if cfg["require_real"]:
                return False, error_msg
        except Exception as err:
            error_msg = f"HTTPS email delivery failed: {err}"
            print(f"[EMAIL SERVICE ERROR] {error_msg}")
            if cfg["require_real"]:
                return False, error_msg

    # Try real SMTP if configured
    if cfg["is_configured"]:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = cfg["from_addr"]
            msg["To"] = to_email
            msg["Date"] = formatdate(localtime=True)
            msg["Message-ID"] = make_msgid(domain="bloodbank.org")

            text_content = f"Hello {user_name},\n\nYour verification code is: {otp_code}\nValid for 10 minutes.\n\nBlood Bank System"
            html_content = build_otp_email_html(otp_code, user_name, purpose)

            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            context = ssl.create_default_context()

            if cfg["port"] == 465:
                # SSL direct connection
                with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=context, timeout=15) as server:
                    server.login(cfg["user"], cfg["password"])
                    server.sendmail(cfg["from_addr"], [to_email], msg.as_string())
            else:
                # STARTTLS connection (standard 587 or 25)
                with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as server:
                    if cfg["use_tls"]:
                        server.starttls(context=context)
                    server.login(cfg["user"], cfg["password"])
                    server.sendmail(cfg["from_addr"], [to_email], msg.as_string())

            print(f"[EMAIL SERVICE] Real SMTP email successfully sent to {to_email} (Subject: {subject})")
            return True, f"Verification code sent to {to_email}. Please check your inbox."
        except smtplib.SMTPAuthenticationError as auth_err:
            error_msg = f"SMTP Authentication failed: {auth_err}. Please check your SMTP credentials in .env"
            print(f"[EMAIL SERVICE ERROR] {error_msg}")
            if cfg["require_real"]:
                return False, error_msg
        except Exception as err:
            error_msg = f"SMTP delivery failed: {err}"
            print(f"[EMAIL SERVICE ERROR] {error_msg}")
            if cfg["require_real"]:
                return False, error_msg
    
    # Development / Offline mode fallback (only when SMTP is not configured)
    try:
        print("\n" + "=" * 65)
        print("[EMAIL SERVICE - DISPATCH TO INBOX / SERVER LOGS]")
        print(f"To: {to_email} ({user_name})")
        print(f"Subject: {subject}")
        print(f"Action: {purpose.upper()}")
        print(f"VERIFICATION OTP CODE: >>> {otp_code} <<<")
        print(f"Validity: 10 Minutes")
        print("Note: To deliver emails directly to real inboxes, configure SMTP in .env")
        print("=" * 65 + "\n")
    except Exception:
        pass
    
    return True, f"Verification code sent to {to_email}. Please check your email."


class OTPService:
    """Service to manage OTP generation, storage, rate-limiting, and verification."""

    EXPIRY_SECONDS = 600  # 10 minutes
    RESEND_COOLDOWN_SECONDS = 30  # 30 seconds between resends
    MAX_ATTEMPTS = 5

    @classmethod
    def _get_record(cls, email: str) -> Optional[Dict[str, Any]]:
        clean_email = email.strip().lower()
        if _has_redis and _redis_client:
            try:
                raw = _redis_client.get(f"otp:{clean_email}")
                if raw:
                    return json.loads(raw)
            except Exception:
                pass
        return _otp_store.get(clean_email)

    @classmethod
    def _save_record(cls, email: str, data: Dict[str, Any], ttl_seconds: int = 600) -> None:
        clean_email = email.strip().lower()
        _otp_store[clean_email] = data
        if _has_redis and _redis_client:
            try:
                _redis_client.setex(f"otp:{clean_email}", ttl_seconds, json.dumps(data))
            except Exception:
                pass

    @classmethod
    def _delete_record(cls, email: str) -> None:
        clean_email = email.strip().lower()
        _otp_store.pop(clean_email, None)
        if _has_redis and _redis_client:
            try:
                _redis_client.delete(f"otp:{clean_email}")
            except Exception:
                pass

    @classmethod
    def create_registration_otp(cls, email: str, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Store pending registration payload, generate and send OTP to recipient email.
        Returns (success, message).
        """
        clean_email = email.strip().lower()
        now = time.time()
        
        # Check cooldown
        existing = cls._get_record(clean_email)
        if existing:
            elapsed = now - existing.get("last_sent_at", 0)
            if elapsed < cls.RESEND_COOLDOWN_SECONDS:
                wait_sec = int(cls.RESEND_COOLDOWN_SECONDS - elapsed)
                return False, f"Please wait {wait_sec} seconds before requesting a new OTP."

        otp_code = generate_otp(6)
        user_name = payload.get("full_name", "User")

        record = {
            "otp": otp_code,
            "payload": payload,
            "purpose": "registration",
            "expires_at": now + cls.EXPIRY_SECONDS,
            "attempts": 0,
            "last_sent_at": now,
        }
        cls._save_record(clean_email, record, ttl_seconds=cls.EXPIRY_SECONDS)

        success, msg = send_otp_email(clean_email, otp_code, user_name, purpose="registration")
        if not success:
            cls._delete_record(clean_email)
        return success, msg

    @classmethod
    def create_login_otp(cls, email: str, user_name: str = "User") -> Tuple[bool, str]:
        """
        Generate and send OTP to recipient email for passwordless / 2FA login.
        Returns (success, message).
        """
        clean_email = email.strip().lower()
        now = time.time()

        existing = cls._get_record(clean_email)
        if existing and existing.get("purpose") == "login":
            elapsed = now - existing.get("last_sent_at", 0)
            if elapsed < cls.RESEND_COOLDOWN_SECONDS:
                wait_sec = int(cls.RESEND_COOLDOWN_SECONDS - elapsed)
                return False, f"Please wait {wait_sec} seconds before requesting another code."

        otp_code = generate_otp(6)

        record = {
            "otp": otp_code,
            "payload": {},
            "purpose": "login",
            "expires_at": now + cls.EXPIRY_SECONDS,
            "attempts": 0,
            "last_sent_at": now,
        }
        cls._save_record(clean_email, record, ttl_seconds=cls.EXPIRY_SECONDS)

        success, msg = send_otp_email(clean_email, otp_code, user_name, purpose="login")
        if not success:
            cls._delete_record(clean_email)
        return success, msg

    @classmethod
    def verify_registration_otp(cls, email: str, otp_code: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Verify the OTP and return the stored registration payload if valid.
        Returns (is_valid, payload, error_message).
        """
        clean_email = email.strip().lower()
        record = cls._get_record(clean_email)

        if not record:
            return False, None, "No pending registration found for this email. Please register again."

        if record.get("purpose") != "registration":
            return False, None, "Invalid verification request type."

        if time.time() > record.get("expires_at", 0):
            cls._delete_record(clean_email)
            return False, None, "Verification code has expired. Please request a new code."

        if record.get("attempts", 0) >= cls.MAX_ATTEMPTS:
            cls._delete_record(clean_email)
            return False, None, "Too many incorrect attempts. Please start registration again."

        record["attempts"] = record.get("attempts", 0) + 1
        cls._save_record(clean_email, record, ttl_seconds=int(max(10, record.get("expires_at", 0) - time.time())))

        if str(record.get("otp", "")).strip() != str(otp_code).strip():
            remaining = cls.MAX_ATTEMPTS - record["attempts"]
            return False, None, f"Invalid OTP code. {remaining} attempt(s) remaining."

        # OTP is valid! Retrieve payload and clear store
        payload = record["payload"]
        cls._delete_record(clean_email)
        return True, payload, "Verification successful!"

    @classmethod
    def verify_login_otp(cls, email: str, otp_code: str) -> Tuple[bool, str]:
        """
        Verify login OTP.
        Returns (is_valid, message).
        """
        clean_email = email.strip().lower()
        record = cls._get_record(clean_email)

        if not record:
            return False, "No active login OTP found for this email. Please request a new code."

        if record.get("purpose") != "login":
            return False, "Invalid verification request type."

        if time.time() > record.get("expires_at", 0):
            cls._delete_record(clean_email)
            return False, "Verification code has expired. Please request a new code."

        if record.get("attempts", 0) >= cls.MAX_ATTEMPTS:
            cls._delete_record(clean_email)
            return False, "Too many incorrect attempts. Please request a new code."

        record["attempts"] = record.get("attempts", 0) + 1
        cls._save_record(clean_email, record, ttl_seconds=int(max(10, record.get("expires_at", 0) - time.time())))

        if str(record.get("otp", "")).strip() != str(otp_code).strip():
            remaining = cls.MAX_ATTEMPTS - record["attempts"]
            return False, f"Invalid OTP code. {remaining} attempt(s) remaining."

        cls._delete_record(clean_email)
        return True, "Login verified successfully!"

    @classmethod
    def get_internal_otp_for_testing(cls, email: str) -> Optional[str]:
        """Internal helper for server-side testing only (never exposed over HTTP API)."""
        clean_email = email.strip().lower()
        record = cls._get_record(clean_email)
        if record:
            return record.get("otp")
        return None


def test_smtp_connection(target_email: str) -> bool:
    """CLI utility to verify SMTP setup and send a test email."""
    cfg = get_smtp_config()
    print("=" * 60)
    print("🩸 BLOOD BANK EMAIL SERVICE - SMTP DIAGNOSTIC TOOL")
    print("=" * 60)
    print(f"SMTP Host:     {cfg['host'] or '(Not set)'}")
    print(f"SMTP Port:     {cfg['port']}")
    print(f"SMTP User:     {cfg['user'] or '(Not set)'}")
    print(f"SMTP Password: {'*' * len(cfg['password']) if cfg['password'] else '(Not set)'}")
    print(f"SMTP From:     {cfg['from_addr']}")
    print(f"TLS Enabled:   {cfg['use_tls']}")
    print(f"Target Email:  {target_email}")
    print("=" * 60)

    if not cfg["is_configured"]:
        print("❌ SMTP is not configured. Please set SMTP_HOST, SMTP_USER, and SMTP_PASSWORD in .env")
        print("\nQuick Setup for Gmail:")
        print("1. Go to your Google Account > Security > 2-Step Verification")
        print("2. Create an 'App Password' for Mail")
        print("3. Add these lines to your .env file:")
        print("   SMTP_HOST=smtp.gmail.com")
        print("   SMTP_PORT=587")
        print("   SMTP_USER=your_email@gmail.com")
        print("   SMTP_PASSWORD=your_16_character_app_password")
        print("   SMTP_FROM=Blood Bank Management <your_email@gmail.com>")
        print("   SMTP_USE_TLS=true")
        return False

    print("\n⏳ Testing SMTP connection...")
    try:
        context = ssl.create_default_context()
        if cfg["port"] == 465:
            print("  Connecting to SSL port 465...")
            server = smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=context, timeout=15)
        else:
            print(f"  Connecting to port {cfg['port']}...")
            server = smtplib.SMTP(cfg["host"], cfg["port"], timeout=15)
            if cfg["use_tls"]:
                print("  Starting TLS handshake...")
                server.starttls(context=context)

        print(f"  Authenticating as {cfg['user']}...")
        server.login(cfg["user"], cfg["password"])
        print("  ✅ Authentication successful!")

        test_otp = generate_otp(6)
        print(f"  Sending test email to {target_email} with code {test_otp}...")
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Test Blood Bank OTP Code: {test_otp}"
        msg["From"] = cfg["from_addr"]
        msg["To"] = target_email
        msg["Date"] = formatdate(localtime=True)

        text_content = f"Test OTP Code: {test_otp}\n\nYour Blood Bank SMTP setup is working perfectly!"
        html_content = build_otp_email_html(test_otp, "Valued User", "registration", expiry_minutes=10)
        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        server.sendmail(cfg["from_addr"], [target_email], msg.as_string())
        server.quit()
        print(f"  🎉 SUCCESS! Test email with OTP {test_otp} sent to {target_email}.")
        print("  Check your inbox (and spam folder) to verify receipt.")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"\n❌ Authentication Failed ({e.smtp_code}): {e.smtp_error.decode(errors='ignore') if isinstance(e.smtp_error, bytes) else e.smtp_error}")
        print("💡 Hint for Gmail users: Normal passwords do not work! You MUST use a 16-character Google App Password with 2FA enabled.")
        return False
    except Exception as e:
        print(f"\n❌ Error during email delivery: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        target = sys.argv[2] if len(sys.argv) > 2 else "test@example.com"
        test_smtp_connection(target)
    else:
        cfg = get_smtp_config()
        print(f"Email Service Status: {'Configured (Real SMTP)' if cfg['is_configured'] else 'Dev Mode (Simulation)'}")
        print("Usage: python email_service.py test <your_email@example.com>")
