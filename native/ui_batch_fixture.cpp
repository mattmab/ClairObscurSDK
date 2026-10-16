#define NOMINMAX
#include <windows.h>
#include <memory>
#include <cstdio>
#include "session_protocol.h"
static const char* fixture_function="SetPosition";
static const char* fixture_owner="CanvasPanelSlot";
template<class T> T local_read(uint64_t) { return static_cast<T>(0x200); }
inline uint64_t call_identity(uint64_t,const CallIdentity&) { return 0x100; }
inline bool exact_name(uint64_t,uint64_t address,const char* name) {
    return std::strcmp(address==0x118 ? fixture_function : fixture_owner,name)==0;
}
#include "ui_batch_runtime.h"

int main() {
#ifdef E33_UI_CONSTRUCTION_SESSION
    CallPacket creation{};
    creation.version=1;creation.parameter_size=8;creation.allocation_extent=8;
    creation.target={1,1,0x100};creation.function={2,1,0x200};creation.field_count=1;
    auto& field=creation.fields[0];field.kind=CallObject;field.width=8;field.dimension=1;
    field.flags=0x480;field.constraint={3,1,0x300};strcpy_s(field.name,"ReturnValue");
    fixture_owner="GameplayStatics";fixture_function="SpawnObject";
    if(!ui_creation(0,creation)) return 30;
    fixture_function="OpenLevel";
    if(ui_creation(0,creation)) return 31;
    fixture_owner="Actor";fixture_function="SpawnObject";
    if(ui_creation(0,creation)) return 32;
    fixture_owner="CanvasPanel";fixture_function="AddChildToCanvas";
    if(!ui_creation(0,creation)) return 33;
    creation.data[0]=1;
    if(ui_creation(0,creation)) return 34;
    fixture_owner="CanvasPanelSlot";fixture_function="SetPosition";
#endif
#ifdef E33_LAYOUT_BATCH_SESSION
    CallPacket call{}; call.return_offset=65535; call.field_count=1;
    if(!ui_setter(0,call)) return 20;
    fixture_owner="Actor";
    if(ui_setter(0,call)) return 21;
    fixture_owner="UserWidget"; fixture_function="SetOwningPlayer";
    if(!ui_setter(0,call)) return 22;
    call.fields[0].flags=0x100;
    if(ui_setter(0,call)) return 23;
    call.fields[0].flags=0; call.return_offset=0;
    if(ui_setter(0,call)) return 24;
#endif
    auto packet=std::make_unique<SessionPacket>();
    auto* data=reinterpret_cast<uint8_t*>(packet->console_text);
    MultiButtonPacket control{};
    control.action.version=1; control.action.operation=1; control.action.owner=33;
    control.action.child_lease=4; control.action.action=5; control.child={1,2,0x10000};
    auto request=[&](uint32_t second=SessionMultiButton) {
        std::memset(data,0,e33_ui::Capacity);
        e33_ui::put(data,1); e33_ui::put(data+4,2);
        uint32_t at=e33_ui::Header;
        for(uint32_t action:{SessionMultiButton,second}) {
            uint32_t bytes=0;
            if(!e33_ui::compress(&control,sizeof(control),data+at+8,e33_ui::Capacity-at-8,bytes)) return false;
            e33_ui::put(data+at,action); e33_ui::put(data+at+4,bytes); at+=8+bytes;
        }
        e33_ui::put(data+8,at); return true;
    };
    unsigned calls=0;
    auto dispatch=[&](SessionPacket* p)->uint32_t {
        ++calls; p->multi_button.action.outcome=2; return 0;
    };
    if(!request()) return 1;
    ui_batch_run(0,packet.get(),dispatch);
    if(calls!=2 || e33_ui::word(data+12)!=2 || e33_ui::word(data+16)) return 2;
    calls=0; if(!request(999)) return 3;
    ui_batch_run(0,packet.get(),dispatch);
    if(calls || !e33_ui::word(data+16)) return 4;
    if(!request()) return 5;
    ui_batch_run(0,packet.get(),[&](SessionPacket* p)->uint32_t {
        ++calls; p->multi_button.action.error=1014; p->multi_button.action.outcome=1; return 0;
    });
    if(calls!=1 || e33_ui::word(data+12)!=1 || !e33_ui::word(data+16)) return 6;
    uint8_t overlapping[18]{}, result[8]{};
    e33_ui::put(overlapping+4,1); overlapping[8]=1;
    e33_ui::put(overlapping+13,1); overlapping[17]=2;
    if(e33_ui::expand(overlapping,sizeof(overlapping),result,sizeof(result))) return 7;
    std::puts("UI batch: bounded codec, complete preflight, stop-on-failure, no replay PASS");
    return 0;
}
