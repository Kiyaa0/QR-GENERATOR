/* 
 * QR Code generator library (C++)
 * 
 * Copyright (c) Project Nayuki. (MIT License)
 * https://www.nayuki.io/page/qr-code-generator-library
 */

#ifndef QRCODE_HPP
#define QRCODE_HPP

#include <cstdint>
#include <string>
#include <vector>

namespace qrcodegen {

class QrSegment final {
public:
    enum class Mode {
        NUMERIC, ALPHANUMERIC, BYTE, KANJI, ECI
    };

    static QrSegment makeBytes(const std::vector<uint8_t> &data);
    static QrSegment makeNumeric(const char *digits);
    static QrSegment makeAlphanumeric(const char *text);
    static std::vector<QrSegment> makeSegments(const char *text);

    Mode mode;
    int numChars;
    std::vector<bool> data;

    QrSegment(Mode md, int numCh, const std::vector<bool> &dt);
    QrSegment(Mode md, int numCh, std::vector<bool> &&dt);

    static int getTotalBits(const std::vector<QrSegment> &segs, int version);
};


class QrCode final {
public:
    enum class Ecc {
        LOW = 0,
        MEDIUM,
        QUARTILE,
        HIGH
    };

    static constexpr int MIN_VERSION = 1;
    static constexpr int MAX_VERSION = 40;

    static QrCode encodeText(const char *text, Ecc ecl);
    static QrCode encodeBinary(const std::vector<uint8_t> &data, Ecc ecl);
    static QrCode encodeSegments(const std::vector<QrSegment> &segs, Ecc ecl,
        int minVersion = 1, int maxVersion = 40, int mask = -1, bool boostEcl = true);

    int version;
    int size;
    Ecc errorCorrectionLevel;
    int mask;

    bool getModule(int x, int y) const;

    QrCode(int ver, Ecc ecl, const std::vector<uint8_t> &dataCodewords, int msk);

private:
    std::vector<bool> modules;
    std::vector<bool> isFunction;

    void drawFunctionPatterns();
    void drawFormatBits(int msk);
    void drawVersion();
    void drawFinderPattern(int x, int y);
    void drawAlignmentPattern(int x, int y);
    void setFunctionModule(int x, int y, bool isBlack);
    bool module(int x, int y) const;

    void drawCodewords(const std::vector<uint8_t> &data);
    static std::vector<uint8_t> addEccAndInterleave(const std::vector<uint8_t> &data, int ver, Ecc ecl);
    static std::vector<uint8_t> reedSolomonComputeDivisor(int degree);
    static std::vector<uint8_t> reedSolomonComputeRemainder(const std::vector<uint8_t> &data, const std::vector<uint8_t> &divisor);
    static uint8_t reedSolomonMultiply(uint8_t x, uint8_t y);

    void applyMask(int msk);
    long getPenaltyScore() const;
    std::vector<int> getAlignmentPatternPositions() const;

    static int getNumDataCodewords(int ver, Ecc ecl);
    static int getNumRawDataModules(int ver);

    static const int8_t ECC_CODEWORDS_PER_BLOCK[4][41];
    static const int8_t NUM_ERROR_CORRECTION_BLOCKS[4][41];
};

} // namespace qrcodegen

#endif // QRCODE_HPP
