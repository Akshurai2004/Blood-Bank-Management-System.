import sys
import os
import re
import subprocess
import threading
import time

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

try:
    import qrcode
    HAS_QR = True
except ImportError:
    HAS_QR = False

def copy_to_clipboard(text):
    try:
        process = subprocess.Popen(['clip'], stdin=subprocess.PIPE, close_fds=True)
        process.communicate(input=text.strip().encode('utf-8'))
    except Exception:
        pass

def print_qr_code(url):
    if not HAS_QR:
        return
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        print("\n" + "=" * 60)
        print("  SCAN WITH YOUR PHONE CAMERA TO OPEN INSTANTLY:")
        print("=" * 60)
        qr.print_ascii(invert=True)
    except Exception as e:
        pass

def main():
    cloudflared_path = os.path.join(os.path.dirname(__file__), "cloudflared.exe")
    if not os.path.exists(cloudflared_path):
        print(f"[ERROR] cloudflared.exe not found at {cloudflared_path}")
        sys.exit(1)

    print("========================================================")
    print("  BLOOD BANK MANAGEMENT SYSTEM - LIVE PUBLIC TUNNEL")
    print("========================================================")
    print("Starting Cloudflare Secure Tunnel...")

    cmd = [cloudflared_path, "tunnel", "--url", "http://localhost:3000"]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding='utf-8',
        errors='replace'
    )

    url_found = False
    tunnel_url = ""

    url_regex = re.compile(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com')

    for line in iter(proc.stdout.readline, ''):
        if not line:
            break
        
        if not url_found:
            match = url_regex.search(line)
            if match:
                tunnel_url = match.group(0)
                url_found = True
                copy_to_clipboard(tunnel_url)
                
                print("\n" + "#" * 65)
                print("  YOUR PUBLIC HTTPS URL IS READY & ACTIVE!")
                print("#" * 65)
                print(f"\n  >> Live URL:  {tunnel_url}\n")
                print("  [+] Copied to your clipboard! (Paste to WhatsApp/Mobile)")
                print("  [+] Accessible on Mobile, Tablet, PC from anywhere worldwide")
                
                print_qr_code(tunnel_url)

                print("=" * 65)
                print("  IMPORTANT: KEEP THIS WINDOW OPEN!")
                print("  Closing this window will stop the live mobile connection.")
                print("=" * 65 + "\n")
                print("--- Live Traffic & Request Logs below ---")
                continue

        # Print cloudflared logs once URL is displayed
        if url_found:
            # Filter verbose metrics, show connections
            if "GET " in line or "POST " in line or "Registered tunnel connection" in line or "error" in line.lower():
                print(line.strip())

    proc.wait()

if __name__ == '__main__':
    main()
