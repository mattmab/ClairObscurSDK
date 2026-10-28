#include "asset_name_number.h"
#include <cassert>
#include <cstdio>
int main() {
    struct Row{const char* input;const char* base;uint32_t number;};
    const Row rows[]={
        {"MCS_EvequeIntro_2","MCS_EvequeIntro",3},
        {"/Game/Folder/MCS_EvequeIntro_2","/Game/Folder/MCS_EvequeIntro",3},
        {"Name_0","Name",1},{"Name_01","Name_01",0},
        {"Name_V2","Name_V2",0},{"Name_","Name_",0},
        {"Name_2147483646","Name",0x7fffffff},
        {"Name_2147483647","Name_2147483647",0},
        {"Name_999999999999999999999999","Name_999999999999999999999999",0}};
    for(const auto& row:rows) {
        char base[128]{};uint32_t number=0;
        assert(asset_split_number(row.input,base,sizeof(base),number));
        assert(!std::strcmp(base,row.base)&&number==row.number);
        assert(asset_append_number(base,sizeof(base),number));
        assert(!std::strcmp(base,row.input));
    }
    char small[5]="Name";uint32_t number=0;
    assert(!asset_split_number("Name_2",small,sizeof(small),number));
    assert(!asset_append_number(small,sizeof(small),3));
    char invalid[32]="Name";assert(!asset_append_number(invalid,sizeof(invalid),0x80000000));
    std::puts("Numbered asset name roundtrip and bounds passed");
}
