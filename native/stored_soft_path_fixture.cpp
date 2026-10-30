#include "stored_soft_path.h"
#include <functional>
#include <iostream>

struct Fixture {
    StoredSoftPathStorage raw{0xfeed,1,0,2,0,0x20000,0,0};
    std::vector<char16_t> text;
    unsigned reads=0;
    bool changed_text=false,changed_header=false;
    std::string package="/Game/Original/Sequence",asset="Sequence";
    size_t budget=262144;
    void subpath(const std::u16string& value) {
        text.assign(value.begin(),value.end());text.push_back(0);
        raw.count=raw.capacity=static_cast<int32_t>(text.size());
    }
    StoredSoftPathCopy copy(uint32_t width=40,uint64_t table=0x6e128d8,bool soft_class=false) {
        return copy_stored_soft_path(reinterpret_cast<const uint8_t*>(&raw),0x10000,width,table,
            [&](uint64_t at,void* target,size_t size) {
                ++reads;
                if(at==0x20000) {
                    if(size!=text.size()*2)throw std::runtime_error("BAD_FIXTURE_SIZE");
                    std::memcpy(target,text.data(),size);
                    if(changed_text && reads==2 && size)static_cast<char16_t*>(target)[0]^=1;
                } else if(at==0x10000 && size==40) {
                    std::memcpy(target,&raw,40);
                    if(changed_header)static_cast<StoredSoftPathStorage*>(target)->cache^=1;
                } else throw std::runtime_error("BAD_FIXTURE_READ");
            },[&](uint32_t id,uint32_t number) {
                if(number || (id!=1 && id!=2))throw std::runtime_error("BAD_FIXTURE_NAME");
                return id==1 ? package : asset;
            },budget,soft_class);
    }
};
bool rejects(const std::function<void()>& operation,const char* expected) {
    try {operation();}catch(const std::runtime_error& error){return error.what()==std::string(expected);}
    return false;
}
int main() {
    Fixture f;f.subpath(u"PersistentLevel.Actor\U0001f3ae");
    const auto value=f.copy();
    if(value.null_path || value.package!="/Game/Original/Sequence" || value.asset!="Sequence" ||
        value.subpath!="PersistentLevel.Actor\xf0\x9f\x8e\xae" || f.reads!=3)return 1;
    f=Fixture{};f.raw.package_id=f.raw.asset_id=0;
    if(!f.copy().null_path)return 2;
    f.subpath(u"");if(!f.copy().null_path)return 3;
    f.raw.asset_id=2;if(!rejects([&]{f.copy();},"SOFT_NULL_PATH_INVALID"))return 4;
    f=Fixture{};f.subpath(u"Child");f.raw.package_id=f.raw.asset_id=0;
    if(!rejects([&]{f.copy();},"SOFT_NULL_PATH_INVALID"))return 5;
    f=Fixture{};if(!rejects([&]{f.copy(32);},"SOFT_PROPERTY_LAYOUT_INVALID") || f.reads)return 6;
    if(!rejects([&]{f.copy(40,0x6e12cb8);},"SOFT_PROPERTY_LAYOUT_INVALID") || f.reads)return 7;
    if(!rejects([&]{f.copy(40,0x6e128d8,true);},"SOFT_PROPERTY_LAYOUT_INVALID") || f.reads)return 21;
    if(f.copy(40,0x6e12cb8,true).asset!="Sequence")return 22;
    f.raw.count=-1;if(!rejects([&]{f.copy();},"SOFT_SUBPATH_COUNTS_INVALID"))return 8;
    f=Fixture{};f.raw.count=1;if(!rejects([&]{f.copy();},"SOFT_SUBPATH_COUNTS_INVALID"))return 9;
    f=Fixture{};f.raw.capacity=1048577;if(!rejects([&]{f.copy();},"SOFT_SUBPATH_COUNTS_INVALID"))return 10;
    f=Fixture{};f.raw.count=f.raw.capacity=4098;if(!rejects([&]{f.copy();},"SOFT_SUBPATH_SIZE_LIMIT"))return 11;
    f=Fixture{};f.subpath(u"A");f.budget=1;if(!rejects([&]{f.copy();},"SOFT_SUBPATH_SIZE_LIMIT"))return 12;
    f=Fixture{};f.subpath(u"A");f.raw.data=1;if(!rejects([&]{f.copy();},"SOFT_SUBPATH_DATA_INVALID"))return 13;
    f=Fixture{};f.subpath(u"A");f.text.back()='X';if(!rejects([&]{f.copy();},"SOFT_SUBPATH_TERMINATOR_INVALID"))return 14;
    f=Fixture{};f.subpath(std::u16string{u'A',0,u'B'});if(!rejects([&]{f.copy();},"SOFT_SUBPATH_EMBEDDED_NULL"))return 15;
    for(const char16_t bad:{char16_t(0xd800),char16_t(0xdc00)}) {
        f=Fixture{};f.subpath(std::u16string{bad});if(!rejects([&]{f.copy();},"SOFT_SUBPATH_UTF16_INVALID"))return 16;
    }
    f=Fixture{};f.subpath(u"A");f.changed_text=true;if(!rejects([&]{f.copy();},"SOFT_SUBPATH_CONTENT_CHANGED"))return 17;
    f=Fixture{};f.changed_header=true;if(!rejects([&]{f.copy();},"SOFT_PATH_STORAGE_CHANGED"))return 18;
    f=Fixture{};f.package="/Game//Bad";if(!rejects([&]{f.copy();},"SOFT_PATH_NAMES_INVALID"))return 19;
    f=Fixture{};f.asset="Bad/Asset";if(!rejects([&]{f.copy();},"SOFT_PATH_NAMES_INVALID"))return 20;
    std::cout << "Stored soft path layout, copy stability, null policy, UTF16 and bounds PASS\n";
    return 0;
}
