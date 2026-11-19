#pragma once
#include <cstdint>
namespace e33_skill_install {
// A rejected partial installation is retryable only after every native owner
// acknowledges rollback. Otherwise keep identity and leases quarantined.
template<class Owner>uint32_t rollback(Owner&owner,uint32_t rejected,uint32_t uncertain){
 if(owner.close())return rejected;
 owner.unknown=true;return uncertain;
}
}
