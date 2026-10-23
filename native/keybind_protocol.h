#pragma once
#include <cstdint>
#include <cstring>

namespace e33_keys {
constexpr uint32_t capacity = 96;
enum : uint32_t { Replace = 1, Drain = 2, Capture = 3 };
struct Binding { uint32_t token, key; };
struct Packet {
    uint32_t version = 1, operation = 0;
    uint64_t session = 0, generation = 0;
    uint32_t count = 0, dropped = 0, error = 0, reserved = 0;
    Binding bindings[capacity]{};
};
static_assert(sizeof(Packet) == 808, "key packet ABI");
inline bool supported_key(uint32_t key) {
    return (key >= 65 && key <= 90) || (key >= 48 && key <= 57) ||
        (key >= 112 && key <= 123) || key == 8 || key == 9 || key == 13 ||
        key == 27 || (key >= 32 && key <= 40) || key == 45 || key == 46 || key == 188 || key == 189 || key == 190;
}
inline bool valid_request(const Packet& p) {
    if(p.version != 1 || !p.session || !p.generation || p.count > capacity ||
       p.dropped || p.error || p.reserved || (p.operation != Replace && p.operation != Drain && p.operation != Capture)) return false;
    if(p.operation == Drain && p.count) return false;
    for(uint32_t i=0;i<capacity;++i) {
        const auto& b=p.bindings[i];
        if(i>=p.count) { if(b.token || b.key) return false; continue; }
        if(!b.token || !supported_key(b.key)) return false;
        for(uint32_t j=0;j<i;++j)
            if(p.bindings[j].token == b.token || p.bindings[j].key == b.key) return false;
    }
    return true;
}
// Game-thread-owned; no engine pointers, allocation, Python calls or locks.
class State {
    uint64_t session_=0, generation_=0;
    Binding bindings_[capacity]{}, events_[capacity]{};
    uint32_t count_=0, queued_=0, dropped_=0;
    bool capturing_=false;
public:
    bool capturing() const { return capturing_; }
    void begin(uint64_t session) { close(); session_=session; }
    void close() { session_=generation_=0; count_=queued_=dropped_=0; capturing_=false;
        std::memset(bindings_,0,sizeof(bindings_)); std::memset(events_,0,sizeof(events_)); }
    bool contains(uint32_t key) const {
        for(uint32_t i=0;i<count_;++i) if(bindings_[i].key==key) return true;
        return false;
    }
    void command(Packet& p, uint32_t reserved_key) {
        if(!valid_request(p) || !session_ || p.session!=session_) { p.error=1; return; }
        if(p.operation==Replace || p.operation==Capture) {
            if(p.generation<=generation_) { p.error=2; return; }
            for(uint32_t i=0;i<p.count;++i)
                if(p.bindings[i].key==reserved_key) { p.error=3; return; }
            generation_=p.generation; count_=p.count; queued_=dropped_=0; capturing_=p.operation==Capture;
            std::memcpy(bindings_,p.bindings,sizeof(bindings_));
            std::memset(events_,0,sizeof(events_));
        } else {
            if(p.generation!=generation_) { p.error=2; return; }
            p.count=queued_; p.dropped=dropped_;
            std::memcpy(p.bindings,events_,sizeof(events_));
            queued_=dropped_=0; std::memset(events_,0,sizeof(events_));
        }
    }
    void press(uint32_t key, bool repeat, bool eligible) {
        if(!session_ || !generation_ || repeat || !eligible) return;
        for(uint32_t i=0;i<count_;++i) if(bindings_[i].key==key) {
            if(queued_<capacity) events_[queued_++]=bindings_[i];
            else if(dropped_!=UINT32_MAX) ++dropped_;
            return;
        }
    }
};
}
