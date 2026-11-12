"""
Batch Engine Module
Menangani pencetakan & pembuatan massal (puluhan ribu tiket/barang)
secara multi-threading dengan performa tinggi.
Menghasilkan berkas gambar QR (PNG / BMP) dan rekap file CSV manifest tiket.
"""

import os
import csv
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Callable

from core.qr_engine import QREngine
from core.cpp_bridge import bridge


class BatchEngine:
    """Mesin Pembuatan QR Code Massal / Batch."""

    @staticmethod
    def generate_batch(
        prefix: str,
        start_number: int,
        count: int,
        output_dir: str,
        secret_key: Optional[str] = None,
        scale: int = 8,
        border: int = 2,
        fill_color: str = "#000000",
        back_color: str = "#FFFFFF",
        threads: int = 4,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> dict:
        """
        Menghasilkan massal berkas QR Code dengan multi-threading.
        Mengembalikan statistik eksekusi (waktu, jumlah file, path manifest CSV).
        """
        os.makedirs(output_dir, exist_ok=True)
        start_time = time.perf_counter()

        manifest_rows = []
        is_encrypted = bool(secret_key and secret_key.strip())
        key = secret_key.strip() if is_encrypted else ""

        # Siapkan daftar tugas
        tasks = []
        for i in range(count):
            num = start_number + i
            ticket_id = f"{prefix}-{num:06d}"

            if is_encrypted:
                payload = bridge.encrypt_ticket(ticket_id, key)
            else:
                payload = ticket_id

            filename = f"{ticket_id}.png"
            filepath = os.path.join(output_dir, filename)
            tasks.append((ticket_id, payload, filepath))

        completed = 0

        def worker(item):
            t_id, p_load, f_path = item
            engine = QREngine(
                data=p_load,
                error_correction="M",
                fill_color=fill_color,
                back_color=back_color,
                box_size=scale,
                border=border,
            )
            engine.save_png(f_path)
            return (t_id, p_load, os.path.basename(f_path))

        # Eksekusi secara paralel menggunakan thread pool
        with ThreadPoolExecutor(max_workers=max(1, threads)) as executor:
            for result in executor.map(worker, tasks):
                manifest_rows.append(result)
                completed += 1
                if progress_callback and completed % 10 == 0:
                    progress_callback(completed, count)

        if progress_callback:
            progress_callback(count, count)

        # Buat berkas manifest CSV rekap
        manifest_path = os.path.join(output_dir, "manifest_tiket.csv")
        with open(manifest_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID Tiket / Barang", "QR Payload (Data / Token)", "Nama Berkas Gambar", "Waktu Dibuat", "Terenkripsi"])
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for t_id, p_load, f_name in manifest_rows:
                writer.writerow([t_id, p_load, f_name, now_str, "YA" if is_encrypted else "TIDAK"])

        elapsed = time.perf_counter() - start_time
        qps = int(count / elapsed) if elapsed > 0 else count

        return {
            "count": count,
            "elapsed_seconds": elapsed,
            "qps": qps,
            "manifest_path": manifest_path,
            "output_dir": output_dir,
            "is_encrypted": is_encrypted,
        }
