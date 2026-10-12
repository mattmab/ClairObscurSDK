#pragma once
#include <cstddef>
#include <cstdint>

// The private music map/array collector remains bounded to64 unique objects.
// Explicit SDK sounds additionally need deterministic cleanup when both paths
// are used together. This is private ownership capacity, not session leases.
constexpr uint32_t kDiscoveredMusicCapacity=64;
#ifdef E33_EXTENDED_OWNED_AUDIO_SESSION
constexpr uint32_t kExplicitSoundCapacity=32;
constexpr uint32_t kOwnedAudioCleanupCapacity=kDiscoveredMusicCapacity+kExplicitSoundCapacity;
constexpr float kOwnedSoundVolumeMaximum=2.f;
static_assert(kOwnedAudioCleanupCapacity==96);
#else
constexpr uint32_t kExplicitSoundCapacity=16;
constexpr uint32_t kOwnedAudioCleanupCapacity=64;
constexpr float kOwnedSoundVolumeMaximum=1.f;
#endif
inline bool owned_sound_slot_available(uint32_t count) {
    return count<kExplicitSoundCapacity;
}
