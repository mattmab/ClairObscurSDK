#include "character_skill_rules.h"
#include <cassert>
#include <fstream>
#include <iostream>
int main(int argc,char**argv){
 assert(argc==2);e33_character_skill_config::Profile p{};std::ifstream input(argv[1],std::ios::binary);input.read(reinterpret_cast<char*>(&p),sizeof(p));assert(input.gcount()==sizeof(p));assert(e33_character_skill_config::valid(p));
 auto s=p.skills[0];s.flags|=64|512;s.buff=2;s.duration=4;
 auto e=e33_character_skill_rules::effect(s,1,1,true,true,4);assert(e.damage==13.5&&e.breaking==.5&&e.element==4&&e.buff==2);
 e=e33_character_skill_rules::effect(s,0,0,false,false,4);assert(e.damage==2&&e.buff==-1);
 assert(e33_character_skill_rules::qualifies_meter(p,true,3,2.,12,11));assert(!e33_character_skill_rules::qualifies_meter(p,false,3,2.,12,11));assert(!e33_character_skill_rules::qualifies_meter(p,true,2,2.,12,11));assert(!e33_character_skill_rules::qualifies_meter(p,true,3,2.,12,12));
 assert(e33_character_skill_rules::next_meter(p,0)==7);assert(e33_character_skill_rules::next_meter(p,28)==30);
 p.own_only=0;assert(e33_character_skill_rules::qualifies_meter(p,false,3,2.,12,11));
 p.skills[0].flags=2048;assert(!e33_character_skill_config::valid(p));p.skills[0].flags=0;p.paths[0][319]='X';assert(!e33_character_skill_config::valid(p));
 std::cout<<"Generic skill effects, input bonuses, and meter policy checks passed\n";
}
