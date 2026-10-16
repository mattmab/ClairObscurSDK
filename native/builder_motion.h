    bool discard_unloaded_selection(uint64_t b) {
        if(!selected_.address || (call_identity(b,selected_) && call_identity(b,selected_actor_)))return false;
        // Streaming can retire a held level actor. Do not stop the camera or
        // restore scene edits; require a fresh click before grabbing again.
        selected_={};selected_actor_={};hover_={};hover_actor_={};
        dragging_=false;carrying_=false;nudging_=false;want_grab_=false;
        duplicate_requested_=false;left_was_=true;gpu_end_click();return true;
    }
    bool move(uint64_t b,const double* v) {
                const double rad=3.141592653589793/180.,cp=std::cos(rotation_[0]*rad),sp=std::sin(rotation_[0]*rad),cy=std::cos(rotation_[1]*rad),sy=std::sin(rotation_[1]*rad);
                const double dir[]={cp*cy,cp*sy,sp};
                position_[0]+=v[0]*dir[0]-v[1]*sy;position_[1]+=v[0]*dir[1]+v[1]*cy;position_[2]+=v[0]*dir[2]+v[2];
                if(!camera_pose(b)){return false;}
                discard_unloaded_selection(b);
                if(selected_.address&&(v[3]||v[4]||v[5]||v[6]||v[7])) {
                    clear();if(!call(b,selected_,19))return discard_unloaded_selection(b);
                    uint8_t pose[96];std::memcpy(pose,args_,96);double loc[3];std::memcpy(loc,pose+32,24);
                    if(v[3])for(int j=0;j<3;++j)loc[j]=position_[j]+dir[j]*depth_+offset_[j];
                    const double delta[]={v[4]*cy-v[5]*sy,v[4]*sy+v[5]*cy,v[6]};
                    for(int j=0;j<3;++j){loc[j]+=delta[j];offset_[j]+=delta[j];}std::memcpy(pose+32,loc,24);
                    if(v[7]) {double q[4];std::memcpy(q,pose,32);const auto s=std::sin(v[7]*rad/2),c=std::cos(v[7]*rad/2);const double rotated[]={c*q[0]-s*q[1],c*q[1]+s*q[0],c*q[2]+s*q[3],c*q[3]-s*q[2]};std::memcpy(pose,rotated,32);}
                    if(!component_pose(b,selected_,pose))return discard_unloaded_selection(b);
                    refresh_candidate(b,selected_);
                }
        return true;
    }
