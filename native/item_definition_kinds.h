#pragma once
#include <cstdint>
namespace e33_item_definition_kinds {
// Vanilla static-data categories: quest/key item, weapon, character cosmetic.
inline bool valid(uint8_t kind,uint8_t subtype,bool has_asset,bool weapon_asset,bool cosmetic_asset){
 if(kind==3)return subtype==7&&!has_asset;
 if(kind==1)return has_asset&&weapon_asset;
 if(kind==8)return has_asset&&cosmetic_asset;
 return false;
}
}
