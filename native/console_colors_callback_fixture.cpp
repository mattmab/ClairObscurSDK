#include "console_colors/callback_cpp_guard.h"
#include <cassert>
#include <stdexcept>
struct Callback {
 int original_calls=0,faults=0;bool emitted=false,started=false,disabled=false;
 void original(){started=true;++original_calls;throw std::runtime_error("original failure");}
 void run(bool fail_before_original){
  try {if(fail_before_original)throw std::runtime_error("pre-emission failure");original();}
  catch(...) {++faults;disabled=true;if(!emitted && !started)original();}
 }
 void guarded(bool fail_before_original) noexcept {
  ConsoleCallbackBoundary::contain_cpp([&]{run(fail_before_original);},[&]{++faults;disabled=true;});
 }
};
int main(){
 Callback first;first.guarded(false);assert(first.original_calls==1 && first.faults==1 && first.disabled);
 Callback second;second.guarded(true);assert(second.original_calls==1 && second.faults==2 && second.disabled);
 int wrong_thread_calls=0,gt_faults=0;
 ConsoleCallbackBoundary::contain_cpp([&]{++wrong_thread_calls;throw std::runtime_error("wrong thread original");},[]{});
 assert(wrong_thread_calls==1 && gt_faults==0);
 bool completed=false;ConsoleCallbackBoundary::contain_cpp([&]{completed=true;},[]{throw 1;});assert(completed);
 // The guard also contains a throwing failure recorder, never terminating.
 ConsoleCallbackBoundary::contain_cpp([]{throw 1;},[]{throw 2;});
}
