#pragma once
// Validation ordering only. Callers retain owned-object/class admission and
// durable operation journals; this helper provides no mutation authority.
namespace e33_engine_profile_call {
template<class Ops> bool invoke_validated(Ops& ops){
    if(!ops.context()||!ops.identities()||!ops.exact_profile()||
       !ops.recipient_derives()||!ops.dispatch_entry())return false;
    ops.dispatch_once();return true;
}
}
