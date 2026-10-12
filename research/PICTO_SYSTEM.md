# Picto / Lumina system research

Status: **live stats, level, shared mastery and Lumina cost editing; full lifecycle coverage incomplete** (2026-10-12).## Installable SDK release preparation (2026-10-12)PictoEditor now imports canonical `expedition33` modules instead of loading`.agent-work/picto` modules by filename. Typed map reading, bounded referenceclosure capture, class asset loading, progression/cost transport and preferenceshave been promoted into `src/expedition33`. Native Picto guards and the map-capablereader have been promoted into `native`; Cinematics-specific files are untouched.`expedition33.paths` resolves SDK settings/logs independently of the mod cache.Picto overrides remain `SDK/settings/picto-editor.json`, keyed by stable Pictodefinition ID. They must never be included in the release ZIP. The standalonereader is expected at `SDK/build/readonly-worker/research_probe.exe`.`scripts/package_mods.py` creates all current mod folders as reproducible`.sdkmod` ZIP archives with root `mod.py` and resources, validates each output,and writes a hash manifest. It neither imports mods nor changes the running game.Initial output: `dist/mod-payload-rc1/SDK_Mods`, 11 archives including Cinematicscatalog data. Integration owns archive materialization, automatic game startup,final RC assembly and coordinated launch validation. Archive conversion alone isnot evidence that game-load bootstrap has passed.The integration lead subsequently assembled`dist/installable-rc1/Expedition33-SDK-0.1.0-rc1.zip` (13,493,540 bytes;SHA-256 `cff0a975e69188044d3f77b0097ae9a498a4f15d510b2d6435df4606944888f1`).Independent checks verified all 155 archive files, the SDK and bootstrap hashes,11 mod archives, and absence of settings, logs, saves and development-tree files.The bundled interpreter's offline integrity check passed after extraction to adifferent directory containing spaces. All 11 mods then imported using only thatrelocated SDK; PictoEditor constructed without engine access and resolved itspreferences and reader paths within the relocated installation.An integration test verifies saved enabled and disabled choices across archivereplacement and cache rebuilding, with unchanged settings bytes. Three Windowsversion-information API forwarding checks matched the system DLL in an isolatednon-game process. These are offline checks, not a live automatic-start result.RC3 supersedes that initial artifact:`dist/installable-rc3/Expedition33-SDK-0.1.0-rc3.zip`, SHA-256`d1ac0f27ea988a2e0d545ab39475c17fd3bf8efa4c44d9784950003737dcb74d`.All 157 files passed the same independent relocation/integrity checks. Liveintegration testing launched through the normal Steam launcher, automaticallystarted the installed host and reached `SDK ready` for PID22944 after loadingthe save. The installed controller log confirms the native Mods pause entryattached. Startup now resolves the current Pawn reference explicitly, supportsthe mounted world-map character and waits through a valid idle title screen.Flight remains enabled while waiting for a supported dismounted character.Visual menu verification and post-restart Picto reapplication remain separatechecks; do not infer them merely from controller readiness.## Restart repair, persistence and menu construction (v0.5 / native v4)The user restarted the game (PID14868) and reported disabled level/mastery/costcontrols. The current host was the v65 Cinematics launcher, which did not exposePicto protocols. Independently, the older Picto v3 admission profiles embeddedPID13448 addresses and raw pointer-bearing Blueprint bytecode. Both issues areaddressed in the isolated v4 runtime. Historical addresses below are evidence,not reusable selectors.Seven original functions now use typed symbolic operand profiles: ChangeLevel,SetPassiveEffectSharedProgression, RefreshUsedLuminaPointsInternal,SetBaseStatsMultiplier, RefreshCurrentGearStats, UpdateEquipmentStats andRefreshSlotData. A strict token walk identifies 933 reference operands. Everyremaining byte matches the previously exercised scripts from the earlier gameprocess. Runtime checks validate registered object outer chains, field ownership,types, offsets, widths, flags, dimensions, target types, names and function shape.Existing expected-value, active-panel, owner and identity checks remain intact.Unknown bytecode/schema changes reject; this is not arbitrary Blueprint admission.The native read-only validator passed all seven profiles in the new process andrejected simulated bytecode and parameter-schema changes for each.The coordinated v65 shutdown released all inspected public/private leases andnative ownership. Loaded v4 PDB: `169fad84-d383-47d5-8691-93fa5c818728`, age10.The user subsequently verified Lumina cost editing works. Level no-op dispatchalso succeeded. Mastery accepts an existing nonnegative int32 progression count(e.g.246) while the requested target remains bounded0..100; large accumulatedprogress no longer prevents Reset/Master. The diagnostic no-op skips targetcounts above100 instead of changing them.### Saved overrides`settings/picto-editor.json` uses the existing SDK `SettingsStore` (versioned,atomic replacement, backup recovery, corrupt-input preservation, stale-writerrejection). The mod-owned record is `sdk.picto-editor`, with options schema1 anda `pictos` map keyed by reflected `ItemDefinitionID`. Only explicitly appliedfields are recorded: stat multipliers for keys1/6/8/9, level, cost, and booleanshared mastery. No object addresses, registry indices or save-file data are stored.An acknowledged edit is saved before secondary UI updates, so a repaint failuredoes not silently discard the preference. A newer user Apply supersedes a queuedrestore for the same field.On mod/controller startup, overrides are queued and restored when an active stockPictos panel and a valid character are available. This first version thereforerequires opening the Pictos menu after a game load; it does not mutate during thetitle screen or force the menu open. Each field is freshly resolved and compared;matching values are skipped. Missing owned Pictos leave their file entries intact.Uncertain or failed writes stop restoration with diagnostics and no blind retry.Restoration does not call game save/progression-save functions.Live evidence: user-applied Cheater cost35 was written at configuration revision1.Repeated mod reloads read that file and completed the queue without errors. Thebounded `picto.verify_saved_restore` diagnostic changed35→34, reconstructed thequeue from a newly opened settings store, and restored35. All26 `.sav` hashes wereidentical before/after. Evidence: `.agent-work/picto/evidence/v4-saved-cost-restore.json`.This verifies active cost reapplication and mod reloads; another full game restart,automatic stat reapplication after that restart, and travel/disconnect lifecyclecoverage remain pending. Pre-v0.5 choices already lost during a restart cannot bereconstructed safely from final derived stat totals; apply those choices again.### Launch and enabled preferencesThe integration lead confirmed that `Registry.set_enabled` persisted preferencescorrectly, but candidate hosts force-enabled bootstrap lists and omitted`restore_enabled()`. Picto hosts now respect explicit disabled choices, bootstrapprotected core mods, and restore saved enabled mods outside a shared read batch.Failures are reported per mod. One saved Flight mod failed to restore because nolocally possessed exploration character was available in the menu; other modscontinued loading, and its desired enabled preference was retained.The lead added `launch-sdk.cmd` selecting combined Cinematics/Picto v4 and made`launch-cinematics.cmd` delegate to it. `launch-picto.cmd` is an alias for the samecanonical entrypoint. The checkout's `.agent-work/picto` support files and v4build outputs remain required; this is not yet a standalone distribution.### Menu latencyConstruction now uses bounded targeted catalogs, operation-scoped readers,existing layout batching, and background inventory indexing. Layout argumentsare prepared only when a batch is ready because subsequent object creationrevokes earlier prepared plans. Nested stored references are captured usingidentity-validated selected catalogs instead of requiring the full game registry.Measured v4 initial construction:11,639.9ms, including6,770ms full catalog and1,395.9ms synchronous inventory indexing. After consolidation:5,470.5ms total,2,240.4ms targeted discovery,0.2ms foreground inventory setup,3,165.5ms widgetcreation. Inventory reading runs afterward on the observation worker. Timingsvary with foreground/background game state. Full selection reads still takeabout640ms; the80ms end-to-end target is **not met**. Next work should add a narrowselected-field reader and further reduce widget construction dispatches; do notweaken identity checks or reuse plans across menu/world lifetimes for speed.Validation: four preference tests, seven control tests, cross-process bytecodenormalization tests, native protocol fixtures, live profile rejection checks,successful menu attachment and saved cost reapplication. Five-extra-hit effectediting is paused under the user's performance/persistence pivot.## Current cost and progression update (v0.4)This section supersedes historical unsupported-feature statements below. Theuser verified functional cost changes everywhere; the compact bottom-right listretained stale cost text until changing page. A targeted UI refresh now runs aftercost Apply using existing TextBlock.SetText, without navigating or changing saves.Live invocation refreshed five stock labels successfully; a subsequent screenshotconfirmed editor, equipped card and compact row all showed the user's currentCheater cost30. The attempted computer-use Apply-path check stopped when the tooldetected concurrent user input; that end-to-end button check remains uncompleted.| Verified owner | Mapping || --- | --- || DT_PassiveEffects | `/Game/Gameplay/Lumina/DT_PassiveEffects.DT_PassiveEffects`; index68215 serial0 address2942671603584 || DataTable row map | Virtual accessor slot0x2d8 contains `48 8d 41 30 c3`, returning object+48. DoesDataTableRowExist RVA0x367f9d0 confirms 24-byte entries: Name+0, row pointer+8. Read-only validation found657 occupied rows. || FPassiveEffect | Extent72; `LuminaCost_15_BC10A93D48987A14F96279AC521E94CF` IntProperty+48; original observed costs1..40 || BP_PassiveEffectInstance_C | PassiveEffectID Name+48; PassiveDefinition Struct+56; OwnerData Object+128. Definitions are cached copies. || BP_CharacterData_C | CurrentlyUsedLuminaPoints Int+556; original RefreshUsedLuminaPointsInternal function79704/9856, address0x2adfcce6980, extent484 and2338-byte script || BP_jRPG_GI_Custom_C | SharedPassiveEffectProgression Name-to-Struct map+3816 is shared mastery authority. Character-local progression is not authoritative. || FPassiveEffectProgression | IsLearnt Bool+8; LearntSteps Int+12 || WBP_GM_COV_LuminaElement_C | LuminaCost CommonTextBlock+792; PassiveEffectInstance Object+832 || WBP_GM_LuminaPoints_C | UsedPoints CommonTextBlock+760; MaxPoints+744 |Native cost operation3 uses the existing isolated progression envelope andgame-thread transport. It checks object identities, active panel/current character,passive owner, row schema/accessor, occupied row identity, expected old cost andall matching cached copies before writing. It changes the four-byte table costand cached definitions, then calls original spent-point recalculation for loadedcharacters. UI range0..100; changes affect all characters. No save call is made.These runtime data-table edits remain until the game process ends; automaticrestoration on mod disable is not implemented.Evidence: `.agent-work/picto/evidence/cost-table-live.json`,`table-layout-native.json`, `cost-character-functions.json`, `cost-scripts.json`,`lumina-compact-fields.json`, `lumina-ui-fields.json`, `picto-v3-loaded.json`.Corrected v3 loaded PDB: c8739c6e-4303-4015-a8f1-2f476600f9eb age6. An initialbuild-script source-path mistake loaded v2; its cost request was rejected withoutcome0, then the source path was corrected and exact loaded PDB verified.A later automated round-trip also failed preflight1721 before writing. Usersubsequently tested successfully; status observed cost27 and Apply1903.7ms.Do not describe the rejected automated round-trips as successful validation.Seven editor control tests and native request fixtures pass. Local drafts areabout13ms; observation is about650-700ms. The requested80ms complete update targetis not achieved. New-process compatibility and zone transitions remain untested.Combo Attack III resolves to BP_LU_ComboAttackC_C inheriting BP_LU_ComboAttackA_C;the extra-hit count has not been proven to be an editable scalar.### Combo Attack count research (after cost acceptance)User confirmed the cost UI now works and requested effect counts in the editor.Retained class loading succeeded for BP_LU_ComboAttackC_C, observed217347/554082at0x2ae5a20c480; parent BP_LU_ComboAttackA_C223930/554078 at0x2aeed90ac00.No gameplay effect was activated by this research.`DT_Balancing_Luminas` at`/Game/Gameplay/Battle/ScalingSystem/BalancingTables/Content/DT_Balancing_Luminas`has row type `S_BalancingTableFloatEntry`, extent8, with DoubleProperty`FloatValue_3_9D7EBC84471861D83D95EC8FC8B0C998` at0.Rows `ComboAttack1_AttackAmountAdded`, `ComboAttack2_attackAmountAdded` and`ComboAttack3_attackAmountAdded` all read1.0. Their names alone do not prove thatthe matching Picto consumes each row.The live727-byte inherited ComboAttackA event graph reads the ComboAttack2 rowat name-constant offsets66 and129, and ComboAttack1 at365. It selects a truncatedinteger using LuminaId (IntProperty+352), adds it to the battle character'sBaseAttackNumber (IntProperty+3936), and clamps that accumulator to0..4.The observed A and C default objects both report LuminaId0; runtime-instanceselection remains unverified. The apparent duplicate row reference must not besilently treated as a verified independent ComboAttack3 mapping.The battle actor event graph is65649 bytes, beyond the old describe-script64KiBlimit. A bounded read-only chunked export verified a stable script header. ItsBaseAttackNumber selector has explicit cases0..3 selecting Attackx1Sequence(array+4728), Attackx2Sequence(Object+4744), Attackx3Sequence(+4752), andAttackx4Sequence(+4760). Thus merely writing5 into a balancing row does not provefive extra hits: both accumulator clamping and attack-sequence selection needattention. No supported six-hit sequence path has been established.Evidence: `combo-inherited-live-retained.json`, `combo-scripts.json`,`combo-balance-schema.json`, `combo-parameters-live.json`,`combo-battle-graph-native.json`. First proposed experiment: observe the actualComboAttackC instance in battle, prove its row selector, then test a reversiblecount increase within an existing sequence. No count write or combat activationhas been performed. The user was asked to enter a battle and wait before attackingso these runtime identities can be inspected without autonomously progressing combat.Live battle follow-up: `combo-runtime-actors-check2.json` contains85 reflectedobjects with0 read errors. Verso actor275607/628670 has BaseAttackNumber3 andthe genuine Attackx1/x2/x3/x4 LevelSequence references. Active buff C117890at2948687822208 reports LuminaId0; B117893 reports1; A117896 reports0. Allthree target Verso stats275624/628673. This confirms that changing theComboAttack1 balancing row alone would change both A and C behavior; merelyediting the unused ComboAttack3 row is not a verified per-Picto implementation.The accumulator is a bonus-hit selector:0 selects x1,1 selects x2,2 selects x3,and3 selects x4. The clamp maximum4 is not evidence for a fifth/sixth attack path.No count, actor property, bytecode, attack sequence or buff state was mutated,and no combat action was selected. User can leave the battle without waiting foran agent-triggered attack; the necessary read-only snapshot is captured.Required implementation before enabling an effect-count control:1. Add a distinct per-Picto override mapping keyed by verified passive ID and   actual effect class, with compare-before-write and owned cleanup. Do not expose   shared row writes as independent Picto controls.2. Validate total extra counts against the existing0..3 sequence selector for a   bounded first experiment. Stacking with the other two Combo effects matters.3. Five extra hits means six total. Author or verify a six-hit execution route   preserving damage, AP gain, timing and turn completion before advertising5.   Increasing only the table value or clamp does not satisfy this requirement.4. Integrate the verified adapter as an `Extra hits` row alongside level/cost/   mastery. Do not present an enabled control that merely edits unused metadata.Effect-count editing remains unimplemented; the current cost/stat editor is leftenabled. This is a verified limitation, not a claim that arbitrary additional hitsare impossible with a larger runtime combat adapter.Earlier sections below retain the history of initial read-only research.

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
