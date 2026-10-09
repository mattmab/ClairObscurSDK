#include <Windows.h>
#include "target_owned_text.h"

// Compile the actual target adapter/template path without calling into a game.
OwnedTextResult compile_owned_text(uint64_t base,OwnedTextStorage& storage,
                                   uint16_t* buffer,uint32_t capacity,uint32_t& count) {
    TargetOwnedTextOps ops{base};
    auto result=create_owned_text(ops,storage,buffer,capacity);
    if(result!=OwnedTextResult::Ok) return result;
    result=copy_owned_text(ops,storage,buffer,capacity,count);
    if(result!=OwnedTextResult::Ok) return result;
    return release_owned_text(ops,storage);
}
