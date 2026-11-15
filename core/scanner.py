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
        """
        Mendeteksi dan mendekode QR Code dari sebuah file gambar.
        Mendukung multi-scale downsampling dan padding agar dapat membaca foto kamera
        smartphone beresolusi tinggi (3000x4000) maupun tangkapan layar langsung.
        """
        try:
            pil_img = Image.open(filepath).convert("RGB")
            cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

            # 1. Coba deteksi langsung
            res = self.process_image_array(cv_img, secret_key)
            if res and res.raw_text:
                return res

            # 2. Tambahkan border margin jika citra terlalu rapat ke tepi
            bordered = cv2.copyMakeBorder(cv_img, 40, 40, 40, 40, cv2.BORDER_CONSTANT, value=[255, 255, 255])
            res = self.process_image_array(bordered, secret_key)
            if res and res.raw_text:
                return res

            # 3. Multi-scale scaling untuk menangani resolusi besar foto kamera HP
            h, w = bordered.shape[:2]
            for max_dim in (1800, 1600, 1400, 1200, 900, 700, 500, 350):
                scale = max_dim / max(h, w)
                if scale < 1.0 or (scale > 1.0 and max(h, w) < 300):
                    resized = cv2.resize(bordered, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR)
                    res = self.process_image_array(resized, secret_key)
                    if res and res.raw_text:
                        return res

            # 4. Uji faktor skala langsung
            for factor in (0.75, 0.5, 0.35):
                resized = cv2.resize(bordered, (int(w * factor), int(h * factor)), interpolation=cv2.INTER_AREA)
                res = self.process_image_array(resized, secret_key)
                if res and res.raw_text:
                    return res

            # 5. Ekstraksi pemisahan kanal warna untuk citra berkontras rendah (misal modul merah di atas latar abu-abu)
            R = bordered[:, :, 2].astype(np.float32)
            G = bordered[:, :, 1].astype(np.float32)
            B = bordered[:, :, 0].astype(np.float32)

            diff_r = R - (G + B) / 2.0
            d_norm = ((diff_r - diff_r.min()) / (diff_r.max() - diff_r.min() + 1e-5) * 255).astype(np.uint8)
            _, th_r = cv2.threshold(d_norm, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            for cand in (th_r, 255 - th_r):
                res = self.process_image_array(cand, secret_key)
                if res and res.raw_text:
                    return res

            # 6. Uji kanal saturasi warna HSV
            hsv = cv2.cvtColor(bordered, cv2.COLOR_BGR2HSV)
            sat = hsv[:, :, 1]
            for cand in (sat, 255 - sat):
                res = self.process_image_array(cand, secret_key)
                if res and res.raw_text:
                    return res

            return None
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
