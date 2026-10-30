#include "authored_occurrence_class_policy.h"
#include <cassert>
#include <cstring>
struct ClassOps {
    bool forged=false,bad_size=false,bad_super=false,bad_package=false;
    bool class_valid(uint64_t t)const{return t>=1 && t<=4;}
    bool named(uint64_t t,const char* name,const char* package)const {
        const char* names[]={"","LevelSequence","CameraAnimationSequence","TemplateSequence","MovieSceneSequence"};
        const char* packages[]={"","/Script/LevelSequence","/Script/TemplateSequence","/Script/TemplateSequence","/Script/MovieScene"};
        return class_valid(t) && !forged && !std::strcmp(names[t],name) &&
               !std::strcmp(packages[t],package) && !(bad_package && t==3);
    }
    uint64_t super(uint64_t t)const{return bad_super ? 1 : t==2 ? 3 : t==3 ? 4 : 0;}
    uint32_t size(uint64_t t)const{return bad_size ? 999 : t==2||t==3 ? 232 : t==4 ? 104 : 0;}
};
int main() {
    ClassOps ops;uint64_t owner=0;uint32_t offset=0;
    assert(e33_authored_occurrence::movie_scene_layout(ops,1,owner,offset) && owner==1 && offset==112);
    assert(e33_authored_occurrence::movie_scene_layout(ops,2,owner,offset) && owner==3 && offset==104);
    assert(e33_authored_occurrence::movie_scene_layout(ops,3,owner,offset) && owner==3 && offset==104);
    ops.bad_size=true;assert(!e33_authored_occurrence::movie_scene_layout(ops,2,owner,offset));ops.bad_size=false;
    ops.bad_super=true;assert(!e33_authored_occurrence::movie_scene_layout(ops,2,owner,offset));ops.bad_super=false;
    ops.bad_package=true;assert(!e33_authored_occurrence::movie_scene_layout(ops,2,owner,offset));ops.bad_package=false;
    ops.forged=true;assert(!e33_authored_occurrence::movie_scene_layout(ops,2,owner,offset));
    assert(!e33_authored_occurrence::movie_scene_layout(ops,0,owner,offset));
    ops.forged=false;assert(!e33_authored_occurrence::movie_scene_layout(ops,4,owner,offset));
}
