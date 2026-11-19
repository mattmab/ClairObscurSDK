#include "item_definition_kinds.h"
#include <cassert>
#include <initializer_list>
int main(){using e33_item_definition_kinds::valid;assert(valid(3,7,false,false,false));assert(!valid(3,7,true,false,false));assert(!valid(3,6,false,false,false));for(uint8_t subtype:{uint8_t(1),uint8_t(13)}){assert(valid(1,subtype,true,true,false));assert(!valid(1,subtype,false,true,false));assert(!valid(1,subtype,true,false,true));}assert(valid(8,0,true,false,true));assert(!valid(8,0,true,true,false));assert(!valid(0,0,false,false,false));}
