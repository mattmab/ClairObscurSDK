#include <cstdint>
#include <cassert>
#include <initializer_list>
#include "menu_lifetime.h"
#include "menu_open_pipeline.h"
struct Ops {};
struct Menu {
    MenuResult attachment=MenuResult::Ok,focused=MenuResult::Ok;
    unsigned attached=0,focus_calls=0;
    MenuResult attach(Ops&,uint64_t,uint64_t){++attached;return attachment;}
    MenuResult focus(Ops&,uint64_t,uint64_t){++focus_calls;return focused;}
};
int main(){
    Ops ops;
    for(const auto result:{MenuResult::Ok,MenuResult::Deferred,MenuResult::Quarantined}){
        Menu menu;menu.attachment=result;
        const auto observed=attach_open_menu(menu,ops,1,2,true);
        assert(observed==result && menu.attached==1);
        assert(menu.focus_calls==(result==MenuResult::Ok?1U:0U));
    }
    for(const auto result:{MenuResult::Deferred,MenuResult::Quarantined}){
        Menu menu;menu.focused=result;
        assert(attach_open_menu(menu,ops,1,2,true)==result);
        assert(menu.attached==1 && menu.focus_calls==1);
    }
    Menu legacy;assert(attach_open_menu(legacy,ops,1,2,false)==MenuResult::Ok);
    assert(legacy.attached==1 && !legacy.focus_calls);
}
