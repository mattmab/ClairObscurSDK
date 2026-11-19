#pragma once
#include <cstdint>
#include <cstddef>
#include <cstring>
namespace e33_character_restore_rules {
struct Snapshot {uint64_t unlocked[9]{},equipped[6]{};unsigned unlock_count=0,equip_count=0;};
struct Appearance {uint64_t skin=0,face=0;};
static_assert(sizeof(Appearance)==16,"Original S_CharacterCustomizationItemData layout");
inline bool same(const Appearance&a,const Appearance&b){return a.skin==b.skin&&a.face==b.face;}
// The original setter ignores None independently for skin and face. Current
// CharacterData wins over an older checkpoint, including unsaved choices.
inline Appearance selection(const Appearance&current,const Appearance&checkpoint){
 return {current.skin?current.skin:checkpoint.skin,current.face?current.face:checkpoint.face};
}
inline Appearance after_set(const Appearance&defaults,const Appearance&selected){return selection(selected,defaults);}
// This is also the native dispatch order: a failed/readback-unknown callback
// never proceeds to the next callback or repeats the setter.
template<class Ops>bool apply_appearance(Ops&ops,const Appearance&selected,uint32_t&stage){
 Appearance current{};stage=14;if(!ops.read(current))return false;
 const auto expected=after_set(current,selected);
 if(same(current,expected))return true; // Refresh already applied these defaults.
 stage=15;if(!ops.set(selected))return false;
 stage=16;if(!ops.read(current)||!same(current,expected))return false;
 stage=17;if(!ops.apply())return false;
 stage=18;return ops.read(current)&&same(current,expected);
}
inline int index(const uint64_t*known,uint64_t value,unsigned count=9){for(unsigned i=0;i<count;++i)if(value&&known[i]==value)return int(i);return -1;}
inline bool valid(const Snapshot&s,const uint64_t*known,unsigned known_count=9){
 if(!known_count||known_count>9||!s.unlock_count||s.unlock_count>known_count||s.equip_count>6)return false;
 unsigned mask=0,slots=0;
 for(unsigned i=0;i<known_count;++i){if(!known[i])return false;for(unsigned j=0;j<i;++j)if(known[i]==known[j])return false;}
 for(unsigned i=0;i<s.unlock_count;++i){const int n=index(known,s.unlocked[i],known_count);if(n<0||(mask&(1U<<n)))return false;mask|=1U<<n;}
 if(!(mask&1)||s.unlocked[0]!=known[0])return false; // Init keeps the starter first.
 for(unsigned i=0;i<s.equip_count;++i){if(!s.equipped[i])continue;const int n=index(known,s.equipped[i],known_count);if(n<0||!(mask&(1U<<n))||(slots&(1U<<n)))return false;slots|=1U<<n;}
 return true;
}
inline bool empty_loadout(const Snapshot&s){for(unsigned i=0;i<s.equip_count;++i)if(s.equipped[i])return false;return true;}
inline unsigned native_equipped_length(const Snapshot&s){unsigned n=s.equip_count;while(n&&!s.equipped[n-1])--n;return n;}
inline bool unlocked_equal(const Snapshot&s,const uint64_t*values,unsigned count){
 if(count!=s.unlock_count)return false;
 // Native Init puts the starter first, then AddUnique follows serialized order.
 unsigned at=0;if(!count||values[at++]!=s.unlocked[0])return false;
 for(unsigned i=1;i<count;++i)if(values[at++]!=s.unlocked[i])return false;
 return true;
}
inline bool file_request(int slot,const char16_t*file,unsigned count){
 if(!file||count>260)return false;
 if(!count){if(slot!=-1)return false;}else if(slot<0||slot>=32||count<2||file[count-1])return false;
 for(unsigned i=0;i<260;++i){if(i+1<count){if(!file[i])return false;}else if(file[i])return false;}
 return true;
}
inline bool selected_file(int requested_slot,int current_slot,int slots,const char16_t*file,int file_count,const char16_t*active,int active_count){
 if(requested_slot!=current_slot||current_slot<0||slots<1||slots>32||current_slot>=slots||
  !file||!active||file_count<2||file_count>260||file_count!=active_count||file[file_count-1]||active[active_count-1])return false;
 for(int i=0;i<file_count-1;++i)if(!file[i]||!active[i])return false;
 return !std::memcmp(file,active,size_t(file_count)*2);
}
}
