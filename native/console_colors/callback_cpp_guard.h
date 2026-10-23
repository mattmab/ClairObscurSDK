#pragma once
namespace ConsoleCallbackBoundary {
// Isolate language exceptions separately from the caller's outer SEH boundary.
// Neither failure path dispatches the action again.
template<class Action,class Fault> inline void contain_cpp(Action&& action,Fault&& fault) noexcept {
 try {action();}
 catch(...) {try {fault();}catch(...) {}}
}
}
