# ClairObscurSDK 0.1.0-rc24

RC24 adds opt-in fast mod refresh scheduling and separates public mod sources and
downloads into [ClairObscureSDKMods](https://github.com/mattmab/ClairObscureSDKMods).
Native runtime 251 and the bootstrap are unchanged from RC23.

Extract the SDK ZIP into the game directory beside Sandfall. It includes SDK
Management, Introspection Harness and LiveObjectViewer. Install optional mod ZIPs
from the mods repository into the same directory. Existing SDK settings and saved
maps are not included or overwritten by these archives. Restart the game after
updating. Do not run a second SDK controller against the same game process.

Enemy HP 0.1.4 displays current health on the game's naturally visible normal-enemy
and boss health bars. Labels follow the original bar's visibility and opacity and
sit above its left end to clear the break meter and burning icon. It changes no
combat values or saves. Enable Enemy HP in Mods; no hotkey is needed.

The new fast refresh callback runs between ordinary mod callbacks. Enemy HP uses
prepared read schemas and a persistent reader to avoid rebuilding a read helper
for every update. Live multi-hit checks generally updated in under 200 ms; one
sample bounded the delay at 172–219 ms, so this is not a hard real-time guarantee.
Normal enemies, bosses, natural visibility, damage refresh, status-icon placement
and fight cleanup were checked in-game.

Scene Editor, Cinematics, flight playback, whole-scene placement and the other
public mods are carried forward from RC23 in the separate mod downloads. Existing
experimental cinematic and actor-binding limitations still apply.

Developers should clone with `git clone --recurse-submodules` or run
`git submodule update --init`. The SDK pins the exact mods commit used for its
integration tests. Mod changes and releases now live in the mods repository.
