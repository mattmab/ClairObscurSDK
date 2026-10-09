#include "session_protocol.h"
#include <cstddef>
#include <iostream>

int main() {
    wchar_t name[96]{};
    session_mapping_name(name,123,456);
    std::wcout << L"{\"message\":\"" << kSessionMessage << L"\",\"mapping\":\"";
    for(const auto c:name) {
        if(!c) break;
        if(c==L'\\') std::wcout << L'\\';
        std::wcout << c;
    }
    std::wcout << L"\",\"size\":" << sizeof(SessionPacket)
               << L",\"retained_offset\":" << offsetof(SessionPacket,retained)
               << L",\"assignment_offset\":" << offsetof(SessionPacket,assignment)
               << L",\"legacy_payload_end\":" << offsetof(SessionPacket,assignment)+sizeof(AssignmentPacket)
               << L",\"alignment\":" << alignof(SessionPacket);
#ifdef E33_TEXT_SESSION
    std::wcout << L",\"text_offset\":" << offsetof(SessionPacket,text)
               << L",\"text_size\":" << sizeof(TextCallPacket)
               << L",\"text_action\":" << SessionTextInvoke;
#endif
    std::wcout << L"}\n";
}
