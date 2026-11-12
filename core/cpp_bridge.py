"""
C++ Native Bridge Module
Menghubungkan antarmuka Python dengan modul biner native C++ (core/qr_native.dll / qr_native.exe).
Menyediakan fallback otomatis ke modul Python murni (core/security.py & core/batch_engine.py)
sehingga aplikasi selalu berjalan 100% stabil dalam berbagai kondisi sistem operasi.
"""

import os
import subprocess
import ctypes
from typing import Tuple, Optional
from core.security import SecureTicket


class CPPBridge:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.dll_path = os.path.join(self.base_dir, "core", "qr_native.dll")
        self.exe_path = os.path.join(self.base_dir, "core", "qr_native.exe")
        self.cdll = None
        self._init_backend()

    def _init_backend(self):
        """Mencoba memuat DLL C++ secara langsung jika diizinkan sistem."""
        if os.path.exists(self.dll_path):
            try:
                # Muat via ctypes
                lib = ctypes.CDLL(self.dll_path, winmode=0)
                # Setup signatur fungsi
                lib.cpp_encrypt_ticket.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
                lib.cpp_encrypt_ticket.restype = ctypes.c_int

                lib.cpp_decrypt_ticket.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
                lib.cpp_decrypt_ticket.restype = ctypes.c_int

                lib.cpp_benchmark_matrix.argtypes = [ctypes.c_int]
                lib.cpp_benchmark_matrix.restype = ctypes.c_double

                self.cdll = lib
            except Exception:
                self.cdll = None

    def is_cpp_active(self) -> bool:
        """Mengembalikan True jika C++ DLL atau C++ EXE dapat digunakan."""
        return self.cdll is not None or os.path.exists(self.exe_path)

    def encrypt_ticket(self, plaintext: str, secret_key: str) -> str:
        """Enkripsi payload dengan keamanan C++ (atau Python fallback interoperabel)."""
        if self.cdll:
            try:
                buf = ctypes.create_string_buffer(4096)
                res = self.cdll.cpp_encrypt_ticket(
                    plaintext.encode("utf-8"),
                    secret_key.encode("utf-8"),
                    buf,
                    4096,
                )
                if res == 0:
                    return buf.value.decode("utf-8")
            except Exception:
                pass

        # Python fallback yang 100% identik secara format
        return SecureTicket.encrypt(plaintext, secret_key)

    def decrypt_ticket(self, token: str, secret_key: str) -> Tuple[int, str]:
        """Dekripsi dan verifikasi keaslian payload tiket."""
        if self.cdll:
            try:
                buf = ctypes.create_string_buffer(4096)
                res = self.cdll.cpp_decrypt_ticket(
                    token.encode("utf-8"),
                    secret_key.encode("utf-8"),
                    buf,
                    4096,
                )
                if res == 0:
                    return 0, buf.value.decode("utf-8")
                elif res == 1:
                    return 1, "PERINGATAN: TIKET PALSU ATAU KUNCI SALAH!"
                else:
                    return res, "Format payload tidak valid."
            except Exception:
                pass

        return SecureTicket.decrypt(token, secret_key)

    def benchmark_speed(self, count: int = 5000) -> Tuple[float, int]:
        """
        Menghitung kecepatan pembuatan QR code matrix.
        Mengembalikan (waktu_ms, qr_per_detik).
        """
        if self.cdll:
            try:
                ms = self.cdll.cpp_benchmark_matrix(count)
                if ms > 0:
                    qps = int(count / (ms / 1000.0))
                    return ms, qps
            except Exception:
                pass

        # Fallback ke benchmark Python
        import time
        import qrcode

        start = time.perf_counter()
        for i in range(min(500, count)):
            qr = qrcode.QRCode(box_size=10, border=2)
            qr.add_data(f"BENCHMARK-{i}")
            qr.make(fit=True)
        elapsed_sec = time.perf_counter() - start
        scaled_ms = (elapsed_sec / min(500, count)) * count * 1000.0
        qps = int(min(500, count) / elapsed_sec)
        return scaled_ms, qps


# Singleton instance
bridge = CPPBridge()
