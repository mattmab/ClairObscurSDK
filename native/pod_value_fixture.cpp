#include "pod_value_codec.h"
#include <iostream>

int main() {
    double vector[2]{160.25, -32.5};
    double anchors[4]{0, 0, 1, 1};
    float floats[4]{0, .25f, .5f, 1};
    auto bytes=[](const auto& value) { return reinterpret_cast<const uint8_t*>(&value); };
    if (!valid_pod_value(PodValueKind::Vector2D, bytes(vector), 16) ||
        !valid_pod_value(PodValueKind::Anchors, bytes(anchors), 32) ||
        !valid_pod_value(PodValueKind::LinearColor, bytes(floats), 16) ||
        !valid_pod_value(PodValueKind::Margin, bytes(floats), 16)) return 1;
    if (valid_pod_value(PodValueKind::Vector2D, bytes(vector), 8) ||
        valid_pod_value(static_cast<PodValueKind>(99), bytes(vector), 16) ||
        valid_pod_value(PodValueKind::Vector2D, nullptr, 16)) return 2;
    vector[0]=1e100;
    if (valid_pod_value(PodValueKind::Vector2D, bytes(vector), 16)) return 3;
    vector[0]=std::numeric_limits<double>::quiet_NaN();
    if (valid_pod_value(PodValueKind::Vector2D, bytes(vector), 16)) return 4;
    floats[3]=std::numeric_limits<float>::infinity();
    if (valid_pod_value(PodValueKind::LinearColor, bytes(floats), 16)) return 5;
    anchors[3]=std::numeric_limits<double>::infinity();
    if (valid_pod_value(PodValueKind::Anchors, bytes(anchors), 32)) return 6;
    std::cout << "Four numeric profiles and seven invalid-value/boundary cases passed.\n";
    return 0;
}
