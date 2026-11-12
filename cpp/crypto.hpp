#ifndef CRYPTO_HPP
#define CRYPTO_HPP

#include "sha256.hpp"
#include <string>
#include <vector>
#include <random>
#include <chrono>
#include <stdexcept>

namespace Security {

class Base64 {
private:
    static const std::string chars;

public:
    static std::string encode(const uint8_t* data, size_t len) {
        std::string ret;
        int i = 0, j = 0;
        uint8_t char_array_3[3];
        uint8_t char_array_4[4];

        while (len--) {
            char_array_3[i++] = *(data++);
            if (i == 3) {
                char_array_4[0] = (char_array_3[0] & 0xfc) >> 2;
                char_array_4[1] = ((char_array_3[0] & 0x03) << 4) + ((char_array_3[1] & 0xf0) >> 4);
                char_array_4[2] = ((char_array_3[1] & 0x0f) << 2) + ((char_array_3[2] & 0xc0) >> 6);
                char_array_4[3] = char_array_3[2] & 0x3f;

                for (i = 0; i < 4; i++) ret += chars[char_array_4[i]];
                i = 0;
            }
        }

        if (i) {
            for (j = i; j < 3; j++) char_array_3[j] = '\0';
            char_array_4[0] = (char_array_3[0] & 0xfc) >> 2;
            char_array_4[1] = ((char_array_3[0] & 0x03) << 4) + ((char_array_3[1] & 0xf0) >> 4);
            char_array_4[2] = ((char_array_3[1] & 0x0f) << 2) + ((char_array_3[2] & 0xc0) >> 6);

            for (j = 0; j < i + 1; j++) ret += chars[char_array_4[j]];
            while ((i++ < 3)) ret += '=';
        }
        return ret;
    }

    static std::vector<uint8_t> decode(const std::string& encoded_string) {
        size_t in_len = encoded_string.size();
        int i = 0, j = 0, in_ = 0;
        uint8_t char_array_4[4], char_array_3[3];
        std::vector<uint8_t> ret;

        while (in_len-- && (encoded_string[in_] != '=') && (isalnum(encoded_string[in_]) || (encoded_string[in_] == '+') || (encoded_string[in_] == '/'))) {
            char_array_4[i++] = encoded_string[in_]; in_++;
            if (i == 4) {
                for (i = 0; i < 4; i++)
                    char_array_4[i] = static_cast<uint8_t>(chars.find(char_array_4[i]));

                char_array_3[0] = (char_array_4[0] << 2) + ((char_array_4[1] & 0x30) >> 4);
                char_array_3[1] = ((char_array_4[1] & 0xf) << 4) + ((char_array_4[2] & 0x3c) >> 2);
                char_array_3[2] = ((char_array_4[2] & 0x3) << 6) + char_array_4[3];

                for (i = 0; i < 3; i++) ret.push_back(char_array_3[i]);
                i = 0;
            }
        }

        if (i) {
            for (j = 0; j < i; j++)
                char_array_4[j] = static_cast<uint8_t>(chars.find(char_array_4[j]));

            char_array_3[0] = (char_array_4[0] << 2) + ((char_array_4[1] & 0x30) >> 4);
            char_array_3[1] = ((char_array_4[1] & 0xf) << 4) + ((char_array_4[2] & 0x3c) >> 2);

            for (j = 0; j < i - 1; j++) ret.push_back(char_array_3[j]);
        }
        return ret;
    }
};

inline const std::string Base64::chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";


class SecureTicket {
public:
    static const std::string PREFIX;

    static std::string encrypt(const std::string& plaintext, const std::string& secret_key) {
        if (plaintext.empty() || secret_key.empty()) return "";

        // 1. Generate 8-byte nonce
        uint8_t nonce[8];
        uint64_t seed = std::chrono::high_resolution_clock::now().time_since_epoch().count();
        std::mt19937_64 rng(seed);
        for (int i = 0; i < 8; ++i) nonce[i] = static_cast<uint8_t>(rng() & 0xFF);

        // 2. Derive keystream and encrypt with XOR stream cipher
        std::vector<uint8_t> cipher(plaintext.size());
        size_t block_count = (plaintext.size() + 31) / 32;

        for (size_t b = 0; b < block_count; ++b) {
            std::string block_input = secret_key + std::string(reinterpret_cast<char*>(nonce), 8) + std::to_string(b);
            auto kblock = SHA256::hash(reinterpret_cast<const uint8_t*>(block_input.data()), block_input.size());

            for (size_t i = 0; i < 32 && (b * 32 + i) < plaintext.size(); ++i) {
                cipher[b * 32 + i] = static_cast<uint8_t>(plaintext[b * 32 + i]) ^ kblock[i];
            }
        }

        // 3. Compute 16-byte HMAC authentication tag over (nonce + cipher)
        std::vector<uint8_t> auth_data;
        auth_data.insert(auth_data.end(), nonce, nonce + 8);
        auth_data.insert(auth_data.end(), cipher.begin(), cipher.end());

        auto full_tag = SHA256::hmac(
            reinterpret_cast<const uint8_t*>(secret_key.data()), secret_key.size(),
            auth_data.data(), auth_data.size()
        );

        // 4. Pack: [Nonce (8B)] + [Tag (16B)] + [Ciphertext (N bytes)]
        std::vector<uint8_t> packed;
        packed.insert(packed.end(), nonce, nonce + 8);
        packed.insert(packed.end(), full_tag.begin(), full_tag.begin() + 16);
        packed.insert(packed.end(), cipher.begin(), cipher.end());

        // 5. Serialize to Base64
        return PREFIX + Base64::encode(packed.data(), packed.size());
    }

    // Status: 0 = OK, 1 = Fake/Tampered Signature, 2 = Format Error, 3 = Empty Key
    static int decrypt(const std::string& token, const std::string& secret_key, std::string& out_plaintext) {
        out_plaintext.clear();
        if (secret_key.empty()) return 3;
        if (token.rfind(PREFIX, 0) != 0) return 2; // Invalid prefix

        std::string b64_data = token.substr(PREFIX.size());
        auto raw = Base64::decode(b64_data);
        if (raw.size() < 24) return 2; // Must have at least 8B nonce + 16B tag

        uint8_t nonce[8];
        memcpy(nonce, raw.data(), 8);

        uint8_t received_tag[16];
        memcpy(received_tag, raw.data() + 8, 16);

        std::vector<uint8_t> cipher(raw.begin() + 24, raw.end());

        // Verify HMAC
        std::vector<uint8_t> auth_data;
        auth_data.insert(auth_data.end(), nonce, nonce + 8);
        auth_data.insert(auth_data.end(), cipher.begin(), cipher.end());

        auto full_tag = SHA256::hmac(
            reinterpret_cast<const uint8_t*>(secret_key.data()), secret_key.size(),
            auth_data.data(), auth_data.size()
        );

        // Constant-time tag check against timing attacks
        int diff = 0;
        for (int i = 0; i < 16; ++i) {
            diff |= (received_tag[i] ^ full_tag[i]);
        }
        if (diff != 0) {
            return 1; // Fake / Counterfeit / Invalid Key!
        }

        // Decrypt with stream cipher
        std::string plain(cipher.size(), '\0');
        size_t block_count = (cipher.size() + 31) / 32;

        for (size_t b = 0; b < block_count; ++b) {
            std::string block_input = secret_key + std::string(reinterpret_cast<char*>(nonce), 8) + std::to_string(b);
            auto kblock = SHA256::hash(reinterpret_cast<const uint8_t*>(block_input.data()), block_input.size());

            for (size_t i = 0; i < 32 && (b * 32 + i) < cipher.size(); ++i) {
                plain[b * 32 + i] = static_cast<char>(cipher[b * 32 + i] ^ kblock[i]);
            }
        }

        out_plaintext = plain;
        return 0; // Success
    }
};

inline const std::string SecureTicket::PREFIX = "SECQR1:";

} // namespace Security

#endif // CRYPTO_HPP
