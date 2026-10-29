#include "session_command_wait_policy.h"
#include <cassert>
int main(){
 e33_command_wait::Policy p;
 assert(!p.notice(4999));assert(p.notice(5000));assert(!p.notice(5001));
 assert(p.notice(12000));assert(!p.expired(59000));assert(p.notice(59000));
 assert(p.expired(60000));assert(!p.notice(60000));
 assert(p.expired(90000));return 0;
}
