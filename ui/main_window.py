"""
Main Window GUI Module
Antarmuka Grafis Desktop Modern menggunakan CustomTkinter.
"""

import os
import tkinter as tk
from tkinter import filedialog, colorchooser, messagebox
from typing import Optional
from PIL import Image

import customtkinter as ctk

from core.qr_engine import QREngine, QRFormatters
from core.clipboard import copy_image_to_clipboard

# Konfigurasi Tema CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class QRApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Setup Jendela Utama
        self.title("Desktop QR Code Generator")
        self.geometry("1120x760")
        self.minsize(980, 680)

        # State Aplikasi
        self.current_tab = "URL / Teks"
        self.fill_color = "#000000"
        self.back_color = "#FFFFFF"
        self.is_transparent_bg = False
        self.selected_logo_path: Optional[str] = None
        self.current_pil_image: Optional[Image.Image] = None
        self.qr_engine_instance: Optional[QREngine] = None

        # Bangun Layout
        self._build_header()
        self._build_main_layout()

        # Render awal QR Code default
        self.after(150, self.generate_qr)

    def _build_header(self):
        """Membuat bar header atas dengan judul dan switch tema."""
        header_frame = ctk.CTkFrame(self, height=60, corner_radius=0, fg_color=("gray90", "#18181b"))
        header_frame.pack(side="top", fill="x")

        # Judul & Branding
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=20, pady=10)

        title_lbl = ctk.CTkLabel(
            title_box,
            text="⚡ QR STUDIO PRO",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=("#1e3a8a", "#60a5fa"),
        )
        title_lbl.pack(anchor="w")

        subtitle_lbl = ctk.CTkLabel(
            title_box,
            text="Generator QR Code Desktop Modern, Fleksibel & Siap Cetak",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60"),
        )
        subtitle_lbl.pack(anchor="w")

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

    def _build_main_layout(self):
        """Membuat split panel: Kiri (Kontrol & Input) dan Kanan (Preview & Ekspor)."""
        body_frame = ctk.CTkFrame(self, fg_color="transparent")
        body_frame.pack(side="top", fill="both", expand=True, padx=15, pady=15)

        body_frame.grid_columnconfigure(0, weight=6)
        body_frame.grid_columnconfigure(1, weight=5)
        body_frame.grid_rowconfigure(0, weight=1)

        # Panel Kiri: Scrollable Control Panel
        self.left_scroll = ctk.CTkScrollableFrame(
            body_frame,
            label_text="⚙️ PENGATURAN & KONTEN QR",
            label_font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.left_scroll.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Panel Kanan: Preview & Actions
        self.right_frame = ctk.CTkFrame(body_frame, corner_radius=12)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        self._build_left_panel_controls()
        self._build_right_panel_preview()

    def _build_left_panel_controls(self):
        """Menyusun seluruh formulir input, pilihan warna, logo, dan opsi koreksi."""
        p = self.left_scroll

        # 1. KATEGORI KONTEN (Segmented Button)
        cat_lbl = ctk.CTkLabel(p, text="1. Pilih Jenis Konten QR:", font=ctk.CTkFont(size=13, weight="bold"))
        cat_lbl.pack(anchor="w", pady=(5, 6))

        self.category_seg = ctk.CTkSegmentedButton(
            p,
            values=["🌐 URL / Teks", "📶 Wi-Fi", "👤 Kontak", "💬 WhatsApp", "✉️ Email"],
            command=self._on_category_change,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.category_seg.set("🌐 URL / Teks")
        self.category_seg.pack(fill="x", pady=(0, 12))

        # Container Frame untuk formulir dinamis
        self.form_container = ctk.CTkFrame(p, corner_radius=8, fg_color=("gray95", "#27272a"))
        self.form_container.pack(fill="x", pady=(0, 15), padx=2, ipady=6)

        self._init_form_fields()
        self._show_form_for_category("🌐 URL / Teks")

        # 2. KUSTOMISASI WARNA
        color_lbl = ctk.CTkLabel(p, text="2. Kustomisasi Warna QR:", font=ctk.CTkFont(size=13, weight="bold"))
        color_lbl.pack(anchor="w", pady=(10, 6))

        color_frame = ctk.CTkFrame(p, corner_radius=8, fg_color=("gray95", "#27272a"))
        color_frame.pack(fill="x", pady=(0, 15), padx=2, ipady=8)

        # Baris Warna QR
        qr_col_box = ctk.CTkFrame(color_frame, fg_color="transparent")
        qr_col_box.pack(fill="x", padx=12, pady=(6, 4))
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

        # Tombol Preset Warna QR
        preset_box = ctk.CTkFrame(color_frame, fg_color="transparent")
        preset_box.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkLabel(preset_box, text="Preset:", font=ctk.CTkFont(size=11), text_color="gray60").pack(side="left", padx=(0, 6))

        presets = [
            ("Hitam", "#000000"),
            ("Navy", "#1E3A8A"),
            ("Zamrud", "#047857"),
            ("Indigo", "#4338CA"),
            ("Crimson", "#B91C1C"),
        ]
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

        # Baris Warna Latar Belakang (Background)
        bg_col_box = ctk.CTkFrame(color_frame, fg_color="transparent")
        bg_col_box.pack(fill="x", padx=12, pady=(4, 4))
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

        # Checkbox Background Transparan
        self.transparent_check = ctk.CTkCheckBox(
            color_frame,
            text="Gunakan Background Transparan (Khusus PNG)",
            font=ctk.CTkFont(size=12),
            command=self._on_transparent_toggle,
        )
        self.transparent_check.pack(anchor="w", padx=12, pady=(4, 6))

        # 3. KUSTOMISASI LOGO TENGAH
        logo_lbl = ctk.CTkLabel(p, text="3. Sisipkan Logo di Tengah (Opsional):", font=ctk.CTkFont(size=13, weight="bold"))
        logo_lbl.pack(anchor="w", pady=(10, 6))

        logo_frame = ctk.CTkFrame(p, corner_radius=8, fg_color=("gray95", "#27272a"))
        logo_frame.pack(fill="x", pady=(0, 15), padx=2, ipady=8)

        # Tombol Pilih File Logo & Info
        logo_btn_row = ctk.CTkFrame(logo_frame, fg_color="transparent")
        logo_btn_row.pack(fill="x", padx=12, pady=6)

        self.upload_logo_btn = ctk.CTkButton(
            logo_btn_row,
            text="📂 Pilih File Logo...",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._choose_logo_file,
        )
        self.upload_logo_btn.pack(side="left")

        self.remove_logo_btn = ctk.CTkButton(
            logo_btn_row,
            text="❌ Hapus",
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
        self.logo_filename_lbl.pack(anchor="w", padx=12, pady=(0, 6))

        # Bentuk Badge & Slider Ukuran Logo
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

        # Slider Proporsi Logo
        slider_row = ctk.CTkFrame(logo_frame, fg_color="transparent")
        slider_row.pack(fill="x", padx=12, pady=6)

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

        # 4. TINGKAT KOREKSI ERROR & RESOLUSI
        opt_lbl = ctk.CTkLabel(p, text="4. Kualitas & Koreksi Error:", font=ctk.CTkFont(size=13, weight="bold"))
        opt_lbl.pack(anchor="w", pady=(10, 6))

        opt_frame = ctk.CTkFrame(p, corner_radius=8, fg_color=("gray95", "#27272a"))
        opt_frame.pack(fill="x", pady=(0, 15), padx=2, ipady=8)

        ec_row = ctk.CTkFrame(opt_frame, fg_color="transparent")
        ec_row.pack(fill="x", padx=12, pady=6)
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

    def _init_form_fields(self):
        """Membuat widget untuk masing-masing formulir kategori."""
        # 1. URL / Teks Bebas
        self.f_url = ctk.CTkFrame(self.form_container, fg_color="transparent")
        ctk.CTkLabel(self.f_url, text="Masukkan URL atau Teks Bebas:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(4, 2))
        self.txt_url = ctk.CTkTextbox(self.f_url, height=80)
        self.txt_url.insert("1.0", "https://github.com")
        self.txt_url.pack(fill="x", padx=10, pady=(0, 4))

        # 2. Wi-Fi
        self.f_wifi = ctk.CTkFrame(self.form_container, fg_color="transparent")
        ctk.CTkLabel(self.f_wifi, text="Nama Jaringan (SSID):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(4, 2))
        self.ent_wifi_ssid = ctk.CTkEntry(self.f_wifi, placeholder_text="Contoh: Kantor_WiFi")
        self.ent_wifi_ssid.insert(0, "WiFi-Kantor-Utama")
        self.ent_wifi_ssid.pack(fill="x", padx=10, pady=(0, 4))

        ctk.CTkLabel(self.f_wifi, text="Kata Sandi (Password):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(4, 2))
        self.ent_wifi_pwd = ctk.CTkEntry(self.f_wifi, placeholder_text="Password Wi-Fi")
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
        self.ent_vc_name = ctk.CTkEntry(self.f_vcard, placeholder_text="Contoh: Budi Santoso")
        self.ent_vc_name.insert(0, "Budi Santoso")
        self.ent_vc_name.pack(fill="x", padx=10, pady=(0, 4))

        ctk.CTkLabel(self.f_vcard, text="No. Telepon / Ponsel:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(2, 2))
        self.ent_vc_phone = ctk.CTkEntry(self.f_vcard, placeholder_text="Contoh: +628123456789")
        self.ent_vc_phone.insert(0, "+6281234567890")
        self.ent_vc_phone.pack(fill="x", padx=10, pady=(0, 4))

        ctk.CTkLabel(self.f_vcard, text="Alamat Email:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(2, 2))
        self.ent_vc_email = ctk.CTkEntry(self.f_vcard, placeholder_text="contoh@email.com")
        self.ent_vc_email.insert(0, "budi@perusahaan.co.id")
        self.ent_vc_email.pack(fill="x", padx=10, pady=(0, 4))

        ctk.CTkLabel(self.f_vcard, text="Organisasi / Perusahaan:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(2, 2))
        self.ent_vc_org = ctk.CTkEntry(self.f_vcard, placeholder_text="PT Solusi Teknologi")
        self.ent_vc_org.insert(0, "PT Solusi Teknologi Indonesia")
        self.ent_vc_org.pack(fill="x", padx=10, pady=(0, 4))

        ctk.CTkLabel(self.f_vcard, text="Website:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(2, 2))
        self.ent_vc_web = ctk.CTkEntry(self.f_vcard, placeholder_text="https://...")
        self.ent_vc_web.insert(0, "https://solusiteknologi.co.id")
        self.ent_vc_web.pack(fill="x", padx=10, pady=(0, 4))

        # 4. WhatsApp
        self.f_wa = ctk.CTkFrame(self.form_container, fg_color="transparent")
        ctk.CTkLabel(self.f_wa, text="Nomor WhatsApp (Kode Negara tanpa +):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(4, 2))
        self.ent_wa_phone = ctk.CTkEntry(self.f_wa, placeholder_text="Contoh: 6281234567890")
        self.ent_wa_phone.insert(0, "6281234567890")
        self.ent_wa_phone.pack(fill="x", padx=10, pady=(0, 4))

        ctk.CTkLabel(self.f_wa, text="Pesan Teks Otomatis:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(4, 2))
        self.txt_wa_msg = ctk.CTkTextbox(self.f_wa, height=70)
        self.txt_wa_msg.insert("1.0", "Halo kak, saya ingin informasi lebih lanjut mengenai produk ini.")
        self.txt_wa_msg.pack(fill="x", padx=10, pady=(0, 4))

        # 5. Email
        self.f_mail = ctk.CTkFrame(self.form_container, fg_color="transparent")
        ctk.CTkLabel(self.f_mail, text="Email Tujuan:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(4, 2))
        self.ent_mail_to = ctk.CTkEntry(self.f_mail, placeholder_text="tujuan@email.com")
        self.ent_mail_to.insert(0, "info@perusahaan.com")
        self.ent_mail_to.pack(fill="x", padx=10, pady=(0, 4))

        ctk.CTkLabel(self.f_mail, text="Subjek Email:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(4, 2))
        self.ent_mail_sub = ctk.CTkEntry(self.f_mail, placeholder_text="Subjek pesan")
        self.ent_mail_sub.insert(0, "Pengajuan Pertanyaan Layanan")
        self.ent_mail_sub.pack(fill="x", padx=10, pady=(0, 4))

        ctk.CTkLabel(self.f_mail, text="Isi Pesan:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(4, 2))
        self.txt_mail_body = ctk.CTkTextbox(self.f_mail, height=65)
        self.txt_mail_body.insert("1.0", "Halo tim support, saya ingin menanyakan terkait rincian layanan...")
        self.txt_mail_body.pack(fill="x", padx=10, pady=(0, 4))

    def _show_form_for_category(self, cat: str):
        """Menampilkan formulir yang sesuai dengan tab yang aktif."""
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
        """Menyusun panel pratinjau (preview) di sisi kanan beserta tombol aksi ekspor."""
        r = self.right_frame

        # Judul Preview
        p_title = ctk.CTkLabel(
            r,
            text="🖼️ PRATINJAU QR CODE",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#1e3a8a", "#60a5fa"),
        )
        p_title.pack(anchor="w", padx=20, pady=(15, 8))

        # Kontainer Gambar Preview (Card Putih/Gelap dengan shadow)
        self.preview_card = ctk.CTkFrame(
            r,
            corner_radius=12,
            fg_color=("gray85", "#18181b"),
            border_width=1,
            border_color=("gray75", "#27272a"),
        )
        self.preview_card.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # Label penampung gambar
        self.qr_preview_label = ctk.CTkLabel(self.preview_card, text="Memuat QR Code...")
        self.qr_preview_label.pack(expand=True, padx=15, pady=15)

        # Info Status QR (Ukuran & Tipe)
        self.info_status_lbl = ctk.CTkLabel(
            r,
            text="Ukuran: - • Siap Digunakan",
            font=ctk.CTkFont(size=11),
            text_color="gray50",
        )
        self.info_status_lbl.pack(pady=(0, 10))

        # Pilihan Resolusi Ekspor PNG
        res_row = ctk.CTkFrame(r, fg_color="transparent")
        res_row.pack(fill="x", padx=20, pady=(0, 10))

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

        # Tombol Aksi Utama
        action_box = ctk.CTkFrame(r, fg_color="transparent")
        action_box.pack(fill="x", padx=20, pady=(0, 15))

        # Tombol Refresh / Generate
        self.btn_refresh = ctk.CTkButton(
            action_box,
            text="⚡ Perbarui Tampilan QR",
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.generate_qr,
        )
        self.btn_refresh.pack(fill="x", pady=(0, 8))

        # Grid Tombol Simpan & Salin
        grid_btns = ctk.CTkFrame(action_box, fg_color="transparent")
        grid_btns.pack(fill="x")
        grid_btns.grid_columnconfigure((0, 1), weight=1)

        self.btn_save_png = ctk.CTkButton(
            grid_btns,
            text="💾 Simpan PNG",
            height=36,
            fg_color="#10b981",
            hover_color="#059669",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._save_as_png,
        )
        self.btn_save_png.grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=2)

        self.btn_save_svg = ctk.CTkButton(
            grid_btns,
            text="📐 Ekspor SVG (Vektor)",
            height=36,
            fg_color="#8b5cf6",
            hover_color="#7c3aed",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._save_as_svg,
        )
        self.btn_save_svg.grid(row=0, column=1, sticky="ew", padx=(4, 0), pady=2)

        self.btn_copy_clip = ctk.CTkButton(
            action_box,
            text="📋 Salin Gambar ke Clipboard",
            height=36,
            fg_color=("gray75", "#3f3f46"),
            hover_color=("gray65", "#52525b"),
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._copy_to_clipboard,
        )
        self.btn_copy_clip.pack(fill="x", pady=(6, 0))

        # Label Notifikasi / Toast Feedback
        self.toast_label = ctk.CTkLabel(
            r,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#10b981",
        )
        self.toast_label.pack(pady=(0, 10))

    def _show_toast(self, message: str, is_error: bool = False):
        """Menampilkan notifikasi feedback sementara."""
        self.toast_label.configure(
            text=message,
            text_color="#ef4444" if is_error else "#10b981",
        )
        self.after(3500, lambda: self.toast_label.configure(text=""))

    def _extract_payload_data(self) -> str:
        """Mengambil dan memformat data dari formulir sesuai kategori aktif."""
        cat = self.current_tab
        if "URL" in cat:
            return self.txt_url.get("1.0", "end-1c").strip()
        elif "Wi-Fi" in cat:
            ssid = self.ent_wifi_ssid.get()
            pwd = self.ent_wifi_pwd.get()
            auth = self.menu_wifi_auth.get()
            hidden = bool(self.chk_wifi_hidden.get())
            return QRFormatters.wifi(ssid, pwd, auth, hidden)
        elif "Kontak" in cat:
            name = self.ent_vc_name.get()
            phone = self.ent_vc_phone.get()
            email = self.ent_vc_email.get()
            org = self.ent_vc_org.get()
            web = self.ent_vc_web.get()
            return QRFormatters.vcard(name=name, phone=phone, email=email, org=org, website=web)
        elif "WhatsApp" in cat:
            phone = self.ent_wa_phone.get()
            msg = self.txt_wa_msg.get("1.0", "end-1c")
            return QRFormatters.whatsapp(phone, msg)
        elif "Email" in cat:
            to = self.ent_mail_to.get()
            sub = self.ent_mail_sub.get()
            body = self.txt_mail_body.get("1.0", "end-1c")
            return QRFormatters.email(to, sub, body)
        return ""

    def generate_qr(self):
        """Mengeksekusi generasi QR Code dan memperbarui tampilan pratinjau."""
        payload = self._extract_payload_data()
        if not payload:
            payload = "https://example.com"

        # Tentukan Error Correction
        ec_val = self.ec_menu.get()
        ec_code = "H"
        if "Q -" in ec_val:
            ec_code = "Q"
        elif "M -" in ec_val:
            ec_code = "M"
        elif "L -" in ec_val:
            ec_code = "L"

        # Background color
        bg = "transparent" if self.is_transparent_bg else self.back_color

        # Buat objek QREngine
        engine = QREngine(
            data=payload,
            error_correction=ec_code,
            fill_color=self.fill_color,
            back_color=bg,
            box_size=12,
            border=2,
        )

        # Setup logo jika ada
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

            # Tampilkan ke Preview Card (di-scale proporsional max 320x320)
            preview_max_dim = 300
            w, h = pil_img.size
            ratio = min(preview_max_dim / w, preview_max_dim / h)
            disp_w = int(w * ratio)
            disp_h = int(h * ratio)

            display_img = pil_img.resize((disp_w, disp_h), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=display_img, dark_image=display_img, size=(disp_w, disp_h))

            self.qr_preview_label.configure(image=ctk_img, text="")
            self.qr_preview_label.image = ctk_img

            self.info_status_lbl.configure(
                text=f"Resolusi Asli: {w} x {h} px • Koreksi: {ec_code} • Siap Diekspor"
            )
        except Exception as err:
            self._show_toast(f"Error: {str(err)}", is_error=True)

    def _choose_logo_file(self):
        """Dialog untuk memilih file logo gambar."""
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
            # Otomatis sarankan High error correction
            self.ec_menu.set("H - High (30% - Aman untuk Logo)")
            self.generate_qr()

    def _clear_logo(self):
        """Menghapus logo yang terpasang."""
        self.selected_logo_path = None
        self.logo_filename_lbl.configure(text="Belum ada logo yang dipilih", text_color="gray50")
        self.generate_qr()

    def _pick_fill_color(self):
        """Dialog pemilih warna untuk QR fill color."""
        color = colorchooser.askcolor(initialcolor=self.fill_color, title="Pilih Warna QR Code")
        if color and color[1]:
            self.fill_color = color[1].upper()
            self.qr_color_entry.delete(0, "end")
            self.qr_color_entry.insert(0, self.fill_color)
            self.qr_color_preview.configure(fg_color=self.fill_color, hover_color=self.fill_color)
            self.generate_qr()

    def _pick_back_color(self):
        """Dialog pemilih warna untuk background."""
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
        """Menerapkan preset warna QR."""
        self.fill_color = hex_color.upper()
        self.qr_color_entry.delete(0, "end")
        self.qr_color_entry.insert(0, self.fill_color)
        self.qr_color_preview.configure(fg_color=self.fill_color, hover_color=self.fill_color)
        self.generate_qr()

    def _on_hex_entry_change(self, mode: str):
        """Validasi jika pengguna mengetik kode warna heksadesimal langsung."""
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
        """Toggle opsi background transparan."""
        self.is_transparent_bg = bool(self.transparent_check.get())
        self.generate_qr()

    def _get_export_dimension(self) -> int:
        """Mengambil target dimensi piksel ekspor dari menu dropdown."""
        res_str = self.export_res_menu.get()
        if "2000" in res_str:
            return 2000
        elif "1200" in res_str:
            return 1200
        elif "400" in res_str:
            return 400
        return 800

    def _save_as_png(self):
        """Menyimpan file hasil QR Code ke format PNG dengan resolusi terpilih."""
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
                self._show_toast(f"✅ Tersimpan ke: {os.path.basename(filepath)}")
            except Exception as e:
                messagebox.showerror("Gagal Menyimpan", f"Terjadi kesalahan saat menyimpan PNG:\n{str(e)}")

    def _save_as_svg(self):
        """Menyimpan file hasil QR Code ke format SVG Vektor."""
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
                self._show_toast(f"✅ Vektor SVG tersimpan ke: {os.path.basename(filepath)}")
            except Exception as e:
                messagebox.showerror("Gagal Menyimpan", f"Terjadi kesalahan saat menyimpan SVG:\n{str(e)}")

    def _copy_to_clipboard(self):
        """Menyalin gambar QR Code saat ini langsung ke clipboard Windows."""
        if not self.current_pil_image:
            self.generate_qr()

        if self.current_pil_image:
            success, msg = copy_image_to_clipboard(self.current_pil_image)
            if success:
                self._show_toast("✅ Gambar berhasil disalin ke Clipboard!")
            else:
                self._show_toast(f"❌ {msg}", is_error=True)
