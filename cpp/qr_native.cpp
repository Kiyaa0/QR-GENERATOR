/*
 * High-Performance C++ QR Native Core Engine
 * Dual-Mode: Can be used as a Windows DLL (ctypes) or standalone High-Speed CLI (.exe)
 */

#include "QrCode.hpp"
#include "bmp_writer.hpp"
#include "crypto.hpp"

#include <iostream>
#include <string>
#include <vector>
#include <thread>
#include <chrono>
#include <sstream>
#include <iomanip>
#include <filesystem>
#include <cstring>

namespace fs = std::filesystem;
using qrcodegen::QrCode;

// Helper to convert hex color string like "#1E3A8A" or "1E3A8A" to RGB
static void parse_hex_color(const char* hex, uint8_t& r, uint8_t& g, uint8_t& b, uint8_t def_r, uint8_t def_g, uint8_t def_b) {
    if (!hex) { r = def_r; g = def_g; b = def_b; return; }
    std::string s(hex);
    if (!s.empty() && s[0] == '#') s = s.substr(1);
    if (s.size() == 6) {
        try {
            r = static_cast<uint8_t>(std::stoul(s.substr(0, 2), nullptr, 16));
            g = static_cast<uint8_t>(std::stoul(s.substr(2, 2), nullptr, 16));
            b = static_cast<uint8_t>(std::stoul(s.substr(4, 2), nullptr, 16));
            return;
        } catch (...) {}
    }
    r = def_r; g = def_g; b = def_b;
}

// Generate RGB pixel buffer for a QR Code
static bool generate_qr_rgb(const QrCode& qr, int scale, int border, 
                            uint8_t fg_r, uint8_t fg_g, uint8_t fg_b,
                            uint8_t bg_r, uint8_t bg_g, uint8_t bg_b,
                            int& out_dim, std::vector<uint8_t>& out_rgb) {
    int qr_size = qr.size;
    out_dim = (qr_size + border * 2) * scale;
    out_rgb.resize(out_dim * out_dim * 3);

    for (int y = 0; y < out_dim; ++y) {
        int qr_y = (y / scale) - border;
        for (int x = 0; x < out_dim; ++x) {
            int qr_x = (x / scale) - border;
            bool is_black = false;
            if (qr_x >= 0 && qr_x < qr_size && qr_y >= 0 && qr_y < qr_size) {
                is_black = qr.getModule(qr_x, qr_y);
            }
            int idx = (y * out_dim + x) * 3;
            if (is_black) {
                out_rgb[idx + 0] = fg_r;
                out_rgb[idx + 1] = fg_g;
                out_rgb[idx + 2] = fg_b;
            } else {
                out_rgb[idx + 0] = bg_r;
                out_rgb[idx + 1] = bg_g;
                out_rgb[idx + 2] = bg_b;
            }
        }
    }
    return true;
}

extern "C" {

// 1. Enkripsi Tiket / Data dengan C++ HMAC & Stream Cipher
__declspec(dllexport) int cpp_encrypt_ticket(const char* plaintext, const char* secret_key, char* out_buf, int max_len) {
    if (!plaintext || !secret_key || !out_buf || max_len <= 0) return -1;
    try {
        std::string enc = Security::SecureTicket::encrypt(plaintext, secret_key);
        if (enc.size() >= static_cast<size_t>(max_len)) return -2;
        std::strncpy(out_buf, enc.c_str(), max_len);
        out_buf[max_len - 1] = '\0';
        return 0;
    } catch (...) {
        return -3;
    }
}

// 2. Dekripsi Tiket & Validasi Keaslian (0 = Asli, 1 = Palsu/Kunci Salah, 2 = Format Salah)
__declspec(dllexport) int cpp_decrypt_ticket(const char* cipher_token, const char* secret_key, char* out_buf, int max_len) {
    if (!cipher_token || !secret_key || !out_buf || max_len <= 0) return -1;
    try {
        std::string plain;
        int status = Security::SecureTicket::decrypt(cipher_token, secret_key, plain);
        if (status == 0) {
            if (plain.size() >= static_cast<size_t>(max_len)) return -2;
            std::strncpy(out_buf, plain.c_str(), max_len);
            out_buf[max_len - 1] = '\0';
        }
        return status;
    } catch (...) {
        return -3;
    }
}

// 3. Generate Single QR Code ke BMP File Super Cepat
__declspec(dllexport) int cpp_generate_single_bmp(const char* text, const char* filepath, int scale, int border,
                                                  const char* fg_hex, const char* bg_hex) {
    if (!text || !filepath) return -1;
    try {
        QrCode qr = QrCode::encodeText(text, QrCode::Ecc::MEDIUM);
        scale = std::max(1, scale);
        border = std::max(0, border);

        uint8_t fg_r, fg_g, fg_b, bg_r, bg_g, bg_b;
        parse_hex_color(fg_hex, fg_r, fg_g, fg_b, 0, 0, 0);
        parse_hex_color(bg_hex, bg_r, bg_g, bg_b, 255, 255, 255);

        int dim = 0;
        std::vector<uint8_t> rgb;
        generate_qr_rgb(qr, scale, border, fg_r, fg_g, fg_b, bg_r, bg_g, bg_b, dim, rgb);
        return ImageIO::write_bmp(filepath, dim, dim, rgb) ? 0 : -2;
    } catch (...) {
        return -3;
    }
}

// 4. Multi-Threaded Batch Generator untuk Puluhan Ribu QR Code
__declspec(dllexport) double cpp_batch_generate_bmps(
    const char* prefix,
    int start_index,
    int count,
    const char* out_dir,
    int scale,
    int border,
    const char* secret_key,
    int num_threads
) {
    if (count <= 0 || !out_dir) return -1.0;
    auto start_time = std::chrono::high_resolution_clock::now();

    try {
        fs::path out_path(out_dir);
        if (!fs::exists(out_path)) {
            fs::create_directories(out_path);
        }

        if (num_threads <= 0) {
            num_threads = std::max(1u, std::thread::hardware_concurrency());
        }

        std::string pref = prefix ? prefix : "TKT";
        std::string key = secret_key ? secret_key : "";
        bool encrypt_mode = !key.empty();

        scale = std::max(1, scale);
        border = std::max(0, border);

        auto worker = [&](int t_id, int start_k, int end_k) {
            (void)t_id;
            for (int k = start_k; k < end_k; ++k) {
                std::ostringstream ss;
                ss << pref << "-" << std::setw(6) << std::setfill('0') << k;
                std::string ticket_id = ss.str();

                std::string payload = ticket_id;
                if (encrypt_mode) {
                    payload = Security::SecureTicket::encrypt(ticket_id, key);
                }

                QrCode qr = QrCode::encodeText(payload.c_str(), QrCode::Ecc::MEDIUM);
                int dim = 0;
                std::vector<uint8_t> rgb;
                generate_qr_rgb(qr, scale, border, 0, 0, 0, 255, 255, 255, dim, rgb);

                std::string filename = (out_path / (ticket_id + ".bmp")).string();
                ImageIO::write_bmp(filename, dim, dim, rgb);
            }
        };

        std::vector<std::thread> pool;
        int chunk_size = (count + num_threads - 1) / num_threads;

        for (int t = 0; t < num_threads; ++t) {
            int s_idx = start_index + t * chunk_size;
            int e_idx = std::min(start_index + count, s_idx + chunk_size);
            if (s_idx < e_idx) {
                pool.emplace_back(worker, t, s_idx, e_idx);
            }
        }

        for (auto& th : pool) {
            if (th.joinable()) th.join();
        }

        auto end_time = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double, std::milli> elapsed = end_time - start_time;
        return elapsed.count();
    } catch (...) {
        return -2.0;
    }
}

// 5. Benchmark Murni: Kecepatan Generasi Matriks QR per Detik
__declspec(dllexport) double cpp_benchmark_matrix(int count) {
    if (count <= 0) return 0.0;
    auto start = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < count; ++i) {
        std::string data = "BENCHMARK-QR-" + std::to_string(i);
        QrCode qr = QrCode::encodeText(data.c_str(), QrCode::Ecc::MEDIUM);
        volatile int s = qr.size;
        (void)s;
    }
    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double, std::milli> ms = end - start;
    return ms.count();
}

} // extern "C"

// CLI Main Entry Point
int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cout << "QR Native C++ Engine v2.0 (High Performance & Security)" << std::endl;
        std::cout << "Usage: qr_native.exe [--bench <count>] [--encrypt <text> <key>] [--decrypt <token> <key>] [--batch <prefix> <start> <count> <out_dir> <scale> <border> <key>]" << std::endl;
        return 0;
    }

    std::string cmd = argv[1];

    if (cmd == "--bench") {
        int count = argc >= 3 ? std::stoi(argv[2]) : 5000;
        double ms = cpp_benchmark_matrix(count);
        double qps = (count / (ms / 1000.0));
        std::cout << "BENCH_RESULT:" << ms << ":" << static_cast<long>(qps) << std::endl;
        return 0;
    }

    if (cmd == "--encrypt" && argc >= 4) {
        std::string text = argv[2];
        std::string key = argv[3];
        std::string enc = Security::SecureTicket::encrypt(text, key);
        std::cout << "ENCRYPT_RESULT:" << enc << std::endl;
        return 0;
    }

    if (cmd == "--decrypt" && argc >= 4) {
        std::string token = argv[2];
        std::string key = argv[3];
        std::string plain;
        int status = Security::SecureTicket::decrypt(token, key, plain);
        std::cout << "DECRYPT_RESULT:" << status << ":" << plain << std::endl;
        return status;
    }

    if (cmd == "--batch" && argc >= 6) {
        std::string prefix = argv[2];
        int start = std::stoi(argv[3]);
        int count = std::stoi(argv[4]);
        std::string out_dir = argv[5];
        int scale = argc >= 7 ? std::stoi(argv[6]) : 4;
        int border = argc >= 8 ? std::stoi(argv[7]) : 2;
        std::string key = argc >= 9 ? argv[8] : "";
        int threads = argc >= 10 ? std::stoi(argv[9]) : 0;

        double ms = cpp_batch_generate_bmps(prefix.c_str(), start, count, out_dir.c_str(), scale, border, key.c_str(), threads);
        std::cout << "BATCH_RESULT:" << ms << ":" << count << std::endl;
        return 0;
    }

    if (cmd == "--generate" && argc >= 4) {
        std::string text = argv[2];
        std::string out_file = argv[3];
        int scale = argc >= 5 ? std::stoi(argv[4]) : 8;
        int border = argc >= 6 ? std::stoi(argv[5]) : 2;
        const char* fg = argc >= 7 ? argv[6] : "#000000";
        const char* bg = argc >= 8 ? argv[7] : "#FFFFFF";

        int res = cpp_generate_single_bmp(text.c_str(), out_file.c_str(), scale, border, fg, bg);
        std::cout << "GENERATE_RESULT:" << (res == 0 ? "OK" : "ERROR") << std::endl;
        return res;
    }

    std::cerr << "Unknown command: " << cmd << std::endl;
    return 1;
}
