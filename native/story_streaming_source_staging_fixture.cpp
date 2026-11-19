#include "story_streaming_source_staging.h"
#include "owned_actor_construction.h"
#include <cassert>
#include <initializer_list>
using namespace e33_story_source_staging;
struct Ops {
    uint8_t enabled=1;unsigned reads=0,writes=0;bool valid=true,write_ok=true,replace_component=false,replace_field=false,ignore_write=false;
    bool observe(Observation& out){
        ++reads;out={uint64_t(0x10000+(replace_component&&writes?8:0)),uint64_t(0x10100+(replace_field&&writes?8:0)),enabled};return valid;
    }
    bool write(const Observation&){++writes;if(!write_ok)return false;if(!ignore_write)enabled=0;return true;}
};
int main(){
    {Ops ops;Journal journal;assert(!disable(journal,ops)&&journal.attempted&&journal.acknowledged&&!ops.enabled&&ops.writes==1);
        assert(disable(journal,ops)==rejected&&ops.writes==1);}
    {Ops ops;ops.enabled=0;Journal journal;assert(!disable(journal,ops)&&journal.acknowledged&&!ops.writes);}
    {Ops ops;ops.valid=false;Journal journal;assert(disable(journal,ops)==rejected&&!journal.attempted&&!ops.writes);}
    {Ops ops;ops.enabled=2;Journal journal;assert(disable(journal,ops)==rejected&&!journal.attempted&&!ops.writes);}
    for(unsigned mode=0;mode<4;++mode){
        Ops ops;Journal journal;ops.write_ok=mode!=0;ops.replace_component=mode==1;ops.replace_field=mode==2;ops.ignore_write=mode==3;
        assert(disable(journal,ops)==uncertain&&journal.attempted&&!journal.acknowledged&&ops.writes==1);
        assert(disable(journal,ops)==rejected&&ops.writes==1);
    }
    // Simulate original construction enabling the source. No game-loop
    // streaming update can see it enabled once allocation ACK is returned.
    for(bool failure:{false,true}){
        Ops ops;ops.enabled=0;ops.write_ok=!failure;Journal staged;e33_owned_actor::ConstructionJournal construction;
        bool retained=false,finished=false;
        const auto result=e33_owned_actor::construct(construction,[]{return true;},[]{return true;},[&]{retained=true;return true;},[]{return true;},
            [&]{ops.enabled=1;finished=true;return true;},[&]{assert(finished&&retained);return !disable(staged,ops);});
        assert(retained&&staged.attempted);
        if(failure){assert(result==e33_owned_actor::ConstructionResult::FinalizationFailed&&construction.phase==e33_owned_actor::ConstructionPhase::FinalizationPending);}
        else assert(result==e33_owned_actor::ConstructionResult::Complete&&!ops.enabled&&staged.acknowledged);
        const auto repeated=e33_owned_actor::construct(construction,[]{assert(false);return false;},[]{return true;},[]{return true;},[]{return true;},[]{return true;},[]{return true;});
        assert(repeated==e33_owned_actor::ConstructionResult::AlreadyAttempted&&ops.writes==1);
    }
}
