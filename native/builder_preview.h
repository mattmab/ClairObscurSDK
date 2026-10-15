    builder_gpu::ImageBridge image_bridge_;
    uint32_t image_result_=0,image_error_=0;double image_max_ms_=0;
    bool image_started_=false,image_pending_=false,image_await_arm_=false;uint64_t image_sequence_=0,image_request_=0;uint32_t image_stage_=0;
    std::array<uint8_t,20984> image_packet_{};
    CallIdentity thumbnail_prop_{},preview_actor_{},preview_capture_{},preview_target_{};
    uint64_t preview_actor_lease_=0,preview_target_lease_=0;
    std::vector<std::pair<CallIdentity,uint64_t>> preview_images_;
    bool preview_setting(uint64_t b,const char* name,uint64_t value) {
        const auto actor=gpu_actor_,capture=gpu_capture_;gpu_actor_=preview_actor_;gpu_capture_=preview_capture_;
        const bool result=gpu_setting(b,name,value);gpu_actor_=actor;gpu_capture_=capture;return result;
    }
    template<class Pool> bool preview_stop(uint64_t b,uint64_t session,Pool& pool) {
        if(image_started_){image_bridge_.stop();image_started_=false;}image_pending_=false;image_await_arm_=false;image_result_=image_error_=0;
        if(thumbnail_prop_.address){if(!clear_spawned(b,session,pool,thumbnail_prop_))return false;thumbnail_prop_={};}
        if(call_identity(b,preview_actor_)){clear();if(!call(b,preview_actor_,2))return false;}preview_actor_={};preview_capture_={};
        if(call_identity(b,preview_target_)){clear();put(0,preview_target_.address);if(!call(b,ids_[83],45))return false;}preview_target_={};
        TargetStrongReferenceOps ops{b,{-1,0,0}};
        if(preview_actor_lease_){if(pool.release(ops,session,preview_actor_lease_)!=StrongLeaseResult::Ok)return false;preview_actor_lease_=0;}
        if(preview_target_lease_){if(pool.release(ops,session,preview_target_lease_)!=StrongLeaseResult::Ok)return false;preview_target_lease_=0;}
        while(!preview_images_.empty()) {
            const auto image=preview_images_.back();
            if(call_identity(b,image.first)){clear();put(0,image.first.address);if(!call(b,ids_[83],45))return false;}
            if(image.second&&pool.release(ops,session,image.second)!=StrongLeaseResult::Ok)return false;
            preview_images_.pop_back();
        }
        return true;
    }
    template<class Pool> bool preview(uint64_t b,uint64_t session,Pool& pool,CallIdentity actor,CallIdentity& imageTarget,bool reuse=false) {
        if(preview_images_.size()>=31)return false;
        auto it=std::find_if(spawned_.begin(),spawned_.end(),[&](const Spawned& s){return s.actor.address==actor.address&&s.actor.serial==actor.serial;});
        if(it==spawned_.end()||!call_identity(b,actor))return false;
        clear();if(!call(b,actor,47))return false;
        if(call_identity(b,it->component)&&call_derives(b,local_read<uint64_t>(it->component.address+16),ids_[63].address)) {
            clear();args_[0]=1;if(!call(b,it->component,48))return false;
        }
        if(!preview_actor_.address) {
            clear();put(0,ids_[0].address);put(8,ids_[80].address);transform(args_+16,position_);args_[112]=1;
            if(!call(b,ids_[4],0))return false;preview_actor_=call_capture(b,get<uint64_t>(136));if(!preview_actor_.address)return false;
            TargetStrongReferenceOps ops{b,preview_actor_};if(pool.acquire(ops,session,preview_actor_.address,preview_actor_lease_)!=StrongLeaseResult::Ok)return false;
            const GpuProperty* property=nullptr;uint64_t owner=0;if(!gpu_property(b,preview_actor_,"CaptureComponent2D",property,owner))return false;
            preview_capture_=call_capture(b,local_read<uint64_t>(preview_actor_.address+property->offset));if(!preview_capture_.address)return false;
            float fov=35.f;uint32_t fovBits;std::memcpy(&fovBits,&fov,4);
            if(!preview_setting(b,"bCaptureEveryFrame",0)||!preview_setting(b,"bCaptureOnMovement",0)||!preview_setting(b,"bUseRayTracingIfEnabled",0)||!preview_setting(b,"CaptureSource",7)||!preview_setting(b,"PrimitiveRenderMode",2)||!preview_setting(b,"FOVAngle",fovBits))return false;
            clear();put(0,preview_actor_.address);transform(args_+16,position_);if(!call(b,ids_[4],1))return false;
        }
        if(!reuse&&preview_target_.address){preview_images_.push_back({preview_target_,preview_target_lease_});preview_target_={};preview_target_lease_=0;}
        if(!preview_target_.address) {
            clear();put(0,ids_[0].address);put(8,int32_t(reuse?322:320));put(12,int32_t(reuse?242:240));args_[16]=2;
            if(!call(b,ids_[83],44))return false;preview_target_=call_capture(b,get<uint64_t>(40));if(!preview_target_.address)return false;
            TargetStrongReferenceOps rtOps{b,preview_target_};if(pool.acquire(rtOps,session,preview_target_.address,preview_target_lease_)!=StrongLeaseResult::Ok)return false;
            // Slate creates a weak reference when a texture enters a brush. Allocate
            // its stable serial before exposing or caching its identity.
            if(!preview_target_.serial){if(rtOps.allocate_serial(preview_target_.index)<=0)return false;preview_target_=call_capture(b,preview_target_.address);}
            if(!preview_setting(b,"TextureTarget",preview_target_.address))return false;
        }
        clear();args_[56]=1;if(!call(b,actor,25))return false;
        double center[3],extent[3];std::memcpy(center,args_+8,24);std::memcpy(extent,args_+32,24);
        const double radius=std::max(10.,std::sqrt(extent[0]*extent[0]+extent[1]*extent[1]+extent[2]*extent[2]));
        const double camera[]={center[0]-radius*3.5,center[1]-radius*2.,center[2]+radius*1.2};
        const double rot[]={-std::atan2(1.2,std::hypot(3.5,2.))*180./3.141592653589793,std::atan2(2.,3.5)*180./3.141592653589793,0.};
        clear();std::memcpy(args_,camera,24);std::memcpy(args_+24,rot,24);args_[304]=1;if(!call(b,preview_actor_,5)||!args_[305])return false;
        clear();if(!call(b,preview_capture_,43))return false;
        clear();put(0,actor.address);args_[8]=1;if(!call(b,preview_capture_,49))return false;
        if(!preview_setting(b,"CaptureSource",7))return false;
        if(!reuse||!image_bridge_.ready()){clear();if(!call(b,preview_capture_,41))return false;}imageTarget=preview_target_;return true;
    }

    template<class Pool> bool thumbnail_mesh(uint64_t b,uint64_t session,Pool& pool,CallIdentity mesh) {
        if(!call_identity(b,mesh)||!call_derives(b,local_read<uint64_t>(mesh.address+16),ids_[85].address))return false;
        if(!image_started_) {
            if(!preview_stop(b,session,pool)||!image_bridge_.start(322,242,2))return false;
            image_started_=true;
        }
        if(image_pending_)return false;
        if(!thumbnail_prop_.address) {
            double pos[]={position_[0],position_[1],position_[2]+100000.};
            uint8_t pose[96]{};transform(pose,pos);CallIdentity component{};
            if(!spawn_asset(b,session,pool,mesh,ids_[84],pose,thumbnail_prop_,component))return false;
        } else {
            auto it=std::find_if(spawned_.begin(),spawned_.end(),[&](const Spawned& row){return row.actor.address==thumbnail_prop_.address&&row.actor.serial==thumbnail_prop_.serial;});
            if(it==spawned_.end()||!call_identity(b,it->actor)||!call_identity(b,it->component))return false;
            clear();put(0,mesh.address);if(!call(b,it->component,46)||!args_[8])return false;
            it->asset=mesh;
        }
        CallIdentity image{};return preview(b,session,pool,thumbnail_prop_,image,true);
    }
    std::wstring preview_directory_,preview_filename_;
    std::vector<std::pair<CallIdentity,uint64_t>> cached_images_;
    bool thumbnail_path(const uint8_t* raw,const wchar_t* suffix) {
        std::wstring key;
        for(size_t i=0;i<64;++i){const auto c=raw[2004+i];if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return false;key.push_back(wchar_t(c));}
        wchar_t exe[1024]{};const auto n=GetModuleFileNameW(nullptr,exe,1024);if(!n||n>=1024)return false;
        const auto root=std::filesystem::path(exe).parent_path().parent_path().parent_path().parent_path();
        preview_directory_=(root/L"SDK"/L"settings"/L"E33WorldBuilder"/L"cache"/L"neutral-v1").wstring();
        preview_filename_=key+suffix;return true;
    }
    struct PreviewString {uint64_t data;int32_t count,capacity;};
    PreviewString preview_string(const std::wstring& value) {return {reinterpret_cast<uint64_t>(value.c_str()),int32_t(value.size()+1),int32_t(value.size()+1)};}
    bool image_begin(uint64_t b,const uint8_t* raw,uint32_t& ready) {
        ready=0;if(!image_started_||image_pending_||image_bridge_.error())return false;
        if(!image_bridge_.ready())return true;
        std::memcpy(image_packet_.data(),raw,image_packet_.size());
        image_result_=image_error_=0;image_stage_=0;image_request_=++image_sequence_;
        if(!image_bridge_.arm(image_request_))return true;
        image_pending_=true;
        if(!preview_setting(b,"CaptureSource",7))return false;
        clear();if(!call(b,preview_capture_,41))return false;ready=1;return true;
    }
    bool image_poll(uint64_t b,uint32_t& ready) {
        ready=0;if(!image_pending_||image_bridge_.error())return false;
        if(image_await_arm_) {
            if(!image_bridge_.arm(image_request_))return true;
            image_await_arm_=false;clear();if(!call(b,preview_capture_,41))return false;
            ready=1;image_result_=1;return true;
        }
        std::vector<uint8_t> rgb;const auto id=image_bridge_.poll_image(rgb);if(!id)return true;
        if(id!=image_request_||rgb.size()!=320*240*3||!thumbnail_path(image_packet_.data(),image_stage_?L".normal.rgb":L".base.rgb"))return false;
        const auto filename=preview_directory_+L"/"+preview_filename_;
        HANDLE file=CreateFileW(filename.c_str(),GENERIC_WRITE,0,nullptr,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
        if(file==INVALID_HANDLE_VALUE)return false;
        DWORD written=0;const bool ok=WriteFile(file,rgb.data(),DWORD(rgb.size()),&written,nullptr)&&written==rgb.size();CloseHandle(file);if(!ok)return false;
        if(!image_stage_) {
            image_stage_=1;image_request_=++image_sequence_;
            if(!preview_setting(b,"CaptureSource",6))return false;
            image_await_arm_=true;ready=1;
        } else {image_pending_=false;ready=2;}
        image_result_=ready;return true;
    }
    void image_tick(uint64_t b) {
        if(!image_pending_||image_error_)return;
        const auto start=std::chrono::steady_clock::now();uint32_t ready=0;
        if(!image_poll(b,ready))image_error_=19480+image_bridge_.error();
        image_max_ms_=std::max(image_max_ms_,std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count());
    }
    bool thumbnail_export(uint64_t b,const uint8_t* raw) {
        uint32_t stage=0;std::memcpy(&stage,raw+2000,4);
        if(stage>1||!call_identity(b,preview_target_)||!thumbnail_path(raw,stage?L".normal.png":L".base.png"))return false;
        clear();put(0,ids_[0].address);put(8,preview_target_.address);put(16,preview_string(preview_directory_));put(32,preview_string(preview_filename_));
        if(!call(b,ids_[83],50))return false;
        if(!stage){if(!preview_setting(b,"CaptureSource",6))return false;clear();if(!call(b,preview_capture_,41))return false;}
        return true;
    }
    template<class Pool> bool thumbnail_import(uint64_t b,uint64_t session,Pool& pool,const uint8_t* raw,CallIdentity& result) {
        if(cached_images_.size()>=128||!thumbnail_path(raw,L".png"))return false;
        preview_filename_=preview_directory_+L"/"+preview_filename_;
        clear();put(0,ids_[0].address);put(8,preview_string(preview_filename_));if(!call(b,ids_[83],51))return false;
        auto texture=call_capture(b,get<uint64_t>(24));if(!texture.address)return false;
        uint64_t lease=0;TargetStrongReferenceOps ops{b,texture};if(pool.acquire(ops,session,texture.address,lease)!=StrongLeaseResult::Ok)return false;
        cached_images_.push_back({texture,lease});
        if(!texture.serial){if(ops.allocate_serial(texture.index)<=0)return false;texture=call_capture(b,texture.address);cached_images_.back().first=texture;}
        result=texture;return true;
    }
    template<class Pool> bool thumbnail_clear(uint64_t b,uint64_t session,Pool& pool) {
        TargetStrongReferenceOps ops{b,{-1,0,0}};
        while(!cached_images_.empty()){if(pool.release(ops,session,cached_images_.back().second)!=StrongLeaseResult::Ok)return false;cached_images_.pop_back();}
        return true;
    }
