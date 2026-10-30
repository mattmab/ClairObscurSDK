#pragma once
#include <cstdint>
namespace e33_command_wait {
constexpr uint64_t deadline_ms=60000,notice_ms=5000,interval_ms=1000;
struct Policy {
    uint64_t next_notice=notice_ms;
    bool expired(uint64_t elapsed)const{return elapsed>=deadline_ms;}
    bool notice(uint64_t elapsed){
        if(expired(elapsed)||elapsed<next_notice)return false;
        next_notice=elapsed+interval_ms;return true;
    }
};
}
