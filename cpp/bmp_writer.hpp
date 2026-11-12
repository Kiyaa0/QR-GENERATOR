#ifndef BMP_WRITER_HPP
#define BMP_WRITER_HPP

#include <vector>
#include <string>
#include <fstream>
#include <cstdint>

#pragma pack(push, 1)
struct BMPHeader {
    uint16_t file_type{0x4D42}; // 'BM'
    uint32_t file_size{0};
    uint16_t reserved1{0};
    uint16_t reserved2{0};
    uint32_t offset_data{54};   // 14 + 40
};

struct BMPInfoHeader {
    uint32_t size{40};
    int32_t width{0};
    int32_t height{0};
    uint16_t planes{1};
    uint16_t bit_count{24};     // 24-bit RGB
    uint32_t compression{0};    // BI_RGB (uncompressed)
    uint32_t size_image{0};
    int32_t x_pixels_per_meter{2835}; // ~72 DPI
    int32_t y_pixels_per_meter{2835};
    uint32_t colors_used{0};
    uint32_t colors_important{0};
};
#pragma pack(pop)

namespace ImageIO {

inline bool write_bmp(const std::string& filename, int width, int height, const std::vector<uint8_t>& rgb_data) {
    std::ofstream out(filename, std::ios::binary);
    if (!out.is_open()) return false;

    // Row size must be a multiple of 4 bytes
    int row_padding = (4 - (width * 3) % 4) % 4;
    uint32_t data_size = (width * 3 + row_padding) * height;

    BMPHeader header;
    header.file_size = 54 + data_size;

    BMPInfoHeader info;
    info.width = width;
    info.height = height; // Positive = bottom-up, negative = top-down
    info.size_image = data_size;

    out.write(reinterpret_cast<const char*>(&header), sizeof(header));
    out.write(reinterpret_cast<const char*>(&info), sizeof(info));

    std::vector<uint8_t> padding(row_padding, 0);

    // Write scanlines from bottom to top (standard BMP order)
    for (int y = height - 1; y >= 0; --y) {
        for (int x = 0; x < width; ++x) {
            int src_idx = (y * width + x) * 3;
            // BMP expects BGR order
            uint8_t b = rgb_data[src_idx + 2];
            uint8_t g = rgb_data[src_idx + 1];
            uint8_t r = rgb_data[src_idx + 0];
            out.put(b);
            out.put(g);
            out.put(r);
        }
        if (row_padding > 0) {
            out.write(reinterpret_cast<const char*>(padding.data()), row_padding);
        }
    }
    return true;
}

} // namespace ImageIO

#endif // BMP_WRITER_HPP
