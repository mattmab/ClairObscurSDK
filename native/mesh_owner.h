#pragma once
#include "mesh_protocol.h"
#include "mesh_profile.h"
#include "surface_query.h"
#include <vector>
#include <algorithm>
#include <string>

// Bounded static geometry, not a general pointer invocation interface.
// Only this owner can destroy its actor. Dispatch remains game-thread owned.
namespace e33_mesh {
inline bool named(uint64_t b,uint64_t o,const char* n,const char* package) {
    return call_capture(b,o).address && exact_name(b,o+24,n) &&
        exact_name(b,local_read<uint64_t>(o+32)+24,package);
}
// Full display-name equality for the observed candidate catalog, including FName numbers.
// No wildcard or prefix acceptance; baseline named() profiles remain unchanged.
inline bool candidate_name(uint64_t b,uint64_t at,const char* expected) {
    const auto number=local_read<uint32_t>(at+4);
    if(!number)return exact_name(b,at,expected);
    const auto suffix=std::string("_")+std::to_string(number-1);
    const std::string full(expected);
    if(full.size()<=suffix.size() || full.compare(full.size()-suffix.size(),suffix.size(),suffix)!=0)return false;
    const auto prefix=full.substr(0,full.size()-suffix.size());
    const uint64_t unnumbered=local_read<uint32_t>(at);
    return exact_name(b,reinterpret_cast<uint64_t>(&unnumbered),prefix.c_str());
}
inline bool candidate_named(uint64_t b,uint64_t o,const char* n,const char* package) {
    if(!call_capture(b,o).address || !candidate_name(b,o+24,n))return false;
    const auto outer=local_read<uint64_t>(o+32);
    return call_capture(b,outer).address && candidate_name(b,outer+24,package) &&
        named(b,local_read<uint64_t>(o+16),"MaterialInstanceConstant","/Script/Engine");
}
inline bool structure(uint64_t,uint64_t,const char*,int);
inline bool fields(uint64_t b,uint64_t owner,const MeshField* expected,size_t count) {
    auto f=local_read<uint64_t>(owner+0x50);
    for(size_t i=0;i<count;++i) {
        const auto& e=expected[i];
        if(!f || local_read<uint64_t>(f)!=b+e.table || local_read<uint64_t>(f+16)!=(owner|1) ||
           !exact_name(b,f+32,e.name) || !exact_name(b,local_read<uint64_t>(f+8),e.type) ||
           local_read<int32_t>(f+0x30)!=1 || local_read<int32_t>(f+0x34)!=e.width ||
           local_read<int32_t>(f+0x44)!=e.offset || local_read<uint64_t>(f+0x38)!=e.flags) return false;
        if(e.boolean && local_read<uint32_t>(f+0x70)!=e.boolean) return false;
        if(*e.structure && !structure(b,local_read<uint64_t>(f+0x70),e.structure,e.width)) return false;
        if(*e.constraint) {
            auto cls=local_read<uint64_t>(f+(!std::strcmp(e.type,"ClassProperty")?0x78:0x70));
            const char* pkg=!std::strcmp(e.constraint,"Object")?"/Script/CoreUObject":
                (!std::strcmp(e.constraint,"PhysicalMaterial")?"/Script/PhysicsCore":"/Script/Engine");
            if(!named(b,cls,e.constraint,pkg) || !call_is_class(b,cls)) return false;
        }
        if(*e.inner) {
            const bool array=!std::strcmp(e.type,"ArrayProperty");
            if(array && (local_read<uint8_t>(f+0x70)&1))return false;
            auto inner=local_read<uint64_t>(f+(array?0x78:0x70));
            if(!inner || local_read<uint64_t>(inner+16)!=f ||
               !exact_name(b,local_read<uint64_t>(inner+8),e.inner) ||
               local_read<int32_t>(inner+0x30)!=1 || local_read<int32_t>(inner+0x34)!=e.inner_width) return false;
            if(*e.inner_structure) {
                auto s=local_read<uint64_t>(inner+0x70);
                // Tangents are always empty in this proof; no tangent element is read or written.
                if(!std::strcmp(e.inner_structure,"ProcMeshTangent")) {
                    if(!named(b,s,"ProcMeshTangent","/Script/ProceduralMeshComponent") || local_read<int32_t>(s+0x58)!=32)return false;
                } else if(!structure(b,s,e.inner_structure,e.inner_width)) return false;
            }
        }
        f=local_read<uint64_t>(f+24);
    }
    return !f;
}
inline bool structure(uint64_t b,uint64_t s,const char* name,int width) {
    // Opaque native-produced hit result: only passed from verified LineTrace
    // to verified BreakHitResult; no caller bytes or internal offsets accepted.
    if(!std::strcmp(name,"HitResult"))return width==248 && named(b,s,name,"/Script/Engine") && local_read<int32_t>(s+0x58)==248;
    if(!named(b,s,name,"/Script/CoreUObject") || local_read<int32_t>(s+0x58)!=width)return false;
    if(!std::strcmp(name,"Rotator")) {
        static const MeshField r[]={{"Pitch","DoubleProperty",0,8,0x18001041000205ULL,0x6e11788ULL,"","",0,"",0U,""},
{"Yaw","DoubleProperty",8,8,0x18001041000205ULL,0x6e11788ULL,"","",0,"",0U,""},
{"Roll","DoubleProperty",16,8,0x18001041000205ULL,0x6e11788ULL,"","",0,"",0U,""}};
        return fields(b,s,r,3);
    }
    if(!std::strcmp(name,"Transform"))return fields(b,s,mesh_Transform,3);
    if(!std::strcmp(name,"Quat"))return fields(b,s,mesh_Quat,4);
    TargetPodSchemaOps ops{b};
    if(!std::strcmp(name,"Vector"))return validate_pod_schema(ops,PodValueKind::Vector,call_capture(b,s));
    if(!std::strcmp(name,"Vector2D"))return validate_pod_schema(ops,PodValueKind::Vector2D,call_capture(b,s));
    if(!std::strcmp(name,"LinearColor"))return validate_pod_schema(ops,PodValueKind::LinearColor,call_capture(b,s));
    return false;
}
inline bool function(uint64_t b,const CallIdentity& id,size_t i) {
    auto fn=call_identity(b,id);const auto& p=mesh_functions[i];
    auto owner=fn?local_read<uint64_t>(fn+32):0;
    return fn && exact_name(b,local_read<uint64_t>(fn+16)+24,"Function") &&
        exact_name(b,fn+24,p.name) && named(b,owner,p.owner,
            !std::strcmp(p.owner,"ProceduralMeshComponent")?"/Script/ProceduralMeshComponent":"/Script/Engine") &&
        local_read<uint32_t>(fn+0xb0)==p.flags && local_read<uint16_t>(fn+0xb6)==p.params &&
        local_read<uint16_t>(fn+0xb8)==p.returned && local_read<int32_t>(fn+0x58)==int(p.extent) &&
        local_read<uint64_t>(fn+0xd8)==b+p.entry && fields(b,fn,p.fields,p.count);
}
inline bool dispatch(uint64_t b,const CallIdentity& recipient,const CallIdentity& fn,size_t index,void* args) {
    if(!TargetPodSchemaOps{b}.context() || !function(b,fn,index))return false;
    auto o=call_identity(b,recipient);if(!o || !call_derives(b,local_read<uint64_t>(o+16),local_read<uint64_t>(fn.address+32)))return false;
    auto pe=local_read<uint64_t>(local_read<uint64_t>(o)+0x268);
    if(pe!=b+0x1393330 && pe!=b+0x332bb90)return false;
    reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(pe)(reinterpret_cast<void*>(o),reinterpret_cast<void*>(fn.address),args);
    return true;
}
struct Vec {double x,y,z;};
struct Array {const void* data;int32_t num,max;};
static_assert(sizeof(Vec)==24 && sizeof(Array)==16,"mesh local layout");
inline void transform(uint8_t* p,const double* position) {
    const double one=1.;std::memcpy(p+24,&one,8);
    if(position)std::memcpy(p+32,position,24);
    for(int i=0;i<3;++i)std::memcpy(p+64+i*8,&one,8);
}
#include "mesh_skin.h"
class Owner {
    Skin skin_;
    uint32_t section_vertices_[64]{};
    uint64_t owner_=0,tokens_[130]{};
    uint32_t section_count_=0,total_vertices_=0,total_pixels_=0;
    bool section_loaded_[64]{};
    std::vector<Vec> file_vertices_,file_normals_;
    std::vector<double> file_uv_;
    std::vector<int32_t> file_indices_;
    CallIdentity actor_{},component_{},pawn_{},material_{},texture_{},functions_[20]{};
    wchar_t texture_path_[512]{};
    Vec vertices_[256]{},normals_[256]{};
    double uv_[256][2]{};int32_t indices_[768]{};
    uint32_t state_=0,step_=0;bool destroyed_=false;
    double position_[3]{};
    // Durable buffers: never keep IPC storage as native cleanup state.
    alignas(16) uint8_t args_[464]{};
    bool call(uint64_t b,const CallIdentity& recipient,size_t fn) {
        step_=uint32_t(fn+1);return dispatch(b,recipient,functions_[fn],fn,args_);
    }
    void clear_args(){std::memset(args_,0,sizeof(args_));}
public:
    bool active()const{return state_!=0;}
    bool animating()const{return state_==1 && skin_.active();}
    template<class Pool> uint32_t poll(uint64_t b,uint64_t session,Pool& pool) {
        if(state_!=1 || !TargetPodSchemaOps{b}.context())return 0;
        bool retiring=!call_identity(b,pawn_);
        if(!retiring) {clear_args();if(!call(b,pawn_,11))return 1806;retiring=args_[0]!=0;}
        if(!retiring) {clear_args();if(!call(b,actor_,11))return 1806;retiring=args_[0]!=0;}
        if(!retiring && !skin_.update(b,component_,position_))retiring=true;
        return retiring?close(b,session,pool):0;
    }
    void reply(MeshPacket& p)const {
        p.state=state_;p.actor=actor_;p.component=component_;if(!p.step)p.step=skin_.restore_step()?1000+skin_.restore_step():step_;
        p.sections=state_==1?section_count_:0;std::memcpy(p.position,position_,24);
        if(p.operation==3){p.inputs[0]=skin_.driver();p.inputs[1]=skin_.asset();p.vertex_count=skin_.switch_ms();p.index_count=skin_.switch_count();}
    }
    template<class Pool> uint32_t close(uint64_t b,uint64_t session,Pool& pool) {
        if(!active())return 0;
        if(!TargetPodSchemaOps{b}.context())return 407;
        if(!skin_.restore(b))return 1833;
        if(state_==3)return 1808; // uncertain dispatch: do not retry mutations
        if(!destroyed_ && actor_.address) {
            const auto actor=call_identity(b,actor_);
            if(actor) {
                clear_args();if(!call(b,actor_,11))return 1802;
                const bool already_destroying=args_[0]!=0;
                if(!function(b,functions_[5],5))return 1802;
                if(!already_destroying) {
                    state_=3;clear_args();
                    if(!call(b,actor_,5)) {state_=2;return 1802;}
                }
            }
            destroyed_=true;state_=2;
        }
        for(int i=129;i>=0;--i)if(tokens_[i]) {
            TargetStrongReferenceOps ops{b,{-1,0,0}};
            const auto error=pool.release(ops,session,tokens_[i]);
            if(error!=StrongLeaseResult::Ok)return uint32_t(error);
            tokens_[i]=0;
        }
        state_=0;section_count_=0;total_vertices_=0;total_pixels_=0;
        std::fill(std::begin(section_loaded_),std::end(section_loaded_),false);
        file_vertices_.clear();file_normals_.clear();file_uv_.clear();file_indices_.clear();
        return 0;
    }
    template<class Pool> void command(uint64_t b,uint64_t session,Pool& pool,MeshPacket& p) {
        if(p.version!=3 || p.operation<1 || p.operation>13 || !p.owner || p.error || p.state || (p.reserved && (p.operation!=5 || p.reserved>64)) || p.section_id>=64 ||
           p.actor.address || p.component.address || p.step || p.sections) {p.error=1800;return;}
        if(p.operation==8) {
            // Read-only, bounded reflected bone capture. No pointer reads from caller data.
            if(!TargetPodSchemaOps{b}.context()){p.error=407;return;}
            for(size_t i=0;i<5;++i)if(!function(b,p.inputs[i+1],20+i)){p.error=1802;p.step=uint32_t(21+i);return;}
            alignas(16) uint8_t a[112]{};
            if(!dispatch(b,p.inputs[0],p.inputs[1],20,a)){p.error=1820;return;}
            int32_t count=0;std::memcpy(&count,a,4);
            if(count<0 || count>2048){p.error=1820;return;}
            struct Bone {char name[64],parent[64];double reference[12],world[12];};
            static_assert(sizeof(Bone)==320,"bone capture record");
            const int32_t first=int32_t(p.section_id)*50;
            const int32_t take=std::max(0,std::min(50,count-first));
            Bone bones[50]{};
            for(int32_t i=0;i<take;++i) {
                const int32_t index=first+i;std::memset(a,0,sizeof(a));std::memcpy(a,&index,4);
                if(!dispatch(b,p.inputs[0],p.inputs[2],21,a)){p.error=1820;return;}
                uint64_t name=0;std::memcpy(&name,a+4,8);
                if(!skin_name(b,name,bones[i].name)){p.error=1821;return;}
                std::memset(a,0,sizeof(a));std::memcpy(a,&name,8);
                if(!dispatch(b,p.inputs[0],p.inputs[5],24,a)){p.error=1820;return;}
                uint64_t parent=0;std::memcpy(&parent,a+8,8);
                if(!skin_name(b,parent,bones[i].parent)){p.error=1821;return;}
                std::memset(a,0,sizeof(a));std::memcpy(a,&index,4);
                if(!dispatch(b,p.inputs[0],p.inputs[3],22,a)){p.error=1820;return;}
                std::memcpy(bones[i].reference,a+16,96);
                std::memset(a,0,sizeof(a));std::memcpy(a,&name,8); // observed RTS_World=0
                if(!dispatch(b,p.inputs[0],p.inputs[4],23,a)){p.error=1820;return;}
                std::memcpy(bones[i].world,a+16,96);
            }
            p.vertex_count=uint32_t(take);p.index_count=uint32_t(count);
            std::memcpy(p.vertices,bones,sizeof(bones));return;
        }
        if(p.operation!=1 && p.operation!=4 && p.operation!=7) {
            if(p.owner!=owner_){p.error=1801;return;}
            if(p.operation==12||p.operation==13) {
                const auto* bytes=reinterpret_cast<const uint8_t*>(&p);
                for(size_t i=88;i<20976;++i)if(bytes[i]){p.error=1800;return;}
                if(p.section_id>(p.operation==12?1U:0U)){p.error=1800;return;}
                if(p.operation==12&&!skin_.freeze(p.section_id!=0)){p.error=1831;return;}
                if(p.operation==13)skin_.samples(p);
            }
            if(p.operation==9) {
                if(state_!=1){p.error=1801;return;}
                p.error=skin_.start(b,p,pawn_,section_count_,section_vertices_);if(p.error)return;
            }
            if(p.operation==10 && !skin_.hide(b)){p.error=1833;return;}
            if(p.operation==11 && !skin_.suspend(b,component_)){p.error=1833;return;}
            if(p.operation==6) {
                if(state_!=1 || p.section_id>section_count_ || section_loaded_[p.section_id]){p.error=1813;return;}
                const auto length=wcsnlen(p.texture_path,512);
                if(length<10 || length>=512 || p.texture_path[1]!=L':' || _wcsicmp(p.texture_path+length-8,L".e33mesh")){p.error=1812;return;}
                HANDLE f=CreateFileW(p.texture_path,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
                if(f==INVALID_HANDLE_VALUE){p.error=1812;return;}
                struct Header {char magic[8];uint32_t vertices,indices;} h{};
                DWORD got=0;LARGE_INTEGER bytes{};
                bool valid=ReadFile(f,&h,sizeof(h),&got,nullptr) && got==sizeof(h) && !std::memcmp(h.magic,"E33MESH1",8) &&
                    h.vertices>=3 && h.vertices<=200000 && h.indices>=3 && h.indices<=600000 && h.indices%3==0 &&
                    total_vertices_+h.vertices<=1000000 && GetFileSizeEx(f,&bytes) &&
                    bytes.QuadPart==16+int64_t(h.vertices)*64+int64_t(h.indices)*4;
                if(!valid){CloseHandle(f);p.error=1813;return;}
                std::vector<double> raw;
                try {raw.resize(size_t(h.vertices)*8);file_vertices_.resize(h.vertices);file_normals_.resize(h.vertices);
                    file_uv_.resize(size_t(h.vertices)*2);file_indices_.resize(h.indices);}
                catch(...) {CloseHandle(f);p.error=1813;return;}
                const auto vertex_bytes=DWORD(raw.size()*8),index_bytes=DWORD(file_indices_.size()*4);
                valid=ReadFile(f,raw.data(),vertex_bytes,&got,nullptr) && got==vertex_bytes &&
                    ReadFile(f,file_indices_.data(),index_bytes,&got,nullptr) && got==index_bytes;
                CloseHandle(f);
                if(!valid){p.error=1813;return;}
                for(uint32_t i=0;i<h.vertices;++i) {
                    const auto* v=raw.data()+size_t(i)*8;
                    for(unsigned j=0;j<8;++j)if(!std::isfinite(v[j]) || std::abs(v[j])>(j<3?10000.:100.)){p.error=1813;return;}
                    const auto n=v[3]*v[3]+v[4]*v[4]+v[5]*v[5];if(n<.99 || n>1.01){p.error=1813;return;}
                    file_vertices_[i]={v[0],v[1],v[2]};file_normals_[i]={v[3],v[4],v[5]};
                    file_uv_[i*2]=v[6];file_uv_[i*2+1]=v[7];
                }
                for(auto index:file_indices_)if(index<0 || uint32_t(index)>=h.vertices){p.error=1813;return;}
                clear_args();std::memcpy(args_,&p.section_id,4);
                const Array v{file_vertices_.data(),int32_t(h.vertices),int32_t(h.vertices)},
                    n{file_normals_.data(),int32_t(h.vertices),int32_t(h.vertices)},
                    uv{file_uv_.data(),int32_t(h.vertices),int32_t(h.vertices)},
                    t{file_indices_.data(),int32_t(h.indices),int32_t(h.indices)};
                std::memcpy(args_+8,&v,16);std::memcpy(args_+24,&t,16);std::memcpy(args_+40,&n,16);std::memcpy(args_+56,&uv,16);
                if(!call(b,component_,4)){p.error=1804;return;}
                section_vertices_[p.section_id]=h.vertices;section_loaded_[p.section_id]=true;section_count_=(std::max)(section_count_,p.section_id+1);total_vertices_+=h.vertices;
            }
            if(p.operation==5) {
                const auto slot=2+p.section_id*2;
                if(state_!=1 || p.section_id>=section_count_ || tokens_[slot] || tokens_[slot+1]){p.error=1801;return;}
                for(size_t i=0;i<4;++i)if(!function(b,p.material_inputs[i+3],i+12)){p.error=1802;p.step=uint32_t(i+13);return;}
                if(!function(b,p.material_inputs[8],16)){p.error=1802;p.step=17;return;}
                const auto parent=call_identity(b,p.material_inputs[0]);
                const auto library=call_identity(b,p.material_inputs[2]);
                const auto rendering=call_identity(b,p.material_inputs[7]);
                const wchar_t* texture_parameter=nullptr;bool surface=false;
                if(named(b,parent,"DefaultImagePlateMaterial","/ImagePlate/DefaultImagePlateMaterial")){texture_parameter=L"InputTexture";surface=false;}
                if(named(b,parent,"Widget3DPassThrough_Opaque","/Engine/EngineMaterials/Widget3DPassThrough_Opaque")){texture_parameter=L"SlateUI";surface=true;}
                if(named(b,parent,"Widget3DPassThrough_Opaque_OneSided","/Engine/EngineMaterials/Widget3DPassThrough_Opaque_OneSided")){texture_parameter=L"SlateUI";surface=true;}
                if(named(b,parent,"Widget3DPassThrough_Masked","/Engine/EngineMaterials/Widget3DPassThrough_Masked")){texture_parameter=L"SlateUI";surface=true;}
                if(named(b,parent,"Widget3DPassThrough_Masked_OneSided","/Engine/EngineMaterials/Widget3DPassThrough_Masked_OneSided")){texture_parameter=L"SlateUI";surface=true;}
                if(named(b,parent,"DefaultSpriteMaterial","/Paper2D/DefaultSpriteMaterial")){texture_parameter=L"SpriteTexture";surface=false;}
                if(named(b,parent,"OpaqueUnlitSpriteMaterial","/Paper2D/OpaqueUnlitSpriteMaterial")){texture_parameter=L"SpriteTexture";surface=false;}
                if(named(b,parent,"M_NPCs","/Game/Characters/M_NPCs")){texture_parameter=L"Base Color Map";surface=false;}
                if(named(b,parent,"M_Characters","/Game/Characters/M_Characters")){texture_parameter=L"Base Color Map";surface=false;}
                if(named(b,parent,"M_Characters1","/Game/Characters/M_Characters1")){texture_parameter=L"Base Color Map";surface=false;}
                if(named(b,parent,"M_Characters_Masked","/Game/Characters/M_Characters_Masked")){texture_parameter=L"Base Color Map";surface=false;}
                if(named(b,parent,"MS_DefaultMaterial_General","/Game/MSPresets/MS_DefaultMaterial_Displacement_00/MS_DefaultMaterial_General")){texture_parameter=L"Albedo";surface=false;}
                #include "mesh_material_candidates.inl"
                if(p.reserved && !surface){p.error=1800;return;}
                const bool lit_tint=named(b,parent,"M_Characters1","/Game/Characters/M_Characters1") || named(b,parent,"M_Characters_Masked","/Game/Characters/M_Characters_Masked");
                if((surface || lit_tint) && !function(b,p.material_inputs[1],19)){p.error=1802;return;}
                if(!texture_parameter || !library || !rendering ||
                   !exact_name(b,rendering+24,"Default__KismetRenderingLibrary") ||
                   !exact_name(b,library+24,"Default__KismetStringLibrary")){p.error=1803;return;}
                const auto length=wcsnlen(p.texture_path,512);
                if(length<8 || length>=512 || p.texture_path[1]!=L':' || _wcsicmp(p.texture_path+length-4,L".png")){p.error=1812;return;}
                std::memcpy(texture_path_,p.texture_path,sizeof(texture_path_));
                HANDLE file=CreateFileW(texture_path_,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
                if(file==INVALID_HANDLE_VALUE){p.error=1812;return;}
                LARGE_INTEGER bytes{};uint8_t header[24]{};DWORD read=0;
                const bool valid=GetFileSizeEx(file,&bytes) && bytes.QuadPart>=24 && bytes.QuadPart<=16777216 &&
                    ReadFile(file,header,24,&read,nullptr) && read==24 && !std::memcmp(header,"\x89PNG\r\n\x1a\n",8) &&
                    header[16]==0 && header[17]==0 && header[20]==0 && header[21]==0 &&
                    (unsigned(header[18])*256+header[19])>0 && (unsigned(header[18])*256+header[19])<=4096 &&
                    (unsigned(header[22])*256+header[23])>0 && (unsigned(header[22])*256+header[23])<=4096;
                CloseHandle(file);if(!valid){p.error=1812;return;}
                const auto pixels=(unsigned(header[18])*256+header[19])*(unsigned(header[22])*256+header[23]);
                if(total_pixels_+pixels>67108864){p.error=1812;return;}
                auto admission=pool.preflight(session,2);if(admission!=StrongLeaseResult::Ok){p.error=uint32_t(admission);return;}
                std::memcpy(functions_+12,p.material_inputs+3,4*sizeof(CallIdentity));
                functions_[16]=p.material_inputs[8];
                clear_args();std::memcpy(args_,&pawn_.address,8);
                const Array path{texture_path_,int32_t(length+1),int32_t(length+1)};std::memcpy(args_+8,&path,16);
                if(!call(b,p.material_inputs[7],16)){p.error=1810;return;}
                uint64_t tex=0;std::memcpy(&tex,args_+24,8);texture_=call_capture(b,tex);
                if(!texture_.address || !named(b,local_read<uint64_t>(tex+16),"Texture2D","/Script/Engine")){p.error=1810;return;}
                TargetStrongReferenceOps tex_ops{b,texture_};
                auto retained=pool.acquire(tex_ops,session,tex,tokens_[slot]);
                if(retained!=StrongLeaseResult::Ok){p.error=uint32_t(retained);return;}
                total_pixels_+=pixels;
                clear_args();std::memcpy(args_,&p.section_id,4);std::memcpy(args_+8,&parent,8);
                if(!call(b,component_,12)){p.error=1810;return;}
                uint64_t mid=0;std::memcpy(&mid,args_+24,8);material_=call_capture(b,mid);
                if(!material_.address){p.error=1810;return;}
                TargetStrongReferenceOps mid_ops{b,material_};retained=pool.acquire(mid_ops,session,mid,tokens_[slot+1]);
                if(retained!=StrongLeaseResult::Ok){p.error=uint32_t(retained);return;}
                if(!material_.serial){mid_ops.allocate_serial(material_.index);material_=call_capture(b,mid);}
                const wchar_t* name=texture_parameter;
                const auto name_length=int32_t(wcslen(name)+1);Array string{name,name_length,name_length};
                clear_args();std::memcpy(args_,&string,16);
                if(!call(b,p.material_inputs[2],15)){p.error=1810;return;}
                uint64_t parameter=0;std::memcpy(&parameter,args_+16,8);
                clear_args();std::memcpy(args_,&parameter,8);std::memcpy(args_+8,&tex,8);
                if(!call(b,material_,13)){p.error=1810;return;}
                clear_args();std::memcpy(args_,&parameter,8);
                if(!call(b,material_,14) || local_read<uint64_t>(reinterpret_cast<uint64_t>(args_+8))!=tex){p.error=1811;return;}
                if(surface || lit_tint) {
                    functions_[19]=p.material_inputs[1];
                    const wchar_t* tint=lit_tint?L"Base Color Tint":L"TintColorAndOpacity";const auto tint_length=int32_t(wcslen(tint)+1);
                    const Array text{tint,tint_length,tint_length};clear_args();std::memcpy(args_,&text,16);
                    if(!call(b,p.material_inputs[2],15)){p.error=1810;return;}
                    std::memcpy(&parameter,args_+16,8);clear_args();std::memcpy(args_,&parameter,8);
                    const float gain=lit_tint?1.f:(p.reserved?float(p.reserved):64.f);const float color[4]={gain,gain,gain,1.f};std::memcpy(args_+8,color,16);
                    if(!call(b,material_,19)){p.error=1810;return;}
                }
            }
            if(p.operation==2)p.error=close(b,session,pool);
            if(p.operation==3 && state_==1) {
                clear_args();if(!call(b,component_,10)){p.error=1806;return;}
                int32_t sections=0;std::memcpy(&sections,args_,4);
                if(sections!=int32_t(section_count_)){p.error=1806;return;}
            }
        } else {
            if(active()){p.error=1801;return;}
            if(!TargetPodSchemaOps{b}.context()){p.error=407;return;}
            for(size_t i=0;i<12;++i)if(!function(b,p.inputs[4+i],i)){p.error=1802;p.step=uint32_t(i+1);return;}
            if(p.operation==4) {
                if(p.vertex_count<3 || p.vertex_count>256 || !p.index_count || p.index_count>768 || p.index_count%3){p.error=1800;return;}
                for(uint32_t i=0;i<p.vertex_count;++i) {
                    for(unsigned j=0;j<8;++j)if(!std::isfinite(p.vertices[i][j]) || std::abs(p.vertices[i][j])>(j<3?10000.:100.)){p.error=1800;return;}
                    const auto* v=p.vertices[i];
                    const auto n=v[3]*v[3]+v[4]*v[4]+v[5]*v[5];
                    if(n<.99 || n>1.01){p.error=1800;return;}
                    vertices_[i]={v[0],v[1],v[2]};normals_[i]={v[3],v[4],v[5]};uv_[i][0]=v[6];uv_[i][1]=v[7];
                }
                for(uint32_t i=0;i<p.index_count;++i) {
                    if(p.indices[i]<0 || uint32_t(p.indices[i])>=p.vertex_count){p.error=1800;return;}
                    indices_[i]=p.indices[i];
                }
            }
            const auto pawn=call_identity(b,p.inputs[0]), gs=call_identity(b,p.inputs[1]);
            const auto ac=call_identity(b,p.inputs[2]),cc=call_identity(b,p.inputs[3]);
            if(!pawn || !gs || (local_read<uint32_t>(pawn+8)&0x30) ||
               !exact_name(b,gs+24,"Default__GameplayStatics") ||
               !named(b,local_read<uint64_t>(gs+16),"GameplayStatics","/Script/Engine") ||
               !named(b,ac,"StaticMeshActor","/Script/Engine") || !call_is_class(b,ac) ||
               !named(b,cc,"ProceduralMeshComponent","/Script/ProceduralMeshComponent") || !call_is_class(b,cc)) {p.error=1803;return;}
            auto admission=pool.preflight(session,2);if(admission!=StrongLeaseResult::Ok){p.error=uint32_t(admission);return;}
            owner_=p.owner;destroyed_=false;actor_={};component_={};
            pawn_=p.inputs[0];
            std::memcpy(functions_,p.inputs+4,12*sizeof(CallIdentity));
            clear_args();if(!call(b,p.inputs[0],6)){p.error=1803;return;}
            std::memcpy(position_,args_,24);
            clear_args();if(!call(b,p.inputs[0],7)){p.error=1803;return;}
            double forward[3];std::memcpy(forward,args_,24);
            for(int i=0;i<3;++i) {
                position_[i]+=forward[i]*350.;if(i==2)position_[i]+=35.;
                if(!std::isfinite(position_[i]) || std::abs(position_[i])>1.e8){p.error=1803;return;}
            }
            if(p.operation==7) {
                const auto system=call_identity(b,p.material_inputs[0]);
                if(!system || !named(b,local_read<uint64_t>(system+16),"KismetSystemLibrary","/Script/Engine") ||
                   !exact_name(b,system+24,"Default__KismetSystemLibrary") ||
                   !function(b,p.material_inputs[1],17) || !function(b,p.material_inputs[2],18)){p.error=1802;p.step=18;return;}
                functions_[17]=p.material_inputs[1];functions_[18]=p.material_inputs[2];
                bool grounded=false;
                for(int attempt=0;attempt<2 && !grounded;++attempt) {
                    if(attempt)for(int i=0;i<2;++i)position_[i]-=forward[i]*175.;
                    const Vec start{position_[0],position_[1],position_[2]+300.},end{position_[0],position_[1],position_[2]-900.};
                    const double trace_start[]={start.x,start.y,start.z},trace_end[]={end.x,end.y,end.z};
                    e33_surface_query::Sample surface{};
                    const auto result=e33_surface_query::sample([&](unsigned stage,uint8_t* values){
                        std::memcpy(args_,values,sizeof(args_));
                        const bool ok=stage?call(b,p.inputs[1],18):call(b,p.material_inputs[0],17);
                        std::memcpy(values,args_,sizeof(args_));return ok;
                    },pawn,trace_start,trace_end,&pawn,1,surface);
                    if(result==e33_surface_query::Result::Rejected){p.error=1814;return;}
                    if(result!=e33_surface_query::Result::Hit)continue;
                    position_[0]=surface.point[0];position_[1]=surface.point[1];position_[2]=surface.point[2]+1.;grounded=true;
                }
                if(!grounded){p.error=1814;return;}
            }
            state_=2;clear_args();std::memcpy(args_,&pawn,8);std::memcpy(args_+8,&ac,8);transform(args_+16,position_);
            args_[112]=1; // verified AlwaysSpawn enum, collision disabled below
            if(!call(b,p.inputs[1],0)){p.error=1804;return;}
            uint64_t actor=0;std::memcpy(&actor,args_+136,8);actor_=call_capture(b,actor);
            if(!actor_.address){p.error=1804;return;}
            TargetStrongReferenceOps actor_ops{b,actor_};
            auto retained=pool.acquire(actor_ops,session,actor,tokens_[0]);actor_=call_capture(b,actor);
            if(retained!=StrongLeaseResult::Ok){p.error=uint32_t(retained);return;}
            clear_args();std::memcpy(args_,&actor,8);transform(args_+16,position_);
            if(!call(b,p.inputs[1],1)){p.error=1804;return;}
            clear_args();if(!call(b,actor_,8)){p.error=1804;return;}
            clear_args();std::memcpy(args_,&cc,8);transform(args_+16,nullptr);args_[112]=1;
            if(!call(b,actor_,2)){p.error=1804;return;}
            uint64_t component=0;std::memcpy(&component,args_+120,8);component_=call_capture(b,component);
            if(!component_.address){p.error=1804;return;}
            TargetStrongReferenceOps component_ops{b,component_};
            retained=pool.acquire(component_ops,session,component,tokens_[1]);component_=call_capture(b,component);
            if(retained!=StrongLeaseResult::Ok){p.error=uint32_t(retained);return;}
            clear_args();args_[0]=2;if(!call(b,component_,9)){p.error=1804;return;}
            clear_args();std::memcpy(args_,&component,8);transform(args_+16,nullptr);
            if(!call(b,actor_,3)){p.error=1804;return;}
            // Registration may assign the first weak-object serial. The object
            // remains strongly owned across this synchronous game-thread call.
            const auto registered=call_capture(b,component);
            if(registered.index!=component_.index || registered.address!=component_.address ||
               (component_.serial && registered.serial!=component_.serial)){p.error=1804;return;}
            component_=registered;
            const Vec points[]={{-65,-65,0},{65,-65,0},{0,65,0},{0,0,130}};
            const int faces[]={0,2,1,0,1,3,1,2,3,2,0,3};
            Vec vertices[12]{},normals[12]{};int32_t indices[12]{};
            for(int face=0;face<4;++face) {
                const auto a=points[faces[face*3]],c=points[faces[face*3+1]],d=points[faces[face*3+2]];
                Vec u{c.x-a.x,c.y-a.y,c.z-a.z},v{d.x-a.x,d.y-a.y,d.z-a.z};
                Vec n{u.y*v.z-u.z*v.y,u.z*v.x-u.x*v.z,u.x*v.y-u.y*v.x};
                const auto length=std::sqrt(n.x*n.x+n.y*n.y+n.z*n.z);n={n.x/length,n.y/length,n.z/length};
                for(int j=0;j<3;++j){auto at=face*3+j;vertices[at]=points[faces[at]];normals[at]=n;indices[at]=at;}
            }
            clear_args();const Array v{vertices,12,12},t{indices,12,12},n{normals,12,12};
            std::memcpy(args_+8,&v,16);std::memcpy(args_+24,&t,16);std::memcpy(args_+40,&n,16);
            if(p.operation==4) {
                const Array cv{vertices_,int32_t(p.vertex_count),int32_t(p.vertex_count)},
                    cn{normals_,int32_t(p.vertex_count),int32_t(p.vertex_count)},
                    cu{uv_,int32_t(p.vertex_count),int32_t(p.vertex_count)},
                    ci{indices_,int32_t(p.index_count),int32_t(p.index_count)};
                std::memcpy(args_+8,&cv,16);std::memcpy(args_+24,&ci,16);std::memcpy(args_+40,&cn,16);std::memcpy(args_+56,&cu,16);
            }
            // Input-only arrays stay alive through synchronous ProcessEvent. Engine
            // CreateMeshSection copies them into its own section storage.
            if(!call(b,component_,4)){p.error=1804;return;}
            clear_args();if(!call(b,component_,10)){p.error=1804;return;}
            int32_t sections=0;std::memcpy(&sections,args_,4);
            if(sections!=1){p.error=1805;return;}
            state_=1;section_count_=1;
        }
        p.state=state_;p.actor=actor_;p.component=component_;p.step=step_;
        p.sections=state_==1?section_count_:0;std::memcpy(p.position,position_,24);
    }
};
}
