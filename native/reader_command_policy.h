#pragma once
#include <cstdint>
#include <string>
#include <vector>

inline bool reader_arguments(const std::vector<std::string>& args,uint32_t pid) {
    if(args.size()==1 && args[0]=="--catalog")return true;
    if(args.size()!=3 || args[1]!=std::to_string(pid))return false;
    return args[0]=="--catalog-values" || args[0]=="--catalog-select" || args[0]=="--catalog-match" ||
        args[0]=="--describe" || args[0]=="--read-values" || args[0]=="--read-table" ||
        args[0]=="--describe-enums" || args[0]=="--resolve-asset-names" || args[0]=="--resolve-export-names";
}
