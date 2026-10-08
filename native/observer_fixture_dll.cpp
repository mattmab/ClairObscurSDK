#include "observer_core.h"
extern "C" __declspec(dllexport) BOOL InstallFixtureObserver(
    void* volatile* slot, ObserverEntry expected, ObserverBuffer* buffer) {
    return install_observer(slot, expected, buffer);
}
extern "C" __declspec(dllexport) BOOL RemoveFixtureObserver() {
    return remove_observer();
}
