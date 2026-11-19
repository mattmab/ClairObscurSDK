#include "narrative_route_inputs.h"
#include <cassert>
#include <iostream>
int main(){
 unsigned inputs[6]{39,40,43,44,75,77},selected[6]{},used=0;
 auto name=[](unsigned i)->uint64_t{return i==39||i==43?10:i==40||i==44?20:i;};
 assert(e33_narrative_routes::unique_inputs(inputs,6,selected,used,name));
 assert(used==4&&selected[0]==39&&selected[1]==40&&selected[2]==75&&selected[3]==77);
 // Distinct callback names need their own routes; a single skill works too.
 assert(e33_narrative_routes::unique_inputs(inputs,6,selected,used,[](unsigned i){return uint64_t(i);}));assert(used==6);
 assert(e33_narrative_routes::unique_inputs(inputs,2,selected,used,name));assert(used==2);
 assert(!e33_narrative_routes::unique_inputs(inputs,7,selected,used,name));assert(!used);
 assert(!e33_narrative_routes::unique_inputs(inputs,6,selected,used,[](unsigned i){return i==44?uint64_t(0):i;}));assert(!used);
 std::cout<<"Named callback routes retain once per name; exact function hooks remain separate\n";
}
