"""
Script khởi chạy Hệ thống Smart E-Mobility Hub - ĐHQG-HCM
Cách chạy:
    python run.py
"""

import sys
import uvicorn
from pathlib import Path

# Đảm bảo đường dẫn gốc của dự án được thêm vào PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Đảm bảo in tiếng Việt chuẩn trên Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

if __name__ == "__main__":
    print("=" * 70)
    print("  SMART E-MOBILITY HUB - KHU ĐÔ THỊ ĐHQG-HCM")
    print("  Hệ thống Điều Phối Phương Tiện Điện & Lập Lịch Sạc Thông Minh")
    print("=" * 70)
    print(f"  * Python: {sys.executable}")
    print(f"  * Project Directory: {ROOT_DIR}")
    print("  * Dashboard Web: http://localhost:8000")
    print("  * Swagger API Docs: http://localhost:8000/docs")
    print("=" * 70)
    print("  Đang khởi động máy chủ Uvicorn...")
    print("  Nhấn Ctrl+C để dừng máy chủ bất kỳ lúc nào.\n")

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
