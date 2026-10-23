#pragma once
#include "metadata_stabilization_runtime.h"
#include "target_strong_reference.h"
#include "stable_identity.h"
// Explicit native Script metadata and same-package native CDOs only.
inline bool metadata_script_package(uint64_t base,uint64_t package){
 if(!package||!call_capture(base,package).address||(local_read<uint32_t>(package+8)&0x40000000))return false;
 const auto cls=local_read<uint64_t>(package+0x10);
 if(!cls||!exact_name(base,cls+0x18,"Package")||local_read<uint64_t>(package+0x20))return false;
 for(const auto*name:{"/Script/CoreUObject","/Script/Engine","/Script/UMG","/Script/CommonUI","/Script/SlateCore","/Script/InputCore"})
  if(exact_name(base,package+0x18,name))return true;
 return false;
}
inline bool metadata_native_class(uint64_t base,uint64_t cls){
 if(!cls||!call_capture(base,cls).address||(local_read<uint32_t>(cls+8)&0x40000000))return false;
 const auto meta=local_read<uint64_t>(cls+0x10);
 return meta&&exact_name(base,meta+0x18,"Class")&&metadata_script_package(base,local_read<uint64_t>(cls+0x20));
}
inline bool metadata_exact_cdo_name(uint64_t base,uint64_t object,uint64_t cls){
 // Same bounded, unnumbered ANSI FName representation as exact_name.
 if(local_read<uint32_t>(cls+0x1c))return false;
 const auto id=local_read<uint32_t>(cls+0x18),block=id>>16,offset=(id&65535)*2;
 const auto pool=base+0x92aadc0;const auto current=local_read<uint32_t>(pool+8),cursor=local_read<uint32_t>(pool+12);
 if(current>=8192||block>current||cursor>0x20000)return false;
 const auto limit=block==current?cursor:0x20000u;if(offset+2>limit)return false;
 const auto data=local_read<uint64_t>(pool+16+uint64_t(block)*8);if(!data)return false;
 const auto header=local_read<uint16_t>(data+offset);const unsigned length=header>>6;
 if((header&1)||!length||length>95||offset+2+length>limit)return false;
 char expected[105]="Default__";
 for(unsigned i=0;i<length;++i){const auto c=local_read<char>(data+offset+2+i);
  if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='_'))return false;
  expected[9+i]=c;
 }expected[9+length]=0;return exact_name(base,object+0x18,expected);
}
inline bool metadata_exact_style(uint64_t base,uint64_t object,uint64_t cls,uint64_t package){
 if(!exact_name(base,cls+0x18,"BlueprintGeneratedClass")||!package||!call_capture(base,package).address||
  (local_read<uint32_t>(package+8)&0x40000000)||local_read<uint64_t>(package+0x20))return false;
 const auto pkg_cls=local_read<uint64_t>(package+0x10);if(!pkg_cls||!exact_name(base,pkg_cls+0x18,"Package"))return false;
 const bool selected=(exact_name(base,object+0x18,"CTS_H2_Outline_C")&&exact_name(base,package+0x18,"/Game/UI/Resources/Styles/Text/Heading/CTS_H2_Outline"))||
  (exact_name(base,object+0x18,"CTS_B1_SmallLine_Outline_C")&&exact_name(base,package+0x18,"/Game/UI/Resources/Styles/Text/Body/Outline/CTS_B1_SmallLine_Outline"));
 if(!selected)return false;
 auto parent=local_read<uint64_t>(object+0x40);
 for(unsigned ancestor_depth=0;parent&&ancestor_depth<128;++ancestor_depth){
  if(!call_capture(base,parent).address)return false;
  if(exact_name(base,parent+0x18,"CommonTextStyle")&&metadata_native_class(base,parent)){
   const auto pkg=local_read<uint64_t>(parent+0x20);
   return pkg&&exact_name(base,pkg+0x18,"/Script/CommonUI");
  }parent=local_read<uint64_t>(parent+0x40);
 }return false;
}
inline bool metadata_script_identity(uint64_t base,const CallIdentity&id){
 const auto object=call_identity(base,id);if(!object||(local_read<uint32_t>(object+8)&0x40000000))return false;
 const auto cls=local_read<uint64_t>(object+0x10),outer=local_read<uint64_t>(object+0x20);if(!cls||!outer)return false;
 if(metadata_exact_style(base,object,cls,outer))return true;
 if(exact_name(base,cls+0x18,"Function"))return metadata_native_class(base,outer);
 if(exact_name(base,cls+0x18,"Class")||exact_name(base,cls+0x18,"Enum")||exact_name(base,cls+0x18,"ScriptStruct"))return metadata_script_package(base,outer);
 return (local_read<uint32_t>(object+8)&0x10)&&metadata_native_class(base,cls)&&
  outer==local_read<uint64_t>(cls+0x20)&&metadata_exact_cdo_name(base,object,cls);
}
template<class Pool>struct MetadataStabilizationOps{
 uint64_t base,session;Pool&pool;
 uint32_t admit(const CallIdentity&id)const{
  TargetStrongReferenceOps refs{base,id};return refs.can_assign()&&metadata_script_identity(base,id)?0:3921;
 }
 uint32_t preflight(uint32_t count)const{return uint32_t(pool.preflight(session,count));}
 uint32_t acquire(const CallIdentity&id,uint64_t&token)const{
  TargetStrongReferenceOps refs{base,id};return uint32_t(pool.acquire(refs,session,id.address,token));
 }
 bool stabilize(const CallIdentity&before,CallIdentity&after)const{
  TargetStrongReferenceOps refs{base,before};after=before;return stabilize_retained_identity(refs,after);
 }
 uint32_t active()const{return uint32_t(pool.active());}
};
