#pragma once
#include <cstring>
// Private synchronous cleanup call identity, not a permission carried in a
// caller packet. Even a byte-identical public Stop cannot borrow this window.
template<class Packet> class SequenceCleanupAdmission {
    const Packet* active_=nullptr;
    const Packet* expected_=nullptr;
public:
    bool begin(const Packet& call,const Packet& expected) {
        if(active_ || std::memcmp(&call,&expected,sizeof(Packet))) return false;
        active_=&call;expected_=&expected;return true;
    }
    bool allows(const Packet& call) const {
        return active_==&call && expected_ && !std::memcmp(&call,expected_,sizeof(Packet));
    }
    void end() {active_=expected_=nullptr;}
};
