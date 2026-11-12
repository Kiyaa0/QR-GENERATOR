"""
Clipboard Helper Module
Menyalin gambar PIL ke clipboard sistem (khususnya Windows) secara aman.
"""

import io
import os
import tempfile
import subprocess
from typing import Tuple
from PIL import Image


def copy_image_to_clipboard(image: Image.Image) -> Tuple[bool, str]:
    """
    Menyalin PIL Image ke Windows Clipboard.
    Mengembalikan (success: bool, message: str).
    """
    # Pastikan format RGB dengan background putih bila RGBA
    rgb_img = Image.new("RGB", image.size, (255, 255, 255))
    if image.mode == "RGBA":
        rgb_img.paste(image, mask=image.split()[3])
    else:
        rgb_img.paste(image)

    # Metode 1: Simpan ke temp file lalu invoke PowerShell SetImage (sangat stabil di Windows)
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, "temp_qr_export.png")

    try:
        rgb_img.save(temp_path, format="PNG")
        # Script PowerShell untuk menyalin gambar ke clipboard
        ps_script = (
            f"Add-Type -AssemblyName System.Windows.Forms; "
            f"$img = [System.Drawing.Image]::FromFile('{temp_path.replace('\\', '/')}'); "
            f"[System.Windows.Forms.Clipboard]::SetImage($img); "
            f"$img.Dispose();"
        )
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True,
            timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if res.returncode == 0:
            return True, "Gambar berhasil disalin ke clipboard!"
    except Exception as e:
        pass

    # Metode 2: Coba ctypes Win32 API
    try:
        import ctypes
        from ctypes import wintypes, c_void_p, c_size_t, c_uint

        output = io.BytesIO()
        rgb_img.save(output, "BMP")
        data = output.getvalue()[14:]  # Skip 14-byte BMP header
        output.close()

        GMEM_MOVEABLE = 0x0002
        CF_DIB = 8

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        kernel32.GlobalAlloc.argtypes = [c_uint, c_size_t]
        kernel32.GlobalAlloc.restype = c_void_p
        kernel32.GlobalLock.argtypes = [c_void_p]
        kernel32.GlobalLock.restype = c_void_p
        kernel32.GlobalUnlock.argtypes = [c_void_p]
        kernel32.GlobalFree.argtypes = [c_void_p]

        user32.OpenClipboard.argtypes = [c_void_p]
        user32.OpenClipboard.restype = wintypes.BOOL
        user32.EmptyClipboard.restype = wintypes.BOOL
        user32.SetClipboardData.argtypes = [c_uint, c_void_p]
        user32.SetClipboardData.restype = c_void_p
        user32.CloseClipboard.restype = wintypes.BOOL

        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
        if h_mem:
            ptr = kernel32.GlobalLock(h_mem)
            if ptr:
                ctypes.memmove(ptr, data, len(data))
                kernel32.GlobalUnlock(h_mem)
                if user32.OpenClipboard(None):
                    try:
                        user32.EmptyClipboard()
                        user32.SetClipboardData(CF_DIB, h_mem)
                        return True, "Gambar berhasil disalin ke clipboard!"
                    finally:
                        user32.CloseClipboard()
    except Exception as e:
        return False, f"Gagal menyalin ke clipboard: {str(e)}"

    return False, "Tidak dapat mengakses clipboard sistem."
