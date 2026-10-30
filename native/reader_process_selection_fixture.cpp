#include "reader_process_selection.h"
#include <iostream>

template<class F> bool rejects(F operation,const std::string& expected) {
    try { operation(); } catch(const std::runtime_error& error) { return error.what()==expected; }
    return false;
}

int main() {
    const std::vector<ReaderProcessCandidate> games={{10,true},{20,true},{30,false}};
    if(select_reader_process(games,10)!=10 || select_reader_process(games,20)!=20)return 1;
    if(!rejects([&]{select_reader_process(games);},"MULTIPLE_GAME_PROCESSES"))return 2;
    if(!rejects([&]{select_reader_process(games,30);},"REQUESTED_GAME_PROCESS_NOT_FOUND"))return 3;
    if(!rejects([&]{select_reader_process(games,40);},"REQUESTED_GAME_PROCESS_NOT_FOUND"))return 4;
    if(!rejects([&]{select_reader_process({});},"GAME_NOT_RUNNING"))return 5;
    if(select_reader_process({{10,true},{20,false}})!=10)return 6;
    for(const std::string invalid:{"","0","-1","+10","10x","4294967296","99999999999"," 10","10 "})
        if(!rejects([&]{parse_reader_process_id(invalid);},"READER_PID_INVALID"))return 7;
    if(parse_reader_process_id("10")!=10 || parse_reader_process_id("4294967295")!=0xffffffffU)return 8;
    std::cout << "Explicit read PID selection and ambiguous discovery rejection passed.\n";
    return 0;
}
