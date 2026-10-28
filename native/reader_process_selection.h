#pragma once
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

// Pure selection policy shared by the read-only probe and its portable fixture.
// A nonzero request comes only from an explicit-PID read operation or the pinned
// read worker. Mutation/injection/session startup continues to request discovery.
struct ReaderProcessCandidate { uint32_t pid; bool shipping_image; };

inline uint32_t parse_reader_process_id(const std::string& value) {
    if(value.empty() || value.size()>10)throw std::runtime_error("READER_PID_INVALID");
    uint64_t result=0;
    for(const auto ch:value) {
        if(ch<'0' || ch>'9')throw std::runtime_error("READER_PID_INVALID");
        result=result*10+uint64_t(ch-'0');
    }
    if(!result || result>0xffffffffULL)throw std::runtime_error("READER_PID_INVALID");
    return static_cast<uint32_t>(result);
}

inline uint32_t select_reader_process(const std::vector<ReaderProcessCandidate>& candidates,
                                      uint32_t requested=0) {
    uint32_t selected=0;
    for(const auto& candidate:candidates) {
        if(!candidate.shipping_image || !candidate.pid || (requested && candidate.pid!=requested))continue;
        if(selected)throw std::runtime_error("MULTIPLE_GAME_PROCESSES");
        selected=candidate.pid;
    }
    if(!selected)throw std::runtime_error(requested ? "REQUESTED_GAME_PROCESS_NOT_FOUND" : "GAME_NOT_RUNNING");
    return selected;
}
