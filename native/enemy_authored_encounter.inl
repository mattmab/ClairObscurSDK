    // Evidence-gated authored-instance recipes. Route 1 is traced to World Map
    // export 4144; this is not inferred from an enemy's display name.
    struct AuthoredRoute {
        uint32_t id;const char* class_name;const char* package;const char* cdo_name;
        const char* original_row;const char* target_row;uint32_t target_number=0;
    };
    const AuthoredRoute* authored_route(uint32_t route){
        static constexpr AuthoredRoute routes[]={
            {1,"BP_EnemyWorld_Sprong_C","/Game/Characters/Enemies/SpringMeadows/Sprong/BP_EnemyWorld_Sprong",
             "Default__BP_EnemyWorld_Sprong_C","YellowForest_Gault*1","WM_Sprong"},
            {2,"BP_jRPG_EnemyWorld_Sapling_C","/Game/Characters/Enemies/YellowForest/Sapling/BP_jRPG_EnemyWorld_Sapling",
             "Default__BP_jRPG_EnemyWorld_Sapling_C","YellowForest_Sapling*1","YF_Sapling*1"},
            {3,"BP_EnemyWorld_AS_DpsPotatobag_C","/Game/Characters/Enemies/AncientSanctuary/PotatoBagRanger/BP_EnemyWorld_AS_DpsPotatobag",
             "Default__BP_EnemyWorld_AS_DpsPotatobag_C","PotatoBag_Dps*1","AS_PotatoBagRanger*1"},
            {4,"BP_jRPG_EnemyWorld_GaultB_C","/Game/Characters/Enemies/YellowForest/Gault/BP_jRPG_EnemyWorld_GaultB",
             "Default__BP_jRPG_EnemyWorld_GaultB_C","YellowForest_GaultB*1","YF_GaultB*1"},
            {5,"BP_EnemyWorld_Lancelier_Unique_C","/Game/Characters/Enemies/SpringMeadows/Lancelier/BP_EnemyWorld_Lancelier_Unique",
             "Default__BP_EnemyWorld_Lancelier_Unique_C","SpringMeadow_UniqueLancelier*1","SM_Lancelier_Alpha"},
            {6,"BP_jRPG_EnemyWorld_Sapling_Alternative_CrushingWall_C","/Game/Characters/Enemies/YellowForest/Sapling/BP_jRPG_EnemyWorld_Sapling_Alternative_CrushingWall",
             "Default__BP_jRPG_EnemyWorld_Sapling_Alternative_CrushingWall_C","SL_Sapling_CrushingWalls","SL_Sapling_CrushingWalls",1},
            {7,"BP_EnemyWorld_UniqueLusterAlpha_C","/Game/Characters/Enemies/Goblu_Ennemies/Luster/BP_EnemyWorld_UniqueLusterAlpha",
             "Default__BP_EnemyWorld_UniqueLusterAlpha_C","Luster*1","GO_LusterAlpha"},
            {8,"BP_EnemyWorld_Goblu_C","/Game/Characters/Enemies/Goblu_Ennemies/Goblu/BP_EnemyWorld_Goblu",
             "Default__BP_EnemyWorld_Goblu_C","Goblu","GO_Goblu"},
            {9,"BP_EnemyWorld_BossEveque_C","/Game/Characters/Enemies/SpringMeadows/Eveque_Boss/BP_EnemyWorld_BossEveque",
             "Default__BP_EnemyWorld_BossEveque_C","SpringMeadow_Eveque*1","SM_Eveque*1"},
            {10,"BP_EnemyWorld_BossEveque_Monolith_C","/Game/Characters/Enemies/SpringMeadows/Eveque_Boss/BP_EnemyWorld_BossEveque_Monolith",
             "Default__BP_EnemyWorld_BossEveque_Monolith_C","SpringMeadow_Eveque*1","ML_Eveque*1"},
            {11,"BP_EnemyWorld_LampMaster_C","/Game/Characters/Enemies/Sea_Cliff/Lampmaster/BP_EnemyWorld_LampMaster",
             "Default__BP_EnemyWorld_LampMaster_C","YellowForest_Gault*1","SC_LampMaster"},
            {12,"BP_EnemyWorld_Franctale_Alpha_C","/Game/Characters/Enemies/Verso_Draft/Franctale/BP_EnemyWorld_Franctale_Alpha",
             "Default__BP_EnemyWorld_Franctale_Alpha_C","VD_FranctaleAlpha*3","VD_FranctaleAlpha*1"}
        };
        for(const auto& candidate:routes)if(candidate.id==route)return &candidate;
        return nullptr;
    }
    struct EncounterFields { uint64_t array=0,data=0,selected=0; };
    bool encounter_fields(uint64_t b,uint64_t actor,EncounterFields& out){
        uint64_t descriptor=0,selected_descriptor=0;
        const auto array=picto_field(b,actor,"PossibleEncounters","ArrayProperty",1984,16,&descriptor);
        const auto selected=picto_field(b,actor,"SelectedEncounter","StructProperty",2000,16,&selected_descriptor);
        if(!array||!selected||!descriptor||!selected_descriptor||
           local_read<uint64_t>(descriptor)!=b+0x6e0de80||local_read<uint64_t>(descriptor+0x38)!=0x1000000000005ULL||
           local_read<uint64_t>(selected_descriptor)!=b+0x6e136a0||
           local_read<uint64_t>(selected_descriptor+0x38)!=0x1000010005ULL)return false;
        const auto inner=local_read<uint64_t>(descriptor+0x78);
        if(!inner||local_read<uint64_t>(inner)!=b+0x6e136a0||local_read<uint64_t>(inner+0x10)!=descriptor||
           local_read<uint32_t>(inner+0x30)!=1||local_read<uint32_t>(inner+0x34)!=16||
           !named(b,local_read<uint64_t>(inner+0x70),"DataTableRowHandle","/Script/Engine")||
           local_read<uint64_t>(inner+0x70)!=local_read<uint64_t>(selected_descriptor+0x70))return false;
        const auto data=local_read<uint64_t>(array);
        const auto count=local_read<int32_t>(array+8),capacity=local_read<int32_t>(array+12);
        if(count!=1||capacity<count||capacity>4096||data<0x10000||(data&7))return false;
        out={array,data,selected};return true;
    }
    struct EncounterOps {
        Owner& owner;uint64_t base;CallIdentity table,cdo;EncounterFields target{};const AuthoredRoute* route=nullptr;uint32_t* failure=nullptr;
        bool preflight(EncounterHandle expected){
            EncounterFields defaults{};
            if(failure)*failure=3025;
            if(!route||!call_identity(base,table)||!call_identity(base,cdo)||
               local_read<uint64_t>(cdo.address+16)!=owner.ids_[4].address||
               !(local_read<uint32_t>(cdo.address+8)&0x10)||
               !exact_name(base,cdo.address+24,route->cdo_name))return false;
            if(failure)*failure=3026;
            if(!owner.encounter_fields(base,owner.actor_.address,target)||!owner.encounter_fields(base,cdo.address,defaults))return false;
            if(failure)*failure=3027;
            if(target.data==defaults.data||local_read<uint64_t>(target.data)!=expected.table||
               local_read<uint64_t>(defaults.data)!=expected.table||
               !exact_name(base,target.data+8,route->original_row)||!exact_name(base,defaults.data+8,route->original_row))return false;
            if(failure)*failure=3028;
            if(local_read<uint64_t>(target.selected)||!exact_name(base,target.selected+8,"None"))return false;
            return true;
        }
        void write_name(uint64_t name){std::memcpy(reinterpret_cast<void*>(target.data+8),&name,8);}
        bool verify_possible(EncounterHandle expected){
            EncounterFields fields{};
            return call_identity(base,table)&&owner.encounter_fields(base,owner.actor_.address,fields)&&
                local_read<uint64_t>(fields.data)==expected.table&&local_read<uint64_t>(fields.data+8)==expected.name;
        }
        bool verify_selected(EncounterHandle expected){
            EncounterFields fields{};
            return call_identity(base,table)&&owner.encounter_fields(base,owner.actor_.address,fields)&&
                local_read<uint64_t>(fields.selected)==expected.table&&local_read<uint64_t>(fields.selected+8)==expected.name;
        }
    };
    bool verify_authored_encounter(uint64_t b){
        if(!encounter_override_.pending())return true;
        EncounterOps ops{*this,b,encounter_table_,{}, {}};
        return encounter_override_.verify_initialized(ops);
    }
    struct EncounterRows {
        uint64_t base;const char* target_row;uint32_t target_number=0;
        template<class T> T read(uint64_t address){return local_read<T>(address);}
        bool matches_name(uint64_t address){return exact_field_name(base,address,target_row,target_number);}
    };
    bool apply_authored_encounter(uint64_t b,CallIdentity table,CallIdentity cdo,uint32_t route,uint32_t& failure){
        failure=3020;
        const auto spec=authored_route(route);
        if(!spec||!named(b,ids_[4].address,spec->class_name,spec->package)||
           !call_identity(b,table)||!named(b,table.address,"DT_jRPG_Encounters","/Game/jRPGTemplate/Datatables/DT_jRPG_Encounters")||
           !named(b,local_read<uint64_t>(table.address+16),"DataTable","/Script/Engine"))return false;
        failure=3021;
        const auto accessor=local_read<uint64_t>(local_read<uint64_t>(table.address)+0x2d8);
        static const uint8_t code[]={0x48,0x8d,0x41,0x30,0xc3};
        for(unsigned i=0;i<sizeof(code);++i)if(local_read<uint8_t>(accessor+i)!=code[i])return false;
        failure=3022;
        const auto row_struct=local_read<uint64_t>(table.address+40);
        if(!call_identity(b,call_capture(b,row_struct))||
           (!named(b,local_read<uint64_t>(row_struct+16),"ScriptStruct","/Script/CoreUObject")&&
            !named(b,local_read<uint64_t>(row_struct+16),"UserDefinedStruct","/Script/Engine"))||
           local_read<int32_t>(row_struct+0x58)<=0||local_read<int32_t>(row_struct+0x58)>4096)return false;
        failure=3023;
        EncounterRows rows{b,spec->target_row,spec->target_number};
        uint64_t key=0;if(!find_unique_encounter_key(rows,table.address+48,key))return false;
        failure=3024;
        EncounterOps ops{*this,b,table,cdo,{},spec,&failure};
        encounter_table_=table;
        return encounter_override_.apply(ops,{table.address,key});
    }
