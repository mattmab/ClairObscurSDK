#pragma once
#include <cstdint>
#include <cstring>
#include <cmath>
#include <limits>

// Value contract derived from this build's reflected fields and UMG thunks.
// Invocation requires the separate v11 capability and native schema validator.
enum class PodValueKind : uint32_t { Vector2D=1, LinearColor, Margin, Anchors };
inline uint32_t pod_value_width(PodValueKind kind) {
    switch (kind) {
        case PodValueKind::Vector2D: case PodValueKind::LinearColor: case PodValueKind::Margin: return 16;
        case PodValueKind::Anchors: return 32;
        default: return 0;
    }
}
inline bool valid_pod_value(PodValueKind kind, const uint8_t* bytes, uint32_t size) {
    const auto width = pod_value_width(kind);
    if (!bytes || !width || size != width) return false;
    const bool doubles = kind == PodValueKind::Vector2D || kind == PodValueKind::Anchors;
    const uint32_t component = doubles ? 8 : 4;
    for (uint32_t offset=0; offset<width; offset+=component) {
        double number;
        if (doubles) std::memcpy(&number, bytes+offset, 8);
        else { float narrow; std::memcpy(&narrow, bytes+offset, 4); number=narrow; }
        // Canvas slot setters narrow Vector2D doubles to float storage.
        if (!std::isfinite(number) || std::abs(number)>std::numeric_limits<float>::max()) return false;
    }
    return true;
}
