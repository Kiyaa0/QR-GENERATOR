"""
QR Studio Pro - Desktop Application Entry Point
Aplikasi Desktop Pembuat QR Code Modern dengan Python Engine.
"""

import sys
import os

# Tambahkan direktori root aplikasi ke sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    try:
        from ui.main_window import QRApp

        app = QRApp()
        app.mainloop()
    except ImportError as e:
        print(f"Error: Dependency belum terpasang dengan lengkap: {e}")
        print("Silakan jalankan: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"Terjadi kesalahan saat menjalankan aplikasi: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
