// Included inside e33_mesh. Exploration-only CPU skinning of owned geometry.
// The game's skeletal component remains the animation driver and is never replaced.
inline bool skin_base_name(uint64_t b,uint32_t id,char (&out)[64]) {
    // Bone FNames may contain spaces/punctuation (for example virtual bones).
    // Keep the same verified allocator-boundary walk as the asset decoder;
    // this decoder is restricted to observed bone names, never asset paths.
    const auto pool=b+0x92aadc0;
    const auto current=local_read<uint32_t>(pool+8),cursor=local_read<uint32_t>(pool+12);
    const uint32_t block=id>>16,offset=(id&65535)*2;
    if(current>=8192||block>current||cursor>0x20000)return false;
    const auto limit=block==current?cursor:0x20000U;
    const auto data=local_read<uint64_t>(pool+16+uint64_t(block)*8);
    if(!data||offset+2>limit)return false;
    uint32_t at=0;
    while(at<offset) {
        const auto h=local_read<uint16_t>(data+at);const uint32_t length=h>>6;
        if(!length)return false;
        const auto extent=(length*((h&1)+1)+3)&~1U;
        if(at+extent>limit)return false;at+=extent;
    }
    if(at!=offset)return false;
    const auto h=local_read<uint16_t>(data+at);const uint32_t length=h>>6;
    if((h&1)||!length||length>=64||at+2+length>limit)return false;
    for(uint32_t i=0;i<length;++i) {
        const auto c=local_read<uint8_t>(data+at+2+i);if(c<32||c>126)return false;out[i]=char(c);
    }
    out[length]=0;return true;
}
inline bool skin_name(uint64_t b,uint64_t name,char (&out)[64]) {
    char base[64]{};if(!skin_base_name(b,uint32_t(name),base))return false;
    std::string value=base;
    // Same observed FName numeric-suffix representation as research_probe.
    if(name>>32)value+="_"+std::to_string(uint32_t(name>>32)-1);
    if(value.size()>=64)return false;
    std::memcpy(out,value.c_str(),value.size()+1);return true;
}
struct SkinInfluence {uint32_t bone;float weight;float point[3],normal[3];};
static_assert(sizeof(SkinInfluence)==32,"skin file influence");
struct SkinVertex {SkinInfluence weights[4];};
struct SkinSection {uint32_t index=0;std::vector<SkinVertex> bind;std::vector<Vec> vertices,normals;};
inline Vec skin_rotate(const double* q,Vec v) {
    const Vec t{2*(q[1]*v.z-q[2]*v.y),2*(q[2]*v.x-q[0]*v.z),2*(q[0]*v.y-q[1]*v.x)};
    return {v.x+q[3]*t.x+q[1]*t.z-q[2]*t.y,v.y+q[3]*t.y+q[2]*t.x-q[0]*t.z,v.z+q[3]*t.z+q[0]*t.y-q[1]*t.x};
}
inline uint64_t skin_field(uint64_t b,uint64_t cls,const char* owner,const char* name,const char* type,int offset,uint64_t table,uint64_t flags) {
    if(!named(b,cls,owner,"/Script/Engine"))return 0;
    auto f=local_read<uint64_t>(cls+0x50);
    for(unsigned i=0;f && i<512;++i,f=local_read<uint64_t>(f+24))if(exact_name(b,f+32,name)) {
        return local_read<uint64_t>(f)==b+table && local_read<uint64_t>(f+16)==(cls|1) &&
            exact_name(b,local_read<uint64_t>(f+8),type) && local_read<int32_t>(f+0x44)==offset &&
            local_read<int32_t>(f+0x30)==1 && local_read<uint64_t>(f+0x38)==flags?f:0;
    }
    return 0;
}
inline CallIdentity skin_reference(uint64_t b,const CallIdentity& object,const char* owner,const char* package,const char* name,int offset,uint64_t flags,const char* constraint) {
    const auto o=call_identity(b,object);if(!o)return {-1,0,0};
    auto cls=local_read<uint64_t>(o+16);
    for(unsigned ancestor=0;cls && ancestor<128;++ancestor,cls=local_read<uint64_t>(cls+0x40)) {
        if(!call_is_class(b,cls))return {-1,0,0};
        if(!named(b,cls,owner,package))continue;
        auto f=local_read<uint64_t>(cls+0x50);
        for(unsigned i=0;f&&i<512;++i,f=local_read<uint64_t>(f+24))if(exact_name(b,f+32,name)) {
            if(local_read<uint64_t>(f)!=b+0x6e11d38||local_read<uint64_t>(f+16)!=(cls|1)||
               !exact_name(b,local_read<uint64_t>(f+8),"ObjectProperty")||local_read<int32_t>(f+0x44)!=offset||
               local_read<int32_t>(f+0x30)!=1||local_read<int32_t>(f+0x34)!=8||local_read<uint64_t>(f+0x38)!=flags)return {-1,0,0};
            const auto type=local_read<uint64_t>(f+0x70);
            if(!call_is_class(b,type)||!exact_name(b,type+24,constraint))return {-1,0,0};
            const auto result=call_capture(b,local_read<uint64_t>(o+offset));
            return result.address && call_derives(b,local_read<uint64_t>(result.address+16),type)?result:CallIdentity{-1,0,0};
        }
        return {-1,0,0};
    }
    return {-1,0,0};
}
inline uint64_t skin_battle_field(uint64_t b,uint64_t cls,const char* name,uint32_t offset,uint32_t size,uint64_t table,uint64_t flags) {
    auto field=local_read<uint64_t>(cls+0x50);
    for(unsigned n=0;field&&n<512;++n,field=local_read<uint64_t>(field+24)) {
        if(!exact_name(b,field+32,name))continue;
        return local_read<uint64_t>(field)==b+table&&local_read<uint64_t>(field+16)==(cls|1)&&
            local_read<uint32_t>(field+0x30)==1&&local_read<uint32_t>(field+0x34)==size&&
            local_read<uint32_t>(field+0x44)==offset&&local_read<uint64_t>(field+0x38)==flags?field:0;
    }
    return 0;
}
// Verified active battle membership, never an unrestricted substitute for possession.
inline bool skin_combat_member(uint64_t b,const CallIdentity& manager,const CallIdentity& pawn) {
    const auto m=call_identity(b,manager),p=call_identity(b,pawn);
    if(!m||!p||(local_read<uint32_t>(m+8)&0x30)||(local_read<uint32_t>(p+8)&0x30))return false;
    const auto cls=local_read<uint64_t>(m+16);
    if(!named(b,cls,"AC_jRPG_BattleManager_C","/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_BattleManager"))return false;
    const auto array=skin_battle_field(b,cls,"PlayerCharacters",184,16,0x6e0de80,0x10805);
    const auto ended=skin_battle_field(b,cls,"BattleEndState",2320,1,0x6e10420,0x8001040010205);
    if(!array||!ended||!exact_name(b,local_read<uint64_t>(array+8),"ArrayProperty")||
       !exact_name(b,local_read<uint64_t>(ended+8),"ByteProperty")||local_read<uint8_t>(m+2320))return false;
    if(local_read<uint8_t>(array+0x70)&1)return false;
    const auto inner=local_read<uint64_t>(array+0x78);
    if(!inner||local_read<uint64_t>(inner)!=b+0x6e11d38||local_read<uint64_t>(inner+16)!=array||
       !exact_name(b,local_read<uint64_t>(inner+8),"ObjectProperty")||local_read<int32_t>(inner+0x30)!=1||local_read<int32_t>(inner+0x34)!=8)return false;
    const auto type=local_read<uint64_t>(inner+0x70);
    if(!named(b,type,"BP_jRPG_Character_Battle_Base_C","/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_Character_Battle_Base")||
       !call_is_class(b,type)||!call_derives(b,local_read<uint64_t>(p+16),type))return false;
    const auto data=local_read<uint64_t>(m+184);const auto count=local_read<int32_t>(m+192),capacity=local_read<int32_t>(m+196);
    if(!data||count<1||count>16||capacity<count||capacity>64)return false;
    for(int32_t i=0;i<count;++i)if(local_read<uint64_t>(data+uint64_t(i)*8)==p)return true;
    return false;
}
#include "hair_reference_fit.h"
class Skin {
    struct Sample {uint64_t frame;double time_ms,work_ms,root[3],joint[3],vertex[3],max_delta,quaternion_norm,normal_norm;};
    static_assert(sizeof(Sample)==120,"bounded render sample");
    Sample samples_[128]{};uint32_t sample_count_=0;bool frozen_=false;uint8_t diagnostic_padding_[11]{};
    static double clock_ms(){LARGE_INTEGER q{},f{};QueryPerformanceCounter(&q);QueryPerformanceFrequency(&f);return double(q.QuadPart)*1000./double(f.QuadPart);}
    CallIdentity driver_{},asset_{},pawn_{},fn_[9]{},visuals_[5]{},skin_controller_{},scene_class_{},battle_manager_{};
    bool hidden_[5]{},changed_[5]{},tick_changed_=false,follow_=false;
    // Development-only: borrow the native skeletal haircut. The game retains
    // ownership, attachments, mesh/materials and selection. Never destroy it.
    bool face_tick_changed_=false;uint8_t face_original_tick_=0;
    CallIdentity hair_setter_{},hair_getter_{},hair_world_getter_{},hair_world_setter_{},hair_absolute_{};
    uint8_t hair_original_absolute_=0;
    struct HairSample {uint64_t frame;double head[7],hair[7],position_error,rotation_error;};
    HairSample hair_samples_[20]{};uint32_t hair_sample_count_=0;
    bool hair_location_changed_=false;
    uint64_t hair_socket_=0;
    double hair_original_[12]{},hair_last_[12]{},hair_basis_[4]{};uint32_t hair_profile_=0;uint8_t hair_padding_[12]{};
    uint64_t handoff_started_=0;
    bool wardrobe_=false;CallIdentity wardrobe_menu_{};
    static void multiply(const double* a,const double* c,double* o) {
        double r[4]{a[3]*c[0]+a[0]*c[3]+a[1]*c[2]-a[2]*c[1],
                    a[3]*c[1]-a[0]*c[2]+a[1]*c[3]+a[2]*c[0],
                    a[3]*c[2]+a[0]*c[1]-a[1]*c[0]+a[2]*c[3],
                    a[3]*c[3]-a[0]*c[0]-a[1]*c[1]-a[2]*c[2]};
        std::memcpy(o,r,32);
    }
    bool hair_layout(uint64_t b) {
        auto sc=call_identity(b,scene_class_);if(!sc)return false;
        auto location=skin_field(b,sc,"SceneComponent","RelativeLocation","StructProperty",296,0x6e136a0,0x48001140000235);
        auto socket=skin_field(b,sc,"SceneComponent","AttachSocketName","NameProperty",184,0x6e13040,0x48001140000220);
        auto parent=skin_field(b,sc,"SceneComponent","AttachParent","ObjectProperty",176,0x6e11d38,0x14c001100080228);
        for(unsigned i=0;i<3;++i) {
            const char* names[]={"bAbsoluteLocation","bAbsoluteRotation","bAbsoluteScale"};
            auto f=skin_field(b,sc,"SceneComponent",names[i],"BoolProperty",392,0x6e119b0,0x48041100000025);
            if(!f||local_read<int32_t>(f+0x34)!=1||local_read<uint32_t>(f+0x70)!=((4U<<i)*0x1010000U+1))return false;
        }
        return location&&socket&&parent&&local_read<int32_t>(location+0x34)==24&&
            local_read<int32_t>(socket+0x34)==8&&local_read<int32_t>(parent+0x34)==8&&
            structure(b,local_read<uint64_t>(location+0x70),"Vector",24);
    }
    static bool hair_same(const double* a,const double* c) {
        double dot=0;for(unsigned i=0;i<4;++i)dot+=a[i]*c[i];
        if(std::abs(std::abs(dot)-1)>.000001)return false;
        for(unsigned i=4;i<11;++i)if(i!=7&&std::abs(a[i]-c[i])>.001)return false;
        return true;
    }
    bool hair_get(uint64_t b,double* t) {
        alignas(16) double result[12]{};
        if(!dispatch(b,visuals_[2],hair_getter_,32,result))return false;
        for(double v:result)if(!std::isfinite(v))return false;
        double norm=0;for(unsigned i=0;i<4;++i)norm+=result[i]*result[i];
        if(std::abs(norm-1)>.001)return false;
        std::memcpy(t,result,96);return true;
    }
    bool hair_set(uint64_t b,const double* transform) {
        alignas(16) uint8_t params[368]{};
        std::memcpy(params,transform,96);params[352]=1;
        return dispatch(b,visuals_[2],hair_setter_,31,params);
    }
    bool hair_absolute(uint64_t b,uint8_t bits) {
        uint8_t args[3]{uint8_t((bits&4)!=0),uint8_t((bits&8)!=0),uint8_t((bits&16)!=0)};
        return dispatch(b,visuals_[2],hair_absolute_,35,args);
    }
    bool hair_world(uint64_t b,double* out) {
        if(!dispatch(b,visuals_[2],hair_world_getter_,33,out))return false; for(unsigned i=0;i<12;++i)if(!std::isfinite(out[i]))return false; return true;
    }
    static bool hair_rigid(const double* t) {
        double n=0;for(unsigned i=0;i<12;++i)if(!std::isfinite(t[i]))return false;
        for(unsigned i=0;i<4;++i)n+=t[i]*t[i];
        if(std::abs(n-1)>.001)return false;
        for(unsigned i=8;i<11;++i)if(std::abs(t[i]-1)>.001)return false;
        return true;
    }
    static void hair_compose(const double* a,const double* c,double* o) {
        multiply(a,c,o);auto v=skin_rotate(a,{c[4],c[5],c[6]});
        o[4]=a[4]+v.x;o[5]=a[5]+v.y;o[6]=a[6]+v.z;
        o[8]=o[9]=o[10]=1;
    }
    static void hair_inverse(const double* a,double* o) {
        o[0]=-a[0];o[1]=-a[1];o[2]=-a[2];o[3]=a[3];
        auto v=skin_rotate(o,{-a[4],-a[5],-a[6]});o[4]=v.x;o[5]=v.y;o[6]=v.z;
        o[8]=o[9]=o[10]=1;
    }
    bool hair_head_reference(uint64_t b,const CallIdentity& object,uint64_t name,double* out) {
        double result[12]{0,0,0,1,0,0,0,0,1,1,1,0};
        for(unsigned ancestor=0;ancestor<32;++ancestor) {
            std::memset(args_,0,sizeof(args_));std::memcpy(args_,&name,8);
            if(!call(b,object,7))return false;
            int32_t index=-1;std::memcpy(&index,args_+8,4);if(index<0||index>=2048)return false;
            std::memset(args_,0,sizeof(args_));std::memcpy(args_,&index,4);
            if(!call(b,object,6))return false;
            double t[12]{},next[12]{};std::memcpy(t,args_+16,96);if(!hair_rigid(t))return false;
            hair_compose(t,result,next);std::memcpy(result,next,96);
            std::memset(args_,0,sizeof(args_));std::memcpy(args_,&name,8);
            if(!call(b,object,8))return false;
            uint64_t parent=0;std::memcpy(&parent,args_+8,8);
            if(!parent){std::memcpy(out,result,96);return true;}
            if(parent==name)return false;name=parent;
        }
        return false;
    }
    uint64_t face_fit_step_=0;
    bool face_fit_owned_=false;
    uint8_t face_fit_absolute_=0;
    double face_fit_original_[12]{},face_fit_last_[12]{};
    CallIdentity face_fit_parent_{};
    uint64_t face_fit_socket_=0;
    bool fit_attachment_source(uint64_t b,const double (&pose)[32][12]) {
        if(!wardrobe_||!hair_profile_)return true;
        face_fit_step_=1;
        const auto face=call_identity(b,visuals_[1]);if(!face||!hair_layout(b))return false;
        uint32_t head=bones_;
        for(uint32_t i=0;i<bones_;++i){char name[64]{};if(!skin_name(b,bone_names_[i],name))return false;if(!_stricmp(name,"head")){head=i;break;}}
        face_fit_step_=2;
        if(head==bones_)return false;
        double world[12]{},head_world[12]{},inverse[12]{},local[12]{},local_inverse[12]{},fitted[12]{},desired[12]{};
        face_fit_step_=3;
        if(!dispatch(b,visuals_[1],hair_world_getter_,33,world))return false;
        std::memset(args_,0,sizeof(args_));std::memcpy(args_,bone_names_+head,8);
        face_fit_step_=4;
        if(!call(b,visuals_[1],1))return false;
        std::memcpy(head_world,args_+16,96);
        face_fit_step_=5;
        // Sciel Wardrobe has verified uniform world scale .94. As in the
        // animated-hair fit, keep scaled joint distances and apply scale once.
        const double face_scale=world[8];
        if(!std::isfinite(face_scale)||face_scale<.5||face_scale>2)return false;
        for(unsigned i=8;i<11;++i) {
            if(!std::isfinite(world[i])||!std::isfinite(head_world[i])||std::abs(world[i]-face_scale)>.0001||std::abs(head_world[i]-face_scale)>.0001)return false;
            world[i]=head_world[i]=1;
        }
        if(!hair_rigid(world)||!hair_rigid(head_world))return false;
        hair_inverse(world,inverse);hair_compose(inverse,head_world,local);hair_inverse(local,local_inverse);
        hair_compose(pose[head],hair_profile_==2?ayane_head_reference_fit:two_b_head_reference_fit,fitted);
        hair_compose(fitted,local_inverse,desired);
        desired[8]=desired[9]=desired[10]=face_scale;
        if(!face_fit_owned_) {
        face_fit_step_=6;
            if(!dispatch(b,visuals_[1],hair_getter_,32,face_fit_original_)||!hair_rigid(face_fit_original_))return false;
        face_fit_step_=7;
            face_fit_absolute_=local_read<uint8_t>(face+392)&28;if(face_fit_absolute_)return false;
            face_fit_parent_=call_capture(b,local_read<uint64_t>(face+176));
        face_fit_step_=8;
            if(!face_fit_parent_.address)return false;
            face_fit_socket_=local_read<uint64_t>(face+184);face_fit_owned_=true;
        face_fit_step_=9;
            uint8_t absolute[3]{1,1,1};if(!dispatch(b,visuals_[1],hair_absolute_,35,absolute))return false;
        }
        face_fit_step_=10;
        if(local_read<uint64_t>(face+176)!=call_identity(b,face_fit_parent_)||local_read<uint64_t>(face+184)!=face_fit_socket_)return false;
        alignas(16) uint8_t params[368]{};std::memcpy(params,desired,96);params[352]=1;
        face_fit_step_=11;
        if(!dispatch(b,visuals_[1],hair_world_setter_,34,params))return false;
        std::memcpy(face_fit_last_,desired,96);
        face_fit_step_=12;double actual[12]{};if(!dispatch(b,visuals_[1],hair_world_getter_,33,actual)||!hair_same(actual,desired))return false;face_fit_step_=0;return true;
    }
    bool restore_attachment_source(uint64_t b) {
        if(!face_fit_owned_)return true;
        const auto face=call_identity(b,visuals_[1]);
        if(face) {
            if(!hair_layout(b)||local_read<uint64_t>(face+176)!=call_identity(b,face_fit_parent_)||local_read<uint64_t>(face+184)!=face_fit_socket_)return false;
            uint8_t absolute[3]{uint8_t((face_fit_absolute_&4)!=0),uint8_t((face_fit_absolute_&8)!=0),uint8_t((face_fit_absolute_&16)!=0)};
            if(!dispatch(b,visuals_[1],hair_absolute_,35,absolute))return false;
            alignas(16) uint8_t params[368]{};std::memcpy(params,face_fit_original_,96);params[352]=1;
            if(!dispatch(b,visuals_[1],hair_setter_,31,params))return false;
            double actual[12]{};if(!dispatch(b,visuals_[1],hair_getter_,32,actual)||!hair_same(actual,face_fit_original_))return false;
        }
        face_fit_owned_=false;return true;
    }
    CallIdentity rejected_hair_{},rejected_hair_asset_{},borrowed_hair_asset_{};
    uint64_t hair_retry_at_=0;uint32_t hair_retry_count_=0;
    double hair_reference_delta_[12]{0,0,0,1,0,0,0,0,1,1,1,0};
    bool fit_hair(uint64_t b,const double (&pose)[32][12]) {
        if(!hair_profile_||battle_manager_.address)return true;
        auto hair=call_identity(b,visuals_[2]);if(!hair||!hair_layout(b))return false;
        // Preserve visible hair while fitting; only rejected fits are hidden.
        const auto asset=call_capture(b,local_read<uint64_t>(hair+1384));
        if(rejected_hair_.address==hair&&rejected_hair_.serial==visuals_[2].serial&&
           rejected_hair_asset_.address==asset.address&&rejected_hair_asset_.serial==asset.serial) {
            if(hair_retry_count_>=12||GetTickCount64()<hair_retry_at_)return true;
        } else {hair_retry_count_=0;hair_retry_at_=0;}
        if(try_fit_hair(b,pose)) {
            // A fully validated fit owns hair visibility for this active rig.
            // Keep the original state in the same restoration ledger.
            if(!changed_[2]) {hidden_[2]=(local_read<uint8_t>(hair+393)&8)!=0;changed_[2]=true;}
            if(local_read<uint8_t>(hair+393)&8) {
                std::memset(args_,0,sizeof(args_));
                if(!call(b,visuals_[2],3))return false;
            }
            rejected_hair_={};rejected_hair_asset_={};hair_retry_count_=0;hair_retry_at_=0;
            return true;
        }
        // Failure of a fit must not retire the independently owned body. Undo
        // only this hair's borrowed transform, then hide the unsupported style.
        if(hair_location_changed_) {
            if(!hair_absolute(b,hair_original_absolute_)||!hair_set(b,hair_original_))return false;
            hair_location_changed_=false;
        }
        if(!changed_[2]){changed_[2]=true;hidden_[2]=(local_read<uint8_t>(hair+393)&8)!=0;}
        std::memset(args_,0,sizeof(args_));args_[0]=1;
        if(!call(b,visuals_[2],3))return false;
        rejected_hair_=visuals_[2];rejected_hair_asset_=asset;
        ++hair_retry_count_;hair_retry_at_=GetTickCount64()+250;
        return true;
    }
    bool try_fit_hair(uint64_t b,const double (&pose)[32][12]) {
        if(!hair_profile_||battle_manager_.address)return true;
        auto hair=call_identity(b,visuals_[2]);auto face=call_identity(b,visuals_[1]);
        if(!hair||!face||!hair_layout(b)||local_read<uint64_t>(hair+176)!=face)return false;
        // Fit is intentionally restricted to the reference asset studied here.
        const auto bone_fn=call_identity(b,fn_[0]); if(!bone_fn||!call_derives(b,local_read<uint64_t>(hair+16),local_read<uint64_t>(bone_fn+32)))return false;
        const auto mesh=local_read<uint64_t>(hair+1384);
        char socket_name[64]{};
        if(!skin_name(b,local_read<uint64_t>(hair+184),socket_name))return false;
        const bool socket_style=mesh && !_stricmp(socket_name,"Head");
        const bool animated_style=mesh && !_stricmp(socket_name,"None");
        if(!socket_style&&!animated_style) {
            // Unsupported hair does not invalidate the independently owned model.
            if(!changed_[2]){changed_[2]=true;hidden_[2]=(local_read<uint8_t>(hair+393)&8)!=0;}
            return false;
        }
        uint32_t head=bones_;
        for(uint32_t i=0;i<bones_;++i){char name[64]{};if(!skin_name(b,bone_names_[i],name))return false;if(!_stricmp(name,"head")){head=i;break;}}
        if(head==bones_)return false;
        const auto socket=local_read<uint64_t>(hair+184);char name[64]{};
        if(!skin_name(b,socket,name)||_stricmp(name,socket_style?"head":"None"))return false;
        if(!hair_location_changed_) {
            if(animated_style) {
                double hr[12]{},fr[12]{};
                if(!hair_head_reference(b,visuals_[2],bone_names_[head],hr)||
                   !hair_head_reference(b,visuals_[1],bone_names_[head],fr))return false;
                for(unsigned i=4;i<7;++i)if(std::abs(hr[i])>500||std::abs(fr[i])>500)return false;
                double fi[12]{};hair_inverse(fr,fi);hair_compose(fi,hr,hair_reference_delta_);
                // Head origins are anatomical anchors, not a transferable height
                // difference between two authored characters. Preserve axis
                // alignment but align the native Head origin to the fitted Head.
                hair_reference_delta_[4]=hair_reference_delta_[5]=hair_reference_delta_[6]=0;
            }
            if(!hair_get(b,hair_original_))return false;
            // Verify the native attachment used in the offline reference fit.

            const double identity[12]{0,0,0,1,0,0,0,0,1,1,1,0};
            {
                double normalized[12]{};std::memcpy(normalized,hair_original_,96);
                const auto scale=normalized[8];
                for(unsigned axis=8;axis<11;++axis)if(!std::isfinite(normalized[axis])||normalized[axis]<.5||normalized[axis]>2)return false;
                if(animated_style&&(std::abs(normalized[9]-scale)>.00001||std::abs(normalized[10]-scale)>.00001))return false;
                normalized[8]=normalized[9]=normalized[10]=1;
                if(!hair_rigid(normalized))return false;
                for(unsigned i=4;i<7;++i)if(std::abs(normalized[i])>100)return false;
                if(animated_style&&!hair_same(normalized,identity))return false;
            }
            hair_original_absolute_=local_read<uint8_t>(hair+392)&28;
            if(hair_original_absolute_)return false;
            borrowed_hair_asset_=call_capture(b,mesh);if(!borrowed_hair_asset_.address)return false;
            hair_socket_=socket;hair_location_changed_=true;
            if(!hair_absolute(b,28))return false;
        }
        if(socket!=hair_socket_||(local_read<uint8_t>(hair+392)&28)!=28)return false;
        const auto* fit=hair_profile_==2?ayane_hair_reference_fit:hair_reference_fit;
        double desired[12]{};multiply(pose[head],fit,desired);
        const auto offset=skin_rotate(pose[head],{fit[4],fit[5],fit[6]});
        desired[4]=pose[head][4]+offset.x;desired[5]=pose[head][5]+offset.y;desired[6]=pose[head][6]+offset.z;
        for(unsigned i=8;i<11;++i)desired[i]=fit[i];
        if(socket_style) {
            double fitted_socket_head[12]{};
            hair_compose(pose[head],hair_profile_==2?ayane_head_reference_fit:two_b_head_reference_fit,fitted_socket_head);
            hair_compose(fitted_socket_head,hair_original_,desired);
            for(unsigned i=8;i<11;++i)desired[i]=hair_original_[i];
        }
        if(animated_style) {
            // Existing bounded GetBoneName and GetSocketTransform dispatch profiles.
            std::memset(args_,0,sizeof(args_));std::memcpy(args_,bone_names_+head,8);
            if(!call(b,visuals_[2],7))return false;
            int32_t index=-1;std::memcpy(&index,args_+8,4);if(index<0||index>=2048)return false;
            std::memset(args_,0,sizeof(args_));std::memcpy(args_,&index,4);
            if(!call(b,visuals_[2],0))return false;
            uint64_t hair_head=0;std::memcpy(&hair_head,args_+4,8);char actual_name[64]{};
            if(!skin_name(b,hair_head,actual_name)||_stricmp(actual_name,"Head"))return false;
            std::memset(args_,0,sizeof(args_));std::memcpy(args_,&hair_head,8);
            if(!call(b,visuals_[2],1))return false;
            double hw[12]{},cw[12]{},ci[12]{},hc[12]{},hci[12]{},fitted_head[12]{};
            std::memcpy(hw,args_+16,96);
            if(!hair_world(b,cw))return false;
            const double scale=hair_original_[8];
            for(unsigned i=8;i<11;++i) {
                if(!std::isfinite(hw[i])||!std::isfinite(cw[i])||std::abs(hw[i]-scale)>.0001||std::abs(cw[i]-scale)>.0001)return false;
                hw[i]=cw[i]=1;
            }
            if(!hair_rigid(hw)||!hair_rigid(cw))return false;
            hair_inverse(cw,ci);hair_compose(ci,hw,hc);hair_inverse(hc,hci);
            hair_compose(pose[head],hair_profile_==2?ayane_head_reference_fit:two_b_head_reference_fit,fitted_head);
            double aligned[12]{};hair_compose(fitted_head,hair_reference_delta_,aligned);
            hair_compose(aligned,hci,desired);
            // hc translation already includes native uniform scale. Preserve it
            // exactly once rather than scaling the attachment offset twice.
            desired[8]=desired[9]=desired[10]=scale;
        }
        alignas(16) uint8_t args[368]{};std::memcpy(args,desired,96);args[352]=1;
        if(!dispatch(b,visuals_[2],hair_world_setter_,34,args))return false;
        std::memcpy(hair_last_,desired,96);
        double actual[12]{};if(!hair_world(b,actual))return false;
        auto& sample=hair_samples_[hair_sample_count_++%20];sample.frame=local_read<uint64_t>(b+0x9272d10);
        for(unsigned i=0;i<7;++i){sample.head[i]=pose[head][i];sample.hair[i]=actual[i];}
        double e=0,dot=0;for(unsigned i=4;i<7;++i)e+=(actual[i]-desired[i])*(actual[i]-desired[i]);
        for(unsigned i=0;i<4;++i)dot+=actual[i]*desired[i];
        sample.position_error=std::sqrt(e);sample.rotation_error=2*std::acos((std::min)(1.0,std::abs(dot)));
        return hair_same(actual,desired);
    }
    uint32_t switch_ms_=0,switch_count_=0;
    struct Rig {CallIdentity asset{};Vec positions[32]{};double rotations[32][4]{};};
    std::vector<Rig> rigs_;
    uint8_t original_tick_=0;
    uint64_t bone_names_[32]{},next_=0;
    uint32_t bones_=0;
    int32_t parents_[32]{};Vec source_[32]{},reference_[32]{};double reference_q_[32][4]{},arm_alignment_[32][4]{};
    std::vector<SkinSection> sections_;
    uint64_t argument_alignment_padding_=0;
    alignas(16) uint8_t args_[144]{};
    bool call(uint64_t b,const CallIdentity& obj,unsigned i) {
        static const size_t indices[]={21,23,25,26,27,28,22,29,24};
        return dispatch(b,obj,fn_[i],indices[i],args_);
    }
    bool wardrobe_valid(uint64_t b) {
        const auto menu=call_identity(b,wardrobe_menu_),actor=call_identity(b,pawn_);
        if(!menu||!actor)return false;
        auto mc=local_read<uint64_t>(menu+16);
        if(!named(b,mc,"WBP_GameMenu_v3_C","/Game/UI/Widgets/InGame_Menu/WBP_GameMenu_v3"))return false;
        // Verified reflected ownership chain, never an actor selected by class name.
        auto scene=skin_reference(b,wardrobe_menu_,"WBP_GameMenu_v3_C","/Game/UI/Widgets/InGame_Menu/WBP_GameMenu_v3","GameMenuScene",1128,2533343509875205ULL,"BP_GameMenuScene_C");
        auto child=skin_reference(b,scene,"BP_GameMenuScene_C","/Game/Gameplay/GameMenu/BP_GameMenuScene","CurrentChildActorToFocus",2056,2251868533752325ULL,"ChildActorComponent");
        auto selected=skin_reference(b,child,"ChildActorComponent","/Script/Engine","ChildActor",568,93660871514915380ULL,"Actor");
        if(selected.address!=pawn_.address||selected.index!=pawn_.index||selected.serial!=pawn_.serial)return false;
        auto page=skin_battle_field(b,mc,"ActivePage",1153,1,0x6e10420,2251869606969861ULL);
        if(!page||!exact_name(b,local_read<uint64_t>(page+8),"ByteProperty")||local_read<uint8_t>(menu+1153)!=7)return false;
        for(unsigned i=0;mc&&i<64;++i,mc=local_read<uint64_t>(mc+0x40)) {
            if(!named(b,mc,"CommonActivatableWidget","/Script/CommonUI"))continue;
            auto f=skin_battle_field(b,mc,"bIsActive",872,1,0x6e119b0,20266268116386324ULL);
            return f&&local_read<uint32_t>(f+0x70)==0xff010001&&local_read<uint8_t>(menu+872)==1;
        }
        return false;
    }
    bool references(uint64_t b,CallIdentity (&out)[5]) {
        if(wardrobe_) {
            if(!wardrobe_valid(b))return false;
            const char* pkg="/Game/Characters/Heros/Cinematics/BP_CineCharacter_Main";
            out[0]=skin_reference(b,pawn_,"BP_CineCharacter_Main_C",pkg,"Body",1040,2251885713555972ULL,"SkeletalMeshComponent");
            out[1]=skin_reference(b,pawn_,"BP_CineCharacter_Main_C",pkg,"Face",1008,2251885713555972ULL,"SkeletalMeshComponent");
            auto actor=call_identity(b,pawn_);if(!actor||!out[0].address||!out[1].address)return false;
            auto cls=local_read<uint64_t>(actor+16);uint64_t f=0;
            for(unsigned n=0;cls&&n<64;++n,cls=local_read<uint64_t>(cls+0x40))if(named(b,cls,"BP_CineCharacter_Main_C",pkg)) {f=skin_battle_field(b,cls,"MeshesToAlter",1672,16,0x6e0de80,549755879429ULL);break;}
            if(!f||!exact_name(b,local_read<uint64_t>(f+8),"ArrayProperty")||(local_read<uint8_t>(f+0x70)&1))return false;
            auto inner=local_read<uint64_t>(f+0x78);
            if(!inner||local_read<uint64_t>(inner)!=b+0x6e11d38||local_read<uint64_t>(inner+16)!=f||!exact_name(b,local_read<uint64_t>(inner+8),"ObjectProperty")||local_read<int32_t>(inner+0x34)!=8)return false;
            auto items=local_read<uint64_t>(actor+1672);auto count=local_read<int32_t>(actor+1680),capacity=local_read<int32_t>(actor+1684);
            if(!items||count<2||count>64||capacity<count||capacity>128)return false;
            auto bonefn=call_identity(b,fn_[0]);if(!bonefn)return false;auto sk=local_read<uint64_t>(bonefn+32);
            for(int32_t i=0;i<count;++i) {
                auto item=call_capture(b,local_read<uint64_t>(items+uint64_t(i)*8));auto o=call_identity(b,item);
                if(!o||o==out[0].address||o==out[1].address||!call_derives(b,local_read<uint64_t>(o+16),sk))continue;
                if(out[2].address)return false;
                std::memset(args_,0,sizeof(args_));if(!call(b,item,5))return false;uint64_t owner=0;std::memcpy(&owner,args_,8);if(owner!=actor)return false;
                out[2]=item;
            }
            if(!out[2].address)return false;
            return true;
        }
        if(battle_manager_.address) {
            if(!skin_combat_member(b,battle_manager_,pawn_))return false;
            for(unsigned i=0;i<3;++i) {
                if(!call_identity(b,visuals_[i]))return false;
                std::memset(args_,0,sizeof(args_));if(!call(b,visuals_[i],5))return false;
                uint64_t owner=0;std::memcpy(&owner,args_,8);if(owner!=call_identity(b,pawn_))return false;
                out[i]=visuals_[i];
            }
            return true;
        }
        const char* package="/Game/Gameplay/CharacterCustomization/Blueprints/BP_CharacterSkinComponent";
        out[0]=skin_reference(b,skin_controller_,"BP_CharacterSkinComponent_C",package,"AttachedBodyOnCharacter",440,0x8001000090205,"SkeletalMeshComponent");
        out[1]=skin_reference(b,skin_controller_,"BP_CharacterSkinComponent_C",package,"AttachedFaceOnCharacter",392,0x8001000090205,"SkeletalMeshComponent");
        const auto face=skin_reference(b,skin_controller_,"BP_CharacterSkinComponent_C",package,"SpawnedCharacterFace",400,0x8001000010a05,"BP_CharacterFaceBase_C");
        const char* face_package="/Game/Characters/Heros/BP_CharacterFaceBase";
        out[2]=skin_reference(b,face,"BP_CharacterFaceBase_C",face_package,"Haircut_SkeletalMesh",664,0x8001400080204,"SkeletalMeshComponent");
        out[3]=skin_reference(b,face,"BP_CharacterFaceBase_C",face_package,"Haircut_StaticMesh",656,0x8001400080204,"StaticMeshComponent");
        out[4]=skin_reference(b,face,"BP_CharacterFaceBase_C",face_package,"Hair",672,0x8001400080204,"GroomComponent");
        const auto sc=call_identity(b,scene_class_),pawn=call_identity(b,pawn_);
        if(!sc||!pawn)return false;
        for(unsigned i=0;i<5;++i) {
            auto o=call_identity(b,out[i]);
            if(!o) {if(i<3)return false;continue;}
            if(!call_derives(b,local_read<uint64_t>(o+16),sc))return false;
            std::memset(args_,0,sizeof(args_));if(!call(b,out[i],5))return false;
            uint64_t owner=0;std::memcpy(&owner,args_,8);if(owner!=pawn)return false;
        }
        return true;
    }
    bool reference_pose(uint64_t b,const CallIdentity& driver,Rig& rig) {
        for(uint32_t i=0;i<bones_;++i) {
            uint64_t name=bone_names_[i];double q[4]{0,0,0,1};Vec p{};
            bool root=false;
            for(unsigned ancestor=0;ancestor<32;++ancestor) {
                std::memset(args_,0,sizeof(args_));std::memcpy(args_,&name,8);
                if(!call(b,driver,7))return false;
                int32_t index=-1;std::memcpy(&index,args_+8,4);if(index<0||index>=2048)return false;
                std::memset(args_,0,sizeof(args_));std::memcpy(args_,&index,4);
                if(!call(b,driver,6))return false;
                double t[12];std::memcpy(t,args_+16,96);
                for(double v:t)if(!std::isfinite(v))return false;
                const double norm=t[0]*t[0]+t[1]*t[1]+t[2]*t[2]+t[3]*t[3];
                if(std::abs(norm-1)>.001||std::abs(t[8]-1)>.001||std::abs(t[9]-1)>.001||std::abs(t[10]-1)>.001)return false;
                p=skin_rotate(t,p);p.x+=t[4];p.y+=t[5];p.z+=t[6];
                const double x=q[0],y=q[1],z=q[2],w=q[3];
                q[0]=t[3]*x+t[0]*w+t[1]*z-t[2]*y;
                q[1]=t[3]*y-t[0]*z+t[1]*w+t[2]*x;
                q[2]=t[3]*z+t[0]*y-t[1]*x+t[2]*w;
                q[3]=t[3]*w-t[0]*x-t[1]*y-t[2]*z;
                std::memset(args_,0,sizeof(args_));std::memcpy(args_,&name,8);
                if(!call(b,driver,8))return false;
                uint64_t parent=0;std::memcpy(&parent,args_+8,8);
                if(!parent){root=true;break;}if(parent==name)return false;name=parent;
            }
            if(!root||std::abs(p.x)>500||std::abs(p.y)>500||std::abs(p.z)>500)return false;
            rig.positions[i]=p;std::memcpy(rig.rotations[i],q,32);
        }
        return true;
    }
    bool align_reference_arms(uint64_t b) {
        for(unsigned i=0;i<32;++i){std::memset(arm_alignment_[i],0,32);arm_alignment_[i][3]=1;}
        // Reference alignment is required for gameplay and preview rigs alike.
        // Recomputed by retarget() for each selected character reference pose.
        char names[32][64]{};
        for(unsigned i=0;i<bones_;++i)if(!skin_name(b,bone_names_[i],names[i]))return false;
        for(unsigned i=0;i<bones_;++i) {
            const bool upper=!_stricmp(names[i],"upperarm_l")||!_stricmp(names[i],"upperarm_r");
            const bool lower=!_stricmp(names[i],"lowerarm_l")||!_stricmp(names[i],"lowerarm_r");
            if(!upper&&!lower)continue;
            const char side=names[i][strlen(names[i])-1];
            unsigned child=bones_;
            for(unsigned j=0;j<bones_;++j)if(parents_[j]==int32_t(i) &&
                !_strnicmp(names[j],upper?"lowerarm_":"hand_",upper?9:5) &&
                tolower(names[j][strlen(names[j])-1])==tolower(side)){child=j;break;}
            if(child==bones_)return false;
            Vec a{source_[child].x-source_[i].x,source_[child].y-source_[i].y,source_[child].z-source_[i].z};
            Vec c{reference_[child].x-reference_[i].x,reference_[child].y-reference_[i].y,reference_[child].z-reference_[i].z};
            const double an=std::sqrt(a.x*a.x+a.y*a.y+a.z*a.z),cn=std::sqrt(c.x*c.x+c.y*c.y+c.z*c.z);
            if(!std::isfinite(an)||!std::isfinite(cn)||an<1||cn<1)return false;
            a={a.x/an,a.y/an,a.z/an};c={c.x/cn,c.y/cn,c.z/cn};
            auto* q=arm_alignment_[i];q[0]=a.y*c.z-a.z*c.y;q[1]=a.z*c.x-a.x*c.z;q[2]=a.x*c.y-a.y*c.x;q[3]=1+a.x*c.x+a.y*c.y+a.z*c.z;
            double n=std::sqrt(q[0]*q[0]+q[1]*q[1]+q[2]*q[2]+q[3]*q[3]);if(n<.001||!std::isfinite(n))return false;
            for(unsigned j=0;j<4;++j)q[j]/=n;
            if(lower)std::memcpy(arm_alignment_[child],q,32);
        }
        return true;
    }
    bool retarget(uint64_t b,const CallIdentity (&visuals)[5]) {
        const auto started=GetTickCount64();
        const auto driver=call_identity(b,visuals[0]);if(!driver)return false;
        const auto asset=call_capture(b,local_read<uint64_t>(driver+1384));if(!asset.address)return false;
        const auto tick=(tick_changed_&&driver==driver_.address)?original_tick_:local_read<uint8_t>(driver+1948);if(tick>4)return false;
        Rig next{};bool found=false;
        for(const auto& cached:rigs_)if(cached.asset.address==asset.address&&cached.asset.serial==asset.serial&&cached.asset.index==asset.index){next=cached;found=true;break;}
        if(!found) {
            next.asset=asset;if(!reference_pose(b,visuals[0],next))return false;
            if(rigs_.size()>=8)rigs_.erase(rigs_.begin());rigs_.push_back(next);
        }
        // A hairstyle swap does not release the body, face or pose driver.
        bool hair_only=hair_profile_&&!battle_manager_.address&&tick_changed_&&
            driver==driver_.address&&asset.address==asset_.address&&asset.serial==asset_.serial;
        for(unsigned i=0;i<5;++i)if(i!=2 &&
            (visuals[i].address!=visuals_[i].address||visuals[i].serial!=visuals_[i].serial))hair_only=false;
        if(hair_only) {
            if(!restore_hair(b))return false;
            if(changed_[2]&&call_identity(b,visuals_[2])) {
                std::memset(args_,0,sizeof(args_));args_[0]=hidden_[2]?1:0;
                if(!call(b,visuals_[2],3))return false;
            }
            visuals_[2]=visuals[2];changed_[2]=false;
            hidden_[2]=visuals_[2].address&&(local_read<uint8_t>(visuals_[2].address+393)&8)!=0;
            rejected_hair_={};rejected_hair_asset_={};hair_retry_count_=0;hair_retry_at_=0;
            switch_ms_=uint32_t(GetTickCount64()-started);++switch_count_;return true;
        }
        if(!restore_visuals(b))return false;
        rejected_hair_={};rejected_hair_asset_={};hair_retry_count_=0;hair_retry_at_=0;
        driver_=visuals[0];asset_=asset;original_tick_=tick;
        std::memcpy(visuals_,visuals,sizeof(visuals_));
        for(unsigned i=0;i<5;++i)hidden_[i]=visuals_[i].address&&(local_read<uint8_t>(visuals_[i].address+393)&8)!=0;
        std::memcpy(reference_,next.positions,sizeof(reference_));std::memcpy(reference_q_,next.rotations,sizeof(reference_q_));
        if(!align_reference_arms(b)||!hide(b))return false;
        switch_ms_=uint32_t(GetTickCount64()-started);++switch_count_;return true;
    }
public:
    bool freeze(bool enabled){if(!active())return false;frozen_=enabled;return true;}
    void samples(MeshPacket& p)const {
        const uint32_t count=(std::min)(hair_sample_count_,20U);
        std::memcpy(p.indices,&count,4);std::memcpy(reinterpret_cast<uint8_t*>(p.indices)+4,&hair_sample_count_,4);
        for(uint32_t i=0;i<count;++i)std::memcpy(reinterpret_cast<uint8_t*>(p.indices)+8+i*sizeof(HairSample),&hair_samples_[(hair_sample_count_-count+i)%20],sizeof(HairSample));
        p.vertex_count=(std::min)(sample_count_,128U);p.index_count=sample_count_;p.section_id=frozen_?1:0;
        for(uint32_t i=0;i<p.vertex_count;++i)std::memcpy(reinterpret_cast<uint8_t*>(p.vertices)+i*sizeof(Sample),&samples_[(sample_count_-p.vertex_count+i)%128],sizeof(Sample));
    }
    uint32_t switch_ms()const{return switch_ms_;}
    uint32_t switch_count()const{return switch_count_;}
    CallIdentity driver()const{return driver_;}
    CallIdentity asset()const{return asset_;}
    bool active()const{return bones_!=0;}
    uint32_t restore_step_=0;
    uint32_t restore_step()const{return face_fit_step_?uint32_t(1000+face_fit_step_):restore_step_;}
    bool restore_hair(uint64_t b) {
        if(hair_location_changed_) {
            auto hair=call_identity(b,visuals_[2]);
            if(hair&&hair_layout(b)&&local_read<uint64_t>(hair+184)==hair_socket_) {
                const bool original_parent=local_read<uint64_t>(hair+176)==call_identity(b,visuals_[1]);
                double current[12]{};
                // The original-parent path owns a saved authored transform. A
                // transient invalid current transform must not prevent restoring it.
                // Reading current is required only to prove ownership after reparenting.
                restore_step_=2;if(!original_parent&&!hair_get(b,current))return false;
                // A character switch may reparent the same hair before this tick.
                // Release our transform only if asset identity and our last write
                // still match; never overwrite a new hairstyle's authored state.
                restore_step_=3;
                if(!original_parent && (!call_identity(b,borrowed_hair_asset_) ||
                   local_read<uint64_t>(hair+1384)!=borrowed_hair_asset_.address ||
                   (local_read<uint8_t>(hair+392)&28)!=28 || !hair_same(current,hair_last_)))return false;
                restore_step_=4;if(!hair_absolute(b,hair_original_absolute_))return false;
                restore_step_=5;if(!hair_set(b,hair_original_))return false;
                restore_step_=6;double restored[12]{};if(!hair_get(b,restored)||!hair_same(restored,hair_original_))return false;
            }
            hair_location_changed_=false;
        }
        return true;
    }
    bool restore_visuals(uint64_t b) {
        restore_step_=1;
        if(!restore_hair(b))return false;
        if(!restore_attachment_source(b))return false;
        if(face_tick_changed_) {
            if(auto face=call_identity(b,visuals_[1])) *reinterpret_cast<uint8_t*>(face+1948)=face_original_tick_;
            face_tick_changed_=false;
        }
        for(unsigned i=0;i<5;++i)if(changed_[i]) {
            if(call_identity(b,visuals_[i])) {
                std::memset(args_,0,sizeof(args_));args_[0]=hidden_[i]?1:0;
                restore_step_=10+i;if(!call(b,visuals_[i],3))return false;
            }
            changed_[i]=false;
        }
        if(tick_changed_) {
            if(auto o=call_identity(b,driver_)) *reinterpret_cast<uint8_t*>(o+1948)=original_tick_;
            tick_changed_=false;
        }
        restore_step_=0;return true;
    }
    bool restore(uint64_t b) {
        if(!restore_visuals(b))return false;
        bones_=0;sections_.clear();rigs_.clear();follow_=false;battle_manager_={};return true;
    }
    bool suspend(uint64_t b,const CallIdentity& component) {
        if(!restore(b))return false;
        std::memset(args_,0,sizeof(args_));args_[0]=1;
        return call(b,component,3);
    }
    uint32_t start(uint64_t b,const MeshPacket& p,const CallIdentity& pawn,uint32_t section_count,const uint32_t* counts) {
        if(active())return 1830;handoff_started_=0;
        if(p.section_id>4)return 1831;wardrobe_=p.section_id>=3;hair_profile_=wardrobe_?(p.section_id==3?2:1):p.section_id;wardrobe_menu_=p.material_inputs[5];
        // Optional visuals must never carry over from a previous model/pawn.
        for(unsigned i=0;i<5;++i){visuals_[i]={};hidden_[i]=false;changed_[i]=false;}
        switch_ms_=switch_count_=0;
        sample_count_=0;hair_sample_count_=0;frozen_=false;
        static const size_t fi[]={21,23,25,26,27,28};
        for(unsigned i=0;i<6;++i)if(!function(b,p.inputs[1+i],fi[i]))return 1802;
        const auto driver=call_identity(b,p.inputs[0]);
        const auto sk=call_identity(b,p.inputs[10]),sc=call_identity(b,p.inputs[11]);
        if(!driver || !call_derives(b,local_read<uint64_t>(driver+16),sk))return 1831;
        const auto tick=skin_field(b,sk,"SkinnedMeshComponent","VisibilityBasedAnimTickOption","EnumProperty",1948,0x6deeee8,0x18041240004205);
        const auto hidden=skin_field(b,sc,"SceneComponent","bHiddenInGame","BoolProperty",393,0x6e119b0,0x18001200000015);
        const auto asset_field=skin_field(b,sk,"SkinnedMeshComponent","SkinnedAsset","ObjectProperty",1384,0x6e11d38,0x14c001000000214);
        if(!tick || !hidden || !asset_field || local_read<int32_t>(tick+0x34)!=1 || local_read<int32_t>(hidden+0x34)!=1 ||
           local_read<uint32_t>(hidden+0x70)!=0x08080001 || local_read<int32_t>(asset_field+0x34)!=8)return 1831;
        auto en=local_read<uint64_t>(tick+0x78);
        if(!named(b,en,"EVisibilityBasedAnimTickOption","/Script/Engine"))return 1831;
        for(unsigned i=0;i<3;++i) {
            static const size_t extra[]={22,29,24};
            if(!function(b,p.inputs[12+i],extra[i]))return 1802;
            fn_[6+i]=p.inputs[12+i];
        }
        driver_=p.inputs[0];pawn_=wardrobe_?p.inputs[15]:pawn;std::memcpy(fn_,p.inputs+1,6*sizeof(CallIdentity));scene_class_=p.inputs[11];
        hair_setter_=p.material_inputs[0];hair_getter_=p.material_inputs[1];hair_world_getter_=p.material_inputs[2];hair_world_setter_=p.material_inputs[3];hair_absolute_=p.material_inputs[4];
        if(!function(b,hair_world_getter_,33)||!function(b,hair_world_setter_,34)||!function(b,hair_absolute_,35))return 1831;
        if(!function(b,hair_setter_,31)||!function(b,hair_getter_,32)||!hair_layout(b))return 1831;
        battle_manager_=wardrobe_?CallIdentity{}:p.inputs[15];
        if(wardrobe_&&!wardrobe_valid(b))return 1831;
        if(battle_manager_.address&&!skin_combat_member(b,battle_manager_,pawn))return 1831;
        skin_controller_=skin_reference(b,pawn,"BP_jRPG_Character_World_C","/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_Character_World","BP_CharacterSkinComponent",2688,0x8001400080204,"BP_CharacterSkinComponent_C");
        if(!wardrobe_&&!battle_manager_.address&&!skin_controller_.address)return 1831;
        asset_=call_capture(b,local_read<uint64_t>(driver+1384));if(!asset_.address)return 1831;
        // The selected character's exact bone names and reference pose are
        // validated below; do not restrict the driver to a Verso asset name.
        for(unsigned i=0;i<3;++i) {
            visuals_[i]=p.inputs[7+i];auto o=call_identity(b,visuals_[i]);
            if(!o || !call_derives(b,local_read<uint64_t>(o+16),sc))return 1831;
            std::memset(args_,0,sizeof(args_));if(!call(b,visuals_[i],5))return 1831;
            uint64_t owner=0;std::memcpy(&owner,args_,8);if(owner!=call_identity(b,pawn_))return 1831;
            hidden_[i]=(local_read<uint8_t>(o+393)&8)!=0;
        }
        if(visuals_[0].address!=driver)return 1831;
        original_tick_=local_read<uint8_t>(driver+1948);if(original_tick_>4)return 1831;
        const auto length=wcsnlen(p.texture_path,512);
        if(length<10 || length>=512 || p.texture_path[1]!=L':' || _wcsicmp(p.texture_path+length-8,L".e33skin"))return 1832;
        HANDLE file=CreateFileW(p.texture_path,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
        if(file==INVALID_HANDLE_VALUE)return 1832;
        LARGE_INTEGER size{};DWORD got=0;std::vector<uint8_t> bytes;
        bool ok=GetFileSizeEx(file,&size) && size.QuadPart>=16 && size.QuadPart<=16*1024*1024;
        if(ok){bytes.resize(size_t(size.QuadPart));ok=ReadFile(file,bytes.data(),DWORD(bytes.size()),&got,nullptr) && got==bytes.size();}
        CloseHandle(file);if(!ok)return 1832;
        size_t at=0;
        auto read=[&](void* dst,size_t n){if(n>bytes.size()-at)return false;std::memcpy(dst,bytes.data()+at,n);at+=n;return true;};
        char magic[8];uint32_t nb=0,ns=0;
        if(!read(magic,8)||std::memcmp(magic,"E33SKIN2",8)||!read(&nb,4)||!read(&ns,4)||!nb||nb>32||ns!=section_count||ns>64)return 1832;
        for(uint32_t i=0;i<nb;++i) {
            uint32_t index=0;char expected[64]{},actual[64]{};
            if(!read(&index,4)||!read(expected,64)||index>=2048||!std::memchr(expected,0,64))return 1832;
            float source[3];double reference[7];
            if(!read(parents_+i,4)||!read(source,12)||!read(reference,56)||parents_[i]>=int32_t(i)||parents_[i]<-1)return 1832;
            for(float v:source)if(!std::isfinite(v)||std::abs(v)>500)return 1832;
            for(double v:reference)if(!std::isfinite(v)||std::abs(v)>500)return 1832;
            const double qnorm=reference[0]*reference[0]+reference[1]*reference[1]+reference[2]*reference[2]+reference[3]*reference[3];
            if(std::abs(qnorm-1)>0.001)return 1832;
            source_[i]={source[0],source[1],source[2]};reference_[i]={reference[4],reference[5],reference[6]};std::memcpy(reference_q_[i],reference,32);
            std::memset(args_,0,sizeof(args_));std::memcpy(args_,&index,4);
            if(!call(b,driver_,0))return 1831;
            std::memcpy(bone_names_+i,args_+4,8);
            if(!skin_name(b,bone_names_[i],actual)||std::strcmp(expected,actual))return 1831;
        }
        std::vector<SkinSection> pending;uint32_t total=0;
        for(uint32_t i=0;i<ns;++i) {
            SkinSection s;uint32_t count=0;
            if(!read(&s.index,4)||!read(&count,4)||s.index!=i||counts[i]!=count||count<3||count>100000||total+count>100000)return 1832;
            total+=count;s.bind.resize(count);s.vertices.resize(count);s.normals.resize(count);
            if(!read(s.bind.data(),size_t(count)*sizeof(SkinVertex)))return 1832;
            for(const auto& v:s.bind) {
                double sum=0;
                for(const auto& w:v.weights) {
                    if(w.bone>=nb || !std::isfinite(w.weight)||w.weight<0||w.weight>1)return 1832;
                    for(unsigned k=0;k<3;++k)if(!std::isfinite(w.point[k])||std::abs(w.point[k])>500||!std::isfinite(w.normal[k])||std::abs(w.normal[k])>1.01f)return 1832;
                    sum+=w.weight;
                }
                if(std::abs(sum-1)>0.0001)return 1832;
            }
            pending.push_back(std::move(s));
        }
        if(at!=bytes.size())return 1832;
        sections_=std::move(pending);bones_=nb;next_=0;
        if(!align_reference_arms(b)){bones_=0;sections_.clear();return 1832;}
        Rig initial;initial.asset=asset_;std::memcpy(initial.positions,reference_,sizeof(reference_));std::memcpy(initial.rotations,reference_q_,sizeof(reference_q_));rigs_.push_back(initial);
        return 0;
    }
    bool hide(uint64_t b) {
        if(!active())return false;
        auto driver=call_identity(b,driver_);if(!driver)return false;
        if(!tick_changed_){tick_changed_=true;*reinterpret_cast<uint8_t*>(driver+1948)=0;}
        // Keep the hidden native face evaluating its Head socket. The skinned
        // tick enum layout was verified in start(), including type and width.
        if(hair_profile_ && !battle_manager_.address && !face_tick_changed_) {
            auto face=call_identity(b,visuals_[1]);
            auto bone_fn=call_identity(b,fn_[0]);
            if(!face||!bone_fn||!function(b,fn_[0],21)||!call_derives(b,local_read<uint64_t>(face+16),local_read<uint64_t>(bone_fn+32)))return false;
            face_original_tick_=local_read<uint8_t>(face+1948);if(face_original_tick_>4)return false;
            face_tick_changed_=true;*reinterpret_cast<uint8_t*>(face+1948)=0;
        }
        for(unsigned i=0;i<5;++i)if(visuals_[i].address && !changed_[i]) {
            if(i==2 && hair_profile_ && !battle_manager_.address)continue; // Fitter owns hair visibility.
            changed_[i]=true;std::memset(args_,0,sizeof(args_));args_[0]=1;
            if(!call(b,visuals_[i],3))return false;
        }
        follow_=true;return true;
    }
    bool update(uint64_t b,const CallIdentity& component,const double* origin) {
        if(!active())return true;
        if(wardrobe_ && !wardrobe_valid(b)) {
            if(!call_identity(b,wardrobe_menu_)||!call_identity(b,pawn_))return false;
            if(!handoff_started_)handoff_started_=GetTickCount64();
            if(GetTickCount64()-handoff_started_>10000)return false;
            if(!restore_visuals(b))return false;
            std::memset(args_,0,sizeof(args_));args_[0]=1;
            return call(b,component,3);
        }
        handoff_started_=0;
        if(!wardrobe_&&battle_manager_.address) {if(!skin_combat_member(b,battle_manager_,pawn_))return false;}
        else if(!wardrobe_) {std::memset(args_,0,sizeof(args_));if(!call(b,pawn_,4)||!args_[0])return false;}
        if(!picto_frame_source(b))return false;
        const auto frame=local_read<uint64_t>(b+0x9272d10);if(frame==next_)return true;if(frame<next_)return false;next_=frame;
        const double started=clock_ms();
        if(follow_) {
            CallIdentity current[5]{};
            if(!references(b,current)) {
                // A transient hairstyle list is not loss of body ownership. Keep
                // the replacement and restoration ledger while Wardrobe streams hair.
                if(wardrobe_ && hair_profile_ && wardrobe_valid(b) &&
                   current[0].address==visuals_[0].address && current[0].serial==visuals_[0].serial &&
                   current[1].address==visuals_[1].address && current[1].serial==visuals_[1].serial) {
                    // Keep the last fitted hairstyle visible through the list refresh.
                    return true;
                }
                if(!restore_visuals(b))return false;
                std::memset(args_,0,sizeof(args_));args_[0]=1;return call(b,component,3);
            }
            bool different=!tick_changed_;
            for(unsigned i=0;i<5;++i)if(current[i].address!=visuals_[i].address||current[i].serial!=visuals_[i].serial)different=true;
            if(local_read<uint64_t>(current[0].address+1384)!=asset_.address)different=true;
            if(different&&!retarget(b,current))return false;
            if(local_read<uint8_t>(component.address+393)&8) {std::memset(args_,0,sizeof(args_));if(!call(b,component,3))return false;}
        }
        auto driver=call_identity(b,driver_);
        if(!driver || !call_identity(b,asset_) || local_read<uint64_t>(driver+1384)!=asset_.address)return false;
        // Character/outfit refresh can reset visibility on a still-owned mesh.
        // Preserve the initial restore ledger, but reassert our active override.
        for(unsigned i=0;i<5;++i)if(changed_[i]) {
            if(i==2&&hair_profile_&&!battle_manager_.address)continue;
            const auto visual=call_identity(b,visuals_[i]);if(!visual)return false;
            if(!(local_read<uint8_t>(visual+393)&8)) {
                std::memset(args_,0,sizeof(args_));args_[0]=1;
                if(!call(b,visuals_[i],3))return false;
            }
        }
        double pose[32][12]{};
        for(uint32_t i=0;i<bones_;++i) {
            std::memset(args_,0,sizeof(args_));std::memcpy(args_,bone_names_+i,8);
            if(!call(b,driver_,1))return false;
            std::memcpy(pose[i],args_+16,96);
            for(unsigned j=0;j<12;++j)if(!std::isfinite(pose[i][j]))return false;
        }
        Sample sample{};sample.frame=frame;sample.time_ms=started;
        std::memcpy(sample.root,pose[0]+4,24);std::memcpy(sample.joint,pose[bones_-1]+4,24);
        for(unsigned i=0;i<4;++i)sample.quaternion_norm+=pose[0][i]*pose[0][i];
        if(frozen_) {
            if(!sections_.empty()&&!sections_[0].vertices.empty())std::memcpy(sample.vertex,&sections_[0].vertices[0],24);
            sample.work_ms=clock_ms()-started;samples_[sample_count_++%128]=sample;return true;
        }
        // Preserve the source rig's lengths. Copy orientation deltas from
        // Verso, then compose source joints along their own parent hierarchy.
        for(uint32_t i=0;i<bones_;++i) {
            double* t=pose[i];const auto* r=reference_q_[i];
            const double x=t[0],y=t[1],z=t[2],w=t[3];
            t[0]=-w*r[0]+x*r[3]-y*r[2]+z*r[1];
            t[1]=-w*r[1]+x*r[2]+y*r[3]-z*r[0];
            t[2]=-w*r[2]-x*r[1]+y*r[0]+z*r[3];
            t[3]=w*r[3]+x*r[0]+y*r[1]+z*r[2];
            double aligned[4]{};multiply(t,arm_alignment_[i],aligned);std::memcpy(t,aligned,32);
            const auto parent=parents_[i];
            if(parent>=0) {
                const auto* pt=pose[parent];
                Vec offset{(source_[i].x-source_[parent].x)*t[8],(source_[i].y-source_[parent].y)*t[9],(source_[i].z-source_[parent].z)*t[10]};
                offset=skin_rotate(pt,offset);
                // Pelvis translation carries the locomotion bob relative to root.
                Vec bob{};
                if(parent==0) {
                    Vec expected=skin_rotate(pt,{(reference_[i].x-reference_[parent].x)*t[8],(reference_[i].y-reference_[parent].y)*t[9],(reference_[i].z-reference_[parent].z)*t[10]});
                    bob={t[4]-pt[4]-expected.x,t[5]-pt[5]-expected.y,t[6]-pt[6]-expected.z};
                }
                t[4]=pt[4]+offset.x+bob.x;t[5]=pt[5]+offset.y+bob.y;t[6]=pt[6]+offset.z+bob.z;
            }
        }
        if(!fit_attachment_source(b,pose)||!fit_hair(b,pose))return false;
        for(auto& s:sections_) {
            for(size_t i=0;i<s.bind.size();++i) {
                Vec v{},n{};
                for(const auto& w:s.bind[i].weights)if(w.weight>0) {
                    const auto* t=pose[w.bone];
                    auto p=skin_rotate(t,{w.point[0]*t[8],w.point[1]*t[9],w.point[2]*t[10]});
                    auto normal=skin_rotate(t,{w.normal[0],w.normal[1],w.normal[2]});
                    v.x+=(p.x+t[4]-origin[0])*w.weight;v.y+=(p.y+t[5]-origin[1])*w.weight;v.z+=(p.z+t[6]-origin[2])*w.weight;
                    n.x+=normal.x*w.weight;n.y+=normal.y*w.weight;n.z+=normal.z*w.weight;
                }
                const auto old=s.vertices[i];const double dx=v.x-old.x,dy=v.y-old.y,dz=v.z-old.z;
                sample.max_delta=(std::max)(sample.max_delta,std::sqrt(dx*dx+dy*dy+dz*dz));
                s.vertices[i]=v;s.normals[i]=n;
            }
            std::memset(args_,0,sizeof(args_));std::memcpy(args_,&s.index,4);
            const auto count=int32_t(s.vertices.size());const Array v{s.vertices.data(),count,count},n{s.normals.data(),count,count};
            std::memcpy(args_+8,&v,16);std::memcpy(args_+24,&n,16);
            if(!call(b,component,2))return false;
        }
        if(!sections_.empty()&&!sections_[0].vertices.empty()) {
            std::memcpy(sample.vertex,&sections_[0].vertices[0],24);
            const auto n=sections_[0].normals[0];sample.normal_norm=std::sqrt(n.x*n.x+n.y*n.y+n.z*n.z);
        }
        sample.work_ms=clock_ms()-started;samples_[sample_count_++%128]=sample;
        return true;
    }
};
