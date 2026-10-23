#pragma once

// Keep attachment and focus in one game-thread request. Every intermediate
// native owner remains journaled by MenuLifecycle; failure never replays either
// operation or claims release.
template<class Menu,class Ops>
MenuResult attach_open_menu(Menu& menu,Ops& ops,uint64_t session,uint64_t owner,bool focus) {
    const auto result=menu.attach(ops,session,owner);
    if(result!=MenuResult::Ok || !focus)return result;
    return menu.focus(ops,session,owner);
}
