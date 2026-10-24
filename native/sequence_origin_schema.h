#pragma once
#include <cstdint>
// Shared exact descriptor profile; target and adversarial fake-memory fixture
// execute the same bounded metadata validation.
template<class Ops> class SequenceOriginSchema {
    Ops& ops_;
public:
    explicit SequenceOriginSchema(Ops& ops):ops_(ops){}
    bool private_instance(uint64_t actor,uint64_t instance) const {
        if(!ops_.registered(actor) || !ops_.registered(instance) ||
           (ops_.template read<uint32_t>(actor+8)&0x40018030U) ||
           (ops_.template read<uint32_t>(instance+8)&0x40018030U)) return false;
        const auto a=ops_.template read<uint64_t>(actor+16),d=ops_.template read<uint64_t>(instance+16);
        if(!ops_.is_class(a) || !ops_.is_class(d) || !named(a,"LevelSequenceActor","/Script/LevelSequence") ||
           !named(d,"DefaultLevelSequenceInstanceData","/Script/LevelSequence")) return false;
        const auto override_field=field(a,"bOverrideInstanceData","BoolProperty",760,1,0x6e119b0,6755468160532485ULL);
        const auto instance_field=field(a,"DefaultInstanceData","ObjectProperty",768,8,0x6e11d38,80501912059249164ULL);
        const auto origin_actor=field(d,"TransformOriginActor","ObjectProperty",48,8,0x6e11d38,79938962105303557ULL);
        const auto origin=field(d,"TransformOrigin","StructProperty",64,96,0x6e136a0,6755469234274309ULL);
        return override_field && ops_.template read<uint32_t>(override_field+0x70)==0x02020001 && instance_field &&
            ops_.is_class(ops_.template read<uint64_t>(instance_field+0x70)) &&
            named(ops_.template read<uint64_t>(instance_field+0x70),"Object","/Script/CoreUObject") && origin_actor &&
            ops_.is_class(ops_.template read<uint64_t>(origin_actor+0x70)) &&
            named(ops_.template read<uint64_t>(origin_actor+0x70),"Actor","/Script/Engine") && origin &&
            transform(ops_.template read<uint64_t>(origin+0x70)) &&
            ops_.template read<uint64_t>(instance+32)==actor && ops_.template read<uint64_t>(actor+768)==instance &&
            !ops_.template read<uint64_t>(instance+48);
    }
    bool named(uint64_t object,const char* name,const char* package) const {
        return ops_.registered(object) && ops_.name(object+24,name) &&
            ops_.registered(ops_.template read<uint64_t>(object+32)) &&
            ops_.name(ops_.template read<uint64_t>(object+32)+24,package);
    }
    uint64_t field(uint64_t owner,const char* name,const char* type,uint32_t offset,
                   uint32_t width,uint64_t table,uint64_t flags) const {
        auto p=ops_.template read<uint64_t>(owner+0x50);uint64_t found=0;
        for(unsigned i=0;p && i<128;++i,p=ops_.template read<uint64_t>(p+0x18)) {
            if(!ops_.name(p+0x20,name)) continue;
            if(found || ops_.template read<uint64_t>(p)!=ops_.base+table || ops_.template read<uint64_t>(p+0x10)!=(owner|1) ||
               !ops_.name(ops_.template read<uint64_t>(p+8),type) || ops_.template read<uint32_t>(p+0x30)!=1 ||
               ops_.template read<uint32_t>(p+0x34)!=width || ops_.template read<uint64_t>(p+0x38)!=flags ||
               ops_.template read<uint32_t>(p+0x44)!=offset) return 0;
            found=p;
        }
        return !p ? found : 0;
    }
    bool scalar_struct(uint64_t s,const char* name,unsigned count) const {
        if(!named(s,name,"/Script/CoreUObject") || ops_.template read<uint32_t>(s+0x58)!=count*8 ||
           ops_.template read<uint64_t>(s+0x40) || !named(ops_.template read<uint64_t>(s+16),"ScriptStruct","/Script/CoreUObject")) return false;
        const char* names[]={"X","Y","Z","W"};auto p=ops_.template read<uint64_t>(s+0x50);
        for(unsigned i=0;i<count;++i) {
            if(!p || p!=field(s,names[i],"DoubleProperty",i*8,8,0x6e11788,6755469251052037ULL)) return false;
            p=ops_.template read<uint64_t>(p+0x18);
        }
        return !p;
    }
    bool transform(uint64_t s) const {
        if(!named(s,"Transform","/Script/CoreUObject") || ops_.template read<uint32_t>(s+0x58)!=96 ||
           ops_.template read<uint64_t>(s+0x40) || !named(ops_.template read<uint64_t>(s+16),"ScriptStruct","/Script/CoreUObject")) return false;
        const char* names[]={"Rotation","Translation","Scale3D"};const unsigned widths[]={32,24,24};
        auto p=ops_.template read<uint64_t>(s+0x50);
        for(unsigned i=0;i<3;++i) {
            if(!p || p!=field(s,names[i],"StructProperty",i*32,widths[i],0x6e136a0,
                    i ? 6755469251052037ULL : 6755469251051525ULL) ||
               !scalar_struct(ops_.template read<uint64_t>(p+0x70),i ? "Vector" : "Quat",i ? 3 : 4)) return false;
            p=ops_.template read<uint64_t>(p+0x18);
        }
        return !p;
    }
};
