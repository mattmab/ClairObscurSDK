#include "mesh_profile.h"
#include "engine_profiles.h"
#include <cassert>
#include <cstring>
namespace e33_mesh {}
namespace baseline {
#include "D:/HobbyDevelopment/ClairObscurSDK/native/mesh_profile.h"
#include "D:/HobbyDevelopment/ClairObscurSDK/native/builder_profile.h"
}
bool text_equal(const char* a,const char* b) {return a && b && !std::strcmp(a,b);}
template<class A,class B> bool field_equal(const A& a,const B& b) {
    return text_equal(a.name,b.name) && text_equal(a.type,b.type) && a.offset==b.offset &&
        a.width==b.width && a.flags==b.flags && a.table==b.table &&
        text_equal(a.structure,b.structure) && text_equal(a.inner,b.inner) &&
        a.inner_width==b.inner_width && text_equal(a.inner_structure,b.inner_structure) &&
        a.boolean==b.boolean && text_equal(a.constraint,b.constraint);
}
template<class A,class B> bool profile_equal(const A& a,const B& b) {
    if(!text_equal(a.owner,b.owner) || !text_equal(a.name,b.name) || a.flags!=b.flags ||
       a.params!=b.params || a.extent!=b.extent || a.returned!=b.returned ||
       a.entry!=b.entry || a.count!=b.count) return false;
    for(size_t i=0;i<a.count;++i) if(!field_equal(a.fields[i],b.fields[i])) return false;
    return true;
}
int main() {
    static_assert(sizeof(mesh_functions)/sizeof(mesh_functions[0]) ==
                  sizeof(baseline::mesh_functions)/sizeof(baseline::mesh_functions[0]));
    for(size_t i=0;i<sizeof(mesh_functions)/sizeof(mesh_functions[0]);++i)
        assert(profile_equal(mesh_functions[i],baseline::mesh_functions[i]));
    for(size_t i=0;i<67;++i) {
        assert(profile_equal(e33_engine_profiles::profiles[i],baseline::e33_builder::profiles[i]));
        assert(text_equal(e33_engine_profiles::packages[i],baseline::e33_builder::packages[i]));
    }
    auto changed=e33_engine_profiles::profiles[5]; changed.entry++;
    assert(!profile_equal(changed,baseline::e33_builder::profiles[5]));
    changed=e33_engine_profiles::profiles[5]; changed.params++;
    assert(!profile_equal(changed,baseline::e33_builder::profiles[5]));
    auto field=changed.fields[0]; field.offset++;
    assert(!field_equal(field,baseline::e33_builder::profiles[5].fields[0]));
}
