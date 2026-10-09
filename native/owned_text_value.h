#pragma once
#include <cstddef>
#include <cstdint>
#include <cstring>

// Layouts observed in this executable's text conversion thunks. Never wire data.
struct TargetStringValue { uint64_t data; int32_t count, capacity; };
struct TargetTextValue { uint64_t data; uint32_t flags, padding; };
static_assert(sizeof(TargetStringValue)==16 && sizeof(TargetTextValue)==16);
static_assert(offsetof(TargetStringValue,count)==8 && offsetof(TargetStringValue,capacity)==12);
static_assert(offsetof(TargetTextValue,flags)==8);
constexpr uint32_t kOwnedTextUnits=4096; // Includes terminating UTF-16 NUL.

enum class OwnedTextState { Empty, Live, ConstructionUnknown, ReadUnknown, ReleaseUnknown };
enum class OwnedTextResult { Ok, Occupied, InvalidInput, InvalidContext,
                             UnsupportedValue, InvalidString, OutputTooSmall,
                             ReleaseDeferred, Uncertain };
struct OwnedTextStorage {
    TargetTextValue value{};
    OwnedTextState state=OwnedTextState::Empty;
    OwnedTextStorage()=default;
    OwnedTextStorage(const OwnedTextStorage&)=delete;
    OwnedTextStorage& operator=(const OwnedTextStorage&)=delete;
    // No native calls in a C++ destructor. Session-owned storage must outlive
    // explicit game-thread cleanup or quarantine after an SEH fault.
};

inline bool valid_text_units(const uint16_t* text,uint32_t count) {
    if(!text || !count || count>kOwnedTextUnits || text[count-1]) return false;
    for(uint32_t i=0;i+1<count;++i) {
        const auto unit=text[i];
        if(!unit) return false; // No embedded NUL or silent prefix truncation.
        if(unit>=0xd800 && unit<=0xdbff) {
            if(i+2>=count || text[i+1]<0xdc00 || text[i+1]>0xdfff) return false;
            ++i;
        } else if(unit>=0xdc00 && unit<=0xdfff) return false;
    }
    return true;
}

template<class Ops>
OwnedTextResult create_owned_text(Ops& ops,OwnedTextStorage& storage,
                                  const uint16_t* text,uint32_t count) {
    if(storage.state==OwnedTextState::Live) return OwnedTextResult::Occupied;
    if(storage.state!=OwnedTextState::Empty) return OwnedTextResult::Uncertain;
    if(!valid_text_units(text,count)) return OwnedTextResult::InvalidInput;
    if(!ops.can_create()) return OwnedTextResult::InvalidContext;
    // Constructor copies this borrowed input synchronously. It must never free
    // or retain this view; this was checked in target constructor1410add50.
    const TargetStringValue view{reinterpret_cast<uint64_t>(text),
                                 static_cast<int32_t>(count),static_cast<int32_t>(count)};
    storage.value={};
    storage.state=OwnedTextState::ConstructionUnknown;
    ops.construct(storage.value,view);
    // Keep uncertainty if an unexpected type appears after construction.
    if(!ops.known_text(storage.value)) return OwnedTextResult::UnsupportedValue;
    storage.state=OwnedTextState::Live;
    return OwnedTextResult::Ok;
}

template<class Ops>
OwnedTextResult copy_owned_text(Ops& ops,OwnedTextStorage& storage,
                                uint16_t* output,uint32_t capacity,uint32_t& count) {
    count=0;
    if(storage.state!=OwnedTextState::Live) return OwnedTextResult::Uncertain;
    if(!output || !capacity || capacity>kOwnedTextUnits) return OwnedTextResult::InvalidInput;
    if(!ops.can_create()) return OwnedTextResult::InvalidContext;
    if(!ops.known_text(storage.value)) return OwnedTextResult::UnsupportedValue;
    // The engine display-string accessor may refresh localization state. If it
    // faults, do not make further engine calls using the uncertain value.
    storage.state=OwnedTextState::ReadUnknown;
    const auto view=ops.display_string(storage.value);
    storage.state=OwnedTextState::Live;
    if(view.count<0 || view.capacity<view.count ||
       static_cast<uint32_t>(view.count)>kOwnedTextUnits ||
       (view.count && !view.data)) return OwnedTextResult::InvalidString;
    uint16_t copied[kOwnedTextUnits]{};
    auto units=static_cast<uint32_t>(view.count);
    if(units) {
        if(!ops.read_units(view.data,copied,units) || !valid_text_units(copied,units))
            return OwnedTextResult::InvalidString;
    } else units=1; // Engine's empty FString has no allocation/terminator.
    if(units>capacity) return OwnedTextResult::OutputTooSmall;
    std::memcpy(output,copied,units*sizeof(uint16_t));
    count=units;
    return OwnedTextResult::Ok;
}

template<class Ops>
OwnedTextResult release_owned_text(Ops& ops,OwnedTextStorage& storage) {
    if(storage.state==OwnedTextState::Empty) return OwnedTextResult::Ok;
    if(storage.state!=OwnedTextState::Live) return OwnedTextResult::Uncertain;
    if(!ops.can_release()) return OwnedTextResult::ReleaseDeferred;
    if(!ops.known_text(storage.value)) return OwnedTextResult::UnsupportedValue;
    storage.state=OwnedTextState::ReleaseUnknown;
    ops.release(storage.value);
    storage.value={};
    storage.state=OwnedTextState::Empty;
    return OwnedTextResult::Ok;
}
