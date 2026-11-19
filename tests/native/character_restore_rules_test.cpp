#include "../../native/character_restore_rules.h"
#include <cassert>
using namespace e33_character_restore_rules;
struct CosmeticOps{
 Appearance state{10,20};unsigned reads=0,sets=0,loads=0,fail_read=0;bool fail_set=false,fail_apply=false,wrong_set=false,wrong_apply=false;
 bool read(Appearance&out){++reads;out=state;return reads!=fail_read;}
 bool set(const Appearance&value){++sets;if(fail_set)return false;state=after_set(state,value);if(wrong_set)++state.skin;return true;}
 bool apply(){++loads;if(fail_apply)return false;if(wrong_apply)++state.face;return true;}
};
int main(){
 uint64_t ids[9]={1,2,3,4,5,6,7,8,9};Snapshot s{{1,2,7,4,3,6,5},{1,2,3,4,5,6},7,6};
 assert(valid(s,ids));assert(native_equipped_length(s)==6);assert(unlocked_equal(s,s.unlocked,7));
 // Different graphs preserve only their own unlocked subset.
 uint64_t small[9]={21,22};Snapshot few{{21,22},{22,0},2,2};assert(valid(few,small,2));assert(!valid(few,small,1));
 // Every arrangement, including an intentionally empty six-slot loadout.
 for(unsigned mask=0;mask<64;++mask){auto c=s;for(unsigned i=0;i<6;++i)if(!(mask&(1U<<i)))c.equipped[i]=0;
  assert(valid(c,ids));assert(empty_loadout(c)==(mask==0));unsigned last=6;while(last&&!(mask&(1U<<(last-1))))--last;assert(native_equipped_length(c)==last);}
 auto bad=s;bad.equipped[0]=9;assert(!valid(bad,ids)); // Never grant an unlearned skill.
 bad=s;bad.equipped[1]=bad.equipped[0];assert(!valid(bad,ids));
 bad=s;bad.unlocked[1]=bad.unlocked[0];assert(!valid(bad,ids));
 bad=s;bad.unlocked[0]=8;assert(!valid(bad,ids));
 bad=s;bad.unlock_count=10;assert(!valid(bad,ids));
 bad=s;bad.equip_count=7;assert(!valid(bad,ids));
 bad=s;for(auto&v:bad.equipped)v=0;assert(valid(bad,ids));assert(empty_loadout(bad));
 bad=s;bad.equip_count=0;assert(valid(bad,ids));assert(empty_loadout(bad));
 bad=s;bad.unlocked[2]=99;assert(!valid(bad,ids));
 auto duplicate=ids[1];ids[1]=ids[0];assert(!valid(s,ids));ids[1]=duplicate;
 assert(!unlocked_equal(s,s.unlocked,6));uint64_t other[7]={1,2,7,4,3,6,8};assert(!unlocked_equal(s,other,7));
 // Only the exact selected native slot/file; no arbitrary skill input.
 const char16_t file[]=u"EXPEDITION_9",different[]=u"EXPEDITION_8",padded[14]=u"EXPEDITION_9";
 static_assert(sizeof(file)==26);
 assert(!selected_file(9,9,10,padded,14,padded,14));
 assert(selected_file(9,9,10,file,13,file,13));
 assert(!selected_file(9,8,10,file,13,file,13));
 assert(!selected_file(10,10,10,file,13,file,13));
 assert(!selected_file(-1,-1,10,file,13,file,13));
 assert(!selected_file(9,9,10,file,13,different,13));
 assert(!selected_file(9,9,10,file,13,file,12));
 char16_t request[260]{};assert(file_request(-1,request,0));assert(!file_request(9,request,0));
 std::memcpy(request,file,sizeof(file));assert(file_request(9,request,13));assert(!file_request(32,request,13));
 assert(!file_request(-1,request,13));assert(!file_request(9,request,261));request[259]=1;assert(!file_request(9,request,13));
 // Current unsaved choices win independently; None falls back to the validated
 // checkpoint and ultimately keeps refreshed defaults, exactly like the setter.
 assert(same(selection({30,40},{31,41}),{30,40}));
 assert(same(selection({30,0},{31,41}),{30,41}));
 assert(same(selection({0,40},{31,41}),{31,40}));
 assert(same(selection({0,0},{31,41}),{31,41}));
 assert(same(after_set({10,20},{30,0}),{30,20}));
 assert(same(after_set({10,20},{0,40}),{10,40}));
 assert(same(after_set({10,20},{0,0}),{10,20}));
 // The same production orchestration is used here; test every read/callback
 // boundary, including a setter that returns without applying the selection.
 uint32_t stage=0;CosmeticOps ok;
 assert(apply_appearance(ok,{30,40},stage));assert(stage==18&&ok.sets==1&&ok.loads==1&&ok.reads==3&&same(ok.state,{30,40}));
 CosmeticOps unchanged;assert(apply_appearance(unchanged,{10,0},stage));assert(stage==14&&unchanged.sets==0&&unchanged.loads==0);
 for(unsigned fail=1;fail<=3;++fail){CosmeticOps c;c.fail_read=fail;assert(!apply_appearance(c,{30,40},stage));assert(c.sets==(fail>1?1U:0U));assert(c.loads==(fail>2?1U:0U));}
 CosmeticOps failed_set;failed_set.fail_set=true;assert(!apply_appearance(failed_set,{30,40},stage));assert(stage==15&&failed_set.sets==1&&failed_set.loads==0);
 CosmeticOps failed_load;failed_load.fail_apply=true;assert(!apply_appearance(failed_load,{30,40},stage));assert(stage==17&&failed_load.sets==1&&failed_load.loads==1);
 CosmeticOps wrong_set;wrong_set.wrong_set=true;assert(!apply_appearance(wrong_set,{30,40},stage));assert(stage==16&&wrong_set.loads==0);
 CosmeticOps wrong_load;wrong_load.wrong_apply=true;assert(!apply_appearance(wrong_load,{30,40},stage));assert(stage==18&&wrong_load.loads==1);
}
