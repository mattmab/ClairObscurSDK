#pragma once
// Read-only bridge for the original save row's script-interface getter.
namespace e33_save_list_entry {
constexpr uint32_t operation=250,rejected=4200,uncertain=4201;
#pragma pack(push,1)
struct Packet {
 uint32_t version=3,op=operation,error=0,state=0;uint64_t owner=0;
 CallIdentity widget{},library{},function{};uint64_t leases[3]{};
 CallIdentity item{};uint8_t tail[20872]{};
};
#pragma pack(pop)
static_assert(sizeof(Packet)==20984,"Save list item query packet");
template<class Pool>void run(uint64_t b,uint64_t session,Pool&pool,Packet&p){
 if(p.version!=3||p.op!=operation||p.error||p.state||!p.owner||p.item.index||p.item.serial||p.item.address){p.error=rejected;return;}
 for(auto v:p.tail)if(v){p.error=rejected;return;}
 const CallIdentity ids[]={p.widget,p.library,p.function};
 for(unsigned i=0;i<3;++i)if(!call_identity(b,ids[i])||!p.leases[i]||!pool.owns_object(session,p.leases[i],ids[i].address)){p.error=rejected;return;}
 const auto f=p.function.address;
 if(!picto_class(b,p.widget.address,"WBP_MM_SaveSlot_C","/Game/UI/Widgets/MainMenu/WBP_MM_SaveSlot")||
    !e33_mesh::named(b,p.library.address,"Default__UserObjectListEntryLibrary","/Script/UMG")||
    !e33_mesh::named(b,f,"GetListItemObject","UserObjectListEntryLibrary")||
    local_read<uint64_t>(f+0xd8)!=b+0x30939a0||local_read<uint32_t>(f+0xb0)!=335684611U||
    local_read<uint16_t>(f+0xb6)!=24||local_read<uint16_t>(f+0xb8)!=16){p.error=rejected;return;}
 const auto argument=picto_struct_field(b,f,"UserObjectListEntry","InterfaceProperty",0,16),
  returned=picto_struct_field(b,f,"ReturnValue","ObjectProperty",16,8);
 if(!argument||!returned||!e33_mesh::named(b,local_read<uint64_t>(argument+0x70),"UserObjectListEntry","/Script/UMG")){p.error=rejected;return;}
 const auto dispatch=local_read<uint64_t>(local_read<uint64_t>(p.library.address)+0x268);
 if(dispatch!=b+0x1393330&&dispatch!=b+0x332bb90){p.error=rejected;return;}
 // This audited helper consumes GetObject(); the row implements the interface
 // in Blueprint, so its native interface pointer is deliberately null.
 alignas(16)uint64_t args[3]={p.widget.address,0,0};
 reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(dispatch)(reinterpret_cast<void*>(p.library.address),reinterpret_cast<void*>(f),args);
 if(!call_identity(b,p.widget)){p.error=rejected;return;}
 if(!args[2]){p.state=2;return;}
 if(!picto_class(b,args[2],"BP_SaveSlotViewItem_C","/Game/UI/Widgets/MainMenu/BP_SaveSlotViewItem")){p.error=rejected;return;}
 p.item=call_capture(b,args[2]);if(!p.item.address){p.error=rejected;return;}p.state=1;
}
}
