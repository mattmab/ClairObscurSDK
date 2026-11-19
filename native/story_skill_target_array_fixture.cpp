#include <cassert>
#include <stdexcept>
#include <iostream>
#include "story_skill_target_array.h"
#include "story_skill_install.h"
struct Ops {
 e33_skill_targets::Array result{0x10000,2,2};int frees=0,retains=0,dispatches=0;unsigned copied=0;
 bool current=true,fail_retain=false,throw_dispatch=false,throw_free=false;
 bool context()const{return current;}
 void dispatch(void*out){++dispatches;*static_cast<e33_skill_targets::Array*>(out)=result;if(throw_dispatch)throw std::runtime_error("dispatch");}
 void count(unsigned n){copied=n;}
 bool retain(uint64_t,unsigned){++retains;return !fail_retain;}
 void free_array(uint64_t){++frees;if(throw_free)throw std::runtime_error("free");}
};
int main(){
 struct PartialOwner{uint64_t owner=42;bool unknown=false,release_ok=true;int close_calls=0;bool close(){++close_calls;if(!release_ok)return false;owner=0;return true;}};
 {PartialOwner o;assert(e33_skill_install::rollback(o,4280,4281)==4280);assert(!o.unknown&&!o.owner&&o.close_calls==1);}
 {PartialOwner o;o.release_ok=false;assert(e33_skill_install::rollback(o,4280,4281)==4281);assert(o.unknown&&o.owner==42&&o.close_calls==1);}
 {e33_skill_targets::Frame f;Ops o;assert(f.query(o));assert(f.available()&&o.frees==1&&o.retains==2&&o.copied==2);}
 {e33_skill_targets::Frame f;Ops o;o.result={};assert(f.query(o));assert(o.frees==0&&o.retains==0&&f.available());}
 {e33_skill_targets::Frame f;Ops o;o.result={0x10000,0,2};assert(f.query(o));assert(o.frees==1&&o.retains==0);}
 {e33_skill_targets::Frame f;Ops o;o.result.count=33;o.result.capacity=33;assert(!f.query(o));assert(!f.available()&&o.frees==0);assert(!f.query(o));assert(o.dispatches==1);}
 {e33_skill_targets::Frame f;Ops o;o.fail_retain=true;assert(!f.query(o));assert(!f.available()&&o.frees==0&&o.retains==1);}
 {e33_skill_targets::Frame f;Ops o;o.throw_dispatch=true;try{f.query(o);assert(false);}catch(const std::runtime_error&){}assert(!f.available()&&o.frees==0&&f.value.data==0x10000);}
 {e33_skill_targets::Frame f;Ops o;o.throw_free=true;try{f.query(o);assert(false);}catch(const std::runtime_error&){}assert(!f.available()&&o.frees==1&&f.value.data==0x10000);assert(!f.query(o));assert(o.frees==1);}
 std::cout<<"Owned skill target array normal/empty/invalid/fault cleanup passed\n";
}
