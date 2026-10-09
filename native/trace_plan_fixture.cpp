#include "trace_plan.h"
#include <cassert>
#include <cstdio>

int main() {
    using namespace e33_trace;
    CallPacket schema{};
    schema.version = 1; schema.target = {1, 0, 0x123}; schema.function = {2, 0, 0x456};
    schema.parameter_size = schema.allocation_extent = 13;
    schema.function_flags = 0x400; schema.entry_rva = 0x1234; schema.return_offset = 12;
    schema.field_count = 3;
    auto set = [&](uint32_t i, const char* name, uint32_t kind, uint32_t offset,
                   uint32_t width, uint32_t dimension, uint64_t flags) {
        auto& f = schema.fields[i];
        strcpy_s(f.name, name); f.kind = kind; f.offset = offset;
        f.width = width; f.dimension = dimension; f.flags = flags;
    };
    set(0, "Input", CallInt32, 0, 4, 1, 0x80);
    set(1, "Outputs", CallInt32, 4, 4, 2, 0x180);
    set(2, "ReturnValue", CallBool, 12, 1, 1, 0x480);
    schema.fields[2].bool_encoding = 0xff010001;
    uint64_t properties[] = {0xa, 0xb, 0xc};
    CapturePlan plan{};
    assert(make_capture_plan(schema, properties, 3, plan));
    assert(plan.count == 4 && plan.extent == 13);
    assert(plan.fields[0].source == StorageKind::locals && plan.fields[0].source_extent == 13);
    assert(plan.fields[1].source == StorageKind::out && plan.fields[1].property == 0xb);
    assert(plan.fields[1].source_extent == 8 && plan.fields[2].source_offset == 4);
    assert(plan.fields[3].source == StorageKind::result && plan.fields[3].source_offset == 0);
    auto reject = [&] {
        assert(!make_capture_plan(schema, properties, 3, plan));
        assert(plan.count == 0 && plan.extent == 0);
    };
    properties[2] = properties[1]; reject(); properties[2] = 0xc;
    schema.data[0] = 1; reject(); schema.data[0] = 0;
    schema.entry_rva = 0; reject(); schema.entry_rva = 0x1234;
    schema.function_flags = 0; reject(); schema.function_flags = 0x400;
    schema.fields[0].kind = CallObject; reject(); schema.fields[0].kind = CallInt32;
    assert(!make_capture_plan(schema, properties, 2, plan));
    schema.field_count = 2; schema.return_offset = 65535;
    schema.parameter_size = schema.allocation_extent = 1;
    set(0, "A", CallBool, 0, 1, 1, 0x80); schema.fields[0].bool_encoding = 0x01010001;
    set(1, "B", CallBool, 0, 1, 1, 0x80); schema.fields[1].bool_encoding = 0x02020001;
    assert(make_capture_plan(schema, properties, 2, plan));
    assert(plan.extent == 2 && plan.fields[0].source_offset == 0 && plan.fields[1].source_offset == 0);
    assert(plan.fields[1].destination_offset == 1);
    schema.field_count = 1; schema.parameter_size = schema.allocation_extent = 8;
    set(0, "Object", CallObject, 0, 8, 1, 0x80);
    schema.fields[0].bool_encoding = 0; schema.fields[0].constraint = {3, 0, 0x789};
    assert(validate_call_packet(schema) == 0);
    assert(!make_capture_plan(schema, properties, 1, plan));
    schema.field_count = 3; schema.parameter_size = schema.allocation_extent = 768;
    for (uint32_t i = 0; i < 3; ++i) {
        schema.fields[i] = {};
        set(i, i == 0 ? "A" : i == 1 ? "B" : "C", CallInt32, i * 256, 4, 64, 0x80);
    }
    assert(validate_call_packet(schema) == 0);
    reject(); // 192 flattened fields exceed the native observation bound.
    std::puts("Native trace planning: scalar routes, arrays, packed bools and schema-only rejection passed.");
}
