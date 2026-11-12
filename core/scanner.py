"""
Fast Scanner Module
Membaca dan mendekode QR Code secara real-time dari Webcam (OpenCV)
atau dari berkas gambar, serta langsung memvalidasi keaslian tiket
terenkripsi menggunakan C++ Security Engine.
"""

from typing import Tuple, Optional
import numpy as np
import cv2
from PIL import Image

from core.cpp_bridge import bridge


class ScanResult:
    def __init__(
        self,
        raw_text: str = "",
        is_encrypted: bool = False,
        verification_status: int = -1,  # 0=Asli, 1=Palsu, 2=Error Format, -1=Plain/Biasa
        decoded_content: str = "",
        message: str = "",
    ):
        self.raw_text = raw_text
        self.is_encrypted = is_encrypted
        self.verification_status = verification_status
        self.decoded_content = decoded_content
        self.message = message


class ScannerEngine:
    def __init__(self):
        self.detector = cv2.QRCodeDetector()

    def scan_image_file(self, filepath: str, secret_key: Optional[str] = None) -> Optional[ScanResult]:
        """Mendeteksi dan mendekode QR Code dari sebuah file gambar."""
        try:
            # Baca gambar via cv2 (tangani path dengan aman)
            pil_img = Image.open(filepath).convert("RGB")
            cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            return self.process_image_array(cv_img, secret_key)
        except Exception as e:
            return ScanResult(message=f"Gagal membaca gambar: {str(e)}")

    def process_image_array(self, bgr_image: np.ndarray, secret_key: Optional[str] = None) -> Optional[ScanResult]:
        """Menganalisis array citra BGR dari kamera atau file."""
        val, points, _ = self.detector.detectAndDecode(bgr_image)
        if not val:
            return None

        # Evaluasi apakah payload ini adalah tiket terenkripsi
        key = (secret_key or "").strip()
        if val.startswith("SECQR1:"):
            if not key:
                return ScanResult(
                    raw_text=val,
                    is_encrypted=True,
                    verification_status=3,
                    decoded_content="[TERENKRIPSI]",
                    message="Tiket terenkripsi SECQR1 terdeteksi. Masukkan Kunci Rahasia untuk memvalidasi.",
                )

            status, plain_or_err = bridge.decrypt_ticket(val, key)
            if status == 0:
                return ScanResult(
                    raw_text=val,
                    is_encrypted=True,
                    verification_status=0,
                    decoded_content=plain_or_err,
                    message=f"[VALID] TIKET ASLI TERVERIFIKASI: {plain_or_err}",
                )
            else:
                return ScanResult(
                    raw_text=val,
                    is_encrypted=True,
                    verification_status=1,
                    decoded_content="PALSU / TIDAK VALID",
                    message="[PERINGATAN] TIKET PALSU ATAU KUNCI SALAH!",
                )
        else:
            return ScanResult(
                raw_text=val,
                is_encrypted=False,
                verification_status=-1,
                decoded_content=val,
                message=f"QR Terdeteksi: {val}",
            )

    def annotate_frame(
        self,
        bgr_frame: np.ndarray,
        secret_key: Optional[str] = None,
    ) -> Tuple[np.ndarray, Optional[ScanResult]]:
        """
        Mendeteksi QR Code pada frame webcam, menggambar kotak deteksi (hijau/merah),
        dan mengembalikan citra teranotasi serta hasil scan.
        """
        val, points, _ = self.detector.detectAndDecode(bgr_frame)
        scan_res = None

        if val and points is not None:
            scan_res = self.process_image_array(bgr_frame, secret_key)

            # Gambar poligon kotak pembungkus QR Code
            pts = points.astype(int).reshape((-1, 1, 2))

            # Warna kotak: Hijau jika Asli/Biasa (0/-1), Merah jika Palsu (1)
            box_color = (0, 220, 0)  # Hijau (BGR)
            if scan_res and scan_res.verification_status == 1:
                box_color = (0, 0, 240)  # Merah (BGR)
            elif scan_res and scan_res.verification_status == 3:
                box_color = (0, 165, 255)  # Oranye (BGR)

            cv2.polylines(bgr_frame, [pts], isClosed=True, color=box_color, thickness=3)

            # Tambahkan label di atas QR
            x, y = pts[0][0]
            label_text = "VERIFIED" if (scan_res and scan_res.verification_status == 0) else (
                "FAKE/TAMPERED" if (scan_res and scan_res.verification_status == 1) else "QR DETECTED"
            )
            cv2.putText(
                bgr_frame,
                label_text,
                (max(10, x), max(25, y - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                box_color,
                2,
            )

        return bgr_frame, scan_res
