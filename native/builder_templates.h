    // Read-only region export. Identity-checked components, bounded batches,
    // exact world-space instance transforms. Never enrolls scenery in edits_.
    bool template_scan(uint64_t b,uint8_t* raw) {
        uint32_t requested=0,instance=0;double low[3],high[3];
        std::memcpy(&requested,raw+2000,4);std::memcpy(&instance,raw+2004,4);
        std::memcpy(low,raw+2016,24);std::memcpy(high,raw+2040,24);
        if(!requested||requested>64||instance>1000000)return false;
        for(int j=0;j<3;++j)if(!std::isfinite(low[j])||!std::isfinite(high[j])||low[j]>high[j])return false;
        CallIdentity objects[64]{};std::memcpy(objects,raw+4096,requested*16);
        uint32_t consumed=0,count=0,skipped=0;
        LARGE_INTEGER start{},now{},freq{};QueryPerformanceCounter(&start);QueryPerformanceFrequency(&freq);
        for(;consumed<requested&&count<64;) {
            auto component=objects[consumed];bool keep=false;
            if(call_identity(b,component)&&!(local_read<uint32_t>(component.address+8)&0x30)&&
               call_derives(b,local_read<uint64_t>(component.address+16),ids_[63].address)) {
                clear();if(call(b,component,18)) {
                    const auto actor=call_capture(b,get<uint64_t>());
                    keep=ordinary(b,actor,component);
                }
            }
            if(!keep){++consumed;instance=0;++skipped;continue;}
            clear();put(0,component.address);if(!call(b,ids_[5],64))return false;
            bool overlap=true;
            for(int j=0;j<3;++j){const auto c=get<double>(8+8*j),e=get<double>(32+8*j);if(c+e<low[j]||c-e>high[j])overlap=false;}
            if(!overlap){++consumed;instance=0;continue;}
            const auto fn=call_identity(b,ids_[105]); // GetInstanceCount profile 65.
            if(!fn)return false;
            const bool instanced=call_derives(b,local_read<uint64_t>(component.address+16),local_read<uint64_t>(fn+32));
            int32_t total=1;
            if(instanced){clear();if(!call(b,component,65))return false;total=get<int32_t>();if(total<0||total>1000000)return false;}
            if(instance>=uint32_t(total)){++consumed;instance=0;continue;}
            double pose[12]{};
            if(instanced){clear();put(0,int32_t(instance));args_[112]=1;if(!call(b,component,66)||!args_[113])return false;std::memcpy(pose,args_+16,96);}
            else {clear();if(!call(b,component,19))return false;std::memcpy(pose,args_,96);}
            bool inside=true;for(int j=0;j<3;++j)if(!std::isfinite(pose[4+j])||pose[4+j]<low[j]||pose[4+j]>high[j])inside=false;
            if(inside){auto* row=raw+4096+128*count++;std::memcpy(row,&component,16);std::memcpy(row+16,pose,96);}
            if(++instance>=uint32_t(total)){++consumed;instance=0;}
            QueryPerformanceCounter(&now);if(double(now.QuadPart-start.QuadPart)/double(freq.QuadPart)>.001)break;
        }
        std::memcpy(raw+3560,&count,4);std::memcpy(raw+3564,&consumed,4);std::memcpy(raw+3568,&instance,4);std::memcpy(raw+3572,&skipped,4);
        return true;
    }
