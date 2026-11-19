#define main prior_schema_fixture_main
#include "pod_schema_fixture.cpp"
#undef main

struct TransformFixture:Fixture {
    uint64_t quat=0,vector3=0,transform=0;
    TransformFixture() {
        memory.stop_after=1000;
        quat=make("Quat",core,32,{"X","Y","Z","W"},"DoubleProperty",0x6e11788,8,6755469251052037ULL);
        vector3=make("Vector",core,24,{"X","Y","Z"},"DoubleProperty",0x6e11788,8,6755469251052037ULL);
        transform=memory.object("Transform",script_struct,core);
        memory.words[transform+0x40]=0;memory.words[transform+0x58]=96;
        auto a=memory.field(transform,"Rotation","StructProperty",0x6e136a0,0,32,6755469251051525ULL);
        auto b=memory.field(transform,"Translation","StructProperty",0x6e136a0,32,24,6755469251052037ULL);
        auto c=memory.field(transform,"Scale3D","StructProperty",0x6e136a0,64,24,6755469251052037ULL);
        memory.words[transform+0x50]=a;memory.words[a+0x18]=b;memory.words[b+0x18]=c;
        memory.words[a+0x70]=quat;memory.words[b+0x70]=vector3;memory.words[c+0x70]=vector3;
    }
};
int main() {
    CallPacket returned{};returned.version=2;returned.parameter_size=returned.allocation_extent=96;
    returned.target={1,1,0x10000};returned.function={2,1,0x20000};
    returned.return_offset=0;returned.field_count=1;
    returned.fields[0]={CallTransform,0,96,1,0x480,0,"ReturnValue",{1,1,0x10000}};
    if(validate_call_packet(returned,true))return 4;
    returned.fields[0].flags=0x80;returned.return_offset=65535;
    if(validate_call_packet(returned,true)!=315)return 5;
    double unit=1.;std::memcpy(returned.data+24,&unit,8);
    if(validate_call_packet(returned,true))return 6;
    TransformFixture f;
    if(!f.check(f.transform,PodValueKind::Transform))return 1;
    auto reject=[](auto mutate){TransformFixture t;mutate(t);if(t.check(t.transform,PodValueKind::Transform))throw std::runtime_error("accepted altered transform schema");};
    reject([](auto&t){t.memory.words[t.transform+0x58]=88;});
    reject([](auto&t){auto p=t.memory.words.at(t.transform+0x50);t.memory.words[p+0x70]=t.vector3;});
    reject([](auto&t){auto p=t.memory.words.at(t.transform+0x50);p=t.memory.words.at(p+0x18);t.memory.words[p+0x44]=40;});
    reject([](auto&t){auto p=t.memory.words.at(t.quat+0x50);t.memory.words[p+0x38]^=1;});
    double raw[12]={0,0,0,1,10,20,30,0,1,1,1,0};
    if(!valid_pod_value(PodValueKind::Transform,reinterpret_cast<uint8_t*>(raw),96))return 2;
    raw[3]=0;
    if(valid_pod_value(PodValueKind::Transform,reinterpret_cast<uint8_t*>(raw),96))return 3;
    std::puts("Transform hierarchy, schema rejection, and quaternion validation passed.");
}
