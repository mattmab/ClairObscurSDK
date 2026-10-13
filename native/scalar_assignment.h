#pragma once
#include "target_object_assignment.h"
#include <cmath>

// Version 2 of the fixed-size assignment envelope. Only independently observed
// scalar descriptors are admitted; no pointer, container or accessor writes.
#pragma pack(push,1)
struct ScalarAssignmentPacket {
 uint32_t version=2,error=0;
 uint64_t token=0,reserved_tokens[2]{};
 CallIdentity target{},owner{};
 uint32_t kind=0,width=0;
 uint64_t vtable=0,expected=0,value=0;
 uint32_t boolean=0,reserved32=0;
 uint64_t reserved64=0,flags=0;
 uint32_t offset=0,dimension=1,reserved_element=0;
 char name[96]{};
 uint32_t outcome=CallNotDispatched;
};
#pragma pack(pop)
static_assert(sizeof(ScalarAssignmentPacket)==232);
inline uint64_t scalar_table(uint32_t kind) {
 const uint64_t tables[]={0,0x6e119b0,0x6e10a98,0x6e11560,0x6e11788};
 return kind<5 ? tables[kind] : 0;
}
inline bool scalar_request(const ScalarAssignmentPacket& p) {
 if(p.version!=2 || p.error || !p.token || p.reserved_tokens[0] || p.reserved_tokens[1] ||
    p.reserved32 || p.reserved64 || p.reserved_element || p.outcome ||
    !assignment_identity(p.target,false) || !assignment_identity(p.owner,false) ||
    !p.kind || p.kind>4 || p.vtable!=scalar_table(p.kind) || p.dimension!=1 ||
    p.offset<40 || p.offset>16777208 || !p.name[0] || p.name[95] ||
    (p.flags&(0x80ULL|0x20000ULL|0x20ULL)))return false;
 for(unsigned i=0;i<96 && p.name[i];++i)if(static_cast<unsigned char>(p.name[i])>=128)return false;
 if(p.kind==1) {
  const uint8_t size=uint8_t(p.boolean),at=uint8_t(p.boolean>>8),bit=uint8_t(p.boolean>>16),mask=uint8_t(p.boolean>>24);
  return p.width==1 && size==1 && !at && bit && !(bit&(bit-1)) && (mask==bit || mask==255) && p.expected<=1 && p.value<=1;
 }
 if(p.boolean || p.width!=(p.kind==4 ? 8u : 4u) || (p.width==4 && ((p.expected|p.value)>>32)))return false;
 if(p.kind==3) { float a,b; std::memcpy(&a,&p.expected,4);std::memcpy(&b,&p.value,4);return std::isfinite(a)&&std::isfinite(b); }
 if(p.kind==4) { double a,b;std::memcpy(&a,&p.expected,8);std::memcpy(&b,&p.value,8);return std::isfinite(a)&&std::isfinite(b); }
 return true;
}
inline uint64_t scalar_property(uint64_t base,const ScalarAssignmentPacket& p) {
 TargetObjectAssignmentOps check{base};
 if(!check.context() || !check.identity(p.target) || !check.identity(p.owner) || !call_is_class(base,p.owner.address) ||
    (local_read<uint32_t>(p.target.address+8)&0x30))return 0;
 const auto cls=local_read<uint64_t>(p.target.address+0x10);
 if(!call_derives(base,cls,p.owner.address))return 0;
 const auto extent=local_read<int32_t>(cls+0x58);
 if(extent<40 || extent>16777216 || uint64_t(p.offset)+p.width>uint64_t(extent))return 0;
 const char* names[]={"","BoolProperty","IntProperty","FloatProperty","DoubleProperty"};
 auto field=local_read<uint64_t>(p.owner.address+0x50);
 for(unsigned count=0;field && count<4096;++count,field=local_read<uint64_t>(field+0x18)) {
  if(!exact_name(base,field+0x20,p.name))continue;
  const auto table=local_read<uint64_t>(field);
  if(table!=base+p.vtable || local_read<uint64_t>(field+0x10)!=(p.owner.address|1) ||
     !exact_name(base,local_read<uint64_t>(field+8),names[p.kind]) ||
     local_read<uint64_t>(field+0x38)!=p.flags || local_read<uint32_t>(field+0x44)!=p.offset ||
     local_read<uint32_t>(field+0x30)!=1 || local_read<uint32_t>(field+0x34)!=p.width ||
     local_read<uint64_t>(table+0x78)!=base+0x10044f0 || local_read<uint64_t>(table+0x80)!=base+0x10044f0 ||
     (p.kind==1 && local_read<uint32_t>(field+0x70)!=p.boolean))return 0;
  return field;
 }
 return 0;
}
inline uint64_t scalar_read(const ScalarAssignmentPacket& p) {
 uint64_t bits=0;std::memcpy(&bits,reinterpret_cast<void*>(p.target.address+p.offset),p.width);
 return p.kind==1 ? ((bits&uint8_t(p.boolean>>24))!=0) : bits;
}
inline void assign_scalar(uint64_t base,ScalarAssignmentPacket& p) {
 if(!scalar_request(p)){p.error=6;return;}
 const auto field=scalar_property(base,p);
 if(!field){p.error=3;return;}
 if(scalar_read(p)!=p.expected){p.error=4;return;}
 p.outcome=CallOutcomeUnknown;
 if(p.kind==1) {
  auto* destination=reinterpret_cast<uint8_t*>(p.target.address+p.offset);
  const auto mask=uint8_t(p.boolean>>24),bit=uint8_t(p.boolean>>16);
  *destination=uint8_t((*destination&~mask)|(p.value ? bit : 0));
 } else std::memcpy(reinterpret_cast<void*>(p.target.address+p.offset),&p.value,p.width);
 if(scalar_property(base,p)!=field || scalar_read(p)!=p.value){p.error=5;return;}
 p.outcome=CallDispatchReturned;
}
