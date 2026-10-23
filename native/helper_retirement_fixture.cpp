#include "helper_retirement.h"
#include <cassert>
#include <cstdio>
struct Ops{
    bool current=true,observed=true,idle=true;unsigned reads=0;
    bool context(){return current;}
    bool fresh_battle_quiescent(bool& value){++reads;value=idle;return observed;}
};
int main(){
    {Ops o;assert(helper_retirement_gate(o,true,true)==0&&o.reads==1);}
    {Ops o;o.idle=false;for(unsigned i=0;i<10;++i)assert(helper_retirement_gate(o,true,true)==407);assert(o.reads==10);o.idle=true;assert(helper_retirement_gate(o,true,true)==0);}
    {Ops o;o.observed=false;assert(helper_retirement_gate(o,true,true)==407);}
    {Ops o;o.current=false;assert(helper_retirement_gate(o,true,true)==407&&o.reads==0);}
    {Ops o;o.current=false;assert(helper_retirement_gate(o,false,true)==0&&o.reads==0);assert(helper_retirement_gate(o,true,false)==0&&o.reads==0);}
    puts("Helper retirement fixture passed: idle release, active deferral, failed observation/context, untouched world-enemy path.");
}
