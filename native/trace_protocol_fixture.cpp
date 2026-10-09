#include <cstddef>
#include "trace_protocol.h"
#include <cassert>
#include <cstdio>
#include <fstream>

int main(int argc, char** argv) {
    using namespace e33_trace;
    if (argc == 2) {
        Packet input{};
        std::ifstream stream(argv[1], std::ios::binary);
        stream.read(reinterpret_cast<char*>(&input), sizeof(input));
        assert(stream.gcount() == sizeof(input) && stream.peek() == std::char_traits<char>::eof());
        assert(valid_request(input));
        std::puts("Python-encoded trace packet accepted by native validator.");
        return 0;
    }
    Packet packet{};
    packet.version = 1; packet.operation = 1; packet.owner = 7;
    packet.duration_ms = 1000; packet.limit = 10; packet.filter.index = -1;
    packet.schema.version = 1; packet.schema.target = {1, 0, 0x10000};
    packet.schema.function = {2, 0, 0x20000}; packet.schema.return_offset = 65535;
    packet.schema.function_flags = 0x400; packet.schema.entry_rva = 0x1234;
    assert(valid_request(packet));
    packet.registration = 1; assert(!valid_request(packet)); packet.registration = 0;
    packet.duration_ms = 300001; assert(!valid_request(packet)); packet.duration_ms = 1000;
    packet.events[7].bytes[4095] = 1; assert(!valid_request(packet)); packet.events[7].bytes[4095] = 0;
    packet.filtered = 1; assert(!valid_request(packet)); packet.filter = {3, 0, 0x30000};
    assert(valid_request(packet));
    packet.filter.serial = -1; assert(!valid_request(packet));
    packet.filtered = 0; packet.filter = {-1, 0, 0};
    packet.operation = 2; packet.registration = 1;
    assert(!valid_request(packet));
    packet.duration_ms = packet.limit = 0; packet.schema = {};
    for (uint32_t operation = 2; operation <= 5; ++operation) {
        packet.operation = operation; assert(valid_request(packet));
    }
    packet.error = 1; assert(!valid_request(packet)); packet.error = 0;
    packet.owner = 0; assert(!valid_request(packet));
    std::puts("Trace wire: packed ABI, operation-specific bounds, filters and empty response fields passed.");
}
