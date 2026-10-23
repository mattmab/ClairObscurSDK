#pragma once
#include "mesh_owner.h"
#include "picto_progression.h"
// Extracted exact bounded owned-component traversal; no allocation or mutation.
namespace e33_owned_actor {
template<class Visit> inline bool visit_components(uint64_t b,uint64_t actor,Visit&& visit){
        using e33_mesh::named;
        uint64_t collected[1024]{};unsigned used=0;
        const char* names[]={"InstanceComponents","BlueprintCreatedComponents"};const int offsets[]={616,632};
        for(unsigned a=0;a<2;++a){
            uint64_t descriptor=0;
            const auto array=picto_field(b,actor,names[a],"ArrayProperty",offsets[a],16,&descriptor);
            if(!array||!descriptor)return false;
            const auto inner=local_read<uint64_t>(descriptor+0x78);
            if(!inner||local_read<uint64_t>(inner)!=b+0x6e11d38||local_read<uint64_t>(inner+0x10)!=descriptor||
               local_read<uint32_t>(inner+0x30)!=1||local_read<uint32_t>(inner+0x34)!=8||
               !named(b,local_read<uint64_t>(inner+0x70),"ActorComponent","/Script/Engine"))return false;
            const auto data=local_read<uint64_t>(array);
            const auto count=local_read<int32_t>(array+8),capacity=local_read<int32_t>(array+12);
            if(count<0||count>512||capacity<count||capacity>1024||(count&&(data<0x10000||(data&7))))return false;
            for(int32_t i=0;i<count;++i){
                const auto object=local_read<uint64_t>(data+uint64_t(i)*8);
                if(!object)continue;
                if(!call_identity(b,call_capture(b,object)))return false;
                if(local_read<uint32_t>(object+8)&0x40000030U)continue;
                if(local_read<uint64_t>(object+32)!=actor)return false;
                bool duplicate=false;for(unsigned j=0;j<used;++j)if(collected[j]==object)duplicate=true;
                if(!duplicate){if(used>=1024)return false;collected[used++]=object;}
            }
        }
        for(unsigned i=0;i<used;++i)if(!visit(collected[i]))return false;
        return true;
    }
}
