#include "observer_fixture_protocol.h"
#include <atomic>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <thread>

alignas(8) static void* volatile entry = nullptr;
static std::atomic<uint64_t> calls{0};
static ObserverEntry current() {
    return reinterpret_cast<ObserverEntry>(InterlockedCompareExchangePointer(&entry, nullptr, nullptr));
}
static void __fastcall target(void* object, void* frame, void* result) {
    ++calls;
    if (frame) { uint8_t nested = 0; current()(object, nullptr, &nested); }
    *static_cast<uint8_t*>(result) = 42;
}
static void __fastcall other(void*, void*, void* result) { *static_cast<uint8_t*>(result) = 7; }
static void require(bool condition, const char* text) { if (!condition) throw std::runtime_error(text); }
int main() {
    try {
        wchar_t executable[32768];
        require(GetModuleFileNameW(nullptr, executable, 32768) != 0, "SELF_PATH");
        auto path = std::filesystem::path(executable).parent_path() / L"observer_fixture.dll";
        HMODULE module = LoadLibraryW(path.c_str()); require(module != nullptr, "LOAD");
        auto install = reinterpret_cast<InstallObserver>(GetProcAddress(module, "InstallFixtureObserver"));
        auto remove = reinterpret_cast<RemoveObserver>(GetProcAddress(module, "RemoveFixtureObserver"));
        require(install && remove, "EXPORTS");
        InterlockedExchangePointer(&entry, reinterpret_cast<void*>(&target));
        ObserverBuffer events{}; int identity = 0; uint8_t result = 0;
        require(install(&entry, &target, &events), "INSTALL");
        require(!install(&entry, &target, &events), "DUPLICATE_NOT_REJECTED");
        auto prefetched = current();
        prefetched(&identity, nullptr, &result);
        prefetched(&identity, &identity, &result);
        require(events.count == 2 && calls == 3 && result == 42, "PASS_THROUGH_OR_REENTRANCY");
        require(events.records[0].object == reinterpret_cast<uint64_t>(&identity) &&
                events.records[0].thread == GetCurrentThreadId() && events.records[0].result == 42, "CONTEXT");
        require(remove() && remove() && current() == &target, "RESTORATION");
        require(FreeLibrary(module), "RELEASE_LOCAL_REFERENCE");
        require(GetModuleHandleW(L"observer_fixture.dll") != nullptr, "RESIDENT_CODE_LOST");
        prefetched(&identity, nullptr, &result);
        require(events.count == 2 && result == 42, "LATE_ENTRY_AFTER_REMOVAL");
        // Repeated publication/removal racing with a thread using a previously
        // fetched pointer. Removal must detach stack-owned storage before return.
        std::atomic<bool> stop{false}, started{false};
        std::thread worker([&] {
            uint8_t value = 0; started = true;
            while (!stop.load()) prefetched(&identity, nullptr, &value);
        });
        while (!started.load()) std::this_thread::yield();
        bool cycles_ok = true;
        for (int iteration = 0; iteration < 1000; ++iteration) {
            ObserverBuffer cycle{};
            if (!install(&entry, &target, &cycle)) { cycles_ok = false; break; }
            current()(&identity, nullptr, &result);
            if (!remove()) { cycles_ok = false; break; }
            uint32_t count = cycle.count, dropped = cycle.dropped;
            prefetched(&identity, nullptr, &result);
            if (cycle.count != count || cycle.dropped != dropped || count == 0) { cycles_ok = false; break; }
        }
        stop = true; worker.join(); require(cycles_ok, "CONCURRENT_CYCLES");
        events = {};
        require(install(&entry, &target, &events), "OVERFLOW_INSTALL");
        for (int i = 0; i < 70; ++i) current()(&identity, nullptr, &result);
        require(remove() && events.count == 64 && events.dropped == 6, "BOUNDED_EVENTS");
        require(install(&entry, &target, &events), "CONFLICT_INSTALL");
        InterlockedExchangePointer(&entry, reinterpret_cast<void*>(&other));
        require(!remove() && current() == &other, "CONFLICT_OVERWRITTEN");
        prefetched(&identity, nullptr, &result);
        require(events.count == 64 && events.dropped == 6, "CONFLICT_STORAGE_NOT_DETACHED");
        std::cout << "{\"fixture_only\":true,\"pass_through\":true,\"context\":true,"
                     "\"nested_notification_suppressed\":true,\"cycles\":1000,\"late_entry_safe\":true,"
                     "\"bounded_events\":true,\"conflict_preserved\":true,\"module_resident\":true}\n";
        return 0;
    } catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}
