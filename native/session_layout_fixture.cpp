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
#ifdef E33_MENU_SESSION
    std::wcout << L",\"menu_offset\":" << offsetof(SessionPacket,menu)
               << L",\"menu_size\":" << sizeof(MenuPacket)
               << L",\"menu_plans_offset\":" << offsetof(MenuPacket,plans)
               << L",\"menu_action\":" << SessionMenu;
#endif
#ifdef E33_BUTTON_ACTION_SESSION
    std::wcout << L",\"button_action_offset\":" << offsetof(SessionPacket,button_action)
               << L",\"button_action_size\":" << sizeof(ButtonActionPacket)
               << L",\"button_action_command\":" << SessionButtonAction;
#endif
    std::wcout << L"}\n";
}
