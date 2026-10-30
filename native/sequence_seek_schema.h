#pragma once
#include "sequence_origin_schema.h"
#include "enum_schema.h"

// Exact supported executable reflection profile. No generic non-POD struct
// admission is added to the public invocation dispatcher.
template<class Ops> class SequenceSeekSchema {
    Ops& ops_;
    SequenceOriginSchema<Ops> fields_;
    bool script(uint64_t object,const char* name,const char* package,uint32_t width) const {
        return fields_.named(object,name,package) &&
            fields_.named(ops_.template read<uint64_t>(object+16),"ScriptStruct","/Script/CoreUObject") &&
            !ops_.template read<uint64_t>(object+0x40) && ops_.template read<uint32_t>(object+0x58)==width;
    }
    bool enumeration(uint64_t property,const char* name,const char* const* members,unsigned count) const {
        const auto id=ops_.capture(ops_.template read<uint64_t>(property+0x78));
        if(!validate_byte_enum_parameter(ops_,property,id) || !fields_.named(id.address,name,"/Script/MovieScene") ||
           ops_.template read<uint32_t>(id.address+0x48)!=count) return false;
        const auto data=ops_.template read<uint64_t>(id.address+0x40);
        for(unsigned i=0;i<count;++i)
            if(!ops_.name(data+i*16,members[i]) || ops_.template read<int64_t>(data+i*16+8)!=i) return false;
        return ops_.template read<uint64_t>(id.address+0x40)==data && ops_.identity(id);
    }
    bool timecode(uint64_t object) const {
        if(!script(object,"Timecode","/Script/CoreUObject",20))return false;
        const char* names[]={"Hours","Minutes","Seconds","Frames","bDropFrameFormat"};
        auto p=ops_.template read<uint64_t>(object+0x50);
        for(unsigned i=0;i<5;++i) {
            if(!p || p!=fields_.field(object,names[i],i==4 ? "BoolProperty" : "IntProperty",i*4,i==4 ? 1 : 4,
                    i==4 ? 0x6e119b0 : 0x6e10a98,6755469234274820ULL) ||
               (i==4 && ops_.template read<uint32_t>(p+0x70)!=0xff010001))return false;
            p=ops_.template read<uint64_t>(p+0x18);
        }
        return !p;
    }
    bool parameters(uint64_t object) const {
        if(!script(object,"MovieSceneSequencePlaybackParams","/Script/MovieScene",56))return false;
        const char* names[]={"Frame","Time","MarkedFrame","Timecode","PositionType","UpdateMethod","bHasJumped"};
        const char* types[]={"StructProperty","FloatProperty","StrProperty","StructProperty","EnumProperty","EnumProperty","BoolProperty"};
        const unsigned offsets[]={0,8,16,32,52,53,54},widths[]={8,4,16,20,1,1,1};
        const uint64_t tables[]={0x6e136a0,0x6e11560,0x6e131d8,0x6e136a0,0x6deeee8,0x6deeee8,0x6e119b0};
        const uint64_t flags[]={6755468160532485ULL,6755469234274821ULL,6755399441056261ULL,
            6755469234274821ULL,6755469234274821ULL,6755469234274821ULL,6755469234274821ULL};
        auto p=ops_.template read<uint64_t>(object+0x50);
        for(unsigned i=0;i<7;++i) {
            if(!p || p!=fields_.field(object,names[i],types[i],offsets[i],widths[i],tables[i],flags[i]))return false;
            if(i==0 && !validate_frame_time_schema(ops_,PodValueKind::FrameTime,ops_.capture(ops_.template read<uint64_t>(p+0x70))))return false;
            if(i==3 && !timecode(ops_.template read<uint64_t>(p+0x70)))return false;
            if(i==4) {
                const char* values[]={"EMovieScenePositionType::Frame","EMovieScenePositionType::Time","EMovieScenePositionType::MarkedFrame",
                    "EMovieScenePositionType::Timecode","EMovieScenePositionType::EMovieScenePositionType_MAX"};
                if(!enumeration(p,"EMovieScenePositionType",values,5))return false;
            }
            if(i==5) {
                const char* values[]={"EUpdatePositionMethod::Play","EUpdatePositionMethod::Jump","EUpdatePositionMethod::Scrub",
                    "EUpdatePositionMethod::EUpdatePositionMethod_MAX"};
                if(!enumeration(p,"EUpdatePositionMethod",values,4))return false;
            }
            if(i==6 && ops_.template read<uint32_t>(p+0x70)!=0xff010001)return false;
            p=ops_.template read<uint64_t>(p+0x18);
        }
        return !p;
    }
public:
    explicit SequenceSeekSchema(Ops& ops):ops_(ops),fields_(ops){}
    bool function(const CallIdentity& identity) const {
        const auto fn=identity.address;
        if(!ops_.context() || !ops_.identity(identity) || !ops_.name(fn+24,"SetPlaybackPosition") ||
           !fields_.named(ops_.template read<uint64_t>(fn+16),"Function","/Script/CoreUObject"))return false;
        const auto owner=ops_.template read<uint64_t>(fn+32);
        if(!ops_.is_class(owner) || !fields_.named(owner,"MovieSceneSequencePlayer","/Script/MovieScene") ||
           ops_.template read<uint32_t>(fn+0xb0)!=67240963 || ops_.template read<uint16_t>(fn+0xb6)!=56 ||
           ops_.template read<uint16_t>(fn+0xb8)!=65535 || ops_.template read<uint32_t>(fn+0x58)!=56 ||
           ops_.template read<uint64_t>(fn+0xd8)!=ops_.base+0x2d6a350)return false;
        const auto p=ops_.template read<uint64_t>(fn+0x50);
        return p && p==fields_.field(fn,"PlaybackParams","StructProperty",0,56,0x6e136a0,4503599627370624ULL) &&
            !ops_.template read<uint64_t>(p+0x18) && parameters(ops_.template read<uint64_t>(p+0x70)) &&
            ops_.identity(identity) && ops_.context();
    }
};
