"""
QRIS (Quick Response Code Indonesian Standard) Module
Menangani parsing, pembentukan payload standar EMVCo / Bank Indonesia,
konversi QRIS Statis menjadi Dinamis (dengan nominal),
serta pembuatan poster standee display pembayaran lengkap.
"""

import os
from typing import Optional, Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFont

from core.qr_engine import QREngine


def get_font(size: int, bold: bool = False):
    """Helper untuk memuat font sistem Windows dengan fallback aman."""
    font_names = (
        ["segoeuib.ttf", "arialbd.ttf", "tahomabd.ttf"]
        if bold
        else ["segoeui.ttf", "arial.ttf", "tahoma.ttf"]
    )
    for name in font_names:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass
    return ImageFont.load_default()


class QRISCore:
    """Mesin Pengolah Payload Standar QRIS EMVCo."""

    @staticmethod
    def calculate_crc16(data: str) -> str:
        """Menghitung CRC16-CCITT standar dengan polynomial 0x1021 dan initial 0xFFFF."""
        crc = 0xFFFF
        for b in data.encode("ascii"):
            crc ^= (b << 8)
            for _ in range(8):
                if crc & 0x8000:
                    crc = ((crc << 1) ^ 0x1021) & 0xFFFF
                else:
                    crc = (crc << 1) & 0xFFFF
        return f"{crc:04X}"

    @classmethod
    def verify_crc(cls, qris_str: str) -> bool:
        """Memvalidasi apakah checksum CRC16 pada QRIS valid."""
        qris = qris_str.strip()
        if len(qris) < 8 or "6304" not in qris:
            return False
        crc_idx = qris.rfind("6304")
        payload = qris[:crc_idx + 4]
        expected_crc = qris[crc_idx + 4:].upper()
        return cls.calculate_crc16(payload) == expected_crc

    @staticmethod
    def build_tlv(tag: int or str, val: str) -> str:
        """Membentuk string format TLV (Tag-Length-Value)."""
        t_str = f"{int(tag):02d}" if isinstance(tag, int) else str(tag).zfill(2)
        v_str = str(val)
        l_str = f"{len(v_str):02d}"
        return f"{t_str}{l_str}{v_str}"

    @classmethod
    def parse_tlv(cls, qris_str: str) -> Dict[str, str]:
        """Mengekstrak seluruh tag TLV tingkat pertama dari string QRIS."""
        qris = qris_str.strip()
        idx = 0
        tlvs = {}
        while idx < len(qris):
            if idx + 4 > len(qris):
                break
            tag = qris[idx:idx + 2]
            try:
                length = int(qris[idx + 2:idx + 4])
            except ValueError:
                break
            val = qris[idx + 4:idx + 4 + length]
            tlvs[tag] = val
            idx += 4 + length
        return tlvs

    @classmethod
    def extract_info(cls, qris_str: str) -> Dict[str, Any]:
        """Mengekstrak informasi penting pedagang (merchant) dari QRIS."""
        tlvs = cls.parse_tlv(qris_str)
        merchant_name = tlvs.get("59", "TOKO MERCHANT")
        city = tlvs.get("60", "JAKARTA")
        postal_code = tlvs.get("61", "")
        amount = int(tlvs["54"]) if "54" in tlvs and tlvs["54"].isdigit() else None
        is_dynamic = tlvs.get("01") == "12"

        # Cari NMID pada Tag 26 atau Tag 51
        nmid = ""
        for parent_tag in ("26", "51"):
            if parent_tag in tlvs:
                sub_tlvs = cls.parse_tlv(tlvs[parent_tag])
                if "01" in sub_tlvs:
                    nmid = sub_tlvs["01"]
                    break

        return {
            "merchant_name": merchant_name,
            "city": city,
            "postal_code": postal_code,
            "nmid": nmid or "ID1020000000000",
            "amount": amount,
            "is_dynamic": is_dynamic,
            "currency": "IDR",
            "raw": qris_str,
        }

    @classmethod
    def create_qris(
        cls,
        merchant_name: str,
        nmid: str = "ID1020021111111",
        city: str = "JAKARTA",
        amount: Optional[int] = None,
        postal_code: str = "12345",
        criteria: str = "UMI",
    ) -> str:
        """Membuat string QRIS standar Bank Indonesia secara lengkap."""
        m_name = (merchant_name.strip() or "MERCHANT TOKO")[:25].upper()
        m_city = (city.strip() or "JAKARTA")[:15].upper()
        clean_nmid = (nmid.strip() or "ID1020021111111")
        clean_post = (postal_code.strip() or "12345")[:10]

        is_dynamic = amount is not None and amount > 0
        point_init = "12" if is_dynamic else "11"

        # Tag 26: Merchant Account Information
        sub26 = (
            cls.build_tlv(0, "ID.CO.QRIS.WWW")
            + cls.build_tlv(1, clean_nmid)
            + cls.build_tlv(2, criteria)
        )
        tag26 = cls.build_tlv(26, sub26)

        parts = [
            "000201",                     # Tag 00: Format Payload
            f"0102{point_init}",           # Tag 01: 11 = Statis, 12 = Dinamis
            tag26,                         # Tag 26: Data Merchant
            "52040000",                   # Tag 52: MCC
            "5303360",                    # Tag 53: Mata uang IDR (360)
        ]

        # Tag 54: Nominal (jika dinamis)
        if is_dynamic:
            amt_str = str(int(amount))
            parts.append(cls.build_tlv(54, amt_str))

        parts.extend([
            "5802ID",                      # Tag 58: Negara ID
            cls.build_tlv(59, m_name),     # Tag 59: Nama Merchant
            cls.build_tlv(60, m_city),     # Tag 60: Kota
            cls.build_tlv(61, clean_post), # Tag 61: Kode Pos
            "6304",                        # Tag 63: Penanda CRC
        ])

        payload_to_crc = "".join(parts)
        crc = cls.calculate_crc16(payload_to_crc)
        return payload_to_crc + crc

    @classmethod
    def convert_static_to_dynamic(cls, raw_qris: str, amount: int) -> str:
        """
        Mengonversi QRIS Statis apa pun (BCA, GoPay, OVO, Dana, ShopeePay, Mandiri, dll.)
        menjadi QRIS Dinamis ber-nominal dengan menghitung ulang CRC16.
        """
        raw = raw_qris.strip()
        if not raw:
            return ""

        # Potong bagian CRC lama (6304XXXX)
        if "6304" in raw:
            base = raw[:raw.rfind("6304")]
        else:
            base = raw

        # Ubah Tag 01 menjadi 12 (Dinamis)
        if base.startswith("000201010211"):
            base = "000201010212" + base[12:]
        elif "010211" in base:
            base = base.replace("010211", "010212", 1)

        amt_str = str(int(amount))
        tag54 = cls.build_tlv(54, amt_str)

        # Sisipkan atau gantikan Tag 54
        if "5303360" in base:
            p1, p2 = base.split("5303360", 1)
            # Hapus tag 54 lama jika ada
            if p2.startswith("54"):
                try:
                    old_len = int(p2[2:4])
                    p2 = p2[4 + old_len:]
                except ValueError:
                    pass
            base = p1 + "5303360" + tag54 + p2
        elif "5802ID" in base:
            p1, p2 = base.split("5802ID", 1)
            base = p1 + tag54 + "5802ID" + p2
        else:
            base = base + tag54

        payload_to_crc = base + "6304"
        crc = cls.calculate_crc16(payload_to_crc)
        return payload_to_crc + crc


class QRISPosterGenerator:
    """Pembuat Gambar Poster / Standee Display Pembayaran QRIS Lengkap."""

    @staticmethod
    def create_qris_center_badge(custom_logo_path: Optional[str] = None) -> Image.Image:
        """Membuat badge logo tengah untuk QR Code (custom atau standar QRIS)."""
        badge_w, badge_h = 130, 75

        if custom_logo_path and os.path.exists(custom_logo_path):
            try:
                with Image.open(custom_logo_path) as logo_raw:
                    logo = logo_raw.convert("RGBA")
                    # Buat badge container putih dengan outline
                    bg = Image.new("RGBA", (badge_w, badge_w), (255, 255, 255, 255))
                    draw = ImageDraw.Draw(bg)
                    draw.rounded_rectangle((2, 2, badge_w - 3, badge_w - 3), radius=14, fill="#FFFFFF", outline="#E2E8F0", width=2)
                    logo.thumbnail((badge_w - 18, badge_w - 18), Image.Resampling.LANCZOS)
                    lw, lh = logo.size
                    bg.paste(logo, ((badge_w - lw) // 2, (badge_w - lh) // 2), mask=logo)
                    return bg
            except Exception:
                pass

        # Default: Emblem resmi bertuliskan QRIS
        bg = Image.new("RGBA", (badge_w, badge_h), (255, 255, 255, 255))
        draw = ImageDraw.Draw(bg)
        draw.rounded_rectangle((2, 2, badge_w - 3, badge_h - 3), radius=10, fill="#FFFFFF", outline="#DC2626", width=3)

        font_qris = get_font(26, bold=True)
        draw.text((badge_w // 2, badge_h // 2 - 2), "QRIS", fill="#DC2626", font=font_qris, anchor="mm")
        return bg

    @classmethod
    def generate_poster(
        cls,
        qr_image: Image.Image,
        merchant_name: str,
        nmid: str = "",
        amount: Optional[int] = None,
        city: str = "JAKARTA",
        custom_logo_path: Optional[str] = None,
    ) -> Image.Image:
        """
        Menghasilkan berkas citra display poster standee meja QRIS
        beresolusi tinggi (740 x 1050 px) yang siap dicetak.
        """
        pw, ph = 740, 1060
        poster = Image.new("RGB", (pw, ph), "#F8FAFC")
        draw = ImageDraw.Draw(poster)

        # 1. Header Banner Atas (Merah Khas Standar QRIS)
        header_h = 120
        draw.rectangle((0, 0, pw, header_h), fill="#DC2626")

        font_h1 = get_font(34, bold=True)
        draw.text((pw // 2, 42), "QRIS", fill="#FFFFFF", font=font_h1, anchor="mm")

        font_sub = get_font(13, bold=False)
        draw.text((pw // 2, 82), "PEMBAYARAN DIGITAL NASIONAL - STANDAR BANK INDONESIA", fill="#FEE2E2", font=font_sub, anchor="mm")

        # 2. Card Container Utama (Putih Elegan)
        card_margin = 35
        card_t = header_h + 20
        card_b = ph - 110
        card_r = pw - card_margin
        card_l = card_margin

        # Card shadow / border
        draw.rounded_rectangle((card_l + 2, card_t + 2, card_r + 2, card_b + 2), radius=16, fill="#E2E8F0")
        draw.rounded_rectangle((card_l, card_t, card_r, card_b), radius=16, fill="#FFFFFF", outline="#CBD5E1", width=1)

        # 3. Identitas Merchant / Toko
        font_mname = get_font(24, bold=True)
        m_display = (merchant_name.strip() or "NAMA TOKO MERCHANT").upper()
        draw.text((pw // 2, card_t + 40), m_display, fill="#0F172A", font=font_mname, anchor="mm")

        font_nmid = get_font(13, bold=False)
        nmid_str = f"NMID: {nmid.strip() or 'ID1020021111111'}"
        draw.text((pw // 2, card_t + 70), nmid_str, fill="#64748B", font=font_nmid, anchor="mm")

        # 4. QR Code di Tengah
        qr_target_size = 440
        qr_resized = qr_image.resize((qr_target_size, qr_target_size), Image.Resampling.LANCZOS)

        # Kotak putih frame QR
        qr_box_l = (pw - qr_target_size) // 2
        qr_box_t = card_t + 100
        draw.rectangle(
            (qr_box_l - 10, qr_box_t - 10, qr_box_l + qr_target_size + 10, qr_box_t + qr_target_size + 10),
            fill="#FFFFFF",
            outline="#E2E8F0",
            width=2,
        )

        poster.paste(qr_resized, (qr_box_l, qr_box_t))

        # 5. Highlight Pill Nominal / Petunjuk
        pill_y = qr_box_t + qr_target_size + 35
        pill_w, pill_h = 520, 52
        pill_l = (pw - pill_w) // 2
        pill_r = pill_l + pill_w

        if amount and amount > 0:
            # Pill Hijau untuk Nominal Tetap
            draw.rounded_rectangle((pill_l, pill_y, pill_r, pill_y + pill_h), radius=26, fill="#ECFDF5", outline="#10B981", width=2)
            font_pill = get_font(17, bold=True)
            draw.text((pw // 2, pill_y + pill_h // 2), f"TOTAL BAYAR: Rp {amount:,.0f}".replace(",", "."), fill="#047857", font=font_pill, anchor="mm")
        else:
            # Pill Biru untuk Nominal Bebas
            draw.rounded_rectangle((pill_l, pill_y, pill_r, pill_y + pill_h), radius=26, fill="#EFF6FF", outline="#3B82F6", width=2)
            font_pill = get_font(15, bold=True)
            draw.text((pw // 2, pill_y + pill_h // 2), "SCAN UNTUK BAYAR DENGAN NOMINAL BEBAS", fill="#1D4ED8", font=font_pill, anchor="mm")

        # Catatan verifikasi
        font_note = get_font(11, bold=False)
        draw.text((pw // 2, pill_y + pill_h + 20), f"Lokasi: {city.upper()} | Cetak Resmi QR Studio Pro", fill="#94A3B8", font=font_note, anchor="mm")

        # 6. Footer Bawah (Daftar Pembayaran)
        font_foot1 = get_font(11, bold=True)
        draw.text((pw // 2, ph - 75), "MENERIMA PEMBAYARAN VIA MOBILE BANKING & E-WALLET", fill="#475569", font=font_foot1, anchor="mm")

        font_foot2 = get_font(11, bold=False)
        partners = "BCA - Mandiri - BNI - BRI - GoPay - OVO - DANA - ShopeePay - LinkAja"
        draw.text((pw // 2, ph - 50), partners, fill="#64748B", font=font_foot2, anchor="mm")

        return poster
