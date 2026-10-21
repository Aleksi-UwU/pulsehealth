import os
import sys
import socket
import uvicorn

def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == "__main__":
    ip = get_lan_ip()
    port = 8000

    print("=" * 65)
    print("🔥 PULSEHEALTH - APPLE WATCH & IPHONE 16 PRO MAX HEALTH JOURNEY")
    print("=" * 65)
    print(f"\n📱 Open on your iPhone 16 Pro Max (Safari):")
    print(f"   ➔  http://{ip}:{port}")
    print(f"\n💻 Open on this Windows PC:")
    print(f"   ➔  http://localhost:{port}")
    print(f"\n⌚ Apple Health Webhook Endpoint:")
    print(f"   ➔  http://{ip}:{port}/api/sync/health")
    print("\n💡 Tip: In Safari on your iPhone, tap 'Share' -> 'Add to Home Screen'")
    print("   to run PulseHealth as a native full-screen OLED app.")
    print("=" * 65 + "\n")

    # Add backend directory to sys.path so app imports work cleanly
    backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
