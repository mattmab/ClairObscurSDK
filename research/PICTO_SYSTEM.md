# Picto / Lumina system research



Status: **live stats, level, shared mastery and Lumina cost editing; full lifecycle coverage incomplete** (2026-10-12).

## Installable SDK release preparation (2026-10-12)

PictoEditor now imports canonical `expedition33` modules instead of loading
`.agent-work/picto` modules by filename. Typed map reading, bounded reference
closure capture, class asset loading, progression/cost transport and preferences
have been promoted into `src/expedition33`. Native Picto guards and the map-capable
reader have been promoted into `native`; Cinematics-specific files are untouched.

`expedition33.paths` resolves SDK settings/logs independently of the mod cache.
Picto overrides remain `SDK/settings/picto-editor.json`, keyed by stable Picto
definition ID. They must never be included in the release ZIP. The standalone
reader is expected at `SDK/build/readonly-worker/research_probe.exe`.

`scripts/package_mods.py` creates all current mod folders as reproducible
`.sdkmod` ZIP archives with root `mod.py` and resources, validates each output,
and writes a hash manifest. It neither imports mods nor changes the running game.
Initial output: `dist/mod-payload-rc1/SDK_Mods`, 11 archives including Cinematics
catalog data. Integration owns archive materialization, automatic game startup,
final RC assembly and coordinated launch validation. Archive conversion alone is
not evidence that game-load bootstrap has passed.

The integration lead subsequently assembled
`dist/installable-rc1/Expedition33-SDK-0.1.0-rc1.zip` (13,493,540 bytes;
SHA-256 `cff0a975e69188044d3f77b0097ae9a498a4f15d510b2d6435df4606944888f1`).
Independent checks verified all 155 archive files, the SDK and bootstrap hashes,
11 mod archives, and absence of settings, logs, saves and development-tree files.
The bundled interpreter's offline integrity check passed after extraction to a
different directory containing spaces. All 11 mods then imported using only that
relocated SDK; PictoEditor constructed without engine access and resolved its
preferences and reader paths within the relocated installation.

An integration test verifies saved enabled and disabled choices across archive
replacement and cache rebuilding, with unchanged settings bytes. Three Windows
version-information API forwarding checks matched the system DLL in an isolated
non-game process. These are offline checks, not a live automatic-start result.

RC3 supersedes that initial artifact:
`dist/installable-rc3/Expedition33-SDK-0.1.0-rc3.zip`, SHA-256
`d1ac0f27ea988a2e0d545ab39475c17fd3bf8efa4c44d9784950003737dcb74d`.
All 157 files passed the same independent relocation/integrity checks. Live
integration testing launched through the normal Steam launcher, automatically
started the installed host and reached `SDK ready` for PID22944 after loading
the save. The installed controller log confirms the native Mods pause entry
attached. Startup now resolves the current Pawn reference explicitly, supports
the mounted world-map character and waits through a valid idle title screen.
Flight remains enabled while waiting for a supported dismounted character.
Visual menu verification and post-restart Picto reapplication remain separate
checks; do not infer them merely from controller readiness.

## Restart repair, persistence and menu construction (v0.5 / native v4)

The user restarted the game (PID14868) and reported disabled level/mastery/cost
controls. The current host was the v65 Cinematics launcher, which did not expose
Picto protocols. Independently, the older Picto v3 admission profiles embedded
PID13448 addresses and raw pointer-bearing Blueprint bytecode. Both issues are
addressed in the isolated v4 runtime. Historical addresses below are evidence,
not reusable selectors.

Seven original functions now use typed symbolic operand profiles: ChangeLevel,
SetPassiveEffectSharedProgression, RefreshUsedLuminaPointsInternal,
SetBaseStatsMultiplier, RefreshCurrentGearStats, UpdateEquipmentStats and
RefreshSlotData. A strict token walk identifies 933 reference operands. Every
remaining byte matches the previously exercised scripts from the earlier game
process. Runtime checks validate registered object outer chains, field ownership,
types, offsets, widths, flags, dimensions, target types, names and function shape.
Existing expected-value, active-panel, owner and identity checks remain intact.
Unknown bytecode/schema changes reject; this is not arbitrary Blueprint admission.
The native read-only validator passed all seven profiles in the new process and
rejected simulated bytecode and parameter-schema changes for each.

The coordinated v65 shutdown released all inspected public/private leases and
native ownership. Loaded v4 PDB: `169fad84-d383-47d5-8691-93fa5c818728`, age10.
The user subsequently verified Lumina cost editing works. Level no-op dispatch
also succeeded. Mastery accepts an existing nonnegative int32 progression count
(e.g.246) while the requested target remains bounded0..100; large accumulated
progress no longer prevents Reset/Master. The diagnostic no-op skips target
counts above100 instead of changing them.

### Saved overrides

`settings/picto-editor.json` uses the existing SDK `SettingsStore` (versioned,
atomic replacement, backup recovery, corrupt-input preservation, stale-writer
rejection). The mod-owned record is `sdk.picto-editor`, with options schema1 and
a `pictos` map keyed by reflected `ItemDefinitionID`. Only explicitly applied
fields are recorded: stat multipliers for keys1/6/8/9, level, cost, and boolean
shared mastery. No object addresses, registry indices or save-file data are stored.
An acknowledged edit is saved before secondary UI updates, so a repaint failure
does not silently discard the preference. A newer user Apply supersedes a queued
restore for the same field.

On mod/controller startup, overrides are queued and restored when an active stock
Pictos panel and a valid character are available. This first version therefore
requires opening the Pictos menu after a game load; it does not mutate during the
title screen or force the menu open. Each field is freshly resolved and compared;
matching values are skipped. Missing owned Pictos leave their file entries intact.
Uncertain or failed writes stop restoration with diagnostics and no blind retry.
Restoration does not call game save/progression-save functions.

Live evidence: user-applied Cheater cost35 was written at configuration revision1.
Repeated mod reloads read that file and completed the queue without errors. The
bounded `picto.verify_saved_restore` diagnostic changed35→34, reconstructed the
queue from a newly opened settings store, and restored35. All26 `.sav` hashes were
identical before/after. Evidence: `.agent-work/picto/evidence/v4-saved-cost-restore.json`.
This verifies active cost reapplication and mod reloads; another full game restart,
automatic stat reapplication after that restart, and travel/disconnect lifecycle
coverage remain pending. Pre-v0.5 choices already lost during a restart cannot be
reconstructed safely from final derived stat totals; apply those choices again.

### Launch and enabled preferences

The integration lead confirmed that `Registry.set_enabled` persisted preferences
correctly, but candidate hosts force-enabled bootstrap lists and omitted
`restore_enabled()`. Picto hosts now respect explicit disabled choices, bootstrap
protected core mods, and restore saved enabled mods outside a shared read batch.
Failures are reported per mod. One saved Flight mod failed to restore because no
locally possessed exploration character was available in the menu; other mods
continued loading, and its desired enabled preference was retained.

The lead added `launch-sdk.cmd` selecting combined Cinematics/Picto v4 and made
`launch-cinematics.cmd` delegate to it. `launch-picto.cmd` is an alias for the same
canonical entrypoint. The checkout's `.agent-work/picto` support files and v4
build outputs remain required; this is not yet a standalone distribution.

### Menu latency

Construction now uses bounded targeted catalogs, operation-scoped readers,
existing layout batching, and background inventory indexing. Layout arguments
are prepared only when a batch is ready because subsequent object creation
revokes earlier prepared plans. Nested stored references are captured using
identity-validated selected catalogs instead of requiring the full game registry.

Measured v4 initial construction:11,639.9ms, including6,770ms full catalog and
1,395.9ms synchronous inventory indexing. After consolidation:5,470.5ms total,
2,240.4ms targeted discovery,0.2ms foreground inventory setup,3,165.5ms widget
creation. Inventory reading runs afterward on the observation worker. Timings
vary with foreground/background game state. Full selection reads still take
about640ms; the80ms end-to-end target is **not met**. Next work should add a narrow
selected-field reader and further reduce widget construction dispatches; do not
weaken identity checks or reuse plans across menu/world lifetimes for speed.

Validation: four preference tests, seven control tests, cross-process bytecode
normalization tests, native protocol fixtures, live profile rejection checks,
successful menu attachment and saved cost reapplication. Five-extra-hit effect
editing is paused under the user's performance/persistence pivot.

## Current cost and progression update (v0.4)

This section supersedes historical unsupported-feature statements below. The
user verified functional cost changes everywhere; the compact bottom-right list
retained stale cost text until changing page. A targeted UI refresh now runs after
cost Apply using existing TextBlock.SetText, without navigating or changing saves.
Live invocation refreshed five stock labels successfully; a subsequent screenshot
confirmed editor, equipped card and compact row all showed the user's current
Cheater cost30. The attempted computer-use Apply-path check stopped when the tool
detected concurrent user input; that end-to-end button check remains uncompleted.

| Verified owner | Mapping |
| --- | --- |
| DT_PassiveEffects | `/Game/Gameplay/Lumina/DT_PassiveEffects.DT_PassiveEffects`; index68215 serial0 address2942671603584 |
| DataTable row map | Virtual accessor slot0x2d8 contains `48 8d 41 30 c3`, returning object+48. DoesDataTableRowExist RVA0x367f9d0 confirms 24-byte entries: Name+0, row pointer+8. Read-only validation found657 occupied rows. |
| FPassiveEffect | Extent72; `LuminaCost_15_BC10A93D48987A14F96279AC521E94CF` IntProperty+48; original observed costs1..40 |
| BP_PassiveEffectInstance_C | PassiveEffectID Name+48; PassiveDefinition Struct+56; OwnerData Object+128. Definitions are cached copies. |
| BP_CharacterData_C | CurrentlyUsedLuminaPoints Int+556; original RefreshUsedLuminaPointsInternal function79704/9856, address0x2adfcce6980, extent484 and2338-byte script |
| BP_jRPG_GI_Custom_C | SharedPassiveEffectProgression Name-to-Struct map+3816 is shared mastery authority. Character-local progression is not authoritative. |
| FPassiveEffectProgression | IsLearnt Bool+8; LearntSteps Int+12 |
| WBP_GM_COV_LuminaElement_C | LuminaCost CommonTextBlock+792; PassiveEffectInstance Object+832 |
| WBP_GM_LuminaPoints_C | UsedPoints CommonTextBlock+760; MaxPoints+744 |

Native cost operation3 uses the existing isolated progression envelope and
game-thread transport. It checks object identities, active panel/current character,
passive owner, row schema/accessor, occupied row identity, expected old cost and
all matching cached copies before writing. It changes the four-byte table cost
and cached definitions, then calls original spent-point recalculation for loaded
characters. UI range0..100; changes affect all characters. No save call is made.
These runtime data-table edits remain until the game process ends; automatic
restoration on mod disable is not implemented.

Evidence: `.agent-work/picto/evidence/cost-table-live.json`,
`table-layout-native.json`, `cost-character-functions.json`, `cost-scripts.json`,
`lumina-compact-fields.json`, `lumina-ui-fields.json`, `picto-v3-loaded.json`.
Corrected v3 loaded PDB: c8739c6e-4303-4015-a8f1-2f476600f9eb age6. An initial
build-script source-path mistake loaded v2; its cost request was rejected with
outcome0, then the source path was corrected and exact loaded PDB verified.
A later automated round-trip also failed preflight1721 before writing. User
subsequently tested successfully; status observed cost27 and Apply1903.7ms.
Do not describe the rejected automated round-trips as successful validation.

Seven editor control tests and native request fixtures pass. Local drafts are
about13ms; observation is about650-700ms. The requested80ms complete update target
is not achieved. New-process compatibility and zone transitions remain untested.
Combo Attack III resolves to BP_LU_ComboAttackC_C inheriting BP_LU_ComboAttackA_C;
the extra-hit count has not been proven to be an editable scalar.

### Combo Attack count research (after cost acceptance)

User confirmed the cost UI now works and requested effect counts in the editor.
Retained class loading succeeded for BP_LU_ComboAttackC_C, observed217347/554082
at0x2ae5a20c480; parent BP_LU_ComboAttackA_C223930/554078 at0x2aeed90ac00.
No gameplay effect was activated by this research.

`DT_Balancing_Luminas` at
`/Game/Gameplay/Battle/ScalingSystem/BalancingTables/Content/DT_Balancing_Luminas`
has row type `S_BalancingTableFloatEntry`, extent8, with DoubleProperty
`FloatValue_3_9D7EBC84471861D83D95EC8FC8B0C998` at0.
Rows `ComboAttack1_AttackAmountAdded`, `ComboAttack2_attackAmountAdded` and
`ComboAttack3_attackAmountAdded` all read1.0. Their names alone do not prove that
the matching Picto consumes each row.

The live727-byte inherited ComboAttackA event graph reads the ComboAttack2 row
at name-constant offsets66 and129, and ComboAttack1 at365. It selects a truncated
integer using LuminaId (IntProperty+352), adds it to the battle character's
BaseAttackNumber (IntProperty+3936), and clamps that accumulator to0..4.
The observed A and C default objects both report LuminaId0; runtime-instance
selection remains unverified. The apparent duplicate row reference must not be
silently treated as a verified independent ComboAttack3 mapping.

The battle actor event graph is65649 bytes, beyond the old describe-script64KiB
limit. A bounded read-only chunked export verified a stable script header. Its
BaseAttackNumber selector has explicit cases0..3 selecting Attackx1Sequence
(array+4728), Attackx2Sequence(Object+4744), Attackx3Sequence(+4752), and
Attackx4Sequence(+4760). Thus merely writing5 into a balancing row does not prove
five extra hits: both accumulator clamping and attack-sequence selection need
attention. No supported six-hit sequence path has been established.

Evidence: `combo-inherited-live-retained.json`, `combo-scripts.json`,
`combo-balance-schema.json`, `combo-parameters-live.json`,
`combo-battle-graph-native.json`. First proposed experiment: observe the actual
ComboAttackC instance in battle, prove its row selector, then test a reversible
count increase within an existing sequence. No count write or combat activation
has been performed. The user was asked to enter a battle and wait before attacking
so these runtime identities can be inspected without autonomously progressing combat.

Live battle follow-up: `combo-runtime-actors-check2.json` contains85 reflected
objects with0 read errors. Verso actor275607/628670 has BaseAttackNumber3 and
the genuine Attackx1/x2/x3/x4 LevelSequence references. Active buff C117890
at2948687822208 reports LuminaId0; B117893 reports1; A117896 reports0. All
three target Verso stats275624/628673. This confirms that changing the
ComboAttack1 balancing row alone would change both A and C behavior; merely
editing the unused ComboAttack3 row is not a verified per-Picto implementation.
The accumulator is a bonus-hit selector:0 selects x1,1 selects x2,2 selects x3,
and3 selects x4. The clamp maximum4 is not evidence for a fifth/sixth attack path.
No count, actor property, bytecode, attack sequence or buff state was mutated,
and no combat action was selected. User can leave the battle without waiting for
an agent-triggered attack; the necessary read-only snapshot is captured.

Required implementation before enabling an effect-count control:

1. Add a distinct per-Picto override mapping keyed by verified passive ID and
   actual effect class, with compare-before-write and owned cleanup. Do not expose
   shared row writes as independent Picto controls.
2. Validate total extra counts against the existing0..3 sequence selector for a
   bounded first experiment. Stacking with the other two Combo effects matters.
3. Five extra hits means six total. Author or verify a six-hit execution route
   preserving damage, AP gain, timing and turn completion before advertising5.
   Increasing only the table value or clamp does not satisfy this requirement.
4. Integrate the verified adapter as an `Extra hits` row alongside level/cost/
   mastery. Do not present an enabled control that merely edits unused metadata.

Effect-count editing remains unimplemented; the current cost/stat editor is left
enabled. This is a verified limitation, not a claim that arbitrary additional hits
are impossible with a larger runtime combat adapter.

Earlier sections below retain the history of initial read-only research.



## Current live implementation



`mods/PictoEditor/mod.py` v0.2 adds directly selectable Health, Defense, Speed,

and Crit Rate rows with current values to the existing Pictos panel. Zero stats

remain visible so a missing bonus can be selected directly. Crit Rate displays

percent. The selected row controls a bounded 0–10 multiplier draft; +/- changes

only that draft, and Apply invokes the original game setters and recomputation.

This is multiplier editing, not direct final-value entry. Root hover/pressed/

selected animations are removed only from the owned container, so child hover

does not scale the entire editor. Controls were visually inspected in the game.



Confirmed numeric keys from reflected maps compared with stock card labels:



| Map key | Meaning | Live evidence |

| --- | --- | --- |

| 1 | Health | Cheater 3389; Fueling Break 1007 |

| 6 | Defense | Fueling Break 544 |

| 8 | Speed | Cheater 917; Fueling Break 507 |

| 9 | Crit Rate, percentage points | Cheater 35%; Fueling Break 31% |



Evidence: `.agent-work/picto/evidence/named-editor-live.json` contains 193 objects

(188 Picto instances and five character data objects), no object-level errors.

Fueling Break's internal ID is `GreatFireBreak`, object index97235, serial0,

address2946241406400 in PID13448. Cheater is index97336, serial0,

address2942016977728. These are observations for this process, never reusable

addresses. Native identity checks remain mandatory.



The user confirmed Apply works and added Health and Defense to Fueling Break

while testing. Its reflected CurrentStats is {8:507,9:31,1:1007,6:544}, with

BaseStatsMultipliers {1:0.4,6:0.4,8:1,9:1}. Stock UI shows those added bonuses.

The assistant has not reset these user edits. The stock four-stat card can crowd

its level text; the editor's named rows remain readable.



### Dispatch and limits



The isolated current-process native candidate admits only exact observed

Blueprint functions and bytecode: `BP_ItemInstance_Gear_C.SetBaseStatsMultiplier`,

`RefreshCurrentGearStats`, `BP_CharacterData_C.UpdateEquipmentStats`, and

`WBP_Panel_Pictos_C.RefreshSlotData`. Runtime schemas, target identities, argument

bounds, CDO rejection and full observed bytecode are checked. Existing generic

object/pause gates remain intact. Candidate sources are under

`.agent-work/picto/runtime-native`; no Cinematics-specific native source was edited.

The candidate is process-bound and is not a distributable, cross-launch profile.



Apply rereads current selection, character and multiplier, rejects changed

selection/value, invokes the setter, recomputes, checks multiplier readback, and

refreshes character equipment and three stock slots. The sequence is not an atomic

transaction; a later failure may leave the setter applied and requires diagnostics.

No save/progression API is invoked. All 26 save hashes matched before/after the

latest read-only inspection; this does not establish persistence behavior of

user edits on a later game save.



### Responsiveness checkpoint



Draft controls now use a separate SDK invocation planner for owned text labels,

retaining validated descriptor observations. Native schema/identity checks still

run at dispatch. Read-only background observations own a separate, short-lived

reader per operation and never access thread-owned session resources or invoke

UFunctions. Reload joins this worker before releasing mod resources.



Measured after deployment: +/- draft handlers 11–15 ms; a direct Speed-row

selection 44.9 ms. These are handler durations, not instrumented end-to-end

input-to-photon latency. Fresh background observation was 502.5 ms. Therefore the

80 ms target is achieved for the sampled handler work only, not yet for fresh

selection reads or Apply. Earlier synchronous Apply measured 586–621 ms; the

latest asynchronous observation implementation still requires a fresh Apply

measurement. Full enumerations have been removed from selection polling.



Four focused offline tests pass: direct zero-stat selection, local-only bounded

drafts, row-switch draft discard, and no-selection rejection. Live named labels,

current values, stable container size, repeated observations, reload and direct

Speed selection were verified. Character transitions, zone transitions and

controller disconnect remain unvalidated for this editor.



Next: profile bounded reads to bring fresh selection/Apply latency toward80ms;

consider a narrow game-thread snapshot/transaction capability if native startup

and metadata work remain dominant. Any new native candidate needs coordinated

controller handoff. Complete stale-menu/travel/disconnect tests before general

release. Cost, unlock, level, arbitrary passive effects and new definitions remain

unsupported. Do not describe the full requested editor as complete.



## Historical discovery and scope notes (superseded where noted above)



## Current scope discussion â€” live Picto editor



**UI requirement clarified:** enabling the mod must expose live editable values

inside the game's existing Pictos menu, following its current Picto and character.

The separate SDK Management inspector presenter is a research tool, not the final

editor UX. The existing Pictos list remains the selection interface. Add native

controls to its detail context for level, Lumina cost/learned state and the four

stat bonuses, with add/remove-stat controls where supported. Closing/reopening the

stock menu must rebind safely; disabling must remove the mod's controls.



Live screenshot on 2026-10-12 confirms the user's open Verso Pictos screen, with

three equipped Picto cards and Luminas530/536. Read-only widget capture

`.agent-work/picto/evidence/picto-menu-current.json` contains323 observations,

zero object-level errors and unchanged26 save hashes. Active panel is a

`WBP_Panel_Pictos_C` (observed index214255/serial543469). Its `bIsActive` is true,

`CurrentCharacterData` references Verso, `FocusedSlot` references `WBP_PictoSlot2`,

while `SelectedPictoViewItem` and `FocusedItem` are null in this state.

`WBP_PictoSlot_C` exposes the exact property `Picto View Item`, which resolves to

`BP_PictoViewItem_C`; that view item exposes `ItemDynamicData`,

`CurrentCharacterData`, `InventoryManager` and `ItemUpgradeSystem`. Thus a selected-

item-only integration would miss the currently focused equipped-slot state.

Widget attachment, selection precedence, numeric editing and mutation routes are

not yet implemented or live validated. No control was injected during this read.



The user now requests defining a mod for editing Pictos from the native menu,

including Lumina cost/unlock, owned Picto level, existing health/speed/critical-rate/

defense bonuses, and adding missing stat bonuses. This supersedes read-only as the

intended final feature set, but no game mutation has been performed or validated.

The sections below dated 2026-10-11 are the historical initial checkpoint.



Proposed first release:



- Search/select an owned Picto and show its equipped character(s), current level,

  stat bonuses, associated Lumina row references and learned state.

- Edit the selected owned Picto's level. Investigate the original recalculation

  path so level and resulting stats remain consistent.

- Edit existing health, speed, critical-rate and defense bonuses. Add/remove a

  bonus entry where the runtime map and original stat aggregation support it.

  These are numeric stats, distinct from adding passive combat effects.

- Edit associated Lumina cost and learned/unlocked state once the definition/

  progression write and recomputation routes are verified. Show whether an edit

  applies to the selected item, a character, or a shared passive definition.

- Stage changes in the native menu, show before/after values, Apply explicitly,

  refresh dependent equipment/Lumina state, and support reverting a successfully

  tracked edit during the same session where the original identity remains valid.

- Save persistence is a separate decision/acceptance item. Neither runtime writes

  nor an Undo control establish session-only behavior when the game can autosave.

  The original no-save-modification research restriction remains until changed.



First-release exclusions: authoring new Picto assets, arbitrary new combat passive

logic or combinations, increasing equipment slot counts, and redesigning global

Lumina rules. Adding health/defense to a speed/critical-rate Picto is in scope as

stat-map editing, subject to live write/aggregation validation.



## Current live findings â€” 2026-10-12



Lead coordination: `.agent-work/picto/LIVE_ACCESS.md`; v65 integration, no competing

lead live work scheduled. Only standalone read-only workers used. Shared controller,

loaded native runtime and Cinematics/Management source files remain untouched.



Current PID13448 executable identity is validated by the existing SDK worker.

Evidence is under `.agent-work/picto/evidence/`:



- `discovery.json`: 2421 name-based leads and live UStruct metadata, zero descriptor

  errors. Names alone are not classified as Picto definitions.

- `targets-current.json`: 914 selected observations; 337 exact Picto asset instances,

  188 Picto inventory instances, five characters. Weapon assets derive from the

  Picto asset class, so the API now uses exact class matching to exclude them.

  UserDefinedEnum member reading is unsupported; it is reported explicitly.

- `typed-maps-current.json`: 193 character/inventory observations through an isolated

  extension of the existing typed native map reader, zero object-level errors.

  Both completed value surveys compared 26 save-file hashes before/after: unchanged.

- `targets.json` records the initial unsupported enum rejection. Subsequent closed-

  worker errors in that initial file are not independent read attempts or live

  facts; the script now exits its operation on a terminal RuntimeQueryError.



Verified property mappings (exact generated names/identity/offset/type records in

the evidence JSON):



| Owner | Property | Observed type / meaning |

| --- | --- | --- |

| `BP_ItemInstance_Gear_Pictos_C` | `CurrentLevel` | IntProperty, offset456 |

| same | `CurrentStats` | Byte -> Double map, offset376 |

| same | `BaseStatsMultipliers` | Byte -> Double map, offset464 |

| base inventory instance | `ItemDefinitionID` | NameProperty, offset48 |

| same | `ItemStaticData` | S_jRPG_Item_StaticData, offset56; contains actual Picto asset reference |

| `BP_DataAsset_Item_Pictos_C` | `PassiveEffects` | Array of FPassiveEffectDataTableRow, offset64; resolves DataTable + RowName |

| same | `BattleBuffs` | ArrayProperty, offset48; observations do not establish nonempty combat effects |

| `BP_CharacterData_C` | `EquipmentInstancePerSlot` | FEquipmentSlot -> Object map, offset2112 |

| same | `EquipmentPerSlot` | FEquipmentSlot -> S_jRPG_Item_StaticData map, offset56 |

| same | `LuminaMaxPointsFromLevel` | IntProperty, offset548 |

| same | `LuminaMaxPointsFromConsumables` | IntProperty, offset552 |

| same | `CurrentlyUsedLuminaPoints` | IntProperty, offset556 |

| same | `EquippedPassiveEffects` | Name array, offset560 |

| same | `PassiveEffectProgressions` | Name -> FPassiveEffectProgression map, offset576 |

| `FPassiveEffect` | generated `LuminaCost` | IntProperty, offset48; row layout verified, DataTable row contents not yet decoded |

| `FPassiveEffectProgression` | generated `IsLearnt`, `LearntSteps` | Bool at8, Int at12 |



The isolated map extension preserves descriptor, storage, occupancy, identity and

double-read guards, reusing existing scalar/struct codecs. It adds Byte->Double,

Name->Struct, Struct->Object and Struct->Struct shapes. Struct-key maps return

immutable copied pairs rather than pretending mutable structures are Python keys.

Native candidate builds /W4 /WX. Existing31 decoder/reader tests and18 focused

extension/fixture tests pass; nine inspector/presenter contract tests also pass.

No write route is confirmed by these read tests.



Readable character identities: Lune, Maelle, Sciel, Monoco, Verso. Their equipment

slot maps resolve to actual weapon/Picto inventory object identities. Slot type2

was observed referencing Picto instances and type1 weapon instances; enum display

labels remain unavailable. Stat numeric keys likewise must not yet be labeled

health/speed/critical-rate/defense without verified enum or calculation evidence.



Confirmed reference example: owned `Dodger` item -> `DA_GearPictos_Dodger` through

the actual `Pictos_Data_103_EE44D66B4E4F16A7FD44FF9F25777CF4` struct member.

`DA_GearPictos_HealOnBuff.PassiveEffects` -> `DT_PassiveEffects` row `HealOnBuff`.

The API reports table/row links without fabricating unavailable row values.



Still pending: stat-key semantic mapping; live Picto write/recompute/unlock routes;

DataTable row reading/cost editing; menu visual validation and native editing

controls; character-switch, zone-transition and controller-disconnect acceptance.

No shared SDK/native candidate integration has occurred.



## Historical initial checkpoint (2026-10-11)



## Isolation and live access



Implementation is staged exclusively under `.agent-work/picto/`. No Cinematics

native file, shared controller, loaded DLL, save, or progression state has been

changed by this work. The lead integration chat owns live access, as specified

in `research/PARALLEL_DEVELOPMENT.md`. A bounded read-only discovery window has

been requested; no live operation has been performed pending that coordination.



## Evidence classification



`evidence/introspection-catalog-first.jsonl` is an existing historical capture

from PID 34604. It supplies discovery leads, **not current identities or verified

Picto behavior**. The following names occur in that capture:



| Historical lead | Observed kind | Research question |

| --- | --- | --- |

| `S_PictosDefinition` | UserDefinedStruct | Definition fields and effect links |

| `DT_PictosDefinitions` | DataTable | Row schema and native row storage |

| `BP_DataAsset_Item_Pictos_C` | BlueprintGeneratedClass | Loaded definition assets |

| `BP_ItemInstance_Gear_Pictos_C` | BlueprintGeneratedClass | Runtime inventory instances |

| `FPassiveEffect` | UserDefinedStruct | Passive definition/reference representation |

| `FPassiveEffectDataTableRow` | UserDefinedStruct | Effect table rows |

| `DT_PassiveEffects` | DataTable | Passive definitions |

| `FPassiveEffectProgression` | UserDefinedStruct | Learned state; read only |

| `FCharacterAssignedEquipment` | UserDefinedStruct | Character equipment mapping |

| `BP_PassiveEffectInstance_C` | BlueprintGeneratedClass | Runtime effect observations |

| `BP_CharacterData_C` | BlueprintGeneratedClass | Character-specific equipment and Lumina state |



Historical functions owned by `BP_CharacterData_C` include

`GetCurrentlyUsedLuminaPoints`, `GetMaxLuminaPoints`, and

`GetEquippedPassiveEffectsData`. Names do not establish purity, supported ABI,

or safe invocation. None have been invoked by this research.



## Staged SDK interface



`.agent-work/picto/src/expedition33/pictos.py` provides `PictoInspector`:



- `list_definitions(query)`, `characters(query)`, and `list(kind, query)` enumerate

  currently loaded objects only; exact class paths must resolve in the catalog.

- `inspect(reference)` revalidates the selected PID/index/serial/address through

  `capture_selected`, then delegates stored values to `read_values`.

- `schema(reference)` delegates live class metadata to `reflection.describe`.

- `export(path)` writes a copied JSON observation, preserving identity, owner,

  property type, unsupported-value diagnostics, and container truncation.

- `close()` clears observations and revokes further operations.



These are staged contracts, not a verified domain mapping. Definition rows,

character assignments, capacities, and effect resolution require current live

evidence before dedicated accessors can be finalized. Failed requests clear the

last exportable observation. No mutation or reflected invocation is exposed.



## Optional inspector



`.agent-work/picto/mods/PictoInspector/mod.py` stages a presenter for the existing

SDK Management native game-themed panel. It shares the existing widget owner and

supports categories, paging, inspection, refresh, and JSON export. Text search

uses `picto_search <text>` because the existing native panel does not implement a

text editor. It has not been loaded into the shared controller or visually tested.



## Validation record



Nine offline contract tests passed in 0.003 seconds using

`.agent-work/picto/tests/test_pictos.py`. They cover stale identity rejection before

value reads, exact identity selection, preserved unsupported/truncated values,

failure invalidation, close revocation, unknown-reference rejection, menu paging,

stale control rejection, and failed-refresh display clearing. These use mocks and

are not substitutes for live validation.



Pending: fresh class/property/enum mappings; repeat reads; real character changes;

zone transitions; shared-controller disconnect; native menu visual acceptance;

before/after save integrity comparison. No claim of validated completion is made.



## Overhaul feasibility



No Picto mutation capability is confirmed. Existing SDK reflection and invocation

support does not establish safe Picto editing. Numeric effect edits, passive

behavior changes, combinations, new definitions, and slot/capacity changes all

remain unverified. DataTable row storage and nested container support need

investigation; no offsets or parameter layouts have been guessed.



The first proposed experiment, after read-only acceptance, is to select a verified

numeric field on an independently owned transient effect copy, record its value,

perform a bounded reversible edit, observe readback, and restore it before releasing

the copy. This is conditional on proving construction, ownership, field semantics,

and teardown; it is not yet approved as safe or scheduled for execution. Avoid

editing inventory, shared default objects, definition tables, unlocks, or saves.



## Next steps



1. Lead grants a serialized discovery window. Run the staged discovery scripts.

2. Record full current identities, class paths, property owners/types, enum members,

   and function metadata; distinguish unsupported native storage from empty data.

3. Finish domain accessors from those observations and test against live data.

4. Lead integrates only reviewed Picto files and loads the optional mod through the

   existing controller. Validate native appearance and lifecycle without restart.

5. Coordinate real character/zone/disconnect coverage and record its actual scope.


### RC3 publication and resumed menu check (2026-10-12)

Published private prerelease `v0.1.0-rc3` from commit `da5de7248124558adaf7217221cb3b30266eb648`. GitHub confirmed the uploaded ZIP SHA-256 matches `d1ac0f27ea988a2e0d545ab39475c17fd3bf8efa4c44d9784950003737dcb74d`. All 826 Python tests passed using the bundled interpreter.

After renewed computer-use permission, visually confirmed the installed native Mods pause entry and successfully opened SDK Mods page 1/2. Cinematics, Continent Flight, Introspection Harness and Live Object Viewer displayed enabled; example mods displayed not loaded. Further navigation encountered concurrent user input twice, so automation yielded the controls. Picto-specific cold-start visual restoration remains pending; no new game values were edited during this check.

## Draft previews and startup restoration — 2026-10-12

The later user scope authorizes runtime Picto edits and persistence of explicitly
applied overrides. It supersedes the earlier read-only discovery scope; save-file
editing and explicit save requests remain excluded.

### Verified mappings and preview calculation

- `/Game/Gameplay/Pictos/BP_ItemInstance_Gear_Pictos.BP_ItemInstance_Gear_Pictos_C:GetScalingDataTable`
  returns `/Game/Gameplay/Pictos/DT_EquipmentScalingTable_Pictos.DT_EquipmentScalingTable_Pictos`.
- `FL_ItemUpgradeHelpers.GetEquipmentScalingLevel` constructs `Level_` plus the
  decimal level for its DataTable lookup.
- Row type `S_GearScalingLevel`: reflected extent 92 bytes; level IntProperty at
  offset 0, `Stats_19_14AC0B3B43D586575C5433A630321A61` Byte-to-Double MapProperty
  at offset 8, ChromaValue IntProperty at offset 88. The live table has 34 rows,
  `Level_0` through `Level_33`.
- `BP_ItemInstance_Gear_C.RefreshCurrentGearStats` multiplies each positive stat
  multiplier by the level row's corresponding base value, calls `FCeil`, converts
  the result to Double, and calls `SetCurrentStatValue`. At level 33 the four base
  values are Health 3765, Defense 2485, Speed 764, Crit Rate 38.
- The game skips nonpositive multipliers without removing an existing CurrentStats
  entry. A zero draft therefore requires explicit clearing, not just rescaling.
- `BP_ItemInstance_Gear_C.SetCurrentStatValue`: 32 parameter bytes, no return,
  StatType Byte at 0, Value Double at 8, Reason FString at 16. The new operation 9
  admits only zeroing one of keys 1/6/8/9, after the multiplier is verified zero and
  the previous integer-valued stat matches the request. It uses the game's setter
  with an empty FString and validates readback. Its complete script and typed
  operands have a relocatable profile; the native capability is
  `picto_stat_clear_protocol=1`.

The reusable `values.read_table_rows` reader reuses the existing reflected value
codecs. It checks table identity, registered row struct, the native row-map
accessor, sparse allocation bounds/occupancy, unique row names, and repeated
storage observations. It exposes no caller-supplied row pointers and invokes no
functions. The editor caches level rows once per mod session; draft clicks perform
no game reads or writes.

### Implemented editor behavior

Drafts are keyed by definition ID and the current object identity. Switching
fields, characters, or Pictos retains each Picto's pending fields. Recycled item
identities invalidate their draft. Rows show projected final values and `*`;
returning a field to its original value removes its marker. Level changes also
preview the resulting stat changes. Apply processes level first, then explicit
multipliers, mastery and cost, refreshes equipment/menu once, and saves all
acknowledged overrides together. This is one user action, not an atomic rollback
transaction. A partial/uncertain native failure suspends further mutation and
retains acknowledged overrides; it is never retried implicitly. Unapplied drafts
are session-local and are not startup overrides.

### Observed validation and timing

- PID 45264: live previews matched all 188 owned Pictos, across 34 observed scaling
  rows. Evidence: `.agent-work/picto/evidence/draft-preview-validation.json`.
- Visually staged Health 2259 and Defense 249 on Cheater, both marked `*`, while
  the stock Picto card remained unchanged. One Apply committed both, updated the
  card, cleared markers, and saved both multiplier overrides in one settings
  revision. The zero-stat edge case was found while reverting the temporary
  Defense test; a guarded setter operation was then added.
- Cold test6 startup restored Cheater Health multiplier 0.7 and cost 35 before
  opening Pictos: 1077.3 ms from mod enable start to confirmed restoration.
  Full owned-widget preparation took 2576.1 ms. Test7 hot enable took 2682.1 ms.
- Test7 local draft painting took 14.3–14.7 ms. Two-field Apply took 342.5 ms;
  a one-field Apply took 318.9 ms. The 80 ms Apply / 2 second full initialization
  targets are NOT yet met. These measurements precede the extra final stat
  readback added for the zero-value fix.
- Python regression suite: 843 passing after the zero-stat change. Native runtime
  and reader compile under `/W4 /WX`; the protocol fixture passes.
- Test8 cold restart (PID 14424) restored saved overrides before any Pictos menu:
  1008.9 ms to restoration, 2648.1 ms to full mod initialization. A fresh read
  matched projected values for all 188 owned Pictos. The validation JSON above
  now records this restart rather than the earlier PID 45264 run.
- Five additional startup-restore tests pass: headless cost restoration, missing
  ownership without granting items, clearing a stale zero-multiplier stat,
  refusing to retry an uncertain mutation, and level-before-multiplier ordering.
  The subsequent live zero-stat check below validates the setter independently
  of cold restart restoration.
- Test8 live menu check (PID 14424): Cheater Defense drafted 0 to 249, applied,
  then drafted back to 0. Before the second Apply the editor showed `0*` while
  the stock card still showed 249. Apply cleared the actual stat to zero and
  removed the draft markers. The stock card retains a Defense label with value
  0; the setter clears its value rather than removing the map entry. Saved
  overrides returned to Health multiplier 0.6, Defense multiplier 0, cost 35
  (settings revision 6). A fresh read of all 188 owned Pictos found no preview
  mismatches. Local draft updates measured 12.9–14.5 ms; the two single-field
  Apply operations measured 333.7 and 279.9 ms. The latency targets remain open.
Character total Lumina capacity, character Attributes, mass leveling/mastery,
Picto ownership removal/unlock-all, and effect-count editing remain outstanding.
Character capacity fields 548/552 and the Byte-to-Int assigned-attributes map at
1480 have read-only live evidence; these are not yet exposed as editable APIs.
Inventory grant/removal names have been found, but their complete behavior and
safe call contracts are not yet verified. Do not confuse shared mastery with
inventory ownership. The first extra-hit experiment still requires inspecting
and validating the live battle buff/attack sequence.

## Native catalog redesign — 2026-10-12

The four-row overlay catalog is superseded as the intended browser design.
The requested direction is a full scrolling catalog adapted from the existing
Pictos screen. This is a design and reflection checkpoint, not a completed or
validated replacement.

Live read-only reflection in PID 35468 verified:

- `WBP_Panel_Pictos_C.PictosList`: ObjectProperty at 1112, class
  `WBP_PictosList_C`.
- `/Game/UI/Widgets/InGame_Menu/Pictos_Panel/WBP_PictosList.WBP_PictosList_C`
  owns `PictosFilter` (ObjectProperty, 1120), `PictosTileView`
  (ObjectProperty, 1128), `SortDropdown` (ObjectProperty, 1144),
  `PictosViewItems` (ArrayProperty, 1208), and `OrderedPictosViewItems`
  (ArrayProperty, 1224).
- Reflected functions include `LoadItemsForCharacter`, `GetPictoViewItems`,
  `AddItemsToList`, `FilterItems`, `IsMatchingFilterConditions`, `SortItems`,
  `RefreshTileViewEntrySize`, `OnElementClicked`, and `OnElementNavigated`.
- `BP_PictoViewItem_C` contains `ItemDynamicData` (StructProperty, 48),
  `CurrentCharacterData` (ObjectProperty, 360), `InventoryManager`
  (ObjectProperty, 368), and `ItemUpgradeSystem` (ObjectProperty, 376).
  Displaying a locked definition through this class is NOT yet verified safe:
  its instance getters and native equip callbacks need inspection first.

Evidence: `.agent-work/picto/evidence/native-catalog-menu-schema.json` and
`native-catalog-list-schema.json`. Addresses/serials in these snapshots belong
only to the captured process and must be resolved again before use.

Intended interaction:

1. Enter a Catalog mode from the Pictos editor, retaining the native screen and
   full scrolling list rather than rebuilding the whole menu.
2. Show all 210 verified normal gameplay definitions, visibly marking owned and
   locked entries. Keep the 132 experimental/unknown definitions in a separate
   inspection section; never mix them into gameplay Unlock all.
3. Add All / Owned / Locked and mastery filters, with name search and native
   sorting/navigation where their behavior is verified.
4. Selection feeds one detail/editor panel. Drafts and `*` remain keyed by Picto
   definition; Apply retains its explicit commit semantics. Locked entries may
   be inspected and explicitly unlocked, but must not flow into normal equip
   handlers as owned items.
5. Put mass level, master owned, and unlock gameplay actions in a dedicated
   toolbar. Bulk ownership scope must remain explicit and independent of the
   current visual filter.
6. Restore stock list source, filters, focus and navigation on leaving Catalog
   mode, disabling the mod, or losing the panel identity.

Next implementation gate: decode the list construction/filter/sort and view-item
instance-access scripts; validate a presentation-only source for locked entries
and intercept catalog selection without triggering equipment mutations. Prefer
SDK-owned presentation objects and existing generic UI/lease facilities. Do not
add inventory entries merely to make a definition visible.

Current candidate status: bulk/ownership controls are implemented but native
add/remove and bulk mutation tests remain incomplete. Cold restart restored
saved overrides before menu opening (1250.9 ms including discovery); full editor
initialization was 3066.8 ms, still above the requested two-second target.
Experimental separation and both catalog counts were checked live. The overlay
has observed label overlap and is not the accepted final browser layout.

### Scrolling catalog implementation and live checks — 2026-10-12

`picto_catalog.NativeCatalog` now supplies a presentation-only native ScrollBox
in the existing Pictos panel. It hides `WBP_PictosList_C` while browsing and
restores its captured `ESlateVisibility` on exit. Definitions remain Python
records; the catalog does not fabricate `BP_PictoViewItem_C` or inventory gear.
Twenty-four leased native buttons are reused across a two-column scrolling
window. Reflected ScrollBox offsets determine the rows; stale click observations
are discarded after rebinding. Existing UI batches update changed text,
visibility and position; unchanged rows are skipped. End uses `ScrollToEnd`,
because rendered viewport size can differ from the requested SizeBox height.

Fresh game PID 40548, catalog-test4 live checks: 210 normal definitions;
Owned filter 188; Locked filter 22; Experimental catalog 132. Selecting locked
Accelerating Heal reported Locked without granting/equipping it. Mouse wheel
scrolling reached Warming Up / Weakness Gain. Back to tools restored the stock
list, its level ordering, and existing equipment. SDK shutdown acknowledged
completed. These checks did not apply ownership or bulk edits.

Saved Cheater multipliers and cost restored on this restart before editor
attachment: restore including discovery 1251.8 ms; full editor enable 3052.9 ms.
The two-second full-enable and 80-ms edit targets remain unproven/unmet.

Removed the prototype search field: `EditableTextBox.GetText` returned native
error 703 (unsupported FText value) in the earlier test3 session. The unknown
outcome was not retried. That session closed and left its catalog widget on the
old panel until game restart. Abrupt controller loss cleanup therefore remains
a limitation; normal catalog exit was verified. No generic text safety guard
was relaxed. Search, mastery filtering, native stock-list source replacement,
and routing catalog selection into the stat editor remain future work.


Centered/wrapped label implementation: reflected
`TextLayoutWidget.SetJustification(InJustification: ByteProperty/ETextJustify)`,
`TextBlock.SetAutoWrapText(InAutoTextWrap: BoolProperty)`, and
`CommonTextBlock.SetWrapTextWidth(InWrapTextAt: IntProperty)` were captured in
live PID 40548. Evidence: `.agent-work/picto/evidence/catalog-text-schema.json`.
Discovery must include ETextJustify; omitting it caused a planning-only metadata
rejection before invocation in test6. Catalog names are no longer truncated;
96-unit row spacing and 90-unit button height provide space for two lines.
Horizontal centering was observed in test7. Test8 adds an SDK-owned Overlay
with vertical-center OverlaySlot alignment so one- and two-line labels are
vertically centered too. Horizontal slot alignment must be Fill (0), while
TextLayoutWidget justification is Center (1). Centering the slot itself made
the initially empty text shrink and wrap into an invalid narrow column in
test8; test9 corrects the available text width. The row pool was reduced to 24 to bound the added widget leases.
Final test9 live checks passed: editor and catalog button labels are centered
horizontally and vertically; Beneficial Contamination wraps onto two centered
lines inside its button without truncation. End reaches Warming Up / Weakness
Gain. All 63 targeted Picto tests pass. Latest full editor enable measured
4445.9 ms; startup discovery/restore measured 1105.1 ms. The two-second full
enable target remains unmet. Stock equipped-card stat-heading overlap is a
separate native card layout issue and is not changed by this button layout fix.

2026-10-12 follow-up: equipped-card layout and scroll reuse
--------------------------------------------------------
Verified live in PID 40548: WBP_PictoSlot_C.WBP_PictoCartridge points to
WBP_PictoCartridge_C; its StatsList is DynamicEntryBox. Runtime
WBP_PictoCombatStat_C entries expose StatType, StatLabel (WBP_WrappingText_C)
and StatValue. StatLabel.Text is CommonTextBlock and TextSizeBox is SizeBox.
The cartridge width is 330, level column 42, and stat spacing 5. Four-stat
cards now use 64-unit heading columns and 0.68 heading render scale.
Native localized heading text is preserved. Numbers retain their original size. Fewer-stat cards keep
stock layout. Observation runs on the existing reader worker once per second;
layout calls remain on the owner thread. Width and scale baselines are kept
for normal disable; RefreshSlotData rebuilds native labels after restoration.
Evidence: .agent-work/picto/evidence/equipped-{card,stat,wrapping}-schema.json
and equipped-stat-values.json. Test11 showed Cheater's four headings separated
from each other and Level; its values remained 3765 / 1452 / 994 / 31%.

Catalog pool slots now use absolute-index modulo pool size. Overlapping rows
keep the same button identity. A one-row scroll changes only two entering
labels and two positions, instead of every pooled row. Tests verify mapping
stability and complete catalog coverage. Increased preloading from 24 entries
with one row above to 32 entries with three rows above and several below.
A 40-entry trial hit the per-mod lease quota (native 401, not dispatched);
it was cleanly unloaded, not retried. Test12 keeps the 256-owner quota intact.
68 targeted Picto tests pass. Test12 live down/up scrolling and selection
mapping passed (Beneficial Contamination selected after row reuse). Large
multi-row jumps can still briefly outrun the preload buffer; an exact 80-ms
end-to-end latency is not claimed. First catalog construction remains lazy.
Test14 normal shutdown restored stock heading text and layout visibly.

Additional live findings: DynamicEntryBox retains inactive stat widgets;
GetNumEntries gives the active count used for compact-card decisions. Stored
WBP_PictoCombatStat_C.StatType can remain stale when a pooled widget is reused
for another stat. Do not relabel a row from that field. The final implementation
preserves native text instead of abbreviating it. WBP_WrappingText_C.UpdateText
is reflected but rejected by native dispatch (205/not dispatched); it is not
used. RefreshSlotData is the verified supported label restoration path.
Test15's final Verso -> Maelle -> Verso check exposed a stale observation:
a native DESCRIPTOR_IDENTITY_CHANGED read failure closes ReadBatch, and the
editor previously kept reusing that closed worker. Test16 added diagnostic
logging and reproduced the failure. Test17 discards failed read-only workers
on their owning thread, clears pending layout observations, and lets the next
poll start a fresh validated read. No failed edit is retried. Two added tests
cover reader disposal and the separate owner-thread failure path (70 pass).
Test17 live verification passed: Verso -> Maelle triggered an actual
DESCRIPTOR_IDENTITY_CHANGED read rejection and recovered on the next read
operation; Maelle's two-stat native headings and current editor selection
returned. Switching back to Verso restored the four compact headings and
Cheater editor values without reloading the controller.
Card layout
observation uses a one-second background cadence, so a native refresh can
briefly show the original spacing before compact formatting reapplies.
No inventory, stats, progression, or saved settings were changed by these UI
checks. Test17 catalog construction after the character roundtrip exposed
unrelated temporary SizeBox objects retained by broad exact-name discovery.
Test18 subsets card observations to equipped rows and metadata, and catalog
construction discovery to metadata, before adopting them into the planner.
This preserves identity validation while excluding unrelated recyclable slots.
Test18 still encountered a catalog identity collision after the roundtrip.
Test19 additionally gives game-owned equipped-card widgets their own SDK
invocation planner, refreshed from each observation. Only metadata is shared
with the owned editor-button planner; volatile card objects are not retained
there. Native identity checks remain mandatory on every invocation.
Test19 still saw an intermittent first-catalog identity rejection. Test20
adds exact previous/incoming identity diagnostics on the fail-closed path.
Test20 passed first catalog creation, ordinary scrolling, normal shutdown,
then a second controller launch with Verso -> Maelle -> Verso followed by
first catalog creation. No rejection was logged in either test20 session.
The earlier intermittent rejection is not proven eliminated; retain the
diagnostic and investigate its precise identities if it recurs.
Installed candidate: picto-catalog-test20, SHA256
a5ad27de4bccbaf2a68d65c199cef70c282250bd329e2ca5192e9df02c8ec363.
# Catalog repair investigation — 2026-10-12

The reported unlock stall was a rejected native operation, not an unacknowledged pending request. Installed controller log at 17:14:50 recorded `picto_inventory` error 1753, outcome 0. The exception escaped the click handler and the outer editor poll changed state to `failed`, explaining why subsequent filter clicks were never processed.

Read-only live evidence in `.agent-work/picto/evidence/catalog-guard-raw-live.json` identifies the exact rejected predicate: `S_jRPG_Item_StaticData.PropertiesSize` is **298** while its aligned `FStructProperty` element width and inventory storage stride are **304**. The final bool is at offset 297. System identity, class package, structure identity, field owner tags, field offsets/types/dimensions all matched. The production guard now compares PropertiesSize to 298; all 304-byte storage checks and other native identity/script/equipment protections remain intact. `native/picto_inventory_schema_fixture.cpp` tests the actual production predicate, rejecting 297, 299, 304 and malformed fields.

Before mutation testing, 27 save files were copied and SHA-256 verified under `.agent-work/picto/backups/catalog-repair-20261012` with a manifest. No save-file write or explicit game-save request is part of the mod.

New SDK pieces: `prepare_ownership(pid)` produces a worker-safe reflected snapshot; `PictoOwnership(scope, snapshot=...)` validates/adopts it on the owning thread. `UnlockTransaction` runs background ownership preflight and postcondition reads, invokes the guarded mutation once, records bounded states, reconciles ambiguous acknowledgements, and never automatically retries a mutation. `BulkUnlockTransaction` operates only on missing verified gameplay rows, reports completed/skipped/failed IDs and supports cancellation after the active operation. The menu requires an explicit second confirmation after displaying the missing count.

Catalog discovery and metadata are cached on the reader worker. Filters use the existing snapshot. The header contains gameplay/owned/locked counts and four filters; the list retains alphabetical ordering and scroll state; the selected details and upper-right editor share definition identity. Per-Picto property drafts are retained while selection changes. Locked entries have no invented inventory level/stats. Effect references and single-passive cost can be read; FText effect descriptions and acquisition information remain explicitly unavailable where the generic reader cannot decode them.

Performance limitation: the existing shared transport requires owner-thread synchronous native dispatch (bounded transport timeout); no supported begin/poll API has been verified by integration. Asynchronous reflection reads do **not** make that dispatch asynchronous. Transaction timings label the combined dispatch/transport duration honestly; native-only execution time is not exposed by the current protocol. Full nonblocking dispatch remains shared-SDK work, and no 80-ms interaction or 2-second complete-editor guarantee is claimed.

Test21 live restart loaded the corrected native build and restored saved Cheater stat/cost overrides before opening Pictos (`restore_ms=1315.7`, full editor enable `3920.9 ms`). It exposed an owner-thread PID access in worker catalog construction; test22 fixes this using the prepared snapshot boundary. Live unlock/layout validation is in progress; these source and restart observations alone do not constitute completion.

### Confirmed live repair checks, through test26

The integration lead verified two real individual unlocks after the 298-byte
schema correction. `AcceleratorHeal` (Accelerating Heal) reached `Unlocked`
at 17:42:29; `AutoPowerful` reached `Unlocked` at 17:58:01. Both had explicit
authoritative ownership readback. The gameplay catalog remained 210 entries;
owned count increased from 188 to 190 and locked count fell from 22 to 20.
These were actual inventory mutations with the verified backup available.
They do not establish inventory persistence across a subsequent game restart.

The controller log records the following transaction measurements, in ms:

| Definition | Ownership preflight | Native dispatch + transport | Verification | Total transaction |
| --- | ---: | ---: | ---: | ---: |
| AcceleratorHeal | 162.92 | 45.37 | 3901.51 | 4109.81 |
| AutoPowerful | 921.73 | 45.87 | 1023.74 | 1991.36 |

These values time the Python transaction phases. Preflight/verification include
worker scheduling and polling delay; dispatch includes native execution,
game-thread scheduling, and synchronous transport. The protocol supplies no
separate native execution clock. Total transaction ends at ownership
verification, before all downstream persistence and UI-refresh work completes.
Do not describe these as input-to-render measurements or native-only timings.

Equipped Cheater removal was rejected with native error **1759, outcome 0**.
The action exception was caught without permanently suspending the editor.
Subsequent live filter checks succeeded: Locked Only (18:04:13), Experimental
(18:05:13), and, after the next controller build, Owned Only (18:13:17).
All Pictos also worked after each successful unlock. Experimental entries
remained separated from normal gameplay unlocking. This verifies a real
guarded failure followed by usable browsing; it does not imply that removing
equipped Pictos is supported. The existing equipment guard is retained.

Measured catalog actions from those sessions:

- Cached selection handler: **60.05–96.63 ms** across logged selections.
- Filter handler: **127.14–207.81 ms** across logged All/Locked/Experimental/
  Owned transitions. These timings exclude subsequent background details reads.
- Original synchronous opening: **10362.01 ms**, including construction.
- Early incremental construction: **93542.56 ms** total wall time with a
  **306.39 ms** maximum construction step; an opening requested before readiness
  waited **36370.01 ms**. A later build recorded **72870.40 ms** construction,
  **270.46 ms** maximum step, and **408.72 ms** opening after controls were ready.
- Catalog reflection snapshot preparation in these sessions:
  **4071.23–5408.68 ms**.

The long incremental-construction wall times show that splitting creation into
steps alone did not meet startup expectations. They include time between mod
polls and must not be reported as continuous native execution. The latest
source adds ModLoader poll diagnostics and a host flag to investigate that
scheduling delay. **Test27 diagnostic validation is pending**; these earlier
measurements do not establish a fix. The 80-ms interaction and two-second
ready-at-mod-launch targets remain unmet or unverified.

Current regression result after diagnostic integration: **929 Python tests
pass** (3.592 s), with workspace TEMP/TMP and isolated localhost test fixtures.
The recorded native baseline contains **66/66 passing fixture executables**;
the separate strict-compile Picto schema fixture validates the corrected
production predicate. Tests cover failed unlock/filter recovery, duplicate and
ambiguous requests, timeout recovery, stale identity, experimental exclusion,
partial bulk failure, draft isolation, source-unavailable Apply rejection,
shutdown reconciliation, and blocking the next bulk dispatch after a settings
write failure. Settings-file roundtrip tests are not substitutes for live
inventory persistence after game restart.

Still requiring live confirmation: game-restart ownership persistence,
confirmed Unlock All Missing completion/partial-recovery behavior, latest
incremental-build timing and diagnostics, and final layout/workflow validation
on the delivered candidate. Bulk throughput has not been measured. FText
effect descriptions and acquisition mappings remain unavailable where the
reader cannot decode or verify them. Source tests and the two individual
unlocks do not satisfy all completion criteria yet.

### Latest verified restart and performance findings — test30

This section supersedes the restart-persistence and diagnostic-pending status
above. A complete game restart changed PID **2404 → 11628**. The installed
bootstrap started the SDK automatically. Read-only snapshots
`.agent-work/picto/evidence/catalog-before-restart.json` and
`.agent-work/picto/evidence/catalog-after-restart.json` confirm:

- The authoritative owned-ID set is exactly equal across restart: **188 Pictos**.
- Cheater and AutoPowerful levels, numerical stats, and all captured stat
  multipliers are exactly equal in the two snapshots.
- The Picto preferences file SHA-256 is unchanged:
  `da872a3fde6c6c979f6aecc36062f05275ee61408376c4ced8436f8abd14b1d1`.
- The user's latest removal choices for `AcceleratorHeal` and
  `LastStandSpeed` remain respected; both are absent. Earlier temporary
  ownership counts of 190 are therefore not the expected restart baseline.

Startup restoration applied saved AutoPowerful ownership, LastStandSpeed
removal, and Cheater multiplier/cost overrides **before Pictos was opened**.
The recorded restoration phase was **2178.4 ms**, with full Picto Editor enable
at **5877.4 ms**. The raw snapshots establish the stated owned-set and
level/stat/multiplier equality; cost restoration is evidenced by the startup
restoration result, rather than a cost field in those snapshots. These checks
verify the mod's configured-state restoration across this complete restart;
they do not establish how every edited field would persist with the mod disabled.

The latest construction measurements are:

| Candidate | Catalog construction wall time | Maximum construction step | Cached metadata snapshot | Open after ready |
| --- | ---: | ---: | ---: | ---: |
| test28 | 26221.91 ms | Not recorded here | Not recorded here | 461.35 ms |
| test30 | 16094.63 ms | 269.17 ms | 4036.12 ms | Not measured in this entry |

Construction wall time includes scheduling between polls. The decrease from
26.22 s to 16.09 s is a measured improvement, but **the two-second complete
startup target and 80-ms interaction target remain unmet**. A ready-open
measurement is not first-use construction latency, and snapshot preparation
is not a filter-switch measurement. Shared poll diagnostics and persistent
readers reduce avoidable work without caching live identities or weakening
lifecycle checks. The existing owner-thread synchronous mutation transport
still does not meet the requested fully nonblocking dispatch requirement.

The live **Unlock All Missing** preview displayed **22** missing normal
gameplay Pictos. Cancel was verified without an ownership mutation. A user
decision about a live partial bulk test is pending; no live bulk completion,
partial-recovery result, or bulk-throughput number is claimed. Unit coverage
of partial failure remains distinct from that outstanding live validation.
The broader catalog repair is therefore not declared complete by these
restart and performance results alone.

### Bulk removal scope and implementation — test32 candidate

The user explicitly expanded Bulk Management to include **Remove All** alongside
Unlock All Missing. The implementation reuses the guarded ownership transaction:
`UnlockTransaction(..., desired=False)` dispatches the stock
`RemoveItemFromInventory` operation with expected ownership 1 and requested
ownership 0. It reports `Removing`, `Removed`, and `Already Absent`; success
requires a fresh authoritative inventory read confirming absence. Unlocking
retains its existing default behavior and states.

Bulk removal snapshots only currently owned, verified normal gameplay Pictos.
Experimental definitions remain excluded. The menu presents the removal count
and requires confirmation; Cancel stops remaining operations while allowing an
already-dispatched operation to finish verification. The native equipment guard
is unchanged: error **1759** protects equipped Pictos, records that item as a
failed removal with an actionable explanation, and permits the bulk operation
to continue with other items. No equipment references are cleared or rewritten
as part of removal. Consequently, Remove All can finish with protected failures;
it does not promise to remove equipped Pictos.

A persisted ownership value of `false` is written only after absence is verified.
Existing per-Picto overrides are preserved rather than discarded when ownership
changes. Duplicate requests, ambiguous acknowledgements, timeouts, and cancellation
retain the same no-blind-retry rules as unlocking. Shutdown reconciliation must
compare the verified membership state with the requested ownership value for
both directions.

The current Python regression suite reports **953 passing tests**, including
removal readback, duplicate/no-op behavior, ambiguous-response reconciliation,
protected-item partial failure, cancellation, and experimental exclusion.
**Test32 live bulk-management validation is pending**; these source-level results
do not establish live bulk throughput or successful completion of every requested
workflow.

### Shared polling measurements — test31

Live diagnostics after Flight discovery moved to its background path show
`mod.Flight` consuming **less than 0.1 ms total across 30 polls**. Measured whole-host
poll windows averaged **124–130 ms**, with maxima around **160 ms**. Latest idle
observations attributed approximately **100 ms outside Picto** and **16 ms to
Picto**. These aggregate poll measurements are not click-to-render latency and
must not be presented as proof of an 80-ms interaction target.

This removes a measured shared polling bottleneck, but existing native batch
transport still performs synchronous owner-thread calls. Background discovery
and faster polling do not provide a nonblocking native mutation API. The earlier
two-second startup and 80-ms interaction requirements remain unmet on the recorded
measurements, and live test32 validation remains outstanding.

### Frame-paced ownership queue (2026-10-12, test33)

Bulk add/remove now has an optional native `picto_batch_protocol=1` path. Python performs one authoritative ownership preflight, submits up to 342 unique asset identities in one bounded packet, polls progress, and reconciles inventory once at completion/cancellation. Confirmed ownership overrides are saved atomically together; stock panel refresh happens once. Older runtimes retain the sequential fallback.

The live reflected `/Script/Engine.KismetSystemLibrary:GetFrameCount` has `Int64Property ReturnValue` at offset 0, parameter size 8, native entry RVA `0x384e0d0`. Its exact 30-byte thunk reads the counter at RVA `0x9272d10`. Read-only live samples advanced 95010 through 95025 in 224 ms; evidence is `.agent-work/picto/evidence/engine-frame-counter.json`. The native queue verifies this thunk and records an increasing actual frame counter for each attempted mutation. Multiple Windows messages in the same frame cannot advance it twice. A bounded Windows timer wakes the existing game-thread message hook; timer duration is not used as a substitute for engine progress. Scheduling is at most one item per engine frame; it can skip frames if the message pump is delayed.

Each item retains all existing stock inventory operation guards (including identities, scripts, equipment and post-dispatch ownership), and failures do not prevent later entries. Queue tokens and scope owners protect status/cancel; duplicate assets and dirty request fields are rejected. Cancellation and controller close stop remaining work. Invalid lifetime, counter rollback, changed thunk, or 60-second timeout stops the native queue. Start is never retried after an ambiguous reply.

Native fixture validates same-frame suppression, increasing frame stamps, protected-item continuation, cancellation, owner mismatch, terminal context, timeout, timer failure, and byte-signature mismatch. Test33 compiles with /W4 /WX.

#### Live validation and readback repair (test34/test35)

PID 20344 loaded the new native runtime after a normal game restart. The first removal attempted 197 entries in 5,269.19 ms: 184 removed and 13 equipped entries protected. The first addition reached all 210 normal gameplay definitions, but final verification rejected recycled object identities from the old catalog. That run was not a successful end-to-end transaction. Ownership refresh now rediscovers the inventory catalog before reading its items; the final stock panel refresh resolves CurrentCharacterData even when the editor has no selected item.

The corrected live UI retest removed 197 of 210 entries in **8,509.45 ms**, preserving all 13 equipped entries. It recorded 210 distinct increasing engine frames across 280 frames. The stock list immediately showed only those 13 entries. Unlock All then added all 197 missing entries in **12,146.62 ms**, with no failures or readback error, across 197 distinct engine frames spanning 251 frames. These elapsed measurements include preflight, final verification, preferences and UI work; they are not native mutation-only timings. One mutation per actual frame is an upper bound, not a promise that every frame is used.

Independent live reads confirmed 13 then 210 owned definitions. Every confirmed addition had `owned=true` in SDK preferences. Cheater remained level 33 with Health 3765, Speed 1452, Defense 994 and Critical Rate 31 throughout. No save files were edited. Evidence: `.agent-work/picto/evidence/frame-batch-live.json`, `frame-batch-fixed-removed.json`, and `frame-batch-fixed-added.json`.

The final suite passes **962 Python tests** plus the native production-header fixture. Test35 also skips unchanged ownership profiles during startup restoration, avoiding an inventory rediscovery for every saved membership; this optimization has regression coverage but no separate timed startup validation yet. The earlier two-second startup and 80-ms interaction targets remain unproven. Native cancellation has fixture coverage; a live mid-queue cancellation of this new path remains a follow-up.

### Mass-level discovery repair (test36)

The 19:17:09 live failure happened before the mass-level job was created: the general menu discovery enumerated transient passive/item instances and exceeded the native `MATCH_RESULT_LIMIT`. This also closed the shared Picto read worker. Progression operations now discover only their required functions, schema types, character/game-instance roots and inventory system. Actual items come from the authoritative inventory map. Menu warmup likewise avoids enumerating transient item/passive instances. Live read-only verification returned 679 progression catalog objects with all 210 owned Pictos and succeeded on subsequent menu discovery.

Post-unlock override restoration now builds fresh progression dependencies instead of merging new inventory objects into a planner catalog containing recycled object slots. Test36 was installed; clean controller shutdown was coordinated after Picto-only reload encountered the already-failed worker. The game itself remained running. Startup restoration succeeded in 5,432.6 ms (inventory portion 1,830.3 ms), still above the earlier two-second target. All 964 Python tests pass. Full mass-level button validation remains pending menu access at this checkpoint.

### Frame-paced mass leveling and current-menu refresh (test38)

Test37 confirmed the earlier discovery repair with 210/210 successful level changes. It also isolates failures from obsolete selection-read futures so they cannot prevent fresh bulk preflight. Its per-item Python progression loop was still slow and only refreshed equipped cards.

Test38 extends the existing native frame queue with level mode (`desired=2`, target 1..33 in the reserved word), gated by `picto_level_batch_protocol=1`. Each owned item identity and inventory membership is revalidated on the game thread before invoking the verified ChangeLevel function. At most one item runs per actual engine frame. A final authoritative inventory read verifies every completed level; confirmed levels are persisted in one preferences write. Character equipment stats are recalculated once per character and the current stock panel calls LoadCharacter, rebuilding its list without leaving the page.

Live PID 30292 validation on 2026-10-12: 210/210 Pictos changed from level 26 to 33 in **5,549.94 ms**, then 210/210 changed back to 26 in **5,434.45 ms**. Both runs had zero failures, 210 distinct recorded mutation frames, and no batch error. These timings include queue preflight, verification, persistence and final menu refresh. The visible stock list, equipped cards and character stats refreshed in the same open menu. Independent readback confirmed all 210 owned items and all 210 saved level overrides at **26**. Evidence: `.agent-work/picto/evidence/frame-level-test38.json`.

Validation: 969 Python tests, native frame-queue fixture, and release native build passed. Installed package: `dist/picto-catalog-test38/Expedition33-SDK-0.1.0-rc4-picto-catalog-test38.zip`, SHA256 `abefc63f41553b0eb84319b02d4b47fd6ba5b5d641b20f8fad62c646de4cc541`. No save files were directly edited. The two-second startup and 80-ms interaction goals are still unmet; this restart logged 6,316.6 ms restoration and 9,587.7 ms total Picto enable time. Startup restoration while a menu is already open can still leave preexisting stock UI values stale until refresh; this is separate from the now-verified mass-level completion refresh. The Lumina list still showed Cheater's original cost 40 while its equipped card showed configured cost 2 after startup; retain this as a startup UI refresh follow-up.

### Clearing saved Picto overrides (test40)

The editor adds Clear all saved changes for the selected definition and the Tools page adds Clear Picto Changes for all saved definitions, including experimental/unowned profiles. A second click confirms, bound to the selected definition and scope. Active property/ownership batches block clearing. The operation atomically removes SDK profiles with the existing SettingsStore revision guard; pending restore entries and drafts are discarded only after successful persistence. It does not mutate live game objects, undo progression in game saves, or invent original levels/mastery/ownership baselines. Other mods' settings are retained. Current runtime overrides may remain until reload, and game-saved progression may survive it.

972 regression tests pass, covering per-definition/all clearing, stale-writer failure preserving both memory and disk, selection-bound confirmation, and busy-batch rejection. Live mod-only reload succeeded; the new native button and confirmation were observed without clearing the user's configuration during automated testing.

### Pre-override baseline capture and live Clear restoration (test41)

Supersedes test40's saved-only Clear semantics. User clarified that Clear must visibly undo edits and requested a record of values before startup overrides. `picto_baselines.py` writes `SDK/settings/picto-baselines.json` through atomic, revision-guarded SettingsStore before invoking startup restoration. It records 342 definition identities, ownership, owned-item levels, four multipliers (including absent stats as zero), Lumina costs, mastery flags and exact mastery steps, plus PID, UTC timestamp and provenance. Same-PID mod/controller reloads reuse the record instead of replacing it with modified values. Clear restores that snapshot with guarded SDK operations before removing saved overrides; missing baselines report an error rather than claiming success. The generic restore path supports the baseline's exact mastery step count.

Coordinated cold restart PID25084 captured 342 definitions at 2026-10-13T00:07:48Z before overrides. Cheater baseline: owned, level33, Health0.6/Defense0/Speed1/Crit0 multipliers, cost40, mastered. These are values loaded from the current save; this cannot recover historical level/mastery/ownership changes already saved by the game. This record is a pre-SDK-override baseline, not a factory-default or original-save claim. Save-slot changes within the same process and newly acquired Picto acquisition baselines need further handling; restart after changing saves before relying on Clear. Current file plus SettingsStore backup is retained, not an unlimited edit history.

974 tests passed. Test41 archive SHA256 d754dfe32333c77bae2739de9a7593735e82f3a65268e13a569ee6ae425c38cc. Startup restore including baseline capture measured7590.5ms and full enable10613.4ms; earlier startup latency targets remain unmet. Live Clear UI validation is pending the Pictos menu at this checkpoint.

### Clear readback and stable status text (test42)

User manually confirmed Cheater Clear and reported success. Independent PID25084 readback confirmed Health2636/multiplier0.7 returned to Health2259/multiplier0.6, with Speed764, level33 and 210 owned entries preserved. Evidence: `.agent-work/picto/evidence/baseline-before-clear.json` and `baseline-after-manual-clear.json`. Current menu also shows the restored Health2259 and cost40.

Fixed competing status writes during a paint: queuing the default before the result could bypass the result through the previous-frame text cache and alternate visible messages. Status is now selected once. Idle has no message; pending changes say select Apply; successful Clear says Starting values restored. All 37 editor-control tests pass, including repeated refresh single-write coverage. Installed and hot-reloaded PictoEditor only; no shared controller restart or native changes. Package: `dist/picto-status-test42/PictoEditor.sdkmod`, SHA256 `75f83f2761e7ba5436a5a8dbc3f441297693013d88fc438f36c5872352149b28`. Live idle display verified. Mod reload took12149.11ms; startup performance target remains unmet.

### Exact stat membership and disable rollback (test43/test44)

The user's zero-stat card report was a real data-shape defect: SetCurrentStatValue(0) retained the map key. Baseline schema2 records `stat_keys` and `multiplier_keys` separately from numerical multipliers. Cheater's fresh PID27624 snapshot captured CurrentStats keys1,8 and multiplier keys1,6,8,9 before configured overrides. Old same-process schema1 snapshots cannot prove original membership and fail exact restoration with a restart-required message rather than guessing.

Live native reflection identified `/Script/Engine.BlueprintMapLibrary:Map_Remove`, entry RVA0x34cc740. Its ordinary-map removal calls the engine FScriptMapHelper removal helper0x1356870 with a 56-byte helper and captured helper/index/count tuple. Read-only disassembly evidence: `.agent-work/picto/evidence/native-34cc740.json` and `native-1356870.json`. New Picto progression op12 is restricted to CurrentStats or BaseStatsMultipliers on verified Picto item instances and supported stat keys. It requires both current value and multiplier to be zero/absent, validates map schema and bounded hash chains, verifies the exact415-byte helper signature, invokes on the existing game thread, and reads back absence. Engine removal maintains hash chains and free lists; there are no direct map memory writes. Protocol capability is `picto_stat_remove_protocol=1`.

Clear uses this operation to remove only keys absent from the recorded baseline; legitimate original zero-valued entries remain. Mod.disable now reconciles pending mutations, restores configured fields to baseline, refreshes the stock panel, then detaches and releases resources. Saved profiles remain intact for re-enable. Restoration errors are reported through mod-disable diagnostics while cleanup proceeds; there is no automatic retry of an uncertain mutation. Ownership removals occur after restoring an item's cost/mastery. Equipped new items remain subject to existing removal protection; that case can prevent complete rollback and is not claimed as verified. Save-slot switching and changes already persisted by the game retain the baseline limitations documented above. Restoring shared cost/mastery after an edited item has already been removed is also not verified and requires further handling.

Live test43 disabled successfully after restoring Cheater from Health10919/Speed3820/Defense10437/Crit103 to Health2259/Speed764 with Defense/Crit absent. The visible stock card contained only Health and Speed. Independent readback confirmed exact CurrentStats membership and unchanged210 ownership. Settings SHA256 stayed87b827dc8f89780a45555fed2d722aa5c31e48e77884e13511d9524bacd6823a. Re-enable restored all four configured stats. Test43 unnecessarily restored every baseline field on210 saved bulk-level profiles and took59528.78ms total. Test44 restricts rollback to configured fields (full baseline when reversing ownership), reducing measured restore time to3778.6ms and total disable to11246.03ms. Repeated disable/re-enable succeeded in the open Pictos menu. Last re-enable7977.04ms; the two-second and80-ms targets remain unmet.

Evidence: `stat-membership-before-disable.json`, `stat-membership-after-disable.json`, `stat-membership-reenabled.json` under `.agent-work/picto/evidence`. 981 Python tests pass plus native hash-chain/packet fixtures and release build /W4 /WX. Installed final Picto mod is test44; native runtime is identical to test43. Final ZIP `dist/picto-catalog-test44/Expedition33-SDK-0.1.0-rc4-picto-catalog-test44.zip`, SHA256803a0a81ba6838392724fea08d0f420a58b074e19826ee1cce0d845204778e7d. Direct Clear-button retest after native upgrade remains separate; its shared restoration routine is verified live through disable. Game left in Pictos with mod enabled and user configuration intact.

## Frame-paced Master All / Unmaster All - test46 (2026-10-12)

Both controls are installed in Picto Tools. They snapshot currently owned Pictos,
skip matching states, submit one native queue, and reconcile once before saving
confirmed results. Unmaster resets partial learnt steps as well as the learnt
flag. Neither action grants experimental definitions.

Protocol 122 retains its 11048-byte v1 layout. New capability
`picto_mastery_batch_protocol=1` enables desired=3 with reserved=0/1. Dependencies
are BP_CharacterData_C, SetPassiveEffectSharedProgression, DT_PassiveEffects, and
BP_jRPG_GI_Custom_C. Entries are actual owned Picto instances. Each frame tick
revalidates ownership through GI.InventorySystem (ObjectProperty offset 3296,
BP_ItemUpgradeSystem_C), reads shared progression, and calls guarded operation 5.
A factored passive-table lookup supplies each row's LuminaUnlockStepsCount;
no assumed battle count. Native completion checks learnt flag and steps.
Identity, lifetime, cancellation and frame-source guards remain. Older runtimes
retain the slower per-item fallback, now supporting unmastering too.

Live PID 38684 after coordinated restart: 210 owned, 174 initially mastered.
Unmaster All: 174 mutations in 174 engine frames, 36 skipped, 0 failures,
5644.98ms including verification/menu refresh. All 210 read back learnt=false and
steps=0. Master All: 210 mutations in 211 frames, 0 failures, 5529.59ms; all 210
read back learnt=true. Every mutation frame strictly increased. The stock list
and equipped-card mastery colors refreshed without changing pages. Ownership,
representative stats and all non-mastery saved settings were unchanged. Final
live and persisted state is all 210 mastered. Evidence:
`.agent-work/picto/evidence/mastery-batch-` before, restarted, unmastered,
mastered and timing JSON files.

Validation: 986 Python tests passed; native frame queue fixture passed for both
mastery targets, frame gating and failure handling; release runtime/reader
compiled with /W4 /WX. Inventory schema addition separately tested and live-read
verified. Installed candidate:
`dist/picto-catalog-test46/Expedition33-SDK-0.1.0-rc4-picto-catalog-test46.zip`.
SHA256: `df4ff4a12093bae1e717842b2e592844d71680f4316ac3e9254f0f8433c549c1`.

Remaining limitation: startup restoration still uses the previous per-item path.
This restart restored 15 saved mastery overrides in 13.8s, total Picto enable
20.4s. The frame upgrade here covers interactive bulk buttons only and does not
satisfy the earlier two-second startup target. Read-only selection observations
can defer on map-change guards during a batch; final reconciliation succeeded.
Next step: extend queued restoration to startup/disable with mixed targets and
baseline identity guards. No Cinematics-specific files changed.

### Startup restoration batch integration — test50, 2026-10-12

Supersedes the startup limitation above: saved level/mastery mismatches now use
the existing bounded native frame batch, grouped by target value. Matching values
are skipped; explicit partial mastery baseline rollback retains its previous path.
Batch failures do not fall back to duplicate per-item mutations. Ownership changes,
costs and multiplier edits retain their guarded paths. No native guards changed.
Baseline capture reads canonical definition rows and projected inventory/mastery
fields rather than preparing grant assets. UI discovery follows restoration.

Normal game exit/relaunch and existing-save load, PID 7760, installed test50:

| Measurement | Recorded previous test46 | Final test50 |
| --- | ---: | ---: |
| Restore operation | 13.8 s (15 mastery changes) | 1.183 s (51 mastery changes) |
| Native batch portion | not used | 1.004 s, one group |
| Baseline plus restoration, settings ready | not separately recorded | 2.986 s |
| Full Picto enable including UI | 20.4 s | 7.254 s |

These are individual live runs, not controlled benchmark distributions. Test49
also passed: restore 1.121 s, settings ready 3.032 s, full enable 6.099 s.
Two-second full startup is NOT achieved; UI construction remains about 3–4 s.
Timing begins at Picto enable, excludes game loading and earlier mods.

Independent readback confirmed 210 owned/210 mastered, representative level-33
stats/multipliers unchanged, and identical saved-settings SHA256. All 342 baseline
profiles and exact mastery steps matched the test48 snapshot from the same save.
Current startup live exercise changed mastery only; grouped level startup is
unit-tested, not independently exercised with mismatching levels in this run.
990 Python regression tests passed. Existing exact-partial-mastery rollback range
limitation was not changed by this optimization.

Evidence: `.agent-work/picto/evidence/startup-test50.json`,
`startup-test50-timings.json`, `startup-test50-baseline.json`, `startup-test50.log`.
Installed package: `dist/picto-startup-test50/Expedition33-SDK-0.1.0-rc4-picto-startup-test50.zip`.
SHA256: `6cc84ee033494b3ef46dd18c07dd6aa7ccbc8921e9173410fb06b81449e3e7e0`.
