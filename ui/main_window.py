"""
Main Window GUI Module
Antarmuka Grafis Desktop Modern menggunakan CustomTkinter.
Mendukung 3 Mode Utama:
1. Generator QR (Single dengan opsi C++ Security Encryption)
2. C++ Batch Generator (Pencetakan massal puluhan ribu tiket + Benchmark)
3. Scanner Kamera & Validasi (Webcam OpenCV scanner + Verifikasi keaslian)
"""

import os
import threading
import tkinter as tk
from tkinter import filedialog, colorchooser, messagebox
from typing import Optional
from PIL import Image

import customtkinter as ctk
import cv2

from core.qr_engine import QREngine, QRFormatters
from core.clipboard import copy_image_to_clipboard
from core.cpp_bridge import bridge
from core.batch_engine import BatchEngine
from core.scanner import ScannerEngine, ScanResult

# Konfigurasi Tema CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class QRApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Setup Jendela Utama
        self.title("QR Studio Pro - Desktop QR Engine & Security Suite")
        self.geometry("1160x800")
        self.minsize(1020, 720)

        # State Aplikasi
        self.current_app_mode = "Generator QR"
        self.current_tab = "URL / Teks"
        self.fill_color = "#000000"
        self.back_color = "#FFFFFF"
        self.is_transparent_bg = False
        self.selected_logo_path: Optional[str] = None
        self.current_pil_image: Optional[Image.Image] = None
        self.qr_engine_instance: Optional[QREngine] = None

        # State Webcam Scanner
        self.is_webcam_running = False
        self.cap: Optional[cv2.VideoCapture] = None
        self.scanner_engine = ScannerEngine()
        self.last_scanned_token = ""

        # Bangun Layout
        self._build_header()
        self._build_container()

        # Render awal QR Code default
        self.after(150, self.generate_qr)

        # Cleanup handler saat aplikasi ditutup
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        self._stop_webcam()
        self.destroy()

    def _build_header(self):
        """Membuat bar header atas dengan navigasi mode dan switch tema."""
        header_frame = ctk.CTkFrame(self, height=65, corner_radius=0, fg_color=("gray90", "#18181b"))
        header_frame.pack(side="top", fill="x")

        # Judul & Branding
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=20, pady=10)

        title_lbl = ctk.CTkLabel(
            title_box,
            text="QR STUDIO PRO",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=("#1e3a8a", "#60a5fa"),
        )
        title_lbl.pack(anchor="w")

        cpp_status = "C++ Engine Aktif" if bridge.is_cpp_active() else "Python Engine"
        subtitle_lbl = ctk.CTkLabel(
            title_box,
            text=f"Desktop Suite | {cpp_status} | Multi-Threaded & Anti-Tamper Security",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray55"),
        )
        subtitle_lbl.pack(anchor="w")

        # Navigasi Mode Aplikasi (Segmented Button Tengah)
        nav_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        nav_box.pack(side="left", expand=True, padx=10)

        self.mode_nav = ctk.CTkSegmentedButton(
            nav_box,
            values=["Generator QR", "C++ Batch Generator", "Scanner & Validasi"],
            command=self._on_mode_change,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.mode_nav.set("Generator QR")
        self.mode_nav.pack()

        # Switch Tema (Dark / Light)
        theme_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        theme_box.pack(side="right", padx=20, pady=10)

        self.theme_switch = ctk.CTkSwitch(
            theme_box,
            text="Mode Gelap",
            command=self._toggle_theme,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.theme_switch.select()
        self.theme_switch.pack()

    def _toggle_theme(self):
        if self.theme_switch.get() == 1:
            ctk.set_appearance_mode("Dark")
            self.theme_switch.configure(text="Mode Gelap")
        else:
            ctk.set_appearance_mode("Light")
            self.theme_switch.configure(text="Mode Terang")

    def _build_container(self):
        """Membuat frame utama yang menampung 3 tampilan mode."""
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=15, pady=10)

        # Mode 1: Generator View
        self.view_generator = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self._build_generator_view(self.view_generator)

        # Mode 2: Batch Generator View
        self.view_batch = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self._build_batch_view(self.view_batch)

        # Mode 3: Scanner View
        self.view_scanner = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self._build_scanner_view(self.view_scanner)

        # Tampilkan mode default
        self.view_generator.pack(fill="both", expand=True)

    def _on_mode_change(self, selected_mode: str):
        self.current_app_mode = selected_mode

        # Matikan webcam jika keluar dari tab scanner
        if selected_mode != "Scanner & Validasi":
            self._stop_webcam()

        self.view_generator.pack_forget()
        self.view_batch.pack_forget()
        self.view_scanner.pack_forget()

        if selected_mode == "Generator QR":
            self.view_generator.pack(fill="both", expand=True)
            self.generate_qr()
        elif selected_mode == "C++ Batch Generator":
            self.view_batch.pack(fill="both", expand=True)
        elif selected_mode == "Scanner & Validasi":
            self.view_scanner.pack(fill="both", expand=True)

    # =========================================================================
    # MODE 1: GENERATOR TUNGGAL DENGAN OPSI ENKRIPSI C++
    # =========================================================================

    def _build_generator_view(self, parent):
        parent.grid_columnconfigure(0, weight=6)
        parent.grid_columnconfigure(1, weight=5)
        parent.grid_rowconfigure(0, weight=1)

        # Panel Kiri: Scrollable Controls
        self.left_scroll = ctk.CTkScrollableFrame(
            parent,
            label_text="KONTEN & PENGATURAN QR",
            label_font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.left_scroll.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Panel Kanan: Preview & Actions
        self.right_frame = ctk.CTkFrame(parent, corner_radius=12)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        self._build_left_panel_controls()
        self._build_right_panel_preview()

    def _build_left_panel_controls(self):
        p = self.left_scroll

        # 1. KATEGORI KONTEN
        cat_lbl = ctk.CTkLabel(p, text="1. Pilih Jenis Konten QR:", font=ctk.CTkFont(size=13, weight="bold"))
        cat_lbl.pack(anchor="w", pady=(5, 6))

        self.category_seg = ctk.CTkSegmentedButton(
            p,
            values=["URL / Teks", "Wi-Fi", "Kontak", "WhatsApp", "Email"],
            command=self._on_category_change,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.category_seg.set("URL / Teks")
        self.category_seg.pack(fill="x", pady=(0, 10))

        self.form_container = ctk.CTkFrame(p, corner_radius=8, fg_color=("gray95", "#27272a"))
        self.form_container.pack(fill="x", pady=(0, 12), padx=2, ipady=6)

        self._init_form_fields()
        self._show_form_for_category("URL / Teks")

        # 2. ENKRIPSI TIKET (SECURITY)
        sec_lbl = ctk.CTkLabel(p, text="2. Keamanan & Enkripsi Tiket (C++ Engine):", font=ctk.CTkFont(size=13, weight="bold"))
        sec_lbl.pack(anchor="w", pady=(8, 4))

        sec_frame = ctk.CTkFrame(p, corner_radius=8, fg_color=("gray95", "#27272a"))
        sec_frame.pack(fill="x", pady=(0, 12), padx=2, ipady=6)

        self.chk_encrypt = ctk.CTkCheckBox(
            sec_frame,
            text="Kunci Payload dengan C++ Authenticated Encryption (Anti-Palsu)",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_encrypt_toggle,
        )
        self.chk_encrypt.pack(anchor="w", padx=12, pady=(6, 4))

        self.sec_key_row = ctk.CTkFrame(sec_frame, fg_color="transparent")
        ctk.CTkLabel(self.sec_key_row, text="Kunci Rahasia (Secret Key):", font=ctk.CTkFont(size=11)).pack(side="left")
        self.ent_secret_key = ctk.CTkEntry(self.sec_key_row, width=220, placeholder_text="Kunci rahasia validasi...")
        self.ent_secret_key.insert(0, "KunciKonser2026!")
        self.ent_secret_key.pack(side="right")
        self.ent_secret_key.bind("<KeyRelease>", lambda e: self.generate_qr())

        # 3. KUSTOMISASI WARNA
        color_lbl = ctk.CTkLabel(p, text="3. Kustomisasi Warna QR:", font=ctk.CTkFont(size=13, weight="bold"))
        color_lbl.pack(anchor="w", pady=(8, 4))

        color_frame = ctk.CTkFrame(p, corner_radius=8, fg_color=("gray95", "#27272a"))
        color_frame.pack(fill="x", pady=(0, 12), padx=2, ipady=6)

        qr_col_box = ctk.CTkFrame(color_frame, fg_color="transparent")
        qr_col_box.pack(fill="x", padx=12, pady=(4, 2))
        ctk.CTkLabel(qr_col_box, text="Warna QR (Modul):", font=ctk.CTkFont(weight="bold")).pack(side="left")

        self.qr_color_preview = ctk.CTkButton(
            qr_col_box,
            text="",
            width=28,
            height=28,
            corner_radius=6,
            fg_color=self.fill_color,
            hover_color=self.fill_color,
            command=self._pick_fill_color,
        )
        self.qr_color_preview.pack(side="right", padx=(8, 0))

        self.qr_color_entry = ctk.CTkEntry(qr_col_box, width=100)
        self.qr_color_entry.insert(0, self.fill_color)
        self.qr_color_entry.pack(side="right")
        self.qr_color_entry.bind("<FocusOut>", lambda e: self._on_hex_entry_change("fill"))

        preset_box = ctk.CTkFrame(color_frame, fg_color="transparent")
        preset_box.pack(fill="x", padx=12, pady=(2, 8))
        presets = [("Hitam", "#000000"), ("Navy", "#1E3A8A"), ("Zamrud", "#047857"), ("Indigo", "#4338CA"), ("Crimson", "#B91C1C")]
        for name, hex_c in presets:
            btn = ctk.CTkButton(
                preset_box,
                text=name,
                width=54,
                height=22,
                font=ctk.CTkFont(size=11),
                fg_color=hex_c,
                hover_color=hex_c,
                command=lambda c=hex_c: self._apply_fill_preset(c),
            )
            btn.pack(side="left", padx=2)

        bg_col_box = ctk.CTkFrame(color_frame, fg_color="transparent")
        bg_col_box.pack(fill="x", padx=12, pady=(4, 2))
        ctk.CTkLabel(bg_col_box, text="Warna Latar (Background):", font=ctk.CTkFont(weight="bold")).pack(side="left")

        self.bg_color_preview = ctk.CTkButton(
            bg_col_box,
            text="",
            width=28,
            height=28,
            corner_radius=6,
            fg_color=self.back_color,
            hover_color=self.back_color,
            command=self._pick_back_color,
        )
        self.bg_color_preview.pack(side="right", padx=(8, 0))

        self.bg_color_entry = ctk.CTkEntry(bg_col_box, width=100)
        self.bg_color_entry.insert(0, self.back_color)
        self.bg_color_entry.pack(side="right")
        self.bg_color_entry.bind("<FocusOut>", lambda e: self._on_hex_entry_change("back"))

        self.transparent_check = ctk.CTkCheckBox(
            color_frame,
            text="Gunakan Background Transparan (PNG)",
            font=ctk.CTkFont(size=12),
            command=self._on_transparent_toggle,
        )
        self.transparent_check.pack(anchor="w", padx=12, pady=(4, 4))

        # 4. LOGO TENGAH
        logo_lbl = ctk.CTkLabel(p, text="4. Sisipkan Logo di Tengah:", font=ctk.CTkFont(size=13, weight="bold"))
        logo_lbl.pack(anchor="w", pady=(8, 4))

        logo_frame = ctk.CTkFrame(p, corner_radius=8, fg_color=("gray95", "#27272a"))
        logo_frame.pack(fill="x", pady=(0, 12), padx=2, ipady=6)

        logo_btn_row = ctk.CTkFrame(logo_frame, fg_color="transparent")
        logo_btn_row.pack(fill="x", padx=12, pady=4)

        self.upload_logo_btn = ctk.CTkButton(
            logo_btn_row,
            text="Pilih File Logo...",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._choose_logo_file,
        )
        self.upload_logo_btn.pack(side="left")

        self.remove_logo_btn = ctk.CTkButton(
            logo_btn_row,
            text="Hapus",
            width=65,
            fg_color="#ef4444",
            hover_color="#dc2626",
            command=self._clear_logo,
        )
        self.remove_logo_btn.pack(side="right")

        self.logo_filename_lbl = ctk.CTkLabel(
            logo_frame,
            text="Belum ada logo yang dipilih",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color="gray50",
        )
        self.logo_filename_lbl.pack(anchor="w", padx=12, pady=(0, 4))

        badge_row = ctk.CTkFrame(logo_frame, fg_color="transparent")
        badge_row.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(badge_row, text="Bentuk Pelindung Logo:", font=ctk.CTkFont(size=12)).pack(side="left")
        self.logo_shape_menu = ctk.CTkOptionMenu(
            badge_row,
            values=["Kotak Membulat (Rounded)", "Lingkaran (Circle)", "Kotak Persegi", "Tanpa Background"],
            width=180,
            command=lambda v: self.generate_qr(),
        )
        self.logo_shape_menu.set("Kotak Membulat (Rounded)")
        self.logo_shape_menu.pack(side="right")

        slider_row = ctk.CTkFrame(logo_frame, fg_color="transparent")
        slider_row.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(slider_row, text="Ukuran Logo:", font=ctk.CTkFont(size=12)).pack(side="left")
        self.logo_size_slider = ctk.CTkSlider(
            slider_row,
            from_=0.15,
            to=0.28,
            number_of_steps=13,
            command=lambda v: self.generate_qr(),
        )
        self.logo_size_slider.set(0.22)
        self.logo_size_slider.pack(side="right", fill="x", expand=True, padx=(12, 0))

        # 5. KOREKSI ERROR
        opt_lbl = ctk.CTkLabel(p, text="5. Tingkat Koreksi Error:", font=ctk.CTkFont(size=13, weight="bold"))
        opt_lbl.pack(anchor="w", pady=(8, 4))

        opt_frame = ctk.CTkFrame(p, corner_radius=8, fg_color=("gray95", "#27272a"))
        opt_frame.pack(fill="x", pady=(0, 15), padx=2, ipady=6)

        ec_row = ctk.CTkFrame(opt_frame, fg_color="transparent")
        ec_row.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(ec_row, text="Error Correction:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")

        self.ec_menu = ctk.CTkOptionMenu(
            ec_row,
            values=[
                "H - High (30% - Aman untuk Logo)",
                "Q - Quartile (25%)",
                "M - Medium (15%)",
                "L - Low (7%)",
            ],
            width=240,
            command=lambda v: self.generate_qr(),
        )
        self.ec_menu.set("H - High (30% - Aman untuk Logo)")
        self.ec_menu.pack(side="right")

    def _on_encrypt_toggle(self):
        if self.chk_encrypt.get() == 1:
            self.sec_key_row.pack(fill="x", padx=12, pady=(4, 6))
        else:
            self.sec_key_row.pack_forget()
        self.generate_qr()

    def _init_form_fields(self):
        # 1. URL / Teks Bebas
        self.f_url = ctk.CTkFrame(self.form_container, fg_color="transparent")
        ctk.CTkLabel(self.f_url, text="Masukkan URL atau Teks Bebas:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(4, 2))
        self.txt_url = ctk.CTkTextbox(self.f_url, height=75)
        self.txt_url.insert("1.0", "TKT-COLDPLAY-VIP-0099")
        self.txt_url.pack(fill="x", padx=10, pady=(0, 4))

        # 2. Wi-Fi
        self.f_wifi = ctk.CTkFrame(self.form_container, fg_color="transparent")
        ctk.CTkLabel(self.f_wifi, text="Nama Jaringan (SSID):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(4, 2))
        self.ent_wifi_ssid = ctk.CTkEntry(self.f_wifi)
        self.ent_wifi_ssid.insert(0, "WiFi-Kantor-Utama")
        self.ent_wifi_ssid.pack(fill="x", padx=10, pady=(0, 4))

        ctk.CTkLabel(self.f_wifi, text="Kata Sandi (Password):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(4, 2))
        self.ent_wifi_pwd = ctk.CTkEntry(self.f_wifi)
        self.ent_wifi_pwd.insert(0, "SandiKuat2026!")
        self.ent_wifi_pwd.pack(fill="x", padx=10, pady=(0, 4))

        wifi_row2 = ctk.CTkFrame(self.f_wifi, fg_color="transparent")
        wifi_row2.pack(fill="x", padx=10, pady=4)
        ctk.CTkLabel(wifi_row2, text="Keamanan:").pack(side="left")
        self.menu_wifi_auth = ctk.CTkOptionMenu(wifi_row2, values=["WPA", "WEP", "Tanpa Sandi (Open)"], width=130)
        self.menu_wifi_auth.set("WPA")
        self.menu_wifi_auth.pack(side="left", padx=10)
        self.chk_wifi_hidden = ctk.CTkCheckBox(wifi_row2, text="Hidden SSID")
        self.chk_wifi_hidden.pack(side="right")

        # 3. Kontak (vCard)
        self.f_vcard = ctk.CTkFrame(self.form_container, fg_color="transparent")
        ctk.CTkLabel(self.f_vcard, text="Nama Lengkap:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(2, 2))
        self.ent_vc_name = ctk.CTkEntry(self.f_vcard)
        self.ent_vc_name.insert(0, "Budi Santoso")
        self.ent_vc_name.pack(fill="x", padx=10, pady=(0, 4))

        ctk.CTkLabel(self.f_vcard, text="No. Telepon / Ponsel:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(2, 2))
        self.ent_vc_phone = ctk.CTkEntry(self.f_vcard)
        self.ent_vc_phone.insert(0, "+6281234567890")
        self.ent_vc_phone.pack(fill="x", padx=10, pady=(0, 4))

        ctk.CTkLabel(self.f_vcard, text="Alamat Email:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(2, 2))
        self.ent_vc_email = ctk.CTkEntry(self.f_vcard)
        self.ent_vc_email.insert(0, "budi@perusahaan.co.id")
        self.ent_vc_email.pack(fill="x", padx=10, pady=(0, 4))

        ctk.CTkLabel(self.f_vcard, text="Organisasi / Perusahaan:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(2, 2))
        self.ent_vc_org = ctk.CTkEntry(self.f_vcard)
        self.ent_vc_org.insert(0, "PT Solusi Teknologi Indonesia")
        self.ent_vc_org.pack(fill="x", padx=10, pady=(0, 4))

        ctk.CTkLabel(self.f_vcard, text="Website:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(2, 2))
        self.ent_vc_web = ctk.CTkEntry(self.f_vcard)
        self.ent_vc_web.insert(0, "https://solusiteknologi.co.id")
        self.ent_vc_web.pack(fill="x", padx=10, pady=(0, 4))

        # 4. WhatsApp
        self.f_wa = ctk.CTkFrame(self.form_container, fg_color="transparent")
        ctk.CTkLabel(self.f_wa, text="Nomor WhatsApp (Kode Negara tanpa +):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(4, 2))
        self.ent_wa_phone = ctk.CTkEntry(self.f_wa)
        self.ent_wa_phone.insert(0, "6281234567890")
        self.ent_wa_phone.pack(fill="x", padx=10, pady=(0, 4))

        ctk.CTkLabel(self.f_wa, text="Pesan Teks Otomatis:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(4, 2))
        self.txt_wa_msg = ctk.CTkTextbox(self.f_wa, height=70)
        self.txt_wa_msg.insert("1.0", "Halo kak, saya ingin informasi lebih lanjut mengenai tiket konser ini.")
        self.txt_wa_msg.pack(fill="x", padx=10, pady=(0, 4))

        # 5. Email
        self.f_mail = ctk.CTkFrame(self.form_container, fg_color="transparent")
        ctk.CTkLabel(self.f_mail, text="Email Tujuan:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(4, 2))
        self.ent_mail_to = ctk.CTkEntry(self.f_mail)
        self.ent_mail_to.insert(0, "info@perusahaan.com")
        self.ent_mail_to.pack(fill="x", padx=10, pady=(0, 4))

        ctk.CTkLabel(self.f_mail, text="Subjek Email:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(4, 2))
        self.ent_mail_sub = ctk.CTkEntry(self.f_mail)
        self.ent_mail_sub.insert(0, "Konfirmasi Tiket")
        self.ent_mail_sub.pack(fill="x", padx=10, pady=(0, 4))

        ctk.CTkLabel(self.f_mail, text="Isi Pesan:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(4, 2))
        self.txt_mail_body = ctk.CTkTextbox(self.f_mail, height=65)
        self.txt_mail_body.insert("1.0", "Halo, terlampir detail tiket saya...")
        self.txt_mail_body.pack(fill="x", padx=10, pady=(0, 4))

    def _show_form_for_category(self, cat: str):
        for frame in (self.f_url, self.f_wifi, self.f_vcard, self.f_wa, self.f_mail):
            frame.pack_forget()

        if "URL" in cat:
            self.f_url.pack(fill="x", padx=5, pady=5)
        elif "Wi-Fi" in cat:
            self.f_wifi.pack(fill="x", padx=5, pady=5)
        elif "Kontak" in cat:
            self.f_vcard.pack(fill="x", padx=5, pady=5)
        elif "WhatsApp" in cat:
            self.f_wa.pack(fill="x", padx=5, pady=5)
        elif "Email" in cat:
            self.f_mail.pack(fill="x", padx=5, pady=5)

    def _on_category_change(self, value: str):
        self.current_tab = value
        self._show_form_for_category(value)
        self.generate_qr()

    def _build_right_panel_preview(self):
        r = self.right_frame

        p_title = ctk.CTkLabel(
            r,
            text="PRATINJAU QR CODE",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#1e3a8a", "#60a5fa"),
        )
        p_title.pack(anchor="w", padx=20, pady=(15, 6))

        self.preview_card = ctk.CTkFrame(
            r,
            corner_radius=12,
            fg_color=("gray85", "#18181b"),
            border_width=1,
            border_color=("gray75", "#27272a"),
        )
        self.preview_card.pack(fill="both", expand=True, padx=20, pady=(0, 8))

        self.qr_preview_label = ctk.CTkLabel(self.preview_card, text="Memuat QR Code...")
        self.qr_preview_label.pack(expand=True, padx=15, pady=15)

        self.info_status_lbl = ctk.CTkLabel(
            r,
            text="Ukuran: - | Siap Digunakan",
            font=ctk.CTkFont(size=11),
            text_color="gray50",
        )
        self.info_status_lbl.pack(pady=(0, 6))

        res_row = ctk.CTkFrame(r, fg_color="transparent")
        res_row.pack(fill="x", padx=20, pady=(0, 8))
        ctk.CTkLabel(res_row, text="Resolusi Simpan PNG:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
        self.export_res_menu = ctk.CTkOptionMenu(
            res_row,
            values=[
                "Standar HD (800 x 800 px)",
                "Tinggi (1200 x 1200 px)",
                "Ultra Tajam / Cetak (2000 x 2000 px)",
                "Kecil (400 x 400 px)",
            ],
            width=210,
        )
        self.export_res_menu.set("Standar HD (800 x 800 px)")
        self.export_res_menu.pack(side="right")

        action_box = ctk.CTkFrame(r, fg_color="transparent")
        action_box.pack(fill="x", padx=20, pady=(0, 10))

        self.btn_refresh = ctk.CTkButton(
            action_box,
            text="Perbarui Tampilan QR",
            height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.generate_qr,
        )
        self.btn_refresh.pack(fill="x", pady=(0, 6))

        grid_btns = ctk.CTkFrame(action_box, fg_color="transparent")
        grid_btns.pack(fill="x")
        grid_btns.grid_columnconfigure((0, 1), weight=1)

        self.btn_save_png = ctk.CTkButton(
            grid_btns,
            text="Simpan PNG",
            height=34,
            fg_color="#10b981",
            hover_color="#059669",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._save_as_png,
        )
        self.btn_save_png.grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=2)

        self.btn_save_svg = ctk.CTkButton(
            grid_btns,
            text="Ekspor SVG (Vektor)",
            height=34,
            fg_color="#8b5cf6",
            hover_color="#7c3aed",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._save_as_svg,
        )
        self.btn_save_svg.grid(row=0, column=1, sticky="ew", padx=(4, 0), pady=2)

        self.btn_copy_clip = ctk.CTkButton(
            action_box,
            text="Salin Gambar ke Clipboard",
            height=34,
            fg_color=("gray75", "#3f3f46"),
            hover_color=("gray65", "#52525b"),
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._copy_to_clipboard,
        )
        self.btn_copy_clip.pack(fill="x", pady=(6, 0))

        self.toast_label = ctk.CTkLabel(
            r,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#10b981",
        )
        self.toast_label.pack(pady=(0, 8))

    def _show_toast(self, message: str, is_error: bool = False):
        self.toast_label.configure(
            text=message,
            text_color="#ef4444" if is_error else "#10b981",
        )
        self.after(3500, lambda: self.toast_label.configure(text=""))

    def _extract_payload_data(self) -> str:
        cat = self.current_tab
        raw = ""
        if "URL" in cat:
            raw = self.txt_url.get("1.0", "end-1c").strip()
        elif "Wi-Fi" in cat:
            ssid = self.ent_wifi_ssid.get()
            pwd = self.ent_wifi_pwd.get()
            auth = self.menu_wifi_auth.get()
            hidden = bool(self.chk_wifi_hidden.get())
            raw = QRFormatters.wifi(ssid, pwd, auth, hidden)
        elif "Kontak" in cat:
            name = self.ent_vc_name.get()
            phone = self.ent_vc_phone.get()
            email = self.ent_vc_email.get()
            org = self.ent_vc_org.get()
            web = self.ent_vc_web.get()
            raw = QRFormatters.vcard(name=name, phone=phone, email=email, org=org, website=web)
        elif "WhatsApp" in cat:
            phone = self.ent_wa_phone.get()
            msg = self.txt_wa_msg.get("1.0", "end-1c")
            raw = QRFormatters.whatsapp(phone, msg)
        elif "Email" in cat:
            to = self.ent_mail_to.get()
            sub = self.ent_mail_sub.get()
            body = self.txt_mail_body.get("1.0", "end-1c")
            raw = QRFormatters.email(to, sub, body)

        if not raw:
            raw = "TKT-DEMO-001"

        # Cek jika enkripsi aktif
        if hasattr(self, "chk_encrypt") and self.chk_encrypt.get() == 1:
            key = self.ent_secret_key.get().strip()
            if key:
                return bridge.encrypt_ticket(raw, key)
        return raw

    def generate_qr(self):
        payload = self._extract_payload_data()

        ec_val = self.ec_menu.get()
        ec_code = "H"
        if "Q -" in ec_val:
            ec_code = "Q"
        elif "M -" in ec_val:
            ec_code = "M"
        elif "L -" in ec_val:
            ec_code = "L"

        bg = "transparent" if self.is_transparent_bg else self.back_color

        engine = QREngine(
            data=payload,
            error_correction=ec_code,
            fill_color=self.fill_color,
            back_color=bg,
            box_size=12,
            border=2,
        )

        if self.selected_logo_path and os.path.exists(self.selected_logo_path):
            shape_str = self.logo_shape_menu.get()
            shape_key = "rounded"
            if "Lingkaran" in shape_str:
                shape_key = "circle"
            elif "Persegi" in shape_str:
                shape_key = "square"
            elif "Tanpa" in shape_str:
                shape_key = "none"

            size_ratio = float(self.logo_size_slider.get())
            engine.set_logo(self.selected_logo_path, shape=shape_key, size_ratio=size_ratio)

        self.qr_engine_instance = engine

        try:
            pil_img = engine.generate_image()
            self.current_pil_image = pil_img

            preview_max_dim = 290
            w, h = pil_img.size
            ratio = min(preview_max_dim / w, preview_max_dim / h)
            disp_w = int(w * ratio)
            disp_h = int(h * ratio)

            display_img = pil_img.resize((disp_w, disp_h), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=display_img, dark_image=display_img, size=(disp_w, disp_h))

            self.qr_preview_label.configure(image=ctk_img, text="")
            self.qr_preview_label.image = ctk_img

            enc_tag = " [Enkripsi C++ Aktif]" if payload.startswith("SECQR1:") else ""
            self.info_status_lbl.configure(
                text=f"Ukuran: {w}x{h} px | Koreksi: {ec_code}{enc_tag} | Siap Diekspor"
            )
        except Exception as err:
            self._show_toast(f"Error: {str(err)}", is_error=True)

    def _choose_logo_file(self):
        filepath = filedialog.askopenfilename(
            title="Pilih Logo Gambar",
            filetypes=[
                ("Image Files", "*.png;*.jpg;*.jpeg;*.webp;*.ico"),
                ("PNG Image", "*.png"),
                ("JPEG Image", "*.jpg;*.jpeg"),
                ("Semua File", "*.*"),
            ],
        )
        if filepath:
            self.selected_logo_path = filepath
            filename = os.path.basename(filepath)
            self.logo_filename_lbl.configure(text=f"Logo aktif: {filename}", text_color="#10b981")
            self.ec_menu.set("H - High (30% - Aman untuk Logo)")
            self.generate_qr()

    def _clear_logo(self):
        self.selected_logo_path = None
        self.logo_filename_lbl.configure(text="Belum ada logo yang dipilih", text_color="gray50")
        self.generate_qr()

    def _pick_fill_color(self):
        color = colorchooser.askcolor(initialcolor=self.fill_color, title="Pilih Warna QR Code")
        if color and color[1]:
            self.fill_color = color[1].upper()
            self.qr_color_entry.delete(0, "end")
            self.qr_color_entry.insert(0, self.fill_color)
            self.qr_color_preview.configure(fg_color=self.fill_color, hover_color=self.fill_color)
            self.generate_qr()

    def _pick_back_color(self):
        color = colorchooser.askcolor(initialcolor=self.back_color, title="Pilih Warna Background")
        if color and color[1]:
            self.back_color = color[1].upper()
            self.bg_color_entry.delete(0, "end")
            self.bg_color_entry.insert(0, self.back_color)
            self.bg_color_preview.configure(fg_color=self.back_color, hover_color=self.back_color)
            self.transparent_check.deselect()
            self.is_transparent_bg = False
            self.generate_qr()

    def _apply_fill_preset(self, hex_color: str):
        self.fill_color = hex_color.upper()
        self.qr_color_entry.delete(0, "end")
        self.qr_color_entry.insert(0, self.fill_color)
        self.qr_color_preview.configure(fg_color=self.fill_color, hover_color=self.fill_color)
        self.generate_qr()

    def _on_hex_entry_change(self, mode: str):
        if mode == "fill":
            val = self.qr_color_entry.get().strip()
            if not val.startswith("#"):
                val = f"#{val}"
            if len(val) == 7:
                self.fill_color = val.upper()
                self.qr_color_preview.configure(fg_color=self.fill_color, hover_color=self.fill_color)
                self.generate_qr()
        elif mode == "back":
            val = self.bg_color_entry.get().strip()
            if not val.startswith("#"):
                val = f"#{val}"
            if len(val) == 7:
                self.back_color = val.upper()
                self.bg_color_preview.configure(fg_color=self.back_color, hover_color=self.back_color)
                self.transparent_check.deselect()
                self.is_transparent_bg = False
                self.generate_qr()

    def _on_transparent_toggle(self):
        self.is_transparent_bg = bool(self.transparent_check.get())
        self.generate_qr()

    def _get_export_dimension(self) -> int:
        res_str = self.export_res_menu.get()
        if "2000" in res_str:
            return 2000
        elif "1200" in res_str:
            return 1200
        elif "400" in res_str:
            return 400
        return 800

    def _save_as_png(self):
        if not self.qr_engine_instance:
            self.generate_qr()

        filepath = filedialog.asksaveasfilename(
            title="Simpan QR Code sebagai PNG",
            defaultextension=".png",
            filetypes=[("PNG Image (*.png)", "*.png"), ("Semua File (*.*)", "*.*")],
        )
        if filepath:
            try:
                target_dim = self._get_export_dimension()
                self.qr_engine_instance.save_png(filepath, max_dimension=target_dim)
                self._show_toast(f"[OK] Tersimpan ke: {os.path.basename(filepath)}")
            except Exception as e:
                messagebox.showerror("Gagal Menyimpan", f"Terjadi kesalahan saat menyimpan PNG:\n{str(e)}")

    def _save_as_svg(self):
        if not self.qr_engine_instance:
            self.generate_qr()

        filepath = filedialog.asksaveasfilename(
            title="Ekspor QR Code sebagai SVG Vektor",
            defaultextension=".svg",
            filetypes=[("SVG Vector (*.svg)", "*.svg"), ("Semua File (*.*)", "*.*")],
        )
        if filepath:
            try:
                self.qr_engine_instance.save_svg(filepath)
                self._show_toast(f"[OK] Vektor SVG tersimpan ke: {os.path.basename(filepath)}")
            except Exception as e:
                messagebox.showerror("Gagal Menyimpan", f"Terjadi kesalahan saat menyimpan SVG:\n{str(e)}")

    def _copy_to_clipboard(self):
        if not self.current_pil_image:
            self.generate_qr()

        if self.current_pil_image:
            success, msg = copy_image_to_clipboard(self.current_pil_image)
            if success:
                self._show_toast("[OK] Gambar berhasil disalin ke Clipboard!")
            else:
                self._show_toast(f"[ERROR] {msg}", is_error=True)

    # =========================================================================
    # MODE 2: BATCH GENERATOR MASSAL & BENCHMARK C++
    # =========================================================================

    def _build_batch_view(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(parent, label_text="C++ HIGH-PERFORMANCE BATCH GENERATOR", label_font=ctk.CTkFont(size=15, weight="bold"))
        scroll.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)

        info_box = ctk.CTkFrame(scroll, fg_color=("gray92", "#27272a"), corner_radius=10)
        info_box.pack(fill="x", padx=15, pady=(5, 15), ipady=8)

        ctk.CTkLabel(
            info_box,
            text="Pembuatan Massal Puluhan Ribu Tiket / Label Gudang",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#1e3a8a", "#60a5fa"),
        ).pack(anchor="w", padx=15, pady=(5, 2))

        ctk.CTkLabel(
            info_box,
            text="Fitur ini memproses pembuatan QR Code menggunakan multi-threading tingkat tinggi.\n"
                 "Dapat otomatis menyertakan enkripsi anti-pemalsuan dan menghasilkan file CSV rekap manifest tiket.",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray70"),
            justify="left",
        ).pack(anchor="w", padx=15, pady=(0, 6))

        # Form Konfigurasi Batch
        form_card = ctk.CTkFrame(scroll, fg_color=("gray95", "#1f1f23"), corner_radius=10)
        form_card.pack(fill="x", padx=15, pady=(0, 15), ipady=12)

        # Baris 1: Prefix Tiket & Nomor Awal
        r1 = ctk.CTkFrame(form_card, fg_color="transparent")
        r1.pack(fill="x", padx=15, pady=6)
        r1.grid_columnconfigure((0, 1), weight=1)

        b_pref_box = ctk.CTkFrame(r1, fg_color="transparent")
        b_pref_box.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ctk.CTkLabel(b_pref_box, text="Prefix ID Tiket / Barang:", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        self.b_ent_prefix = ctk.CTkEntry(b_pref_box, placeholder_text="Contoh: TKT-COLDPLAY-VIP")
        self.b_ent_prefix.insert(0, "TKT-KONSER-2026")
        self.b_ent_prefix.pack(fill="x", pady=(2, 0))

        b_start_box = ctk.CTkFrame(r1, fg_color="transparent")
        b_start_box.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        ctk.CTkLabel(b_start_box, text="Nomor Urut Awal:", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        self.b_ent_start = ctk.CTkEntry(b_start_box)
        self.b_ent_start.insert(0, "1")
        self.b_ent_start.pack(fill="x", pady=(2, 0))

        # Baris 2: Jumlah Tiket & Folder Tujuan
        r2 = ctk.CTkFrame(form_card, fg_color="transparent")
        r2.pack(fill="x", padx=15, pady=6)
        r2.grid_columnconfigure((0, 1), weight=1)

        b_cnt_box = ctk.CTkFrame(r2, fg_color="transparent")
        b_cnt_box.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ctk.CTkLabel(b_cnt_box, text="Jumlah QR yang Dihasilkan:", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        self.b_menu_count = ctk.CTkOptionMenu(
            b_cnt_box,
            values=["50 Tiket", "100 Tiket", "500 Tiket", "1000 Tiket (1K)", "5000 Tiket (5K)", "10000 Tiket (10K)"],
        )
        self.b_menu_count.set("500 Tiket")
        self.b_menu_count.pack(fill="x", pady=(2, 0))

        b_dir_box = ctk.CTkFrame(r2, fg_color="transparent")
        b_dir_box.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        ctk.CTkLabel(b_dir_box, text="Folder Penyimpanan Hasil:", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        b_dir_row = ctk.CTkFrame(b_dir_box, fg_color="transparent")
        b_dir_row.pack(fill="x", pady=(2, 0))

        self.b_ent_dir = ctk.CTkEntry(b_dir_row)
        default_export = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output_batch")
        self.b_ent_dir.insert(0, default_export)
        self.b_ent_dir.pack(side="left", fill="x", expand=True)

        ctk.CTkButton(b_dir_row, text="Browse", width=75, command=self._browse_batch_dir).pack(side="right", padx=(6, 0))

        # Baris 3: Opsi Enkripsi Keamanan Massal
        r3 = ctk.CTkFrame(form_card, fg_color="transparent")
        r3.pack(fill="x", padx=15, pady=(8, 4))

        self.b_chk_encrypt = ctk.CTkCheckBox(
            r3,
            text="Enkripsi Seluruh Tiket dengan Kunci Rahasia C++ (Mencegah Pemalsuan)",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_batch_encrypt_toggle,
        )
        self.b_chk_encrypt.select()
        self.b_chk_encrypt.pack(anchor="w")

        self.b_key_row = ctk.CTkFrame(form_card, fg_color="transparent")
        self.b_key_row.pack(fill="x", padx=15, pady=(2, 6))
        ctk.CTkLabel(self.b_key_row, text="Kunci Rahasia Acara / Tiket:").pack(side="left")
        self.b_ent_key = ctk.CTkEntry(self.b_key_row, width=280)
        self.b_ent_key.insert(0, "EventKunciRahasia2026!")
        self.b_ent_key.pack(side="left", padx=10)

        # Tombol Aksi Batch & Benchmark
        btn_row = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=(5, 10))

        self.btn_run_batch = ctk.CTkButton(
            btn_row,
            text="Mulai Batch Printing Sekarang",
            height=42,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            command=self._run_batch_generation,
        )
        self.btn_run_batch.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_bench = ctk.CTkButton(
            btn_row,
            text="Uji Benchmark Speed",
            height=42,
            width=200,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#8b5cf6",
            hover_color="#7c3aed",
            command=self._run_benchmark_test,
        )
        self.btn_bench.pack(side="right")

        # Progress Bar & Status
        self.b_progress = ctk.CTkProgressBar(scroll)
        self.b_progress.set(0)
        self.b_progress.pack(fill="x", padx=15, pady=(8, 4))

        self.b_status_lbl = ctk.CTkLabel(
            scroll,
            text="Status: Siap menjalankan batch generation",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="gray60",
        )
        self.b_status_lbl.pack(pady=(0, 15))

    def _browse_batch_dir(self):
        folder = filedialog.askdirectory(title="Pilih Folder Output Batch")
        if folder:
            self.b_ent_dir.delete(0, "end")
            self.b_ent_dir.insert(0, folder)

    def _on_batch_encrypt_toggle(self):
        if self.b_chk_encrypt.get() == 1:
            self.b_key_row.pack(fill="x", padx=15, pady=(2, 6))
        else:
            self.b_key_row.pack_forget()

    def _run_batch_generation(self):
        prefix = self.b_ent_prefix.get().strip() or "TKT"
        start_num = int(self.b_ent_start.get().strip() or "1")
        cnt_str = self.b_menu_count.get()
        count = int(cnt_str.split()[0].replace("K", "000"))
        out_dir = self.b_ent_dir.get().strip()
        key = self.b_ent_key.get().strip() if self.b_chk_encrypt.get() == 1 else None

        self.btn_run_batch.configure(state="disabled", text="Sedang Memproses Batch...")
        self.b_progress.set(0)
        self.b_status_lbl.configure(text=f"Memproses {count} QR Code...", text_color="#3b82f6")

        def thread_target():
            def progress(done, total):
                self.after(0, lambda: self.b_progress.set(done / total))
                self.after(0, lambda: self.b_status_lbl.configure(text=f"Proses: {done}/{total} QR selesai..."))

            stats = BatchEngine.generate_batch(
                prefix=prefix,
                start_number=start_num,
                count=count,
                output_dir=out_dir,
                secret_key=key,
                progress_callback=progress,
            )

            def on_finish():
                self.btn_run_batch.configure(state="normal", text="Mulai Batch Printing Sekarang")
                self.b_progress.set(1.0)
                sec = stats["elapsed_seconds"]
                qps = stats["qps"]
                msg = f"[OK] Selesai! {count} file berhasil dibuat dalam {sec:.2f} detik ({qps:,} QR/detik)\nManifest: {stats['manifest_path']}"
                self.b_status_lbl.configure(text=msg, text_color="#10b981")
                messagebox.showinfo("Batch Selesai", msg)

            self.after(0, on_finish)

        threading.Thread(target=thread_target, daemon=True).start()

    def _run_benchmark_test(self):
        self.btn_bench.configure(state="disabled", text="Menguji...")
        self.b_status_lbl.configure(text="Menjalankan benchmark generasi matriks QR Code...", text_color="#8b5cf6")

        def thread_target():
            ms, qps = bridge.benchmark_speed(count=3000)

            def on_finish():
                self.btn_bench.configure(state="normal", text="Uji Benchmark Speed")
                res_txt = f"Hasil Benchmark: 3,000 QR matriks diproses dalam {ms:.1f} ms (~{qps:,} QR/detik)"
                self.b_status_lbl.configure(text=res_txt, text_color="#8b5cf6")
                messagebox.showinfo("Benchmark Selesai", res_txt)

            self.after(0, on_finish)

        threading.Thread(target=thread_target, daemon=True).start()

    # =========================================================================
    # MODE 3: SCANNER CEPAT & VERIFIKASI KEASLIAN TIKET
    # =========================================================================

    def _build_scanner_view(self, parent):
        parent.grid_columnconfigure((0, 1), weight=1)
        parent.grid_rowconfigure(0, weight=1)

        # Sisi Kiri: Video Feed / Pratinjau Kamera
        cam_card = ctk.CTkFrame(parent, corner_radius=12)
        cam_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=5)

        ctk.CTkLabel(
            cam_card,
            text="KAMERA SCANNER REAL-TIME",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#1e3a8a", "#60a5fa"),
        ).pack(anchor="w", padx=15, pady=(15, 8))

        # Layar penampil frame kamera
        self.cam_screen = ctk.CTkLabel(
            cam_card,
            text="Kamera belum aktif.\nKlik 'Mulai Scanner Webcam' di samping untuk menyalakan.",
            font=ctk.CTkFont(size=13),
            fg_color=("gray85", "#18181b"),
            corner_radius=10,
        )
        self.cam_screen.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # Sisi Kanan: Kontrol & Hasil Verifikasi Keaslian
        res_card = ctk.CTkFrame(parent, corner_radius=12)
        res_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=5)

        ctk.CTkLabel(
            res_card,
            text="VERIFIKASI KEASLIAN TIKET",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#1e3a8a", "#60a5fa"),
        ).pack(anchor="w", padx=15, pady=(15, 10))

        # Input Kunci Rahasia Verifikasi
        k_box = ctk.CTkFrame(res_card, fg_color=("gray92", "#27272a"), corner_radius=8)
        k_box.pack(fill="x", padx=15, pady=(0, 15), ipady=6)

        ctk.CTkLabel(k_box, text="Kunci Rahasia Verifikasi Tiket:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=10, pady=(4, 2))
        self.scan_key_ent = ctk.CTkEntry(k_box, placeholder_text="Masukkan Secret Key...")
        self.scan_key_ent.insert(0, "EventKunciRahasia2026!")
        self.scan_key_ent.pack(fill="x", padx=10, pady=(0, 4))

        # Tombol Kontrol Scanner
        btn_box = ctk.CTkFrame(res_card, fg_color="transparent")
        btn_box.pack(fill="x", padx=15, pady=(0, 15))

        self.btn_toggle_cam = ctk.CTkButton(
            btn_box,
            text="Mulai Scanner Webcam",
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#3b82f6",
            hover_color="#2563eb",
            command=self._toggle_webcam,
        )
        self.btn_toggle_cam.pack(fill="x", pady=(0, 8))

        self.btn_scan_file = ctk.CTkButton(
            btn_box,
            text="Scan dari File Gambar...",
            height=36,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("gray75", "#3f3f46"),
            hover_color=("gray65", "#52525b"),
            command=self._scan_from_file_dialog,
        )
        self.btn_scan_file.pack(fill="x")

        # Badge Status Hasil Verifikasi
        ctk.CTkLabel(res_card, text="Status Hasil Pemindaian:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=15, pady=(10, 4))

        self.scan_badge = ctk.CTkLabel(
            res_card,
            text="MENUNGGU PEMINDAIAN...",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=("gray85", "#27272a"),
            corner_radius=8,
            height=42,
        )
        self.scan_badge.pack(fill="x", padx=15, pady=(0, 10))

        # Box Detail Isi Data
        ctk.CTkLabel(res_card, text="Isi Konten Data Terdekripsi:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=15, pady=(4, 2))
        self.txt_scan_content = ctk.CTkTextbox(res_card, height=140)
        self.txt_scan_content.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    def _toggle_webcam(self):
        if not self.is_webcam_running:
            self._start_webcam()
        else:
            self._stop_webcam()

    def _start_webcam(self):
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                messagebox.showerror("Kamera Gagal", "Tidak dapat membuka kamera webcam. Pastikan kamera terpasang dan tidak sedang dipakai aplikasi lain.")
                return

            self.is_webcam_running = True
            self.btn_toggle_cam.configure(text="Hentikan Scanner Webcam", fg_color="#ef4444", hover_color="#dc2626")
            self._update_webcam_loop()
        except Exception as e:
            messagebox.showerror("Error Kamera", str(e))

    def _stop_webcam(self):
        self.is_webcam_running = False
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

        if hasattr(self, "btn_toggle_cam"):
            self.btn_toggle_cam.configure(text="Mulai Scanner Webcam", fg_color="#3b82f6", hover_color="#2563eb")
        if hasattr(self, "cam_screen"):
            self.cam_screen.configure(image="", text="Kamera nonaktif.\nKlik 'Mulai Scanner Webcam' untuk menyalakan.")

    def _update_webcam_loop(self):
        if not self.is_webcam_running or not self.cap:
            return

        ret, frame = self.cap.read()
        if ret:
            key = self.scan_key_ent.get().strip()
            annotated_frame, scan_res = self.scanner_engine.annotate_frame(frame, secret_key=key)

            # Convert BGR ke RGB
            rgb_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            h, w, _ = rgb_frame.shape

            # Scale agar proporsional ke ukuran layar
            target_w = 460
            target_h = int(h * (target_w / w))
            resized = cv2.resize(rgb_frame, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

            pil_img = Image.fromarray(resized)
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(target_w, target_h))

            self.cam_screen.configure(image=ctk_img, text="")
            self.cam_screen.image = ctk_img

            if scan_res:
                self._update_scan_ui_result(scan_res)

        self.after(25, self._update_webcam_loop)

    def _scan_from_file_dialog(self):
        filepath = filedialog.askopenfilename(
            title="Pilih Gambar QR untuk Di-scan",
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp;*.webp"), ("Semua File", "*.*")],
        )
        if filepath:
            key = self.scan_key_ent.get().strip()
            res = self.scanner_engine.scan_image_file(filepath, secret_key=key)
            if res:
                self._update_scan_ui_result(res)
            else:
                self.scan_badge.configure(text="TIDAK DITEMUKAN QR CODE", fg_color="#ef4444", text_color="#ffffff")
                self.txt_scan_content.delete("1.0", "end")
                self.txt_scan_content.insert("1.0", "Tidak ada kode QR yang terdeteksi pada berkas gambar ini.")

    def _update_scan_ui_result(self, res: ScanResult):
        # Hindari spam render jika token sama persis
        if res.raw_text == self.last_scanned_token:
            return
        self.last_scanned_token = res.raw_text

        if res.verification_status == 0:
            # Tiket Asli
            self.scan_badge.configure(text="[VALID] TIKET ASLI TERVERIFIKASI", fg_color="#10b981", text_color="#ffffff")
        elif res.verification_status == 1:
            # Tiket Palsu / Kunci Salah
            self.scan_badge.configure(text="[PERINGATAN] TIKET PALSU!", fg_color="#ef4444", text_color="#ffffff")
        elif res.verification_status == 3:
            # Perlu Kunci
            self.scan_badge.configure(text="[KUNCI DIBUTUHKAN] TIKET TERENKRIPSI", fg_color="#f59e0b", text_color="#000000")
        else:
            # QR Normal / Plain text
            self.scan_badge.configure(text="QR CODE BIASA TERDETEKSI", fg_color="#3b82f6", text_color="#ffffff")

        self.txt_scan_content.delete("1.0", "end")
        details = (
            f"Pesan Status:\n{res.message}\n\n"
            f"Konten Terdekripsi:\n{res.decoded_content}\n\n"
            f"Raw Payload Token:\n{res.raw_text}"
        )
        self.txt_scan_content.insert("1.0", details)
