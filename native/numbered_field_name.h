#pragma once
// Explicit base and number, obtained from reflected metadata. No suffix parsing
// or wildcard names. Existing profile callers retain their zero-number rule.
inline bool exact_field_name(uint64_t base,uint64_t fname,const char* name,uint32_t number=0) {
    if(local_read<uint32_t>(fname+4)!=number) return false;
    const uint64_t unnumbered=local_read<uint32_t>(fname);
    return exact_name(base,reinterpret_cast<uint64_t>(&unnumbered),name);
}
