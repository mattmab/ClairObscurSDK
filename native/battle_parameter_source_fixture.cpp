#include "battle_parameter_source_match.h"
#include <cassert>
#include <map>
#include <string>
using namespace e33_enemy_spawn;
struct Node {std::string name;uint32_t number;uint64_t outer;};
struct Ops {
    std::map<uint64_t,Node> nodes{{1,{"Trigger",2,2}},{2,{"Conditional",1,3}},
        {3,{"Root_7",0,4}},{4,{"/Game/Actions/Root_7",0,0}}};
    bool valid(uint64_t object){return nodes.count(object)==1;}
    bool name(uint64_t object,const char* text,uint32_t number){return nodes.at(object).name==text&&nodes.at(object).number==number;}
    uint64_t outer(uint64_t object){return nodes.at(object).outer;}
};
int main(){
    const ParameterSourceProfile profile={"/Game/Actions/Root_7",3,{{"Trigger",2},{"Conditional",1},{"Root_7",0}}};
    {Ops o;assert(match_parameter_source(o,3,1,&profile,1));}
    {Ops o;o.nodes[1].number=1;assert(!match_parameter_source(o,3,1,&profile,1));}
    {Ops o;o.nodes[1].name="Trigger_1";o.nodes[1].number=0;assert(!match_parameter_source(o,3,1,&profile,1));}
    {Ops o;o.nodes[3].name="Root";o.nodes[3].number=8;assert(!match_parameter_source(o,3,1,&profile,1));}
    {Ops o;o.nodes[2].outer=1;assert(!match_parameter_source(o,3,1,&profile,1));}
    {Ops o;o.nodes.erase(2);assert(!match_parameter_source(o,3,1,&profile,1));}
    {Ops o;o.nodes[4].outer=3;assert(!match_parameter_source(o,3,1,&profile,1));}
    {Ops o;assert(!match_parameter_source(o,2,1,&profile,1));}
    {Ops o;ParameterSourceProfile duplicate[]={profile,profile};assert(!match_parameter_source(o,3,1,duplicate,2));}
    {Ops o;assert(!match_parameter_source(o,3,1,nullptr,1));assert(!match_parameter_source(o,3,1,&profile,47));}
    return 0;
}
