    // Target-build AssetRegistry interface and AssetData cleanup, audited from
    // GetAssetRegistry (2027f30/203f080) and GetAssetsByClass (2028190).
    struct RegistryArray {uint64_t data=0;int32_t count=0,capacity=0;};
    RegistryArray registry_pending_;
    bool registry_started_=false,registry_complete_=false;
    std::vector<std::string> registry_paths_;
    std::unordered_map<std::string,std::pair<uint64_t,uint64_t>> registry_names_;
    bool registry_name(uint64_t b,uint64_t name,std::string& result) {
        const auto id=uint32_t(name),block=id>>16,offset=(id&65535)*2;
        const auto pool=b+0x92aadc0;const auto current=local_read<uint32_t>(pool+8),cursor=local_read<uint32_t>(pool+12);
        if(current>=8192||block>current||cursor>0x20000)return false;
        const auto limit=block==current?cursor:0x20000U;
        const auto data=local_read<uint64_t>(pool+16+uint64_t(block)*8);
        if(!data||offset+2>limit)return false;
        const auto h=local_read<uint16_t>(data+offset);const auto length=uint32_t(h>>6);
        if((h&1)||!length||length>500||offset+2+length>limit)return false;
        result.assign(reinterpret_cast<const char*>(data+offset+2),length);
        for(char ch:result)if(!((ch>='A'&&ch<='Z')||(ch>='a'&&ch<='z')||(ch>='0'&&ch<='9')||ch=='_'||ch=='/'||ch=='-'))return false;
        if(name>>32)result+="_"+std::to_string(uint32_t(name>>32)-1);
        return true;
    }
    void registry_release(uint64_t b) {
        // Exact destruction sequence from the generated GetAssetsByClass thunk:
        // chunk-ID allocation, shared bundle data, tag-map value, then TArray.
        for(int32_t i=0;i<registry_pending_.count;++i) {
            const auto p=registry_pending_.data+uint64_t(i)*104;
            const auto chunks=local_read<uint64_t>(p+88);
            if(chunks)reinterpret_cast<void(__fastcall*)(uint64_t)>(b+0x107c7d0)(chunks);
            const auto shared=local_read<uint64_t>(p+72);
            if(shared&&InterlockedDecrement(reinterpret_cast<LONG*>(shared+8))==0) {
                const auto table=local_read<uint64_t>(shared);
                reinterpret_cast<void(__fastcall*)(uint64_t)>(local_read<uint64_t>(table))(shared);
                if(InterlockedDecrement(reinterpret_cast<LONG*>(shared+12))==0)
                    reinterpret_cast<void(__fastcall*)(uint64_t,uint32_t)>(local_read<uint64_t>(table+8))(shared,1);
            }
            reinterpret_cast<void(__fastcall*)(uint64_t)>(b+0x12176c0)(p+56);
        }
        if(registry_pending_.data)reinterpret_cast<void(__fastcall*)(uint64_t)>(b+0x107c7d0)(registry_pending_.data);
        registry_pending_={};
    }
    bool registry_page(uint64_t b,uint8_t* raw) {
        if(!registry_complete_) {
            if(registry_started_)return false; // Never replay an ambiguous query.
            const auto registry=local_read<uint64_t>(b+0x9326c90);
            if(!registry||local_read<uint64_t>(registry)!=b+0x70718d0||local_read<uint64_t>(b+0x70718d0+48)!=b+0x2001d90)return false;
            const auto mesh=call_identity(b,ids_[85]);
            if(!mesh||!named(b,mesh,"StaticMesh","/Script/Engine"))return false;
            const uint64_t classPath[]={local_read<uint64_t>(local_read<uint64_t>(mesh+32)+24),local_read<uint64_t>(mesh+24)};
            registry_started_=true;
            const bool ok=reinterpret_cast<bool(__fastcall*)(uint64_t,const uint64_t*,RegistryArray*,bool)>(b+0x2001d90)(registry,classPath,&registry_pending_,false);
            if(registry_pending_.count<0||registry_pending_.count>250000||registry_pending_.capacity<registry_pending_.count||registry_pending_.capacity>500000||(!registry_pending_.data&&registry_pending_.count))return false;
            if(ok)for(int32_t i=0;i<registry_pending_.count;++i) {
                const auto row=registry_pending_.data+uint64_t(i)*104;
                if(local_read<uint64_t>(row+32)!=classPath[0]||local_read<uint64_t>(row+40)!=classPath[1])continue;
                std::string package,asset;
                if(registry_name(b,local_read<uint64_t>(row),package)&&registry_name(b,local_read<uint64_t>(row+16),asset)&&package.rfind("/Game/",0)==0&&package.size()+asset.size()+2<=512)
                {
                    registry_paths_.push_back(package+"."+asset);
                    registry_names_[package+"."+asset]={local_read<uint64_t>(row),local_read<uint64_t>(row+16)};
                }
            }
            registry_release(b);
            if(!ok)return false;
            std::sort(registry_paths_.begin(),registry_paths_.end());
            registry_paths_.erase(std::unique(registry_paths_.begin(),registry_paths_.end()),registry_paths_.end());
            registry_complete_=true;
        }
        uint32_t offset=0;std::memcpy(&offset,raw+2000,4);
        const auto total=uint32_t(registry_paths_.size());if(offset>total)return false;
        const auto count=std::min(32U,total-offset);
        std::memcpy(raw+3560,&total,4);std::memcpy(raw+3564,&count,4);
        for(uint32_t i=0;i<count;++i)std::memcpy(raw+4096+i*512,registry_paths_[offset+i].c_str(),registry_paths_[offset+i].size()+1);
        return true;
    }
