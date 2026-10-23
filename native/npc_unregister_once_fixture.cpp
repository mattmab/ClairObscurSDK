#include "npc_unregister_once.h"
#include <cassert>
#include <iostream>
#include <stdexcept>
using namespace e33_npc_presentation;
struct Ops {
    bool accepted=true,returned=true,throw_validation=false,throw_dispatch=false;
    unsigned validations=0,calls=0;
    bool validate(){++validations;if(throw_validation)throw std::runtime_error("validation");return accepted;}
    bool dispatch_once(){++calls;if(throw_dispatch)throw std::runtime_error("dispatch");return returned;}
};
int main(){
    unsigned checks=0;
    {UnregisterJournal j;Ops o;assert(j.run(o)==UnregisterResult::Complete&&o.calls==1);
     assert(j.run(o)==UnregisterResult::Complete&&o.calls==1&&o.validations==1);checks+=2;}
    {UnregisterJournal j;Ops o;o.accepted=false;assert(j.run(o)==UnregisterResult::Rejected&&o.calls==0&&j.phase==UnregisterPhase::Ready);
     o.accepted=true;assert(j.run(o)==UnregisterResult::Complete&&o.calls==1);checks+=2;}
    {UnregisterJournal j;Ops o;o.returned=false;assert(j.run(o)==UnregisterResult::UnknownOutcome&&o.calls==1&&j.phase==UnregisterPhase::Pending);
     o.returned=true;assert(j.run(o)==UnregisterResult::UnknownOutcome&&o.calls==1&&o.validations==1);checks+=2;}
    {UnregisterJournal j;Ops o;o.throw_dispatch=true;
     try{j.run(o);assert(false);}catch(const std::runtime_error&){}
     assert(j.phase==UnregisterPhase::Pending&&o.calls==1);
     o.throw_dispatch=false;assert(j.run(o)==UnregisterResult::UnknownOutcome&&o.calls==1);checks+=2;}
    {UnregisterJournal j;Ops o;o.throw_validation=true;
     try{j.run(o);assert(false);}catch(const std::runtime_error&){}
     assert(j.phase==UnregisterPhase::Ready&&o.calls==0);
     o.throw_validation=false;assert(j.run(o)==UnregisterResult::Complete&&o.calls==1);checks+=2;}
    {UnregisterJournal nearby,distant;Ops n,d;assert(nearby.run(n)==UnregisterResult::Complete);
     d.returned=false;assert(distant.run(d)==UnregisterResult::UnknownOutcome);
     assert(nearby.run(n)==UnregisterResult::Complete&&n.calls==1);
     assert(distant.run(d)==UnregisterResult::UnknownOutcome&&d.calls==1);checks+=4;}
    std::cout<<checks<<" unregister journal checks passed; no engine calls executed\n";
}
