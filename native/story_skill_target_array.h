#pragma once
#include <cstdint>
namespace e33_skill_targets {
struct Array {uint64_t data=0;int32_t count=0,capacity=0;};
static_assert(sizeof(Array)==16);
enum class State {idle,dispatching,returned,retaining,freeing,unknown};
// A function OutParm owns its returned allocation. Keep it durable through
// exceptions; never free a guessed pointer or repeat an uncertain dispatch.
struct Frame {
 Array value{};State state=State::idle;
 bool available()const{return state==State::idle;}
 template<class Ops>bool query(Ops&ops){
  if(!available()||!ops.context())return false;
  state=State::dispatching;ops.dispatch(&value);state=State::returned;
  if(!ops.context()||value.count<0||value.count>32||value.capacity<value.count||value.capacity>4096||
    (value.capacity&&(!value.data||(value.data&7)))||(!value.capacity&&value.data)||
    value.data>UINT64_MAX-uint64_t(value.capacity)*8){state=State::unknown;return false;}
  const auto copy=value;ops.count(uint32_t(value.count));
  for(int i=0;i<value.count;++i){state=State::retaining;if(!ops.retain(value.data+uint64_t(i)*8,unsigned(i))){state=State::unknown;return false;}state=State::returned;}
  if(!ops.context()||value.data!=copy.data||value.count!=copy.count||value.capacity!=copy.capacity){state=State::unknown;return false;}
  if(value.data){state=State::freeing;ops.free_array(value.data);}value={};state=State::idle;return true;
 }
};
}
