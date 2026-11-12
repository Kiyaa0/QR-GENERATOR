"""
Core Security Module
Mengimplementasikan enkripsi terotentikasi (HMAC-SHA256 + Stream Cipher + Nonce)
untuk payload QR Code (Anti-Pemalsuan Tiket).
Kompatibel 100% secara interoperabel dengan implementasi C++ (cpp/crypto.hpp).
"""

import os
import hmac
import hashlib
import base64
from typing import Tuple

PREFIX = "SECQR1:"


class SecureTicket:
    """Protokol Pengamanan Payload QR Code (Anti-Counterfeiting)."""

    @staticmethod
    def encrypt(plaintext: str, secret_key: str) -> str:
        """
        Mengenkripsi plaintext dengan kunci rahasia.
        Format keluaran: SECQR1:<Base64(Nonce[8] + HMACTag[16] + Ciphertext[N])>
        """
        if not plaintext or not secret_key:
            return ""

        plain_bytes = plaintext.encode("utf-8")
        key_bytes = secret_key.encode("utf-8")

        # 1. Generate 8-byte random nonce
        nonce = os.urandom(8)

        # 2. Derive keystream dan enkripsi dengan XOR stream cipher
        cipher = bytearray(len(plain_bytes))
        block_count = (len(plain_bytes) + 31) // 32

        for b in range(block_count):
            block_input = key_bytes + nonce + str(b).encode("utf-8")
            kblock = hashlib.sha256(block_input).digest()
            for i in range(32):
                idx = b * 32 + i
                if idx < len(plain_bytes):
                    cipher[idx] = plain_bytes[idx] ^ kblock[i]

        # 3. Hitung 16-byte HMAC tag atas (nonce + cipher)
        auth_data = nonce + bytes(cipher)
        full_tag = hmac.new(key_bytes, auth_data, hashlib.sha256).digest()
        tag = full_tag[:16]

        # 4. Kemas dan serialize ke Base64
        packed = nonce + tag + bytes(cipher)
        return PREFIX + base64.b64encode(packed).decode("utf-8")

    @staticmethod
    def decrypt(token: str, secret_key: str) -> Tuple[int, str]:
        """
        Mendekripsi token dan memverifikasi integritas signature.
        Mengembalikan (status_code, pesan/plaintext):
          status 0 = ASLI & VALID (Keaslian terverifikasi)
          status 1 = PALSU / KUNCI SALAH (HMAC signature gagal cocok)
          status 2 = FORMAT SALAH / BUKAN TIKET TERENKRIPSI
          status 3 = KUNCI KOSONG
        """
        if not secret_key:
            return 3, "Kunci rahasia tidak boleh kosong."

        token = token.strip()
        if not token.startswith(PREFIX):
            return 2, "Bukan token tiket terenkripsi SECQR1."

        try:
            raw = base64.b64decode(token[len(PREFIX):])
            if len(raw) < 24:
                return 2, "Payload data rusak atau terlalu pendek."

            nonce = raw[:8]
            received_tag = raw[8:24]
            cipher = raw[24:]

            key_bytes = secret_key.encode("utf-8")
            auth_data = nonce + cipher
            expected_tag = hmac.new(key_bytes, auth_data, hashlib.sha256).digest()[:16]

            # Verifikasi constant-time untuk mencegah timing attack
            if not hmac.compare_digest(received_tag, expected_tag):
                return 1, "PERINGATAN: TIKET PALSU ATAU KUNCI RAHASIA SALAH!"

            # Dekripsi stream cipher
            plain = bytearray(len(cipher))
            block_count = (len(cipher) + 31) // 32
            for b in range(block_count):
                block_input = key_bytes + nonce + str(b).encode("utf-8")
                kblock = hashlib.sha256(block_input).digest()
                for i in range(32):
                    idx = b * 32 + i
                    if idx < len(cipher):
                        plain[idx] = cipher[idx] ^ kblock[i]

            return 0, plain.decode("utf-8")
        except Exception as e:
            return 2, f"Format tidak valid: {str(e)}"
