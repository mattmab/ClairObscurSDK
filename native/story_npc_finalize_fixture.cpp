#include "story_npc_finalize.h"
#include <cassert>
#include <vector>
#include <stdexcept>
using namespace e33_story_npc_finalize;
struct Ops {
    bool admitted=true,context=true,verified=true;uint32_t fail=0,throw_at=0;std::vector<uint32_t> calls;
    bool validate(){return admitted;}
    bool current(){return context;}
    bool perform(uint32_t step){calls.push_back(step);if(step==throw_at)throw std::runtime_error("interrupted");return step!=fail;}
    bool verify(){return verified;}
};
int main(){
    {Journal journal;Ops ops;const auto result=run(journal,true,ops);assert(!result.error&&result.completed==7&&result.attempted==7);assert(ops.calls==std::vector<uint32_t>({1,2,4}));assert(run(journal,true,ops).error==rejected&&ops.calls.size()==3);}
    {Journal journal;Ops ops;const auto result=run(journal,false,ops);assert(!result.error&&result.completed==5&&result.attempted==5);assert(ops.calls==std::vector<uint32_t>({1,4}));}
    {Journal journal;Ops ops;ops.admitted=false;assert(run(journal,true,ops).error==rejected&&!journal.attempted&&ops.calls.empty());}
    {Journal journal;Ops ops;ops.context=false;const auto result=run(journal,true,ops);assert(result.error==uncertain&&!result.completed&&!result.attempted&&ops.calls.empty());}
    for(const auto step:{1U,2U,4U}){Journal journal;Ops ops;ops.fail=step;const auto result=run(journal,true,ops);assert(result.error==uncertain&&result.completed==step-1&&result.attempted==(step*2-1));assert(journal.completed==result.completed&&journal.steps_attempted==result.attempted);}
    {Journal journal;Ops ops;ops.throw_at=2;try{run(journal,true,ops);assert(false);}catch(const std::runtime_error&){}assert(journal.attempted&&journal.completed==1&&journal.steps_attempted==3);assert(run(journal,true,ops).error==rejected);}
    {Journal journal;Ops ops;ops.verified=false;const auto result=run(journal,true,ops);assert(result.error==uncertain&&result.completed==7&&result.attempted==7);}
    {Packet p{};p.owner=5;const CallIdentity id{1,1001,0x10000};p.npc=p.dialogue_class=p.speaker=p.system_cdo=id;for(auto& field:p.definitions)field=id;assert(valid(p));p.show_visual=1;assert(!valid(p));p.visual_owner=5;p.visual=id;assert(!valid(p));p.visual_owner=6;assert(valid(p));p.completed=1;assert(!valid(p));p.completed=0;p.tail[9]=1;assert(!valid(p));}
}
