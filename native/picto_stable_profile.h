#pragma once
#include "picto_stable_shapes.h"
#ifndef E33_PICTO_REMOTE_PROFILE
inline void picto_profile_copy(uint64_t at,void* out,size_t size) { std::memcpy(out,reinterpret_cast<void*>(at),size); }
#endif
inline CallIdentity call_capture(uint64_t base,uint64_t object);
inline bool picto_stable_name(uint64_t base,uint64_t at,const char* text,uint32_t number,uint32_t number_offset=4) {
 if(local_read<uint32_t>(at+number_offset)!=number)return false;
 const auto id=local_read<uint32_t>(at);if((id>>16)>=8192)return false;
 const auto block=local_read<uint64_t>(base+0x92aadc0+16+uint64_t(id>>16)*8);
 if(!block)return false;
 const auto entry=block+(id&65535)*2;const auto header=local_read<uint16_t>(entry);
 const auto length=std::strlen(text);
 if((header&1) || (header>>6)!=length || length>1023 || (id&65535)*2+2+length>0x20000)return false;
 char bytes[1024]{};picto_profile_copy(entry+2,bytes,length);
 return !std::memcmp(bytes,text,length);
}
inline bool picto_stable_object(uint64_t base,uint64_t object,uint32_t index) {
 if(index>=sizeof(picto_objects)/sizeof(PictoObjectShape) || !object || !call_capture(base,object).address)return false;
 const auto& shape=picto_objects[index];
 if(!exact_name(base,local_read<uint64_t>(object+0x10)+0x18,shape.type))return false;
 for(size_t i=0;i<shape.count;++i) {
  if(!object || !call_capture(base,object).address || !picto_stable_name(base,object+24,shape.chain[i].name,shape.chain[i].number))return false;
  object=local_read<uint64_t>(object+32);
 }
 return !object;
}
inline bool picto_stable_field(uint64_t base,uint64_t field,uint32_t index,unsigned owner_depth=0) {
 if(!field || (field&7) || owner_depth>8 || index>=sizeof(picto_fields)/sizeof(PictoFieldShape))return false;
 const auto& f=picto_fields[index];
 if(local_read<uint64_t>(field)!=base+f.vtable || !picto_stable_name(base,field+32,f.name,f.number) ||
 !exact_name(base,local_read<uint64_t>(field+8),f.type) || local_read<int32_t>(field+68)!=f.offset ||
 local_read<int32_t>(field+52)!=f.width || local_read<int32_t>(field+48)!=f.dimension || local_read<uint64_t>(field+56)!=f.flags)return false;
 const auto owner=local_read<uint64_t>(field+16);
 if(f.owner_kind==0) {
  if(!(owner&1) || !picto_stable_object(base,owner&~uint64_t(1),f.owner_id))return false;
  auto current=local_read<uint64_t>((owner&~uint64_t(1))+80);unsigned count=0;
  for(;current && current!=field && ++count<512;current=local_read<uint64_t>(current+24)){}
  if(current!=field)return false;
 } else if((owner&1) || !picto_stable_field(base,owner,f.owner_id,owner_depth+1))return false;
 return !f.target_id || picto_stable_object(base,local_read<uint64_t>(field+112),f.target_id-1);
}
inline bool picto_stable_script(uint64_t base,uint64_t function,uint32_t index) {
 if(index>=sizeof(picto_scripts)/sizeof(PictoScriptShape))return false;
 const auto& s=picto_scripts[index];
 if(!picto_stable_object(base,function,s.object_id) || local_read<uint32_t>(function+0xb0)!=s.flags ||
 local_read<uint16_t>(function+0xb6)!=s.params || local_read<uint16_t>(function+0xb8)!=s.return_offset ||
 local_read<uint32_t>(function+0x58)!=s.extent || local_read<uint64_t>(function+0xd8)!=base+0x13937a0 ||
 local_read<int32_t>(function+0x68)!=static_cast<int32_t>(s.size) || s.size>8192)return false;
 const auto script=local_read<uint64_t>(function+0x60);
 if(!script)return false;
 uint8_t normalized[8192]{};picto_profile_copy(script,normalized,s.size);
 size_t end=0;
 for(size_t i=0;i<s.count;++i) {
  const auto& b=s.bindings[i];const size_t width=b.kind==2?12:8;
  if(b.offset<end || b.offset>s.size || width>s.size-b.offset)return false;
  end=b.offset+width;
  const auto value=local_read<uint64_t>(script+b.offset);
  if((b.kind==0 && !picto_stable_object(base,value,b.index)) ||
     (b.kind==1 && !picto_stable_field(base,value,b.index)) ||
     (b.kind==2 && (!picto_stable_name(base,script+b.offset,b.name,b.number,8) || local_read<uint32_t>(script+b.offset+4)!=b.padding)) ||
     (b.kind==3 && value) || b.kind>3)return false;
  std::memset(normalized+b.offset,0,width);
 }
 return !std::memcmp(normalized,s.bytes,s.size);
}
