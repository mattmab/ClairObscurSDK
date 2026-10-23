#pragma once
#include <cstdint>
namespace e33_retired_world {
// Pop only after a returned release ACK; a Deferred/unknown suffix stays owned.
template<class Rows,class Release>uint32_t release_reverse(Rows&rows,Release release){
 while(!rows.empty()){const auto error=release(rows.back());if(error)return error;rows.pop_back();}
 return 0;
}
}
