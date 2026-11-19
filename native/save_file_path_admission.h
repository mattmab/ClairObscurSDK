#pragma once
// One original read-only Blueprint FString helper. This does not admit other
// Blueprint text calls; the normal copied-string constructor/destructor gate
// still validates every parameter and owns all temporary/result storage.
inline bool admit_save_file_path(uint64_t base,uint64_t object,uint64_t function,uint64_t owner,const CallPacket&p){
#ifndef E33_GAME_OWNED_CINEMATIC_SESSION
 (void)base;(void)object;(void)function;(void)owner;(void)p;return false;
#else
 if(p.version!=kStringCallVersion||p.entry_rva!=0x13937a0||p.function_flags!=474218496U||p.parameter_size!=32||p.allocation_extent!=56||p.return_offset!=16||p.field_count!=2||p.object_count)return false;
 TargetGameOwnedCinematic proof{base,object,function,owner};
 if(!proof.live_target()||!proof.named(owner,"BP_SaveManager_C","/Game/Gameplay/Save/BP_SaveManager")||!exact_name(base,function+24,"ComputeSaveFilePath")||
  !local_read<uint64_t>(function+0x60)||local_read<int32_t>(function+0x68)<=0||local_read<int32_t>(function+0x68)>65536)return false;
 const char*names[]={"SaveName","ReturnValue","CallFunc_GetGameInstanceSubsystem_ReturnValue","CallFunc_ComputeSaveNameWithPath_ReturnValue"};
 const int offsets[]={0,16,32,40},widths[]={16,16,8,16};
 const uint64_t flags[]={2251799813685908ULL,2251799813687168ULL,2251868533162496ULL,2251799813685760ULL};
 auto field=local_read<uint64_t>(function+0x50);
 for(unsigned i=0;i<4;++i){const bool obj=i==2;
  if(!field||local_read<uint64_t>(field)!=base+(obj?0x6e11d38:0x6e131d8)||local_read<uint64_t>(field+16)!=(function|1)||
   !exact_name(base,field+32,names[i])||!exact_name(base,local_read<uint64_t>(field+8),obj?"ObjectProperty":"StrProperty")||
   local_read<int32_t>(field+0x30)!=1||local_read<int32_t>(field+0x34)!=widths[i]||local_read<int32_t>(field+0x44)!=offsets[i]||local_read<uint64_t>(field+0x38)!=flags[i])return false;
  if(obj&&!proof.named(local_read<uint64_t>(field+0x70),"PlatformsSubsystem","/Script/SandFall"))return false;
  if(i<2){const auto&f=p.fields[i];if(f.kind!=kStringCallKind||f.offset!=unsigned(offsets[i])||f.width!=16||f.dimension!=1||f.flags!=flags[i]||f.bool_encoding||std::strcmp(f.name,names[i]))return false;}
  field=local_read<uint64_t>(field+24);
 }
 if(field)return false;
 // Retain the ordinary current-manager/idle constraints independently of the
 // Python observer. Reflected offsets are read only after exact field checks.
 auto property=[&](uint64_t instance,const char*name,const char*kind,int width)->uint64_t{
  for(auto cls=local_read<uint64_t>(instance+16),class_depth=uint64_t(0);cls&&++class_depth<32;cls=local_read<uint64_t>(cls+0x40)){
   for(auto f=local_read<uint64_t>(cls+0x50),n=uint64_t(0);f&&++n<512;f=local_read<uint64_t>(f+24)){
    if(!exact_name(base,f+32,name))continue;
    if(local_read<uint64_t>(f+16)!=(cls|1)||!exact_name(base,local_read<uint64_t>(f+8),kind)||local_read<int32_t>(f+0x30)!=1||local_read<int32_t>(f+0x34)!=width)return 0;
    const int offset=local_read<int32_t>(f+0x44),extent=local_read<int32_t>(cls+0x58);if(offset<0||offset>extent-width)return 0;
    if(width==1&&local_read<uint32_t>(f+0x70)!=0xff010001U)return 0;
    return instance+unsigned(offset);
   }
  }return 0;
 };
 const auto gi_ref=property(object,"GameInstanceReference","ObjectProperty",8);
 const auto gi=gi_ref?local_read<uint64_t>(gi_ref):0;
 if(!proof.valid(gi)||(local_read<uint32_t>(gi+8)&0x40000030))return false;
 const auto manager=property(gi,"SaveManager","ObjectProperty",8),saving=property(object,"SaveIsInProgress","BoolProperty",1),loading=property(object,"LoadIsInProgress","BoolProperty",1);
 return manager&&local_read<uint64_t>(manager)==object&&saving&&loading&&!local_read<uint8_t>(saving)&&!local_read<uint8_t>(loading);
#endif
}
