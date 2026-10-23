#include "engine_profile_invocation_policy.h"
#include <cassert>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
struct Ops {
    std::string fail,exception;std::vector<std::string> trace;unsigned calls=0;
    bool gate(const char* name){trace.emplace_back(name);if(exception==name)throw std::runtime_error(name);return fail!=name;}
    bool context(){return gate("context");}bool identities(){return gate("identities");}
    bool exact_profile(){return gate("schema");}bool recipient_derives(){return gate("ancestry");}
    bool dispatch_entry(){return gate("entry");}void dispatch_once(){++calls;if(exception=="dispatch")throw std::runtime_error("dispatch");}
};
int main(){
    unsigned tests=0;
    {Ops ops;assert(e33_engine_profile_call::invoke_validated(ops)&&ops.calls==1);
     assert((ops.trace==std::vector<std::string>{"context","identities","schema","ancestry","entry"}));++tests;}
    for(const auto* gate:{"context","identities","schema","ancestry","entry"}){
        Ops ops;ops.fail=gate;assert(!e33_engine_profile_call::invoke_validated(ops)&&ops.calls==0&&ops.trace.back()==gate);++tests;
        Ops throwing;throwing.exception=gate;try{e33_engine_profile_call::invoke_validated(throwing);assert(false);}catch(const std::runtime_error&){}
        assert(throwing.calls==0&&throwing.trace.back()==gate);++tests;
    }
    {Ops ops;ops.exception="dispatch";try{e33_engine_profile_call::invoke_validated(ops);assert(false);}catch(const std::runtime_error&){}
     assert(ops.calls==1);++tests;}
    std::cout<<tests<<" engine profile validation/order checks passed; no engine calls executed\n";
}
