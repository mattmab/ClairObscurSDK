#pragma once
#include "invocation_protocol.h"
#include "text_call_protocol.h"
#include "string_call_frame.h"
#include "enum_call_protocol.h"
#include "asset_call_protocol.h"
#include "sequence_call_protocol.h"
#include "blueprint_trace_profile.h"
#include "blueprint_call_protocol.h"
#include "blueprint_name_resolution.h"
#include <cmath>
#include "call_rejection_diagnostics.h"
#include "picto_edit_profile.h"

#ifdef E33_EMPTY_TITLE_SESSION
inline bool (*cinematic_empty_trap_armed)(const CallIdentity&)=nullptr;
inline uint32_t (*cinematic_play_preflight)(uint64_t,const CallPacket&)=nullptr;
#endif
#ifdef E33_SEQUENCE_ORIGIN_SESSION
inline uint32_t (*sequence_origin_play_preflight)(uint64_t,const CallPacket&)=nullptr;
#endif

// Uses the target's own dispatcher, with no thunk ABI emulation or promise that
// an RPC body ran. The optional retention sink owns object outputs before return.
// Nontrivial text requires a separate explicit callback table and durable frame;
// existing session callers do not opt in to that candidate path.
inline uint64_t call_identity(uint64_t base, const CallIdentity& id) {
    auto value=fixed_slot(base,id.index,id.serial);
    return value && value==id.address ? value : 0;
}
inline bool call_derives(uint64_t base,uint64_t cls,uint64_t expected) {
    for(unsigned ancestry_depth=0;cls && ancestry_depth<128;++ancestry_depth) {
        auto index=local_read<int32_t>(cls+0xc);
        // Validate registration without assuming classes have nonzero serials.
        int32_t count=local_read<int32_t>(base+0x9361b84);
        if(index<0 || index>=count) return false;
        auto chunks=local_read<uint64_t>(base+0x9361b70);
        auto slot=local_read<uint64_t>(chunks+uint64_t(index>>16)*8)+uint64_t(index&65535)*24;
        if(local_read<uint64_t>(slot)!=cls) return false;
        if(cls==expected) return true;
        cls=local_read<uint64_t>(cls+0x40);
    }
    return false;
}
inline CallIdentity call_capture(uint64_t base,uint64_t object) {
    if(!object) return {-1,0,0};
    auto index=local_read<int32_t>(object+0xc);
    auto count=local_read<int32_t>(base+0x9361b84);
    if(index<0 || index>=count) return {-1,0,0};
    auto chunks=local_read<uint64_t>(base+0x9361b70);
    auto slot=local_read<uint64_t>(chunks+uint64_t(index>>16)*8)+uint64_t(index&65535)*24;
    if(local_read<uint64_t>(slot)!=object) return {-1,0,0};
    return {index,local_read<int32_t>(slot+0x10),object};
}
inline bool call_is_class(uint64_t base,uint64_t object) {
    auto type=local_read<uint64_t>(object+0x10);
    for(unsigned step=0;type && step<128;++step) {
        if(!call_capture(base,type).address) return false;
        if(exact_name(base,type+0x18,"Class")) return true;
        type=local_read<uint64_t>(type+0x40);
    }
    return false;
}
#ifdef E33_GAME_OWNED_CINEMATIC_SESSION
#include "target_game_owned_cinematic.h"
#include "target_scavenger_repeat.h"
#endif

struct CallRetention {
    void* context;
    uint32_t (*preflight)(void*,const CallPacket&);
    uint32_t (*capture)(void*,uint32_t,CallIdentity&);
};
struct CallPodValidation {
    bool (*validate)(uint64_t,uint64_t,PodValueKind,const CallIdentity&);
};
struct CallTextHandling {
    TextCallPacket* packet;
    uint8_t* arguments; // Durable native-session storage, not the wire buffer.
    void* context;
    bool (*available)(void*);
    uint32_t (*prepare)(void*);
    uint32_t (*begin)(void*);
    uint32_t (*returned)(void*);
    uint32_t (*finish)(void*);
    bool strings=false;
};
struct CallEnumValidation {
    RetainedCallPacket* packet;
    // Null value validates an output's type without treating zero as an input.
    bool (*validate)(uint64_t,uint64_t,const CallIdentity&,const uint8_t*);
};
struct CallEntryValidation {
    bool (*owned)(uint64_t address, uint64_t expected, uint64_t current);
};
struct CallAssetValidation {
    RetainedCallPacket* packet;
    bool (*validate)(uint64_t,uint64_t,const CallIdentity&,const uint8_t*);
};
struct CallSequenceValidation {
    RetainedCallPacket* packet;
    bool (*validate)(uint64_t,uint64_t,const CallIdentity&);
};
inline bool call_entry_matches(uint64_t address, uint64_t expected, const CallEntryValidation* validator) {
    const auto current = local_read<uint64_t>(address);
    return current == expected || (validator && validator->owned && validator->owned(address, expected, current));
}
inline bool call_blueprint_name(uint64_t base,uint64_t fname) {
    const auto id=local_read<uint32_t>(fname);
    if((id>>16)>=8192)return false;
    const auto block=local_read<uint64_t>(base+0x92aadc0+0x10+uint64_t(id>>16)*8);
    if(!block)return false;
    const auto at=block+(id&65535)*2;
    const auto header=local_read<uint16_t>(at);
    const auto length=header>>6;
    if((header&1) || !length || (id&65535)*2+2+length>0x20000)return false;
    return length<16 || std::memcmp(reinterpret_cast<void*>(at+2),"ExecuteUbergraph",16)!=0;
}
inline uint32_t reflected_call(uint64_t base,CallPacket& packet,const CallRetention* retention=nullptr,
                               const CallPodValidation* pod=nullptr,const CallTextHandling* text=nullptr,
                               const CallEnumValidation* enums=nullptr,bool validate_only=false,
                               const CallEntryValidation* entry_validation=nullptr, bool blueprint_observation=false,
                               const CallAssetValidation* assets=nullptr,const CallSequenceValidation* sequence=nullptr,
                               uint32_t* rejection_detail=nullptr) {
    if(rejection_detail) *rejection_detail=0;
    const bool pod_enabled=pod && pod->validate;
    const bool blueprint_enabled=packet.version==kBlueprintCallVersion && pod_enabled &&
        retention && retention->preflight && retention->capture && !text && !enums && !assets && !sequence;
    const bool asset_enabled=assets && assets->packet && &assets->packet->call==&packet && assets->validate &&
        pod_enabled && retention && retention->preflight && retention->capture && !text && !enums;
    if(assets && !asset_enabled) return 1453;
    const bool sequence_enabled=sequence && sequence->packet && &sequence->packet->call==&packet && sequence->validate &&
        pod_enabled && retention && retention->preflight && retention->capture && !text && !enums && !assets;
    if(sequence && !sequence_enabled) return 1463;
    const bool enum_enabled=enums && enums->packet && &enums->packet->call==&packet && enums->validate &&
        pod_enabled && retention && retention->preflight && retention->capture && !text;
    if(enums && !enum_enabled) return 753;
    const bool text_enabled=text && text->packet && &text->packet->retained.call==&packet &&
        text->arguments && text->context && text->available && text->prepare && text->begin && text->returned && text->finish &&
        pod_enabled && retention && retention->preflight && retention->capture;
    if(text && !text_enabled) return 227;
    // Never overwrite a frame still owning uncertain native arguments.
    if(text_enabled && !text->available(text->context)) return 230;
    if(auto invalid=blueprint_enabled ? validate_blueprint_call(packet) : sequence_enabled ? validate_sequence_call(*sequence->packet) : asset_enabled ? validate_asset_call(*assets->packet) : enum_enabled ? validate_enum_call(*enums->packet) :
       text_enabled ? (text->strings ? validate_string_call(*text->packet) : validate_text_call(*text->packet)) : validate_call_packet(packet,pod_enabled)) return invalid;
    packet.outcome=CallNotDispatched;
    if((packet.version!=kCallVersion && !blueprint_enabled && !(sequence_enabled && packet.version==kSequenceCallVersion) && !(asset_enabled && packet.version==kAssetCallVersion) && !(pod_enabled && packet.version==kPodCallVersion) && !(text_enabled && (packet.version==kTextCallVersion || (text->strings && packet.version==kStringCallVersion))) && !(enum_enabled && packet.version==kEnumCallVersion)) || packet.parameter_size>kCallBytes ||
       packet.parameter_size>packet.allocation_extent || packet.allocation_extent>65536 ||
       packet.field_count>kCallFields || packet.object_count>kCallObjects) return 200;
    if(local_read<DWORD>(base+0x9272d30)!=GetCurrentThreadId() ||
       local_read<uint8_t>(base+0x9272cfc) || local_read<uint8_t>(base+0x934e968)) return 201;
    auto object=call_identity(base,packet.target), function=call_identity(base,packet.function);
    // Keep the original short circuit: never read target flags unless both
    // identities match. Capture why this exact guard rejected before returning.
    const bool forbidden=object && function && (local_read<uint32_t>(object+8)&0x40000000);
    if(!object || !function || forbidden) {
        if(rejection_detail) *rejection_detail=call_identity_rejection_detail(object!=0,function!=0,forbidden);
        return 202;
    }
    auto fn_class=local_read<uint64_t>(function+0x10);
    auto owner=local_read<uint64_t>(function+0x20);
    if(!exact_name(base,fn_class+0x18,"Function") ||
       !call_derives(base,local_read<uint64_t>(object+0x10),owner)) return 203;
    if(asset_enabled && (!exact_name(base,function+0x18,packet.entry_rva==0x3860250?"LoadClassAsset_Blocking":"LoadAsset_Blocking") ||
       !exact_name(base,owner+0x18,"KismetSystemLibrary") ||
       !exact_name(base,local_read<uint64_t>(owner+0x20)+0x18,"/Script/Engine") ||
       !exact_name(base,object+0x18,"Default__KismetSystemLibrary"))) return 1454;
    if(sequence_enabled && (!exact_name(base,function+0x18,"CreateLevelSequencePlayer") ||
       !exact_name(base,owner+0x18,"LevelSequencePlayer") ||
       !exact_name(base,local_read<uint64_t>(owner+0x20)+0x18,"/Script/LevelSequence") ||
       !exact_name(base,object+0x18,"Default__LevelSequencePlayer") ||
       !(local_read<uint32_t>(object+8)&0x10))) return 1466;
    if(local_read<uint32_t>(function+0xb0)!=packet.function_flags ||
       local_read<uint16_t>(function+0xb6)!=packet.parameter_size ||
       local_read<uint16_t>(function+0xb8)!=packet.return_offset ||
       local_read<int32_t>(function+0x58)!=static_cast<int32_t>(packet.allocation_extent) ||
       packet.entry_rva>=166776832 || !call_entry_matches(function+0xd8,base+packet.entry_rva,entry_validation)) return 204;
    // V8 is an explicit Blueprint opt-in; ordinary calls retain the ban.
    // Verify actual engine thunk and nonempty Script, not a caller address.
    if(blueprint_enabled && (!blueprint_function_admitted(packet.function_flags,packet.entry_rva,"Function") ||
       !call_blueprint_name(base,function+0x18) ||
       local_read<uint64_t>(function+0xd8)!=base+kBlueprintThunkRva ||
       !local_read<uint64_t>(function+0x60) || local_read<int32_t>(function+0x68)<=0 ||
       local_read<int32_t>(function+0x68)>16*1024*1024 ||
       local_read<int32_t>(function+0x6c)<local_read<int32_t>(function+0x68)))return 1472;
    bool game_owned_blueprint=false;
#ifdef E33_GAME_OWNED_CINEMATIC_SESSION
    if(!(packet.function_flags&0x400)) {
        TargetGameOwnedCinematic admission{base,object,function,owner};
        game_owned_blueprint=admit_game_owned_cinematic(admission,packet);
    }
#endif
    if(!(packet.function_flags&0x400) && !blueprint_enabled && !game_owned_blueprint && !admit_picto_edit(base,object,function,owner,packet) && !(blueprint_observation && validate_only &&
        blueprint_damage_schema(packet) && exact_name(base,function+0x18,"OnCharacterReceivedDamages") &&
        exact_name(base,owner+0x18,"BP_BattleSummaryStatsManager_C"))) return 205;
    auto dispatch=local_read<uint64_t>(local_read<uint64_t>(object)+0x268);
    if(dispatch!=base+0x1393330 && dispatch!=base+0x332bb90) return 206;
    alignas(16) uint8_t local_arguments[kCallBytes]{};
    auto arguments=text_enabled ? text->arguments : local_arguments;
    uint8_t used[kCallBytes]{};
    uint64_t enum_properties[kCallFields]{};
    std::memcpy(arguments,packet.data,packet.parameter_size);
    auto property=local_read<uint64_t>(function+0x50);
    unsigned seen=0, walked=0, returns=0;
    const char* kinds[]={"", "BoolProperty","ByteProperty","UInt16Property","IntProperty",
                         "FloatProperty","DoubleProperty","ObjectProperty","ClassProperty",
                         "StructProperty","StructProperty","StructProperty","StructProperty","TextProperty","EnumProperty","StructProperty","StrProperty","SoftObjectProperty","StructProperty","StructProperty","StructProperty","NameProperty","StructProperty"};
    static_assert(sizeof(kinds)/sizeof(kinds[0])==CallGuid+1, "Reflected kind table must cover every admitted kind");
    for(;property;property=local_read<uint64_t>(property+0x18)) {
        if(++walked>4096) return 207;
        auto flags=local_read<uint64_t>(property+0x38);
        if(!(flags&0x80)) continue;
        if(seen>=packet.field_count) return 208;
        const auto& field=packet.fields[seen++];
        if(field.kind>=sizeof(kinds)/sizeof(kinds[0]) || field.kind<CallBool || (field.kind>(sequence_enabled ? kSequenceSettingsKind : asset_enabled ? kAssetCallKind : enum_enabled ? kEnumCallKind : text_enabled ? (text->strings ? kStringCallKind : kTextCallKind) : pod_enabled && (packet.version==kPodCallVersion || blueprint_enabled) ? CallAnchors : CallClass) && !(blueprint_enabled && field.kind==kBlueprintNameKind) && !(pod_enabled && (field.kind==CallGuid || field.kind==CallVector || frame_time_call_enabled(field.kind) || timespan_call_enabled(field.kind)))) || !field.name[0] || field.name[95] ||
           field.flags!=flags || local_read<uint64_t>(property+0x10)!=(function|1) ||
           !exact_name(base,property+0x20,field.name) ||
           !exact_name(base,local_read<uint64_t>(property+8),(asset_enabled && packet.entry_rva==0x3860250 && field.kind==kAssetCallKind)?"SoftClassProperty":kinds[field.kind]) ||
           field.offset!=local_read<uint32_t>(property+0x44) || field.width!=local_read<uint32_t>(property+0x34) ||
           field.dimension!=local_read<uint32_t>(property+0x30) || !field.dimension || field.dimension>64 ||
           !field.width || uint64_t(field.offset)+uint64_t(field.width)*field.dimension>packet.parameter_size) return 209;
        if(flags&0x400) { ++returns; if(field.offset!=packet.return_offset || field.dimension!=1) return 210; }
        unsigned width=field.kind==CallByte ? 1 : field.kind==CallUInt16 ? 2 :
            field.kind==CallInt32 || field.kind==CallFloat ? 4 : 8;
        if(field.kind==kSequenceSettingsKind) {
            width=40;
            if(!sequence_enabled || !sequence->validate(base,property,field.constraint)) return 1464;
        }
        if(field.kind==kAssetCallKind) {
            width=40;
            if(!asset_enabled || !assets->validate(base,property,field.constraint,arguments+field.offset)) return 1455;
        }
        if(field.kind==kEnumCallKind) {
            const bool input=!(flags&0x400) && (!(flags&0x100) || (flags&0x8000000));
            width=1;
            if(!enum_enabled || !enums->validate(base,property,field.constraint,
                                               input ? arguments+field.offset : nullptr)) return 754;
            enum_properties[seen-1]=property;
        }
        if(field.kind==kStringCallKind) {
            width=16;
            const bool file=exact_name(base,function+0x18,"SetFilePath")&&exact_name(base,owner+0x18,"FileMediaSource")&&
                exact_name(base,local_read<uint64_t>(owner+0x20)+0x18,"/Script/MediaAssets");
            const bool texture=exact_name(base,function+0x18,"ImportFileAsTexture2D")&&exact_name(base,owner+0x18,"KismetRenderingLibrary")&&
                exact_name(base,local_read<uint64_t>(owner+0x20)+0x18,"/Script/Engine")&&
                exact_name(base,object+0x18,"Default__KismetRenderingLibrary")&&(local_read<uint32_t>(object+8)&0x10);
            if(!text_enabled || !text->strings || local_read<uint64_t>(property)!=base+0x6e131d8 ||
               local_read<uint64_t>(base+0x6e132e8)!=base+0x133a600 ||
               local_read<uint64_t>(base+0x6e132c8)!=base+0x1368400 ||
               local_read<uint64_t>(base+0x6e13258)!=base+0x10044f0 ||
               (!file&&!texture)) return 764;
        }
        if(field.kind==kTextCallKind) {
            width=16;
            if(!text_enabled || local_read<uint64_t>(property)!=base+0x6e1ba00 || field.dimension!=1) return 228;
        }
        if(field.kind==CallTimespan) {
            if(!timespan_call_enabled(field.kind) || !timespan_media_packet(packet) ||
               !call_capture(base,owner).address || !exact_name(base,owner+0x18,"MediaPlayer") ||
               !exact_name(base,local_read<uint64_t>(owner+0x20)+0x18,"/Script/MediaAssets") ||
               !exact_name(base,function+0x18,packet.entry_rva==0x3208990 ? "GetTime" : "GetDuration")) return 225;
        }
        if(field.kind==CallQualifiedFrameTime && (packet.version!=kPodCallVersion || !(field.flags&0x400) || field.dimension!=1 || !frame_time_call_enabled(field.kind))) return 225;
        if(call_pod_kind(field.kind)) {
            width=pod_value_width(call_pod_profile(field.kind));
            if(!pod->validate(base,property,call_pod_profile(field.kind),field.constraint)) return 225;
        }
        uint8_t mask=255, byte_offset=0;
        if(field.kind==CallBool) {
            auto encoding=local_read<uint32_t>(property+0x70);
            mask=uint8_t(encoding>>24); byte_offset=uint8_t(encoding>>8);
            auto byte_mask=uint8_t(encoding>>16);
            if(encoding!=field.bool_encoding || !mask || !byte_mask || (byte_mask&~mask) ||
               (byte_mask&(byte_mask-1)) || uint8_t(encoding)!=field.width || byte_offset>=field.width) return 211;
            width=field.width;
        }
        if(field.width!=width) return 212;
        if(field.kind==kBlueprintNameKind) {
            uint64_t name=0;
            if(!blueprint_enabled || !e33_blueprint_names::resolve(base,field.name+std::strlen(field.name)+1,name))return 1474;
            std::memcpy(arguments+field.offset,&name,8);
        }
        for(unsigned element=0;element<field.dimension;++element) {
            auto at=field.offset+element*width;
            for(unsigned byte=0;byte<width;++byte) {
                uint8_t bits=field.kind==CallBool ? (byte==byte_offset ? mask : 0) : 255;
                if(used[at+byte]&bits) return 213;
                used[at+byte]|=bits;
            }
            if(field.kind==CallFloat && !std::isfinite(local_read<float>(reinterpret_cast<uint64_t>(arguments+at)))) return 214;
            if(field.kind==CallDouble && !std::isfinite(local_read<double>(reinterpret_cast<uint64_t>(arguments+at)))) return 214;
            if(field.kind==CallObject || field.kind==CallClass) {
                if(local_read<uint64_t>(reinterpret_cast<uint64_t>(arguments+at))) return 215;
                auto constraint=call_identity(base,field.constraint);
                if(!constraint || !call_is_class(base,constraint) || local_read<uint64_t>(property+(field.kind==CallClass ? 0x78 : 0x70))!=constraint) return 216;
                unsigned matches=0;
                for(unsigned j=0;j<packet.object_count;++j) if(packet.objects[j].offset==at) {
                    if(++matches>1 || (flags&0x400) || ((flags&0x100) && !(flags&0x8000000))) return 217;
                    auto argument=call_identity(base,packet.objects[j].identity);
                    if(!argument || (field.kind==CallClass && !call_is_class(base,argument)) ||
                       !call_derives(base,field.kind==CallClass ? argument : local_read<uint64_t>(argument+0x10),constraint)) return 218;
                    std::memcpy(arguments+at,&argument,8);
                }
            }
        }
    }
    if(seen!=packet.field_count || returns>1 || ((packet.return_offset==65535)!=(returns==0))) return 219;
    for(unsigned j=0;j<packet.object_count;++j) {
        bool matched=false;
        for(unsigned f=0;f<packet.field_count;++f) {
            const auto& field=packet.fields[f];
            if(field.kind!=CallObject && field.kind!=CallClass) continue;
            for(unsigned i=0;i<field.dimension;++i) if(packet.objects[j].offset==field.offset+i*8) matched=true;
        }
        if(!matched) return 220;
    }
    // Read-only schema/identity preflight for durable native cleanup plans.
    // Stop before ownership callbacks, text construction or ProcessEvent.
    if(validate_only) return 0;
    if(retention) {
        auto error=retention->preflight(retention->context,packet);
        if(error) return error;
    }
    if(text_enabled) {
        if(auto error=text->prepare(text->context)) return error;
        // Native constructors may allocate. Revalidate identities and context
        // before placing owned text values into the actual invocation frame.
        if(call_identity(base,packet.target)!=object || call_identity(base,packet.function)!=function ||
           local_read<DWORD>(base+0x9272d30)!=GetCurrentThreadId() || local_read<uint8_t>(base+0x9272cfc) ||
           local_read<uint8_t>(base+0x934e968) || local_read<uint8_t>(base+0x9272cea) ||
           (local_read<uint32_t>(object+8)&0x40000000) ||
           !call_entry_matches(function+0xd8,base+packet.entry_rva,entry_validation) ||
           local_read<uint64_t>(local_read<uint64_t>(object)+0x268)!=dispatch) return 229;
        for(unsigned i=0;i<packet.object_count;++i)
            if(!call_identity(base,packet.objects[i].identity)) return 229;
        if(auto error=text->begin(text->context)) return error;
    }
#ifdef E33_EMPTY_TITLE_SESSION
    if(cinematic_play_preflight) {
        if(auto error=cinematic_play_preflight(base,packet)) return error;
    }
#endif
#ifdef E33_SEQUENCE_ORIGIN_SESSION
    if(sequence_origin_play_preflight) {
        if(auto error=sequence_origin_play_preflight(base,packet)) return error;
    }
#endif
#ifdef E33_GAME_OWNED_CINEMATIC_SESSION
    bool scoped_scavenger_repeat=false;
    ScavengerRepeatGuard repeat_guard{};
    TargetScavengerRepeat repeat_source{{base,object,function,owner},{},0};
    if(game_owned_blueprint) {
        TargetGameOwnedCinematic admission{base,object,function,owner};
        if(call_identity(base,packet.target)!=object || call_identity(base,packet.function)!=function ||
           local_read<DWORD>(base+0x9272d30)!=GetCurrentThreadId() || local_read<uint8_t>(base+0x9272cfc) ||
           local_read<uint8_t>(base+0x934e968) || local_read<uint8_t>(base+0x9272cea) ||
           local_read<uint32_t>(function+0xb0)!=packet.function_flags ||
           !call_entry_matches(function+0xd8,base+packet.entry_rva,entry_validation) ||
           local_read<uint64_t>(local_read<uint64_t>(object)+0x268)!=dispatch ||
           !admit_game_owned_cinematic(admission,packet))return 229;
        if(game_owned_cinematic_packet(packet)==GameOwnedCinematicCall::execute_scavenger) {
            repeat_source.asset=packet.objects[0].identity;
            repeat_source.address=repeat_source.asset.address+48+234;
            if(game_owned_repeat_active || !repeat_guard.prepare(repeat_source))return 229;
            scoped_scavenger_repeat=true;
        }
    }
#endif
    packet.outcome=CallOutcomeUnknown; // A fault/timeout after this point cannot be retried safely.
    using Dispatch=void(__fastcall*)(void*,void*,void*);
#ifdef E33_GAME_OWNED_CINEMATIC_SESSION
    if(scoped_scavenger_repeat) {
        if(!dispatch_scavenger_repeat(dispatch,object,function,arguments,&repeat_source,&repeat_guard))return 229;
    } else
#endif
    reinterpret_cast<Dispatch>(dispatch)(reinterpret_cast<void*>(object),reinterpret_cast<void*>(function),arguments);
    if(asset_enabled && std::memcmp(arguments,packet.data,40)) return 1456;
    if(sequence_enabled && std::memcmp(arguments+16,packet.data+16,40)) return 1465;
    if(text_enabled) if(auto error=text->returned(text->context)) return error;
    // Capture and scrub all pointer slots, including input references. Never
    // publish raw pointer bytes as return values. Only the explicit retention
    // sink acquires ownership; the established v6/v7 path remains observational.
    packet.object_count=0;
    for(unsigned f=0;f<packet.field_count;++f) {
        const auto& field=packet.fields[f];
        if(field.kind==kEnumCallKind &&
           !enums->validate(base,enum_properties[f],field.constraint,arguments+field.offset)) return 755;
        if(field.kind==CallTimespan) {
            if(!timespan_call_enabled(field.kind) || !timespan_media_packet(packet) ||
               !call_capture(base,owner).address || !exact_name(base,owner+0x18,"MediaPlayer") ||
               !exact_name(base,local_read<uint64_t>(owner+0x20)+0x18,"/Script/MediaAssets") ||
               !exact_name(base,function+0x18,packet.entry_rva==0x3208990 ? "GetTime" : "GetDuration")) return 225;
        }
        if(field.kind==CallQualifiedFrameTime && (packet.version!=kPodCallVersion || !(field.flags&0x400) || field.dimension!=1 || !frame_time_call_enabled(field.kind))) return 225;
        if(call_pod_kind(field.kind)) {
            for(unsigned i=0;i<field.dimension;++i)
                if(!valid_pod_value(call_pod_profile(field.kind),arguments+field.offset+i*field.width,field.width)) return 226;
        }
        if(field.kind==kBlueprintNameKind) {
            // Input-only registered names never leak raw FName IDs to Python.
            std::memset(arguments+field.offset,0,8);
        }
        if(field.kind!=CallObject && field.kind!=CallClass) continue;
        for(unsigned i=0;i<field.dimension;++i) {
            auto offset=field.offset+i*8;
            auto value=local_read<uint64_t>(reinterpret_cast<uint64_t>(arguments+offset));
            if(value) {
                if(packet.object_count>=kCallObjects) return 221;
                auto identity=call_capture(base,value);
                if(!identity.address) return 222;
                auto constraint=call_identity(base,field.constraint);
                if(!constraint || (field.kind==CallClass && !call_is_class(base,value)) ||
                   !call_derives(base,field.kind==CallClass ? value : local_read<uint64_t>(value+0x10),constraint)) return 224;
                if(retention && (field.flags&0x500)) {
                    auto error=retention->capture(retention->context,offset,identity);
                    if(error) return error; // Session still owns every acquired holder.
                }
                packet.objects[packet.object_count++]={offset,identity};
            }
            std::memset(arguments+offset,0,8);
        }
    }
    if(!call_identity(base,packet.target) || !call_identity(base,packet.function)) return 223;
    if(text_enabled) if(auto error=text->finish(text->context)) return error;
    std::memcpy(packet.data,arguments,packet.parameter_size);
    packet.outcome=CallDispatchReturned;
    return 0;
}
