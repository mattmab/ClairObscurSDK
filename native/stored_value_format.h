#pragma once
#include <cmath>
#include <iomanip>
#include <limits>
#include <locale>
#include <sstream>
#include <string>

template<typename Number>
inline std::string stored_float_json(Number value) {
    if (!std::isfinite(value))
        return std::isnan(value) ? "{\"$float\":\"nan\"}" :
               value > 0 ? "{\"$float\":\"inf\"}" : "{\"$float\":\"-inf\"}";
    std::ostringstream stream;
    stream.imbue(std::locale::classic());
    stream << std::setprecision(std::numeric_limits<Number>::max_digits10) << value;
    auto text = stream.str();
    // Preserve float type and negative zero, without showpoint's invalid JSON
    // trailing decimal point for values such as 225000000.
    if (text.find_first_of(".eE") == std::string::npos) text += ".0";
    return text;
}
