# QR Studio Pro - High-Performance QR Suite (Python + C++)

Aplikasi Desktop modern berbasis Python dengan integrasi C++ Native Engine untuk pembuatan QR Code, QRIS Pembayaran Nasional (Statis & Dinamis dengan Custom Gambar), pencetakan massal (batch generation), pengamanan enkripsi tiket (anti-pemalsuan), serta scanner webcam real-time.

---

## Fitur Unggulan

### 1. QRIS Pembayaran Nasional & Custom Gambar
- Standar EMVCo / Bank Indonesia & ASPI dengan perhitungan checksum CRC16-CCITT otomatis.
- Mode Buat QRIS Baru: Memasukkan Nama Toko / Merchant, NMID, Kota, Kode Pos, dan Nominal Pembayaran (Rp).
- Mode Ubah QRIS Statis Jadi Dinamis: Mengubah QRIS yang sudah ada (dari BCA, GoPay, OVO, Dana, ShopeePay, Mandiri, dll.) dengan menyuntikkan nominal bayar tertentu.
- Kustomisasi Gambar Logo:
  - Emblem resmi QRIS otomatis di tengah QR Code dengan badge pelindung.
  - Opsi unggah Logo Toko / Usaha kustom sendiri.
- Pembuat Poster Standee Meja QRIS Lengkap Siap Cetak:
  - Header resmi merah QRIS & Bank Indonesia.
  - Nama Merchant & NMID toko.
  - Frame QR Code beresolusi tinggi dengan logo kustom.
  - Highlight pill nominal pembayaran (Rp) atau petunjuk bayar.
  - Footer daftar mitra e-wallet & mobile banking (BCA, Mandiri, BNI, BRI, GoPay, OVO, Dana, ShopeePay, LinkAja).
  - Tombol simpan Poster Standee resolusi tinggi (740 x 1060 px).

### 2. Keamanan & Enkripsi Tiket C++ (Anti-Pemalsuan)
- Algoritma autentikasi kriptografi tingkat rendah HMAC-SHA256 + Stream Cipher + Nonce (cpp/crypto.hpp & core/security.py).
- Mencegah pemalsuan tiket: Jika seseorang mencoba mengedit payload QR Code, signature digital C++ otomatis gagal diverifikasi dan menampilkan peringatan "[PERINGATAN] TIKET PALSU ATAU KUNCI SALAH!".
- Hanya tiket yang dibuat dan diverifikasi dengan Kunci Rahasia (Secret Key) yang sama yang akan menampilkan status "[VALID] TIKET ASLI TERVERIFIKASI".

### 3. High-Performance Batch Generator (Pencetakan Massal)
- Mencetak ratusan hingga puluhan ribu QR Code dalam hitungan detik menggunakan multi-threading C++.
- Otomatis membuat berkas rekap manifest_tiket.csv berisi daftar ID Tiket, QR Payload terenkripsi, nama file gambar, dan timestamp pembuatan.
- Dilengkapi fitur Uji Benchmark Speed untuk mengukur kecepatan pemrosesan QR Code per detik.

### 4. Fast Scanner Real-Time (Webcam OpenCV & File)
- Pemindaian langsung menggunakan kamera webcam laptop/PC (OpenCV cv2.QRCodeDetector).
- Deteksi real-time dengan penanda kotak hijau/merah di sekeliling QR Code.
- Verifikasi instan: otomatis mendekripsi dan mengecek keaslian token tiket atau mengenali format QRIS saat tertangkap kamera.
- Opsi scan langsung dari berkas gambar lokal (PNG, JPG, BMP).

---

## Cara Menjalankan Aplikasi

### Opsi 1: Klik Ganda
Cukup klik ganda berkas run.bat di folder proyek ini.

### Opsi 2: Melalui Terminal / PowerShell
```powershell
# Aktifkan virtual environment
.\venv\Scripts\activate

# Jalankan aplikasi
python main.py
```

---

## Meng-compile C++ Native Engine (Opsional)

Kode sumber C++ berada di folder cpp/. Jika Anda ingin memodifikasi atau meng-compile ulang berkas biner C++ (qr_native.dll & qr_native.exe), jalankan:

```powershell
.\cpp\build_cpp.bat
```
Atau secara manual menggunakan MinGW GCC:
```powershell
g++ -O3 -std=c++17 -static -o core/qr_native.exe cpp/qr_native.cpp cpp/QrCode.cpp
g++ -O3 -shared -std=c++17 -static -o core/qr_native.dll cpp/qr_native.cpp cpp/QrCode.cpp
```

---

## Struktur Proyek

```
QR PYTHON/
|-- cpp/                      # Sumber C++ Native
|   |-- QrCode.hpp & .cpp     # Engine matriks QR C++ (Nayuki)
|   |-- sha256.hpp            # Implementasi SHA-256 & HMAC C++
|   |-- crypto.hpp            # Protokol enkripsi tiket terotentikasi
|   |-- bmp_writer.hpp        # Ultra-fast BMP image writer
|   |-- qr_native.cpp         # Main C++ engine & C-export DLL
|   `-- build_cpp.bat         # Script kompilasi g++
|-- core/
|   |-- qris.py               # Engine QRIS Bank Indonesia & Generator Poster
|   |-- qr_engine.py          # Engine utama QR Python & SVG
|   |-- security.py           # Protokol kriptografi interoperabel Python
|   |-- cpp_bridge.py         # Jembatan penghubung C++ dan Python
|   |-- batch_engine.py       # Mesin multi-threaded batch generator
|   |-- scanner.py            # Mesin scanner OpenCV webcam & file
|   `-- clipboard.py          # Helper salin ke clipboard Windows
|-- ui/
|   |-- __init__.py
|   `-- main_window.py        # Antarmuka CustomTkinter (3 Mode)
|-- main.py                   # Entry point aplikasi
|-- run.bat                   # Launcher double-click
|-- requirements.txt          # Daftar dependensi pip
`-- README.md                 # Dokumentasi proyek
```
