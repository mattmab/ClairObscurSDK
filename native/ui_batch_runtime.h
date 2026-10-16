#pragma once
#include "ui_batch_protocol.h"

// Existing menu setters, owned controls, and capability-gated construction.
// All operations reuse validated dispatchers; no arbitrary function batches.
inline bool ui_setter(uint64_t base,const CallPacket& call) {
    if(call.return_offset!=65535 || !call.field_count || call.field_count>2) return false;
    for(uint32_t i=0;i<call.field_count;++i) if(call.fields[i].flags&0x500) return false;
    const auto function=call_identity(base,call.function);
    if(!function) return false;
    const auto owner=local_read<uint64_t>(function+0x20);
#ifdef E33_LAYOUT_BATCH_SESSION
    if(exact_name(base,owner+0x18,"CommonButtonBase") &&
       exact_name(base,function+0x18,"SetMinDimensions")) return call.field_count==2;
#endif
    if(call.field_count!=1) return false;
#ifdef E33_LAYOUT_BATCH_SESSION
    if(exact_name(base,owner+0x18,"Image") &&
       exact_name(base,function+0x18,"SetBrushResourceObject")) return true;
    if ((exact_name(base,owner+0x18,"CommonButtonBase") &&
            (exact_name(base,function+0x18,"SetIsSelectable") || exact_name(base,function+0x18,"SetIsToggleable"))) ||
        (exact_name(base,owner+0x18,"Widget") &&
            (exact_name(base,function+0x18,"SetRenderScale") || exact_name(base,function+0x18,"SetRenderTransformPivot"))) ||
        (exact_name(base,owner+0x18,"GridSlot") &&
            (exact_name(base,function+0x18,"SetPadding") || exact_name(base,function+0x18,"SetLayer") ||
             exact_name(base,function+0x18,"SetHorizontalAlignment") || exact_name(base,function+0x18,"SetVerticalAlignment")))) return true;
    if ((exact_name(base,owner+0x18,"CanvasPanelSlot") &&
            (exact_name(base,function+0x18,"SetPosition") || exact_name(base,function+0x18,"SetSize") ||
             exact_name(base,function+0x18,"SetAnchors"))) ||
        (exact_name(base,owner+0x18,"OverlaySlot") &&
            (exact_name(base,function+0x18,"SetHorizontalAlignment") ||
             exact_name(base,function+0x18,"SetVerticalAlignment"))) ||
        (exact_name(base,owner+0x18,"TextLayoutWidget") && exact_name(base,function+0x18,"SetJustification")) ||
        (exact_name(base,owner+0x18,"CommonTextBlock") && exact_name(base,function+0x18,"SetStyle")) ||
        (exact_name(base,owner+0x18,"Border") && exact_name(base,function+0x18,"SetBrushColor")) ||
        (exact_name(base,owner+0x18,"Button") && exact_name(base,function+0x18,"SetBackgroundColor")) ||
        (exact_name(base,owner+0x18,"UserWidget") && exact_name(base,function+0x18,"SetOwningPlayer"))) return true;
#endif
    return (exact_name(base,function+0x18,"SetText") && exact_name(base,owner+0x18,"TextBlock")) ||
        ((exact_name(base,function+0x18,"SetVisibility") || exact_name(base,function+0x18,"SetIsEnabled")) &&
         exact_name(base,owner+0x18,"Widget"));
}
inline void* ui_item(SessionPacket* packet,uint32_t action,uint32_t& size) {
    switch(action) {
    case SessionRetainedInvoke: size=sizeof(packet->retained); return &packet->retained;
    case SessionTextInvoke: size=sizeof(packet->text); return &packet->text;
    case SessionMultiButton: size=sizeof(packet->multi_button); return &packet->multi_button;
    default: size=0; return nullptr;
    }
}
inline bool ui_creation(uint64_t base,const CallPacket& call) {
#ifdef E33_UI_CONSTRUCTION_SESSION
    if(validate_call_packet(call,true) || retained_call_slots(call)!=1) return false;
    const auto function=call_identity(base,call.function);
    if(!function) return false;
    const auto owner=local_read<uint64_t>(function+0x20);
    // No dependent addresses on the wire: each input is an already observed
    // identity. Existing retained dispatch validates schemas and owns outputs.
    return (exact_name(base,owner+0x18,"GameplayStatics") && exact_name(base,function+0x18,"SpawnObject")) ||
        (exact_name(base,owner+0x18,"CanvasPanel") && exact_name(base,function+0x18,"AddChildToCanvas")) ||
        (exact_name(base,owner+0x18,"Overlay") && exact_name(base,function+0x18,"AddChildToOverlay")) ||
        (exact_name(base,owner+0x18,"PanelWidget") && exact_name(base,function+0x18,"AddChild")) ||
        (exact_name(base,owner+0x18,"ContentWidget") && exact_name(base,function+0x18,"SetContent"));
#else
    (void)base; (void)call; return false;
#endif
}
inline bool ui_item_valid(uint64_t base,SessionPacket* packet,uint32_t action) {
    if(action==SessionMultiButton) return valid_multi_button_request(packet->multi_button) &&
        (packet->multi_button.action.operation==1 || packet->multi_button.action.operation==3);
    if(action==SessionTextInvoke) return !validate_text_call(packet->text) &&
        ui_setter(base,packet->text.retained.call);
    return retained_call_empty(packet->retained) &&
        (ui_setter(base,packet->retained.call) || ui_creation(base,packet->retained.call));
}
inline bool ui_item_ok(SessionPacket* packet,uint32_t action) {
    if(action==SessionMultiButton) return !packet->multi_button.action.error &&
        packet->multi_button.action.outcome==2;
    const auto& call=action==SessionTextInvoke ? packet->text.retained.call : packet->retained.call;
    return !call.error && call.outcome==CallDispatchReturned;
}
template<class Dispatch>
void ui_batch_run(uint64_t base,SessionPacket* packet,Dispatch dispatch) {
    // Single game-thread execution; packet inputs are copied before dispatch.
    static uint8_t input[e33_ui::Capacity], output[e33_ui::Capacity];
    auto* wire=reinterpret_cast<uint8_t*>(packet->console_text);
    const auto size=e33_ui::word(wire+8);
    const auto count=e33_ui::word(wire+4);
    std::memset(output,0,sizeof(output));
    e33_ui::put(output,1); e33_ui::put(output+4,count);
    uint32_t used=e33_ui::Header, completed=0,error=1200;
    if(e33_ui::header(wire,size,true) && size<=e33_ui::Capacity-e33_ui::Limit*64) {
        std::memcpy(input,wire,size);
        uint32_t at=e33_ui::Header;
        bool valid=true;
        // Bounds and operation whitelist checked for the entire batch first.
        for(uint32_t i=0;i<count && valid;++i) {
            if(size-at<8) { valid=false; break; }
            auto action=e33_ui::word(input+at), bytes=e33_ui::word(input+at+4); at+=8;
            uint32_t extent=0; auto* item=ui_item(packet,action,extent);
            valid=item && bytes<=size-at && e33_ui::expand(input+at,bytes,item,extent) &&
                ui_item_valid(base,packet,action);
            if(valid) at+=bytes;
        }
        valid=valid && at==size;
        if(valid) {
            error=0; at=e33_ui::Header;
            for(uint32_t i=0;i<count;++i) {
                auto action=e33_ui::word(input+at), bytes=e33_ui::word(input+at+4); at+=8;
                uint32_t extent=0; auto* item=ui_item(packet,action,extent);
                if(!e33_ui::expand(input+at,bytes,item,extent)) { error=1201; break; }
                at+=bytes;
                packet->request.action=action;
                auto dispatched=dispatch(packet);
                ++completed;
                uint32_t encoded=0;
                if(e33_ui::Capacity-used<8 ||
                   !e33_ui::compress(item,extent,output+used+8,e33_ui::Capacity-used-8,encoded)) {
                    error=1202; break;
                }
                e33_ui::put(output+used,action); e33_ui::put(output+used+4,encoded); used+=8+encoded;
                if(dispatched || !ui_item_ok(packet,action)) { error=1203; break; }
            }
        }
    }
    packet->request.action=e33_ui::Action;
    e33_ui::put(output+8,used); e33_ui::put(output+12,completed); e33_ui::put(output+16,error);
    std::memcpy(wire,output,used);
}
