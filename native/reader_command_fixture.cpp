#include "reader_command_policy.h"
#include <cassert>
int main() {
    assert(reader_arguments({"--catalog"},17));
    for(const auto name:{"--resolve-asset-names","--resolve-export-names","--catalog-values","--describe"}) {
        assert(reader_arguments({name,"17","/Game/Test.Test"},17));
        assert(!reader_arguments({name,"18","/Game/Test.Test"},17));
        assert(!reader_arguments({name,"17","x","extra"},17));
    }
    for(const auto name:{"--session","--thread-ping","--invoke-proof","--observe-proof","--unknown"})
        assert(!reader_arguments({name,"17","x"},17));
    return 0;
}
