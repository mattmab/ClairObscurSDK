#include "enemy_retirement.h"
#include <cassert>
struct Ops {
    bool eligible=true,field=true,battle=false;
    unsigned reads=0,destroys=0,releases=0;
    bool context(){return eligible;}
    bool battle_state(bool& value){++reads;value=battle;return field;}
    uint32_t close(bool has_work,bool world){
        const auto result=enemy_retirement_gate(*this,has_work,world);
        if(result)return result;
        if(has_work){++destroys;++releases;}
        return 0;
    }
};
int main(){
    {Ops o;o.battle=true;assert(o.close(true,true)==407&&!o.destroys&&!o.releases);o.battle=false;assert(o.close(true,true)==0&&o.destroys==1&&o.releases==1);}
    {Ops o;o.field=false;assert(o.close(true,true)==2937&&!o.destroys&&!o.releases);}
    {Ops o;o.eligible=false;assert(o.close(true,true)==407&&!o.reads&&!o.destroys&&!o.releases);}
    {Ops o;o.field=false;assert(o.close(true,false)==0&&!o.reads&&o.destroys==1);}
    {Ops o;o.eligible=false;assert(o.close(false,false)==0&&!o.reads&&!o.destroys&&!o.releases);}
    {Ops o;assert(o.close(true,true)==0&&o.reads==1&&o.destroys==1&&o.releases==1);}
    {Ops o;o.field=false;o.battle=false;assert(o.close(true,true)==2937);o.field=true;assert(o.close(true,true)==0&&o.destroys==1);}
    {Ops o;o.battle=true;for(int i=0;i<10;++i)assert(o.close(true,true)==407);assert(!o.destroys&&!o.releases);}
}
