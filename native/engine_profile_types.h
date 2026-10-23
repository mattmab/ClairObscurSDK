#pragma once
#include <cstddef>
#include <cstdint>
struct MeshField {const char* name;const char* type;int offset,width;uint64_t flags,table;const char* structure;const char* inner;int inner_width;const char* inner_structure;uint32_t boolean;const char* constraint;};
struct MeshFunction {const char* owner;const char* name;uint32_t flags,params,extent,returned;uint64_t entry;const MeshField* fields;size_t count;};
