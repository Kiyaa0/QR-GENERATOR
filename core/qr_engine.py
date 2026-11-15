"""
QR Code Engine Module
Menangani logika pembentukan data (URL, Wi-Fi, vCard, WhatsApp, Email),
generasi matriks QR Code, kustomisasi visual (warna, logo, badge),
serta ekspor ke berbagai format (PNG, JPEG, SVG).
"""

import io
import re
import urllib.parse
from typing import Optional, Tuple
import xml.etree.ElementTree as ET

import qrcode
from qrcode.constants import (
    ERROR_CORRECT_L,
    ERROR_CORRECT_M,
    ERROR_CORRECT_Q,
    ERROR_CORRECT_H,
)
from qrcode.image.svg import SvgPathImage
from PIL import Image, ImageDraw


# Mapping tingkat koreksi error
ERROR_LEVELS = {
    "L": ERROR_CORRECT_L,  # ~7% recovery
    "M": ERROR_CORRECT_M,  # ~15% recovery
    "Q": ERROR_CORRECT_Q,  # ~25% recovery
    "H": ERROR_CORRECT_H,  # ~30% recovery (sangat disarankan bila ada logo)
}


class QRFormatters:
    """Helper untuk menyusun format data standar QR Code."""

    @staticmethod
    def escape_wifi(text: str) -> str:
        """Escape karakter khusus untuk string konfigurasi Wi-Fi."""
        for char in ("\\", ";", ",", ":", '"'):
            text = text.replace(char, f"\\{char}")
        return text

    @classmethod
    def wifi(cls, ssid: str, password: str = "", auth_type: str = "WPA", hidden: bool = False) -> str:
        """
        Format koneksi Wi-Fi standar (ZXing):
        WIFI:T:<WPA|WEP|nopass>;S:<ssid>;P:<password>;H:<true|false>;;
        """
        auth = "nopass" if auth_type.upper() in ("NONE", "NOPASS", "OPEN") else auth_type.upper()
        escaped_ssid = cls.escape_wifi(ssid.strip())
        escaped_pwd = cls.escape_wifi(password) if auth != "nopass" else ""
        h_flag = "true" if hidden else "false"

        pwd_part = f"P:{escaped_pwd};" if auth != "nopass" else ""
        return f"WIFI:T:{auth};S:{escaped_ssid};{pwd_part}H:{h_flag};;"

    @staticmethod
    def vcard(
        name: str,
        phone: str = "",
        email: str = "",
        org: str = "",
        title: str = "",
        website: str = "",
        note: str = "",
    ) -> str:
        """Format kartu nama digital vCard 3.0 standar."""
        lines = [
            "BEGIN:VCARD",
            "VERSION:3.0",
            f"FN:{name.strip()}",
        ]
        if phone.strip():
            lines.append(f"TEL;TYPE=CELL:{phone.strip()}")
        if email.strip():
            lines.append(f"EMAIL:{email.strip()}")
        if org.strip():
            lines.append(f"ORG:{org.strip()}")
        if title.strip():
            lines.append(f"TITLE:{title.strip()}")
        if website.strip():
            lines.append(f"URL:{website.strip()}")
        if note.strip():
            lines.append(f"NOTE:{note.strip()}")
        lines.append("END:VCARD")
        return "\n".join(lines)

    @staticmethod
    def whatsapp(phone: str, message: str = "") -> str:
        """Format tautan pesan WhatsApp langsung (wa.me)."""
        clean_phone = re.sub(r"[^\d]", "", phone)
        if message.strip():
            encoded = urllib.parse.quote(message.strip())
            return f"https://wa.me/{clean_phone}?text={encoded}"
        return f"https://wa.me/{clean_phone}"

    @staticmethod
    def email(to: str, subject: str = "", body: str = "") -> str:
        """Format standar mailto."""
        params = []
        if subject.strip():
            params.append(f"subject={urllib.parse.quote(subject.strip())}")
        if body.strip():
            params.append(f"body={urllib.parse.quote(body.strip())}")

        query = f"?{'&'.join(params)}" if params else ""
        return f"mailto:{to.strip()}{query}"

    @staticmethod
    def qris(
        merchant_name: str,
        nmid: str = "",
        city: str = "JAKARTA",
        amount: Optional[int] = None,
    ) -> str:
        """Format pembayaran standar QRIS Bank Indonesia."""
        from core.qris import QRISCore
        return QRISCore.create_qris(
            merchant_name=merchant_name,
            nmid=nmid,
            city=city,
            amount=amount,
        )



class QREngine:
    """Engine utama untuk meng-generate dan mengkustomisasi QR Code."""

    def __init__(
        self,
        data: str,
        error_correction: str = "H",
        fill_color: str = "#000000",
        back_color: str = "#FFFFFF",
        box_size: int = 12,
        border: int = 2,
    ):
        self.data = data.strip() if data else ""
        self.error_correction = error_correction.upper()
        self.fill_color = fill_color or "#000000"
        self.back_color = back_color or "#FFFFFF"
        self.box_size = max(4, int(box_size))
        self.border = max(1, int(border))

        self.logo_path: Optional[str] = None
        self.logo_shape: str = "rounded"  # 'rounded', 'circle', 'square', 'none'
        self.logo_size_ratio: float = 0.22  # Proporsi aman terhadap lebar QR
        self.logo_bg_color: Optional[str] = None
        self.logo_padding: int = 8

    def set_logo(
        self,
        logo_path: Optional[str],
        shape: str = "rounded",
        size_ratio: float = 0.22,
        bg_color: Optional[str] = None,
        padding: int = 8,
    ):
        """Konfigurasi logo tengah."""
        self.logo_path = logo_path
        self.logo_shape = shape
        self.logo_size_ratio = min(0.30, max(0.10, size_ratio))
        self.logo_bg_color = bg_color
        self.logo_padding = max(2, int(padding))

    def _create_qr_object(self) -> qrcode.QRCode:
        ec_level = ERROR_LEVELS.get(self.error_correction, ERROR_CORRECT_H)
        # Jika ada logo, otomatis wajib minimal Q atau H agar terbaca
        if self.logo_path and ec_level in (ERROR_CORRECT_L, ERROR_CORRECT_M):
            ec_level = ERROR_CORRECT_H

        qr = qrcode.QRCode(
            version=None,
            error_correction=ec_level,
            box_size=self.box_size,
            border=self.border,
        )
        qr.add_data(self.data if self.data else " ")
        qr.make(fit=True)
        return qr

    def generate_image(self) -> Image.Image:
        """Menghasilkan PIL Image (RGBA) dari QR Code beserta kustomisasi warna dan logo."""
        qr = self._create_qr_object()

        # Tangani background transparan bila diminta
        is_transparent = self.back_color.lower() in ("transparent", "none", "")

        if is_transparent:
            # Generate dasar dengan putih lalu replace dengan transparan
            base_img = qr.make_image(
                fill_color=self.fill_color,
                back_color="#FFFFFF",
            ).convert("RGBA")
            data = base_img.getdata()
            new_data = []
            for item in data:
                # Jika piksel putih/hampir putih, jadikan transparan
                if item[0] > 240 and item[1] > 240 and item[2] > 240:
                    new_data.append((255, 255, 255, 0))
                else:
                    new_data.append(item)
            base_img.putdata(new_data)
        else:
            base_img = qr.make_image(
                fill_color=self.fill_color,
                back_color=self.back_color,
            ).convert("RGBA")

        # Jika ada logo, tempelkan ke tengah
        if self.logo_path:
            base_img = self._embed_logo(base_img)

        return base_img

    def _embed_logo(self, qr_img: Image.Image) -> Image.Image:
        """Memasukkan logo ke bagian tengah QR Code dengan badge proteksi pembacaan."""
        try:
            with Image.open(self.logo_path) as raw_logo:
                logo = raw_logo.convert("RGBA")
        except Exception:
            return qr_img

        qr_w, qr_h = qr_img.size
        target_size = int(qr_w * self.logo_size_ratio)

        # Pertahankan rasio aspek logo
        logo.thumbnail((target_size, target_size), Image.Resampling.LANCZOS)
        lw, lh = logo.size

        # Tentukan warna latar belakang badge logo
        bg_col = self.logo_bg_color or (
            "#FFFFFF" if self.back_color.lower() in ("transparent", "none", "") else self.back_color
        )

        pad = self.logo_padding
        box_left = (qr_w - lw) // 2 - pad
        box_top = (qr_h - lh) // 2 - pad
        box_right = (qr_w + lw) // 2 + pad
        box_bottom = (qr_h + lh) // 2 + pad

        draw = ImageDraw.Draw(qr_img)

        # Gambar background badge pelindung agar modul QR tidak bertabrakan dengan logo
        if self.logo_shape == "circle":
            center_x = qr_w // 2
            center_y = qr_h // 2
            radius = max(lw, lh) // 2 + pad
            draw.ellipse(
                (center_x - radius, center_y - radius, center_x + radius, center_y + radius),
                fill=bg_col,
            )
        elif self.logo_shape == "rounded":
            draw.rounded_rectangle(
                (box_left, box_top, box_right, box_bottom),
                radius=max(6, pad + 2),
                fill=bg_col,
            )
        elif self.logo_shape == "square":
            draw.rectangle(
                (box_left, box_top, box_right, box_bottom),
                fill=bg_col,
            )
        # 'none' artinya tanpa background tambahan

        # Tempelkan logo di titik tengah
        paste_pos = ((qr_w - lw) // 2, (qr_h - lh) // 2)
        qr_img.paste(logo, paste_pos, mask=logo)

        return qr_img

    def generate_svg(self) -> str:
        """Menghasilkan teks string SVG vektor dari QR Code."""
        qr = self._create_qr_object()

        is_transparent = self.back_color.lower() in ("transparent", "none", "")
        bg_color = None if is_transparent else self.back_color
        fill_col = self.fill_color

        class StyledSvgPathImage(SvgPathImage):
            background = bg_color
            QR_PATH_STYLE = {
                "fill": fill_col,
                "fill-opacity": "1",
                "fill-rule": "nonzero",
                "stroke": "none",
            }

        svg_img = qr.make_image(image_factory=StyledSvgPathImage)
        return svg_img.to_string().decode("utf-8")

    def save_png(self, filepath: str, max_dimension: Optional[int] = None):
        """Menyimpan QR Code ke format PNG dengan opsi custom ukuran resolusi."""
        img = self.generate_image()
        if max_dimension and max_dimension > 0:
            img = img.resize((max_dimension, max_dimension), Image.Resampling.NEAREST)
        img.save(filepath, format="PNG")

    def save_jpeg(self, filepath: str, quality: int = 95, max_dimension: Optional[int] = None):
        """Menyimpan QR Code ke format JPG/JPEG."""
        img = self.generate_image()
        if max_dimension and max_dimension > 0:
            img = img.resize((max_dimension, max_dimension), Image.Resampling.NEAREST)
        # JPEG tidak mendukung transparansi, buat background putih jika RGBA
        rgb_img = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "RGBA":
            rgb_img.paste(img, mask=img.split()[3])
        else:
            rgb_img.paste(img)
        rgb_img.save(filepath, format="JPEG", quality=quality)

    def save_svg(self, filepath: str):
        """Menyimpan QR Code ke file SVG vektor."""
        svg_content = self.generate_svg()
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(svg_content)
