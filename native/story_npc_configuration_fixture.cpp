#include "story_npc_configuration.h"
#include <iostream>
#include <stdexcept>
#include <vector>
struct Ops {
    bool valid=true,match=true,collision_enabled=true;int fail=0;std::vector<int> calls;
    bool preflight(){return valid;}
    bool action(int n){calls.push_back(n);return n!=fail;}
    bool interactable(bool enabled){return action(enabled?4:1);}
    bool dialogue(){return action(2);}
    bool speaker(){return action(3);}
    bool collision(bool enabled){collision_enabled=enabled;return action(5);}
    bool matches(){return match;}
};
void check(bool value){if(!value)throw std::runtime_error("Story NPC configuration check failed");}
int main(){
    using namespace e33_story_npc;
    {Journal j;Ops o;check(configure(j,false,o)==0);check(o.calls==std::vector<int>({1,2,3}));
     check(configure(j,false,o)==rejected);check(configure(j,true,o)==0);check(j.active);check(configure(j,true,o)==rejected);}
    {Journal j;Ops o;check(configure(j,true,o)==rejected);check(o.calls.empty());o.valid=false;check(configure(j,false,o)==rejected);check(!j.configure_attempted);}
    for(int fail=1;fail<=3;++fail){Journal j;Ops o;o.fail=fail;check(configure(j,false,o)==unknown);check(!j.configured);check(configure(j,true,o)==rejected);check(configure(j,false,o)==rejected);}
    {Journal j;Ops o;o.match=false;check(configure(j,false,o)==unknown);check(!j.configured);}
    {Journal j;Ops o;check(configure(j,false,o)==0);o.fail=5;check(configure(j,true,o)==unknown);check(!j.active);check(configure(j,true,o)==rejected);}
    {Journal j;Ops o;check(configure(j,false,o)==0);o.calls.clear();check(configure(j,true,o,false,true)==0);
     check(o.calls.empty()&&!j.activate_attempted&&!j.active);check(configure(j,true,o,false)==0);check(j.active&&!o.collision_enabled);}
    std::cout<<"Story NPC configuration ordering and ownership journal checks passed\n";
}
