#include "timeline_blueprint_reveal.h"
#include <cassert>
using namespace e33_timeline_blueprint;
int main() {
    for(int failure=0;failure<5;++failure){
        RevealJournal journal;int stage=0,calls=0;
        auto step=[&](){++calls;return stage++!=failure;};
        const auto result=reveal(journal,step,step,step,step,step);
        assert(result==(failure==0?RevealResult::Rejected:RevealResult::Unknown));
        assert(calls==failure+1);assert(journal.attempted==(failure!=0));
        if(failure){
            assert(reveal(journal,step,step,step,step,step)==RevealResult::Rejected);
            assert(calls==failure+1);
        }
    }
    RevealJournal journal;int calls=0;
    auto ok=[&](){++calls;return true;};
    assert(reveal(journal,ok,ok,ok,ok,ok)==RevealResult::Complete);
    assert(calls==5&&journal.attempted);
    assert(reveal(journal,ok,ok,ok,ok,ok)==RevealResult::Rejected);
    assert(calls==5);
}
