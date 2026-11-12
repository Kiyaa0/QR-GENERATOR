# ⚡ QR Studio Pro - Desktop QR Code Generator

Aplikasi Desktop modern berbasis Python untuk membuat dan mengkustomisasi QR Code berkualitas tinggi dengan antarmuka grafis (GUI) yang elegan.

---

## ✨ Fitur Unggulan

1. **Multi-Kategori Konten**:
   - 🌐 **URL & Teks Bebas**: Tautan website, catatan, atau teks apa pun.
   - 📶 **Wi-Fi Otomatis**: Buat QR untuk Wi-Fi (SSID, Password, WPA/WEP/Open, Hidden SSID). Tamu cukup scan untuk langsung terhubung tanpa ketik password!
   - 👤 **Kartu Nama Digital (vCard 3.0)**: Nama, nomor HP, email, perusahaan/organisasi, jabatan, hingga link website.
   - 💬 **WhatsApp Direct**: Nomor tujuan internasional dan template pesan otomatis (`wa.me`).
   - ✉️ **Email (Mailto)**: Email penerima, subjek, dan isi pesan otomatis.

2. **Kustomisasi Desain & Warna**:
   - Pilihan warna modul QR kustom (dengan color picker & preset warna modern: Hitam, Navy, Zamrud, Indigo, Crimson).
   - Pilihan warna background kustom atau opsi **Background Transparan**.
   - Input manual kode HEX `#RRGGBB`.

3. **Logo di Tengah QR (Center Logo & Badge)**:
   - Unggah gambar logo Anda sendiri (PNG, JPG, WebP, ICO).
   - Pilihan bentuk pelindung logo (*Rounded badge*, *Circle*, *Square*, atau *No background*) agar QR Code tetap **100% mudah discan**.
   - Slider proporsi ukuran logo yang aman.

4. **Kualitas & Ekspor Siap Cetak**:
   - **PNG Resolusi Tinggi**: Pilihan dari 400px hingga 2000px Ultra HD.
   - **SVG Vektor**: File vektor murni dengan ukuran tak terhingga (*lossless*), siap dicetak pada banner, merchandise, brosur, atau sablon.
   - **📋 Salin ke Clipboard**: Salin gambar QR langsung ke clipboard tanpa perlu simpan file terlebih dahulu.
   - **Mode Gelap / Terang**: Dukungan Dark Mode dan Light Mode bawaan.

---

## 🚀 Cara Menjalankan Aplikasi

### Opsi 1: Klik Ganda (Paling Mudah)
Cukup klik ganda file **`run.bat`** di folder proyek ini. Aplikasi akan langsung terbuka tanpa jendela terminal hitam.

### Opsi 2: Melalui Terminal / PowerShell
```powershell
# Aktifkan virtual environment
.\venv\Scripts\activate

# Jalankan aplikasi
python main.py
```

---

## 📦 Struktur Proyek

```
QR PYTHON/
├── core/
│   ├── __init__.py
│   ├── qr_engine.py      # Engine QR, parser format data, logo merger & SVG generator
│   └── clipboard.py      # Helper integrasi clipboard Windows
├── ui/
│   ├── __init__.py
│   └── main_window.py    # Tampilan GUI CustomTkinter modern
├── venv/                 # Virtual environment terisolasi
├── main.py               # Entry point aplikasi
├── run.bat               # File launcher double-click
├── requirements.txt      # Daftar dependency
└── README.md             # Dokumentasi proyek
```

---

## 🛠️ (Opsional) Mengubah Aplikasi Menjadi File `.exe` Mandiri

Jika ingin membagikan aplikasi ini ke teman atau komputer lain tanpa perlu install Python:

1. Pastikan virtual environment aktif:
   ```powershell
   .\venv\Scripts\activate
   ```
2. Pasang PyInstaller:
   ```powershell
   pip install pyinstaller
   ```
3. Lakukan build menjadi 1 file `.exe`:
   ```powershell
   pyinstaller --noconsole --onefile --name "QR_Studio_Pro" --collect-all customtkinter main.py
   ```
4. File `.exe` siap pakai akan berada di folder `dist/QR_Studio_Pro.exe`.
