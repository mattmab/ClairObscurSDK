#include "session_protocol.h"
#include "fixed_invocation.h"
#include "observer_core.h"
#include "console_attachment.h"
#ifdef E33_TRACE_SESSION
#include "target_trace_registry.h"
static e33_trace::Registry<TargetTraceOps> session_traces;
static uint32_t trace_cleanup_error = 0;
static bool session_trace_entry(uint64_t address, uint64_t expected, uint64_t current) {
    return session_traces.allows_entry(address, expected, current);
}
static const CallEntryValidation trace_entry_validation{session_trace_entry};
#define E33_TRACE_ENTRY_VALIDATION (&trace_entry_validation)
#else
#define E33_TRACE_ENTRY_VALIDATION nullptr
#endif
#ifdef E33_POD_SESSION
#include "target_pod_schema.h"
static bool validate_target_pod(uint64_t base,uint64_t property,PodValueKind kind,const CallIdentity& id) {
    TargetPodSchemaOps ops{base};
    return validate_pod_parameter(ops,property,kind,id);
}
static const CallPodValidation pod_validation{validate_target_pod};
static const CallPodValidation* session_pod_validation=&pod_validation;
#elif defined(E33_REFLECTED_SESSION)
#include "reflected_invocation.h"
#include "picto_progression.h"
static const CallPodValidation* session_pod_validation=nullptr;
#endif
#ifdef E33_ASSIGNMENT_SESSION
#include "target_object_assignment.h"
#ifdef E33_SCALAR_ASSIGNMENT_SESSION
#include "scalar_assignment.h"
#endif
#endif
#ifdef E33_ENUM_SESSION
#include "enum_schema.h"
static bool validate_target_enum(uint64_t base,uint64_t property,const CallIdentity& id,const uint8_t* value) {
    TargetPodSchemaOps ops{base};
    return value ? validate_byte_enum_value(ops,property,id,*value) : validate_byte_enum_parameter(ops,property,id);
}
#endif
#ifdef E33_REFLECTED_SESSION
#include "reflected_invocation.h"
#include "picto_progression.h"
#endif
#ifdef E33_SEQUENCE_SESSION
#include "target_asset_call.h"
#endif
#ifdef E33_LEASE_SESSION
#include "target_strong_reference.h"
#include "strong_lease_pool.h"
#ifdef E33_STABLE_SESSION
#include "stable_identity.h"
#ifdef E33_METADATA_STABILIZE_SESSION
#include "stable_lease_runtime.h"
#endif
#endif
static StrongLeasePool<> session_leases;
static uint64_t lease_session=0;
#endif
#ifdef E33_SEQUENCER_ARRAY_SESSION
#include "target_sequencer_array.h"
static e33_sequencer_array::Frame session_sequencer_array;
#endif
#ifdef E33_AUTHORED_CURVE_SESSION
#include "target_authored_curve_patch.h"
static e33_curve_patch::Frame session_curve_patch;
#endif
#ifdef E33_SEQUENCE_BINDING_VALUE_SESSION
#include "target_portable_binding.h"
static e33_portable_binding::Frame session_portable_binding;
#endif

static SchedulePacket target{};
static ObserverBuffer session_events{};
static uint64_t runtime_base = 0, target_object = 0, target_function = 0;
#ifdef E33_CONSOLE_COLORS_SESSION
#include "runtime_console_colors.h"
#endif
#ifdef E33_AUDIO_ISOLATION_SESSION
#include "picto_batch.h"
static PictoBatch session_picto_batch;
#ifdef E33_ZONE_TRAVEL_SESSION
#include "zone_travel.h"
#include "qa_encounter.h"
#include "qa_mime.h"
#endif
#endif
#ifdef E33_MESH_SESSION
#include "mesh_owner.h"
#include <array>
#include "builder_owner.h"
static e33_builder::Owner session_builder;
static e33_mesh::Owner session_mesh;
#include "map_runtime_owner.h"
static e33_map_runtime::Owner session_map_runtime;
#ifdef E33_MAP_LOAD_GATE_SESSION
#include "map_load_gate.h"
static e33_map_load_gate::Owner session_map_load_gate;
#include "map_asset_preparation.h"
static e33_map_asset_preparation::Owner session_map_assets;
#endif
#ifdef E33_ENEMY_SPAWN_SESSION
#include "enemy_spawn_owner.h"
#include "npc_original_admission.h"
#include "npc_membership_observation.h"
#ifdef E33_NPC_PRESENTATION_RESEARCH
#include "npc_research_service.h"
static e33_npc_presentation::ResearchService session_npc_research;
#endif
static e33_enemy_spawn::Owner session_enemy_spawn;
#ifdef E33_TIMELINE_ACTOR_POOL_SESSION
#include "timeline_actor_channel.h"
struct TimelineActorOwner: e33_enemy_spawn::Owner {TimelineActorOwner():Owner(false,true){}};
static TimelineActorOwner session_timeline_actors[e33_timeline_actor::capacity];
static e33_timeline_actor::Slots session_timeline_slots;
#endif
#if E33_RUNTIME_CINEMATIC_VERSION>=186
#include "encounter_tuning_owner.h"
static e33_encounter_tuning::Owner session_encounter_tuning;
#endif
#if E33_RUNTIME_CINEMATIC_VERSION>=177
#include "owned_battle_arena_channel.h"
#if E33_RUNTIME_CINEMATIC_VERSION>=191
#include "owned_arena_slots.h"
static e33_enemy_spawn::Owner session_owned_battle_arenas[2]={e33_enemy_spawn::Owner{true},e33_enemy_spawn::Owner{true}};
static e33_owned_arena::Slots session_owned_arena_slots{};
#else
static e33_enemy_spawn::Owner session_owned_battle_arena{true};
#endif
#endif
#ifdef E33_BATTLE_PARAMETER_FRAME_RESEARCH
#include "battle_parameter_research_owner.h"
static e33_enemy_spawn::ParameterResearchOwner session_parameter_research;
#endif
#endif
#ifdef E33_RUNTIME_CINEMATIC_SESSION
#ifdef E33_RUNTIME_SCENE_EDITOR_SESSION
#include "runtime_scene_owner.h"
static e33_runtime_scene::Owner session_runtime_cinematic;
#else
#include "runtime_cinematic_owner.h"
static e33_runtime_cinematic::Owner session_runtime_cinematic;
#endif
#endif
#endif

#ifdef E33_KEYBIND_SESSION
static e33_keys::State session_keys;
#endif
#ifdef E33_MENU_SESSION
#include "target_menu_ops.h"
static TargetMenuStorage session_menu;
#ifdef E33_AUDIO_ISOLATION_SESSION
#include "target_scoped_assignment.h"
static TargetScopedAssignment session_override;
#endif
#ifdef E33_MUSIC_AUDIO_SESSION
#include "music_audio_owner.h"
static MusicAudioOwner session_music_audio;
#endif
#ifdef E33_SEQUENCE_PLAYER_SESSION
#include "sequence_owner.h"
static SequenceOwner session_sequence;
#ifdef E33_CINEMATIC_SOUND_EVENT_SESSION
#include "cinematic_sound_event.h"
#ifdef E33_CINEMATIC_WIDGET_SESSION
#include "cinematic_widget_owner.h"
#include "cinematic_getter_profile.h"
#include "cinematic_track_profile.h"
#include "cinematic_callback_profile.h"
#include "cinematic_widget_hook.h"
static CinematicWidgetHook session_widget_hook;
#endif
static CinematicSoundEvent session_sound_event;
#endif
static uint32_t guarded_sequence_close() {
    __try {
        auto result=session_sequence.close(runtime_base);
        if(result) return result;
#ifdef E33_CINEMATIC_WIDGET_SESSION
        __try { result=session_widget_hook.close(runtime_base); }
        __except(EXCEPTION_EXECUTE_HANDLER) { result=1513; }
#endif
#ifdef E33_CINEMATIC_SOUND_EVENT_SESSION
        uint32_t sound_result=0;
        __try { sound_result=session_sound_event.close(runtime_base); }
        __except(EXCEPTION_EXECUTE_HANDLER) { sound_result=1503; }
        if(!result) result=sound_result;
#endif
#ifdef E33_MUSIC_AUDIO_SESSION
        {
            uint32_t audio_result=0;
            __try { audio_result=session_music_audio.close(runtime_base,lease_session,session_leases); }
            __except(EXCEPTION_EXECUTE_HANDLER) { audio_result=1493; }
            if(!result) result=audio_result;
            // Sequence evaluation has stopped. Even if private audio cleanup
            // fails, restore the global reference; keep private leases pinned
            // and report the audio failure rather than leaving GI redirected.
            const auto restored=session_override.close(runtime_base);
            if(!result) result=restored;
        }
#endif
#ifdef E33_AUDIO_ISOLATION_SESSION
        if(!result) result=session_override.close(runtime_base);
#endif
        return result;
    }
    __except(EXCEPTION_EXECUTE_HANDLER) { return 1473; }
}
#endif
#ifdef E33_MEDIA_SESSION
#include "media_owner.h"
static MediaOwner session_media;
static uint32_t guarded_media_close() {
    __try { return session_media.close(runtime_base); }
    __except(EXCEPTION_EXECUTE_HANDLER) { return 1403; }
}
#endif
static MenuResult close_menu_actions() {
#ifdef E33_MULTI_BUTTON_SESSION
    auto multi=session_menu.multi_actions.close();
    if(multi==ButtonDelegateResult::Deferred) return MenuResult::Deferred;
    if(multi!=ButtonDelegateResult::Ok) {
        session_menu.menu.quarantine(); return MenuResult::Quarantined;
    }
#endif
#ifdef E33_BUTTON_ACTION_SESSION
    auto result=session_menu.actions.close();
    if(result==ButtonDelegateResult::Deferred) return MenuResult::Deferred;
    if(result!=ButtonDelegateResult::Ok) {
        session_menu.menu.quarantine(); return MenuResult::Quarantined;
    }
#endif
    return MenuResult::Ok;
}
#ifdef E33_CINEMATIC_EPOCH_RETIRE_SESSION
static uint32_t retire_cinematic_menu_actions(const e33_retired_world::Snapshot& source) {
    if(!session_menu.menu.active())return 0;
    if(!e33_retired_world::same(session_menu.epoch.world(),source.world))return 1403;
    TargetMenuOps<StrongLeasePool<>> proof{session_menu,session_leases};
    const auto ready=proof.context();
    if(ready!=MenuContext::Ready)return ready==MenuContext::Deferred?407:1403;
    if(!session_menu.epoch_cleanup)return 1404;
    session_menu.menu.stop_actions();
    const auto removed=close_menu_actions();
    return removed==MenuResult::Ok?0:removed==MenuResult::Deferred?407:1403;
}
#endif
#include "menu_open_pipeline.h"
static MenuResult menu_command(MenuPacket& wire) {
    auto& s=session_menu;
    TargetMenuOps<StrongLeasePool<>> ops{s,session_leases};
    const auto operation=static_cast<MenuOperation>(wire.operation);
#ifdef E33_MULTI_BUTTON_SESSION
    const auto multi_gate=s.multi_actions.gate();
    if(multi_gate==ButtonDelegateResult::Deferred) return MenuResult::Deferred;
    if(multi_gate!=ButtonDelegateResult::Ok) { s.menu.quarantine(); return MenuResult::Quarantined; }
#endif
#ifdef E33_BUTTON_ACTION_SESSION
    const auto gate=s.actions.gate();
    if(gate==ButtonDelegateResult::Deferred) return MenuResult::Deferred;
    if(gate!=ButtonDelegateResult::Ok) { s.menu.quarantine(); return MenuResult::Quarantined; }
#endif
    if(operation==MenuOperation::Prepare
#ifdef E33_VIEWER_MENU_SESSION
        || operation==MenuOperation::Open
#endif
        ) {
        if(s.menu.active()) return MenuResult::Busy;
        // Copy before acquiring any ownership; IPC is never cleanup storage.
        s.base=runtime_base; s.session=lease_session; s.owner=wire.owner;
        s.widget_lease=wire.widget_lease; s.child_lease=wire.child_lease;
        s.engine=wire.engine; s.widget=wire.widget; s.child=wire.child;
        s.player=wire.player; s.library=wire.library;
        std::memcpy(s.plans,wire.plans,sizeof(s.plans));
        auto result=s.menu.prepare(ops,s.session,s.owner,s.widget_lease,s.child_lease);
#ifdef E33_VIEWER_MENU_SESSION
        if(operation==MenuOperation::Open && result==MenuResult::Ok) {
            result=attach_open_menu(s.menu,ops,s.session,s.owner,
#ifdef E33_MENU_OPEN_FOCUS_SESSION
                true
#else
                false
#endif
            );

        }
#endif
        return result;
    }
    if(s.menu.active() && (s.session!=lease_session || s.owner!=wire.owner)) return MenuResult::Invalid;
    switch(operation) {
    case MenuOperation::Attach: return s.menu.attach(ops,lease_session,wire.owner);
    case MenuOperation::Focus: return s.menu.focus(ops,lease_session,wire.owner);
#ifdef E33_RETIRED_WORLD_SESSION
    case MenuOperation::Retire:
#endif
    case MenuOperation::Close: {
#ifdef E33_RETIRED_WORLD_SESSION
        if(s.menu.active()){
            const auto ready=ops.context();
            if(ready!=MenuContext::Ready)return ready==MenuContext::Deferred?MenuResult::Deferred:MenuResult::Quarantined;
            if(operation==MenuOperation::Retire && !s.epoch_cleanup)return MenuResult::Invalid;
            if(s.epoch_cleanup){
#ifdef E33_SEQUENCE_PLAYER_SESSION
                if(session_sequence.active())return MenuResult::Quarantined;
#endif
#ifdef E33_MEDIA_SESSION
                if(session_media.active())return MenuResult::Quarantined;
#endif
            }
        }
#endif
#ifdef E33_SEQUENCE_PLAYER_SESSION
        auto sequence=guarded_sequence_close();
        if(sequence) return sequence==407 ? MenuResult::Deferred : MenuResult::Quarantined;
#endif
#ifdef E33_MEDIA_SESSION
        auto media=guarded_media_close();
        if(media) return media==407 ? MenuResult::Deferred : MenuResult::Quarantined;
#endif
        s.menu.stop_actions();
        auto result=close_menu_actions();
        if(result==MenuResult::Ok)result=s.menu.close(ops,lease_session,wire.owner);
        return result;
    }
    case MenuOperation::Status: return MenuResult::Ok;
    default: return MenuResult::Invalid;
    }
}
static void guarded_menu_command(MenuPacket& wire) {
    if(!valid_menu_request(wire)) { wire.error=810; return; }
    wire.outcome=static_cast<uint32_t>(MenuOutcome::Unknown);
    __try {
        auto result=menu_command(wire);
        wire.error=result==MenuResult::Ok ? 0 : 810+static_cast<uint32_t>(result);
#ifdef E33_MENU_DIAGNOSTIC_SESSION
        if(wire.error==811 && (wire.operation==1 || wire.operation==6) && !session_menu.menu.active() && session_menu.preparation_diagnostic)
            wire.error=session_menu.preparation_diagnostic;
#endif
        wire.outcome=static_cast<uint32_t>(MenuOutcome::Returned);
    } __except(EXCEPTION_EXECUTE_HANDLER) {
#ifdef E33_MULTI_BUTTON_SESSION
        session_menu.multi_actions.quarantine();
#endif
#ifdef E33_BUTTON_ACTION_SESSION
        session_menu.actions.quarantine();
#endif
        session_menu.menu.quarantine();
        wire.error=816;
    }
    wire.active=session_menu.menu.active() ? 1 : 0;
}
static MenuResult guarded_menu_close() {
    __try {
#ifdef E33_RETIRED_WORLD_SESSION
        if(session_menu.menu.active()){
            TargetMenuOps<StrongLeasePool<>> proof{session_menu,session_leases};
            const auto ready=proof.context();
            if(ready!=MenuContext::Ready)return ready==MenuContext::Deferred?MenuResult::Deferred:MenuResult::Quarantined;
            if(session_menu.epoch_cleanup){
#ifdef E33_SEQUENCE_PLAYER_SESSION
                if(session_sequence.active())return MenuResult::Quarantined;
#endif
#ifdef E33_MEDIA_SESSION
                if(session_media.active())return MenuResult::Quarantined;
#endif
            }
        }
#endif
#ifdef E33_SEQUENCE_PLAYER_SESSION
        auto sequence=guarded_sequence_close();
        if(sequence) return sequence==407 ? MenuResult::Deferred : MenuResult::Quarantined;
#endif
        session_menu.menu.stop_actions();
        auto result=close_menu_actions();
        if(result!=MenuResult::Ok) return result;
        TargetMenuOps<StrongLeasePool<>> ops{session_menu,session_leases};
        return session_menu.menu.close_session(ops);
    } __except(EXCEPTION_EXECUTE_HANDLER) {
#ifdef E33_MULTI_BUTTON_SESSION
        session_menu.multi_actions.quarantine();
#endif
#ifdef E33_BUTTON_ACTION_SESSION
        session_menu.actions.quarantine();
#endif
        session_menu.menu.quarantine();
        return MenuResult::Quarantined;
    }
}
#ifdef E33_BUTTON_ACTION_SESSION
static ButtonDelegateResult button_action_command(ButtonActionPacket& wire) {
    auto& s=session_menu;
#ifdef E33_MULTI_BUTTON_SESSION
    auto multi_gate=s.multi_actions.gate();
    if(multi_gate!=ButtonDelegateResult::Ok) return multi_gate;
#endif
    auto allowed=s.actions.gate();
    if(allowed!=ButtonDelegateResult::Ok) return allowed;
    // IPC selects an action ID, never an arbitrary object/delegate address.
    if(!s.menu.active() || s.session!=lease_session || wire.owner!=s.owner ||
       wire.child_lease!=s.child_lease ||
       !session_leases.owns_object(lease_session,s.child_lease,s.child.address) ||
       !session_leases.owns_object(lease_session,s.widget_lease,s.widget.address))
        return ButtonDelegateResult::Invalid;
    switch(static_cast<ButtonActionOperation>(wire.operation)) {
    case ButtonActionOperation::Bind: {
        TargetMenuOps<StrongLeasePool<>> ops{s,session_leases};
        if(!s.menu.accepts_actions() || ops.context()!=MenuContext::Ready ||
           s.child_slate.slate.state!=SlateReferenceState::Live)
            return ButtonDelegateResult::Invalid;
        return s.actions.bind(runtime_base,lease_session,wire.owner,wire.action,s.child_slate);
    }
    case ButtonActionOperation::Drain: {
        size_t count=0;
        uint64_t dropped=0;
        MenuActionEvent copied[kButtonActionCapacity]{};
        auto result=s.actions.drain(lease_session,copied,kButtonActionCapacity,count,dropped);
        wire.count=static_cast<uint32_t>(count);
        wire.dropped=dropped;
        std::memcpy(wire.events,copied,count*sizeof(MenuActionEvent));
        return result;
    }
    case ButtonActionOperation::Unbind: return s.actions.close();
    case ButtonActionOperation::Status: return ButtonDelegateResult::Ok;
    default: return ButtonDelegateResult::Invalid;
    }
}
static void guarded_button_action(ButtonActionPacket& wire) {
    if(!valid_button_action_request(wire)) { wire.error=910; return; }
    wire.outcome=static_cast<uint32_t>(ButtonActionOutcome::Unknown);
    __try {
        auto result=button_action_command(wire);
        wire.error=result==ButtonDelegateResult::Ok ? 0 : 910+static_cast<uint32_t>(result);
        wire.state=static_cast<uint32_t>(session_menu.actions.state());
        if(result==ButtonDelegateResult::Ok) wire.registration=session_menu.actions.registration();
        wire.outcome=static_cast<uint32_t>(ButtonActionOutcome::Returned);
        if(result==ButtonDelegateResult::Quarantined) session_menu.menu.quarantine();
    } __except(EXCEPTION_EXECUTE_HANDLER) {
#ifdef E33_MULTI_BUTTON_SESSION
        session_menu.multi_actions.quarantine();
#endif
        session_menu.actions.quarantine(); session_menu.menu.quarantine(); wire.error=916;
    }
}
#endif
#endif
static bool observing = false;
#ifdef E33_MULTI_BUTTON_SESSION
static ButtonDelegateResult multi_button_command(MultiButtonPacket& packet) {
    auto& s=session_menu;
    auto& wire=packet.action;
    auto single_gate=s.actions.gate();
    if(single_gate!=ButtonDelegateResult::Ok) return single_gate;
    auto allowed=s.multi_actions.gate();
    if(allowed!=ButtonDelegateResult::Ok) return allowed;
    if(!s.menu.active() || s.session!=lease_session || wire.owner!=s.owner ||
       !session_leases.owns_object(lease_session,s.widget_lease,s.widget.address))
        return ButtonDelegateResult::Invalid;
    switch(static_cast<ButtonActionOperation>(wire.operation)) {
    case ButtonActionOperation::Bind: {
        TargetMenuOps<StrongLeasePool<>> ops{s,session_leases};
        const auto& child=packet.child;
        if(!s.menu.accepts_actions() || ops.context()!=MenuContext::Ready ||
           !session_leases.owns_object(lease_session,wire.child_lease,child.address) ||
           !call_identity(runtime_base,child) ||
           !ops.exact_class(child.address,"Button","/Script/UMG") ||
           (local_read<uint32_t>(child.address+8)&(0x10|0x40000000)))
            return ButtonDelegateResult::Invalid;
        auto tree=local_read<uint64_t>(child.address+0x20);
        if(!ops.exact_class(tree,"WidgetTree","/Script/UMG") ||
           local_read<uint64_t>(tree+0x20)!=s.widget.address) return ButtonDelegateResult::Invalid;
        uint64_t widget=0, controller=0, instance=0;
        if(!TargetButtonReference::observe(runtime_base,child,widget,controller,instance))
            return ButtonDelegateResult::Invalid;
        TargetButtonReferenceOps refs{runtime_base};
        auto captured=s.control_focus.retain(refs,widget,controller);
        if(captured==SlateReferenceResult::Busy) return ButtonDelegateResult::Busy;
        if(captured!=SlateReferenceResult::Ok) {
            s.menu.quarantine(); s.multi_actions.quarantine();
            return ButtonDelegateResult::Quarantined;
        }
        return s.multi_actions.bind(runtime_base,lease_session,wire.owner,wire.action,wire.child_lease,child);
    }
    case ButtonActionOperation::Drain: {
        size_t count=0; uint64_t dropped=0;
        MenuActionEvent copied[kButtonActionCapacity]{};
        auto result=s.multi_actions.drain(lease_session,copied,kButtonActionCapacity,count,dropped);
        wire.count=static_cast<uint32_t>(count); wire.dropped=dropped;
        std::memcpy(wire.events,copied,count*sizeof(MenuActionEvent));
        return result;
    }
    case ButtonActionOperation::Unbind: return s.multi_actions.remove(lease_session,wire.child_lease);
    case ButtonActionOperation::Status:
        return s.multi_actions.protects_lease(wire.child_lease) ? ButtonDelegateResult::Ok : ButtonDelegateResult::Invalid;
    default: return ButtonDelegateResult::Invalid;
    }
}
static void guarded_multi_button(MultiButtonPacket& packet) {
    auto& wire=packet.action;
    if(!valid_multi_button_request(packet)) { wire.error=1010; return; }
    wire.outcome=static_cast<uint32_t>(ButtonActionOutcome::Unknown);
    __try {
        auto result=multi_button_command(packet);
        wire.error=result==ButtonDelegateResult::Ok ? 0 : 1010+static_cast<uint32_t>(result);
        wire.state=static_cast<uint32_t>(session_menu.multi_actions.state(wire.child_lease));
        if(result==ButtonDelegateResult::Ok)
            wire.registration=session_menu.multi_actions.registration(wire.child_lease);
        wire.outcome=static_cast<uint32_t>(ButtonActionOutcome::Returned);
        if(result==ButtonDelegateResult::Quarantined) session_menu.menu.quarantine();
    } __except(EXCEPTION_EXECUTE_HANDLER) {
        session_menu.multi_actions.quarantine(); session_menu.actions.quarantine();
        session_menu.menu.quarantine(); wire.error=1016;
    }
}
#endif
static unsigned console_toggle_key=0;
#ifdef E33_TEXT_SESSION
#include "target_text_call.h"
// Never borrow the shared mapping for ownership or cleanup. These records live
// in the pinned module even after a controller exits or an engine call faults.
#ifdef E33_STRING_SESSION
static TextCallPacket session_string_packet;
static StringCallFrame session_string_frame;
static bool string_available(void*) { return session_string_frame.available(); }
static uint32_t string_prepare(void*) { return session_string_frame.prepare(session_string_packet) ? 0 : 765; }
static uint32_t string_begin(void*) { return session_string_frame.begin() ? 0 : 765; }
static uint32_t string_returned(void*) { return session_string_frame.returned(session_string_packet) ? 0 : 766; }
static uint32_t string_finish(void*) { return session_string_frame.state==StringFrameState::Returned ? 0 : 766; }
static uint32_t guarded_string_invoke(const CallRetention* retention) {
    CallTextHandling handling{&session_string_packet,session_string_frame.arguments,&session_string_frame,
        string_available,string_prepare,string_begin,string_returned,string_finish,true};
    __try { return reflected_call(runtime_base,session_string_packet.retained.call,retention,
                                  session_pod_validation,&handling); }
    __except(EXCEPTION_EXECUTE_HANDLER) { return 767; }
}
#endif
static TextCallPacket session_text_packet;
static TargetTextCall session_text;
static TextFrameResult guarded_text_cleanup() {
    __try {
        TargetOwnedTextOps ops{session_text.base};
        return session_text.frame.cleanup(ops);
    } __except(EXCEPTION_EXECUTE_HANDLER) { return TextFrameResult::Quarantined; }
}
static uint32_t guarded_text_invoke(const CallRetention* retention) {
    __try {
        const auto handling=session_text.handling();
        return reflected_call(session_text.base,session_text_packet.retained.call,
                              retention,session_pod_validation,&handling,nullptr,false,E33_TRACE_ENTRY_VALIDATION);
    } __except(EXCEPTION_EXECUTE_HANDLER) { return 708; }
}
#endif
#ifdef E33_RETAINED_SESSION
static uint32_t retain_preflight(void*,const CallPacket& call) {
    return static_cast<uint32_t>(session_leases.preflight(lease_session,retained_call_slots(call)));
}
static uint32_t retain_output(void* context,uint32_t offset,CallIdentity& identity) {
    auto& retained=*static_cast<RetainedCallPacket*>(context);
    if(retained.count>=kCallObjects) return 401;
    TargetStrongReferenceOps ops{runtime_base,identity};
    uint64_t token=0;
    auto result=session_leases.acquire(ops,lease_session,identity.address,token);
    if(result!=StrongLeaseResult::Ok) return static_cast<uint32_t>(result);
    retained.leases[retained.count++]={offset,token};
#ifdef E33_STABLE_SESSION
    // The pool already owns this object before any serial-allocation side effect.
    if(!stabilize_retained_identity(ops,identity)) return 413;
#endif
    return 0;
}
#endif

bool backend_shutting_down() {
    return runtime_base && local_read<uint8_t>(runtime_base + 0x9272cfc) != 0;
}
static bool lifetime_valid() {
    if (!runtime_base || backend_shutting_down() || GetCurrentThreadId() != target.target_tid) return false;
    int32_t first = local_read<int32_t>(runtime_base + 0x9361b60);
    int32_t last = local_read<int32_t>(runtime_base + 0x9361b64);
    int32_t capacity = local_read<int32_t>(runtime_base + 0x9361b68);
    return first > 0 && last == first - 1 && first <= capacity &&
        capacity <= local_read<int32_t>(runtime_base + 0x9361b84) &&
        local_read<uint8_t>(runtime_base + 0x9361b6c) == 0 &&
        target.object_index >= 0 && target.object_index < first && target.function_index >= 0 && target.function_index < first &&
        fixed_slot(runtime_base, target.object_index, target.object_serial) == target_object &&
        fixed_slot(runtime_base, target.function_index, target.function_serial) == target_function;
}
uint32_t backend_open(SessionPacket* packet) {
#ifdef E33_AUTHORED_CURVE_SESSION
    if(session_curve_patch.quarantined())return 3783;
#endif
#ifdef E33_SEQUENCER_ARRAY_SESSION
    if(session_sequencer_array.quarantined())return 3743;
#endif
#ifdef E33_SEQUENCE_PLAYER_SESSION
    if(session_sequence.active()) return 1473;
#endif
#ifdef E33_MEDIA_SESSION
    if(session_media.active()) return 1403;
#endif
#ifdef E33_MENU_SESSION
    if(session_menu.menu.active()) return 800;
#endif
#ifdef E33_TEXT_SESSION
    // Failed ownership from a previous session is never adopted by a new owner.
    if(!session_text.frame.available()) return 230;
#ifdef E33_STRING_SESSION
    if(!session_string_frame.available()) return 765;
#endif
#endif
    // Opening first verifies the fixed, already-proven getter and target thread.
    target = packet->request;
    uint32_t error = invoke_fixed_guarded(&target);
    if (error) return error;
    runtime_base = reinterpret_cast<uint64_t>(GetModuleHandleW(nullptr));
    target_object = fixed_slot(runtime_base, target.object_index, target.object_serial);
    target_function = fixed_slot(runtime_base, target.function_index, target.function_serial);
    if(!lifetime_valid()) return 60;
#ifdef E33_TRACE_SESSION
    if (!session_traces.begin(runtime_base, packet->request.nonce)) return 931;
    trace_cleanup_error = 0;
#endif
#ifdef E33_LEASE_SESSION
    auto lease_error=session_leases.begin(packet->request.nonce);
    if(lease_error!=StrongLeaseResult::Ok) {
#ifdef E33_TRACE_SESSION
        session_traces.close(false);
#endif
        return static_cast<uint32_t>(lease_error);
    }
    lease_session=packet->request.nonce;
#endif
#ifdef E33_KEYBIND_SESSION
    session_keys.begin(packet->request.nonce);
#endif
    return 0;
}
#ifdef E33_UI_BATCH_SESSION
#include "ui_batch_runtime.h"
#endif
#ifdef E33_PAUSE_MENU_SESSION
#include "pause_attachment.h"
static PauseAttachmentPool pause_attachment;
static uint32_t guarded_pause_close(bool terminal) {
    __try { return pause_attachment.close(runtime_base,terminal); }
    __except(EXCEPTION_EXECUTE_HANDLER) { return 1303; }
}
#endif
#ifdef E33_LEASE_SESSION
static bool lease_release_protected(uint64_t token){
#ifdef E33_AUTHORED_CURVE_SESSION
    if(session_curve_patch.protects(token))return true;
#endif
#ifdef E33_BATTLE_COMPLETION_RECEIPT_SESSION
    if(session_parameter_research.protects(token))return true;
#endif
#ifdef E33_PAUSE_MENU_SESSION
    if(pause_attachment.protects(token))return true;
#endif
#ifdef E33_MENU_SESSION
    if(session_menu.menu.protects(lease_session,token)
#ifdef E33_RETIRED_WORLD_SESSION
       ||(session_menu.menu.active() && token && token==session_menu.epoch.token())
#endif
#ifdef E33_MULTI_BUTTON_SESSION
       ||session_menu.multi_actions.protects_lease(token)
#endif
    )return true;
#endif
#ifdef E33_MEDIA_SESSION
    if(session_media.protects(token))return true;
#endif
#ifdef E33_SEQUENCE_PLAYER_SESSION
    if(session_sequence.protects(token))return true;
#endif
#ifdef E33_AUDIO_ISOLATION_SESSION
    if(session_override.protects(token))return true;
#endif
#ifdef E33_MUSIC_AUDIO_SESSION
    if(session_music_audio.protects(token))return true;
#endif
#ifdef E33_CINEMATIC_SOUND_EVENT_SESSION
    if(session_sound_event.protects(token))return true;
#endif
#ifdef E33_CINEMATIC_WIDGET_SESSION
    if(session_widget_hook.protects(token))return true;
#endif
#if defined(E33_RETIRED_WORLD_SESSION) && defined(E33_MESH_SESSION)
    if(session_map_runtime.protects(token))return true;
    if(session_map_assets.protects(token))return true;
#endif
    return false;
}
#endif
#ifdef E33_LEASE_RELEASE_BATCH_SESSION
#include "lease_release_batch_runtime.h"
static uint32_t guarded_lease_release_token(uint64_t token){
    __try{
        if(lease_release_protected(token))return uint32_t(StrongLeaseResult::Busy);
        TargetStrongReferenceOps ops{runtime_base,{-1,0,0}};
        return uint32_t(session_leases.release(ops,lease_session,token));
    }__except(EXCEPTION_EXECUTE_HANDLER){return uint32_t(StrongLeaseResult::Quarantined);}
}
struct LeaseReleaseBatchOps {
    uint32_t admit(uint64_t token)const{
        if(!session_leases.contains_token(lease_session,token))return uint32_t(StrongLeaseResult::Stale);
        return lease_release_protected(token)?uint32_t(StrongLeaseResult::Busy):0;
    }
    uint32_t release(uint64_t token)const{return guarded_lease_release_token(token);}
    uint32_t active()const{return session_leases.active();}
};
static void lease_release_batch(e33_lease_batch::Packet& packet){
    LeaseReleaseBatchOps ops;e33_lease_batch::run(packet,ops);
}
#endif
#ifdef E33_METADATA_STABILIZE_SESSION
#include "metadata_stabilization_target.h"
#endif
uint32_t backend_command(SessionPacket* packet) {
    if (!lifetime_valid()) return 61;
#ifdef E33_GROWING_LEASE_SESSION
    if(!session_leases.set_owner(lease_session,packet->lease_owner)) return 404;
#endif
    switch (packet->request.action) {
#ifdef E33_METADATA_STABILIZE_SESSION
    case e33_metadata::Action:{
        MetadataStabilizationOps<decltype(session_leases)> ops{runtime_base,lease_session,session_leases};
        e33_metadata::run(*reinterpret_cast<e33_metadata::Packet*>(packet->console_text),ops);return 0;
    }
#endif

#ifdef E33_MESH_SESSION
    case SessionMesh: {
        auto& p=*reinterpret_cast<MeshPacket*>(packet->console_text);
#ifdef E33_AUTHORED_CURVE_SESSION
        if(p.operation==e33_curve_patch::operation){
            auto& edit=*reinterpret_cast<e33_curve_patch::Packet*>(&p);
            __try{authored_curve_patch_command(runtime_base,lease_session,session_leases,edit,session_curve_patch,!session_sequence.active());}
            __except(EXCEPTION_EXECUTE_HANDLER){edit.error=session_curve_patch.quarantined()?3783:3780;
                if(session_curve_patch.quarantined())edit.state=edit.outcome=2;}
            return 0;
        }
#endif
#ifdef E33_SEQUENCE_BINDING_VALUE_SESSION
        if(p.operation==e33_portable_binding::operation){
            auto& query=*reinterpret_cast<e33_portable_binding::Packet*>(&p);
            __try{portable_binding_command(runtime_base,lease_session,session_leases,query,session_portable_binding);}
            __except(EXCEPTION_EXECUTE_HANDLER){query.error=session_portable_binding.quarantined()?3763:3760;
                if(session_portable_binding.quarantined())query.state=query.outcome=2;}
            return 0;
        }
#endif
#ifdef E33_SEQUENCER_ARRAY_SESSION
        if(p.operation==e33_sequencer_array::operation) {
            auto& query=*reinterpret_cast<e33_sequencer_array::Packet*>(&p);
            __try {sequencer_array_command(runtime_base,lease_session,session_leases,query,session_sequencer_array);}
            __except(EXCEPTION_EXECUTE_HANDLER) {
                query.error=session_sequencer_array.quarantined() ? 3743 : 3741;
                if(session_sequencer_array.quarantined())query.state=query.outcome=2;
            }
            return 0;
        }
#endif
#if E33_RUNTIME_CINEMATIC_VERSION>=186
        if(p.operation>=157&&p.operation<=159){
            __try {session_encounter_tuning.command(runtime_base,lease_session,session_leases,p,session_enemy_spawn,session_npc_research);}
            __except(EXCEPTION_EXECUTE_HANDLER){p.error=3637;}
            return 0;
        }
#endif
#if defined(E33_ENEMY_SPAWN_SESSION) && E33_RUNTIME_CINEMATIC_VERSION>=177
        if(p.operation>=e33_owned_arena::prepare&&p.operation<=e33_owned_arena::qualify_helper){
            p.error=e33_owned_arena::validate(p);if(p.error)return 0;
#if E33_RUNTIME_CINEMATIC_VERSION>=192
            if(p.operation==e33_owned_arena::component_pose&&reinterpret_cast<const uint8_t*>(&p)[24]==1){
                if(!session_enemy_spawn.has_work()||!session_enemy_spawn.token_matches(p.owner)){p.error=3644;return 0;}
                __try {
                    CallIdentity query[3]{};double pose[12]{};e33_component_pose::Report report{};
                    const auto* bytes=reinterpret_cast<const uint8_t*>(&p);
                    std::memcpy(query,bytes+88,sizeof(query));std::memcpy(pose,bytes+2000,sizeof(pose));
                    p.error=session_enemy_spawn.set_owned_component_pose(runtime_base,lease_session,session_leases,query,pose,report,true);
                    std::memcpy(reinterpret_cast<uint8_t*>(&p)+4096,&report,sizeof(report));
                    if(!p.error)p.state=1;
                }__except(EXCEPTION_EXECUTE_HANDLER){p.error=3602;}
                return 0;
            }
#endif
#if E33_RUNTIME_CINEMATIC_VERSION>=191
            const int arena_slot=p.operation==e33_owned_arena::prepare?
                session_owned_arena_slots.reserve(p.owner):session_owned_arena_slots.find(p.owner);
            if(arena_slot<0){
                if(p.operation==e33_owned_arena::status)p.state=1;
                else if(p.operation!=e33_owned_arena::retire)p.error=3640;
                return 0; // never fall back to another owner's arena
            }
            auto& session_owned_battle_arena=session_owned_battle_arenas[arena_slot];
#endif
            if(!session_owned_battle_arena.token_matches(p.owner)){p.error=3601;return 0;}
            const auto operation=p.operation;
            if(operation==e33_timeline_actor::construct&&session_timeline_slots.find(p.owner)>=0){p.error=3773;return 0;}
            __try {
                if(operation==e33_owned_arena::qualify_helper){
#if E33_RUNTIME_CINEMATIC_VERSION>=181
                    CallIdentity query[4]{};double relative[12]{};e33_enemy_spawn::HelperSourceFrameReport report{};
                    std::memcpy(query,reinterpret_cast<uint8_t*>(&p)+88,sizeof(query));
                    std::memcpy(relative,reinterpret_cast<uint8_t*>(&p)+2000,sizeof(relative));
                    p.error=session_owned_battle_arena.qualify_owned_helper(runtime_base,lease_session,session_leases,session_enemy_spawn,query,relative,report);
                    std::memcpy(reinterpret_cast<uint8_t*>(&p)+4096,&report,sizeof(report));if(!p.error)p.state=1;
#else
                    p.error=3600;
#endif
                }else if(operation==e33_owned_arena::ground){
#if E33_RUNTIME_CINEMATIC_VERSION>=180
                    CallIdentity query[9]{};e33_enemy_spawn::ArenaGroundReport report{};
                    std::memcpy(query,reinterpret_cast<uint8_t*>(&p)+88,sizeof(query));
                    const auto flags=reinterpret_cast<uint8_t*>(&p)[24];
                    const bool approach=(flags&1)!=0;const bool detailed=(flags&2)!=0;
                    const bool advisory=(flags&4)!=0;
                    e33_enemy_spawn::ArenaGroundDiagnostics diagnostics{};
#if E33_RUNTIME_CINEMATIC_VERSION<184
                    if(advisory)p.error=3600;
                    else
#endif
#if E33_RUNTIME_CINEMATIC_VERSION<183
                    if(detailed)p.error=3600;
                    else
#endif
#if E33_RUNTIME_CINEMATIC_VERSION<182
                    if(approach)p.error=3600;
                    else
#endif
                    p.error=session_owned_battle_arena.ground_owned_arena(runtime_base,lease_session,session_leases,query,report,approach,detailed?&diagnostics:nullptr,!advisory);
                    std::memcpy(reinterpret_cast<uint8_t*>(&p)+4096,&report,sizeof(report));if(!p.error)p.state=1;
#if E33_RUNTIME_CINEMATIC_VERSION>=183
                    if(detailed)std::memcpy(reinterpret_cast<uint8_t*>(&p)+4448,&diagnostics,sizeof(diagnostics));
#endif
#else
                    p.error=3600;
#endif
                }else if(operation==e33_owned_arena::component_pose){
#if E33_RUNTIME_CINEMATIC_VERSION>=178
                    CallIdentity query[3]{};double pose[12]{};e33_component_pose::Report report{};
                    const auto* bytes=reinterpret_cast<const uint8_t*>(&p);
                    std::memcpy(query,bytes+88,sizeof(query));std::memcpy(pose,bytes+2000,sizeof(pose));
                    p.error=session_owned_battle_arena.set_owned_component_pose(runtime_base,lease_session,session_leases,query,pose,report);
                    std::memcpy(reinterpret_cast<uint8_t*>(&p)+4096,&report,sizeof(report));
                    if(!p.error)p.state=1;
#else
                    p.error=3600;
#endif
                }else if(operation==e33_owned_arena::status){
                    const auto actor=session_owned_battle_arena.staged_actor();
                    std::memcpy(reinterpret_cast<uint8_t*>(&p)+4096,&actor,sizeof(actor));
#if E33_RUNTIME_CINEMATIC_VERSION>=191
                    p.state=2; // a reservation is pending work, including failed prepare
#else
                    p.state=session_owned_battle_arena.has_work()?2:1;
#endif
                }else{
                    p.operation=operation==e33_owned_arena::prepare?120:111;
                    session_owned_battle_arena.command(runtime_base,lease_session,session_leases,p);
                }
            }__except(EXCEPTION_EXECUTE_HANDLER){p.error=3602;}
#if E33_RUNTIME_CINEMATIC_VERSION>=191
            if(operation==e33_owned_arena::retire&&!p.error&&
               !session_owned_arena_slots.retired(static_cast<unsigned>(arena_slot),p.error,session_owned_battle_arena.has_work()))p.error=3641;
#endif
            p.operation=operation;return 0;
        }
#endif
#ifdef E33_ENEMY_SPAWN_SESSION
#ifdef E33_BATTLE_PARAMETER_FRAME_RESEARCH
        if((p.operation>=124 && p.operation<=130)||p.operation==160) {
            __try {
                e33_enemy_spawn::ParameterInstanceAuthority<StrongLeasePool<>> authority{};
#ifdef E33_NPC_PRESENTATION_RESEARCH
                if(session_npc_research.has_work()&&p.operation>=127){
                    authority.owner=&session_npc_research;
                    authority.owns=[](void* owner,uint64_t base,uint64_t session,StrongLeasePool<>& pool,uint64_t token,
                            const CallIdentity& actor,uint64_t& name){
                        return static_cast<e33_npc_presentation::ResearchService*>(owner)->owned_parameter_instance_name(base,session,pool,token,actor,name);
                    };
                    authority.entry=[](void* owner,uint64_t base,uint64_t session,StrongLeasePool<>& pool,uint64_t token,
                            const CallIdentity& actor,const CallIdentity& manager,const CallIdentity& function,uint64_t& name){
                        return static_cast<e33_npc_presentation::ResearchService*>(owner)->owned_entry_context(base,session,pool,token,actor,manager,function,name);
                    };
                    authority.arena=[](void* owner,uint64_t base,uint64_t session,StrongLeasePool<>& pool,uint64_t token,const CallIdentity& actor,CallIdentity& arena){
                        return static_cast<e33_npc_presentation::ResearchService*>(owner)->owned_entry_arena(base,session,pool,token,actor,arena);
                    };
                    authority.copy_arena=[](void* owner,uint64_t base,uint64_t session,StrongLeasePool<>& pool,uint64_t token,
                            const CallIdentity& actor,const CallIdentity& arena,void* destination){
                        return static_cast<e33_npc_presentation::ResearchService*>(owner)->copy_entry_arena(base,session,pool,token,actor,arena,destination);
                    };
                    authority.dispatch=[](void* owner,uint64_t base,uint64_t session,StrongLeasePool<>& pool,uint64_t token,
                            const CallIdentity& actor,const CallIdentity& manager,const CallIdentity& function){
                        return static_cast<e33_npc_presentation::ResearchService*>(owner)->note_entry_dispatch(base,session,pool,token,actor,manager,function);
                    };
                }
#if defined(E33_RUNTIME_SCENE_EDITOR_SESSION) && E33_RUNTIME_CINEMATIC_VERSION >= 172
                if(!authority.owner && session_runtime_cinematic.visual_stage_active() && p.operation>=127){
                    authority.owner=&session_runtime_cinematic;
                    authority.owns=[](void* owner,uint64_t base,uint64_t,StrongLeasePool<>&,uint64_t token,
                            const CallIdentity& actor,uint64_t& name){
                        return static_cast<e33_runtime_scene::Owner*>(owner)->visual_parameter_instance(base,token,actor,name);
                    };
                    authority.entry=[](void* owner,uint64_t base,uint64_t,StrongLeasePool<>&,uint64_t token,
                            const CallIdentity& actor,const CallIdentity& manager,const CallIdentity& function,uint64_t& name){
                        return static_cast<e33_runtime_scene::Owner*>(owner)->visual_parameter_context(base,token,actor,manager,function,name);
                    };
                    authority.arena=[](void* owner,uint64_t base,uint64_t,StrongLeasePool<>&,uint64_t token,const CallIdentity& actor,CallIdentity& arena){
                        return static_cast<e33_runtime_scene::Owner*>(owner)->visual_parameter_arena(base,token,actor,arena);
                    };
                    authority.copy_arena=[](void* owner,uint64_t base,uint64_t,StrongLeasePool<>&,uint64_t token,
                            const CallIdentity& actor,const CallIdentity& arena,void* destination){
                        return static_cast<e33_runtime_scene::Owner*>(owner)->visual_parameter_copy_arena(base,token,actor,arena,destination);
                    };
                    // No dispatch callback in v172: preflight proves only the
                    // owned arena/parameter connection, never combat readiness.
                }
#endif
#endif
#if E33_RUNTIME_CINEMATIC_VERSION >= 195
                if(!authority.owner&&session_enemy_spawn.is_trigger_anchor()&&p.operation>=128){
                    authority.owner=&session_enemy_spawn;
                    authority.owns=[](void* owner,uint64_t base,uint64_t session,StrongLeasePool<>& pool,uint64_t token,
                            const CallIdentity& actor,uint64_t& name){
                        return static_cast<e33_enemy_spawn::Owner*>(owner)->owned_instance_name(base,session,pool,token,actor,name);
                    };
                    authority.entry=[](void* owner,uint64_t base,uint64_t session,StrongLeasePool<>& pool,uint64_t token,
                            const CallIdentity& actor,const CallIdentity& manager,const CallIdentity& function,uint64_t& name){
                        return static_cast<e33_enemy_spawn::Owner*>(owner)->owned_entry_context(base,session,pool,token,actor,manager,function,name);
                    };
                    authority.arena=[](void* owner,uint64_t base,uint64_t session,StrongLeasePool<>& pool,uint64_t token,const CallIdentity& actor,CallIdentity& arena){
                        return static_cast<e33_enemy_spawn::Owner*>(owner)->owned_entry_arena(base,session,pool,token,actor,arena);
                    };
                    authority.copy_arena=[](void* owner,uint64_t base,uint64_t session,StrongLeasePool<>& pool,uint64_t token,
                            const CallIdentity& actor,const CallIdentity& arena,void* destination){
                        return static_cast<e33_enemy_spawn::Owner*>(owner)->copy_entry_arena(base,session,pool,token,actor,arena,destination);
                    };
                    authority.dispatch=[](void* owner,uint64_t base,uint64_t session,StrongLeasePool<>& pool,uint64_t token,
                            const CallIdentity& actor,const CallIdentity& manager,const CallIdentity& function){
                        auto& trigger=*static_cast<e33_enemy_spawn::Owner*>(owner);CallIdentity bound{};
                        if(!trigger.owned_entry_arena(base,session,pool,token,actor,bound))return false;
                        for(auto& arena:session_owned_battle_arenas){
                            const auto selected=arena.staged_actor();
                            if(selected.index==bound.index&&selected.serial==bound.serial&&selected.address==bound.address)
                                return trigger.note_trigger_entry_dispatch(base,session,pool,token,actor,manager,function,arena);
                        }
                        return false;
                    };
                }
#endif
                session_parameter_research.command(runtime_base,lease_session,session_leases,p,session_enemy_spawn,authority);
            }
            __except(EXCEPTION_EXECUTE_HANDLER) {p.error=3056;}
            return 0;
        }
#endif
#ifdef E33_NPC_PRESENTATION_RESEARCH
        if(p.operation>=136&&p.operation<=147){
#ifdef E33_BATTLE_PARAMETER_FRAME_RESEARCH
            if(session_parameter_research.holds_resources()&&p.operation!=137&&p.operation!=140&&p.operation!=144){p.error=3495;session_npc_research.snapshot(p);return 0;}
#endif
            __try {session_npc_research.command(runtime_base,lease_session,session_leases,p,session_enemy_spawn.has_work());}
            __except(EXCEPTION_EXECUTE_HANDLER){p.error=3453;session_npc_research.snapshot(p);}
            return 0;
        }
        if(p.operation==135){
            auto* raw=reinterpret_cast<uint8_t*>(&p);bool padding=true;
            for(size_t i=24;i<sizeof(p);++i)if((i<88||i>=136)&&raw[i])padding=false;
            if(p.version!=3||p.error||p.state||!p.owner||!padding){p.error=3420;return 0;}
            e33_npc_presentation::MembershipObservation observation{};bool observed=false;
            __try {observed=e33_npc_presentation::observe_memberships(runtime_base,p.inputs[0],p.inputs[1],p.inputs[2],observation);}
            __except(EXCEPTION_EXECUTE_HANDLER){p.error=3422;return 0;}
            if(!observed){p.error=3421;return 0;}
            static_assert(sizeof(observation)==56,"NPC membership observation extent");
            std::memcpy(raw+4096,&observation,sizeof(observation));p.state=1;return 0;
        }
        if(p.operation==134){
            auto* raw=reinterpret_cast<uint8_t*>(&p);bool padding=true;
            for(size_t i=24;i<sizeof(p);++i)if((i<88||i>=136)&&raw[i])padding=false;
            if(p.version!=3||p.error||p.state||!p.owner||!padding){p.error=3400;return 0;}
            bool admitted=false;
            __try {admitted=e33_npc_presentation::original_class_contract(runtime_base,p.inputs[0],p.inputs[1],p.inputs[2]);}
            __except(EXCEPTION_EXECUTE_HANDLER){p.error=3402;return 0;}
            if(!admitted){p.error=3401;return 0;}
            const uint32_t yes=1;std::memcpy(raw+4096,&yes,4);p.state=1;return 0;
        }
#endif
#ifdef E33_TIMELINE_ACTOR_POOL_SESSION
        if(p.operation>=e33_timeline_actor::construct&&p.operation<=e33_timeline_actor::retire){
            if((p.error=e33_timeline_actor::validate(p)))return 0;
            const auto operation=p.operation;
            const int slot=operation==e33_timeline_actor::construct?session_timeline_slots.reserve(p.owner):session_timeline_slots.find(p.owner);
            if(slot<0){p.error=operation==e33_timeline_actor::construct?3769:3770;return 0;}
            auto& actor=session_timeline_actors[slot];
            p.operation=operation==e33_timeline_actor::construct?120:operation==e33_timeline_actor::reveal?221:111;
            __try{actor.command(runtime_base,lease_session,session_leases,p);}
            __except(EXCEPTION_EXECUTE_HANDLER){p.error=3772;}
            p.operation=operation;
            if(operation==e33_timeline_actor::retire&&!p.error&&
               !session_timeline_slots.retired(static_cast<unsigned>(slot),p.error,actor.has_work()))p.error=3771;
            return 0;
        }
#endif
        if((p.operation>=110 && p.operation<=123)||p.operation==131||p.operation==132||p.operation==133||p.operation==221) {
#ifdef E33_BATTLE_PARAMETER_FRAME_RESEARCH
            // A failed private frame retains the trigger it was authorized by.
            // Normal shutdown already closes parameters before enemies/arenas.
            if(session_enemy_spawn.is_trigger_anchor()&&session_parameter_research.holds_resources()&&
               (p.operation==111||p.operation==118)){p.error=p.operation==111?407:3654;return 0;}
#endif
#ifdef E33_NPC_PRESENTATION_RESEARCH
            if(session_npc_research.has_work()){p.error=3452;return 0;}
#endif
            __try {session_enemy_spawn.command(runtime_base,lease_session,session_leases,p);}
            __except(EXCEPTION_EXECUTE_HANDLER) {p.error=2910;}
            return 0;
        }
#endif
#ifdef E33_MAP_LOAD_GATE_SESSION
        if(p.operation>=104&&p.operation<=106){
            __try{session_map_assets.command(runtime_base,lease_session,session_leases,p);}
            __except(EXCEPTION_EXECUTE_HANDLER){session_map_assets.quarantine();p.error=2169;}
            return 0;
        }
        if(p.operation>=99&&p.operation<=103){
            __try{session_map_load_gate.command(runtime_base,p);}
            __except(EXCEPTION_EXECUTE_HANDLER){session_map_load_gate.quarantine();p.error=2142;}
            return 0;
        }
#endif
        if(p.operation>=93 && (p.operation<=97
#ifdef E33_RETIRED_WORLD_SESSION
            ||(p.version==3 && (p.operation==98||p.operation==107))
#endif
            )) {
            __try {session_map_runtime.command(runtime_base,lease_session,session_leases,p);}
            __except(EXCEPTION_EXECUTE_HANDLER) {session_map_runtime.quarantine();p.error=2109;}
            return 0;
        }
#ifdef E33_RUNTIME_CINEMATIC_SESSION
        if(p.operation>=70 && p.operation<=
#ifdef E33_RUNTIME_SCENE_EDITOR_SESSION
            98
#else
            73
#endif
#if defined(E33_RUNTIME_SCENE_EDITOR_SESSION) && E33_RUNTIME_CINEMATIC_VERSION >= 171
            || p.operation==148
#endif
#if defined(E33_RUNTIME_SCENE_EDITOR_SESSION) && E33_RUNTIME_CINEMATIC_VERSION >= 172
            || p.operation==149
#endif
#if defined(E33_RUNTIME_SCENE_EDITOR_SESSION) && E33_RUNTIME_CINEMATIC_VERSION >= 174
            || p.operation==150
#endif
        ) {
#ifdef E33_BATTLE_PARAMETER_FRAME_RESEARCH
            if(session_parameter_research.holds_resources() && p.operation!=73){p.error=3495;return 0;}
#endif
            __try {session_runtime_cinematic.command(runtime_base,p,session_builder.active() || session_mesh.active() || session_sequence.active());}
            __except(EXCEPTION_EXECUTE_HANDLER) {session_runtime_cinematic.quarantine();p.error=2015;}
            return 0;
        }
        if(p.operation>=20 &&
#ifdef E33_RETIRED_WORLD_SESSION
            p.operation!=68 &&
#endif
            session_runtime_cinematic.active()){p.error=2001;return 0;}
#endif
        if(p.operation>=20) {session_builder.command(runtime_base,lease_session,session_leases,p);p.step=session_builder.step();return 0;}
        session_mesh.command(runtime_base,lease_session,session_leases,p);session_mesh.reply(p);return 0;
    }
#endif
#ifdef E33_GROWING_LEASE_SESSION
    case SessionLeasePolicy: {
        auto& p=*reinterpret_cast<LeasePolicyPacket*>(packet->console_text);
        if(p.version!=1 || (p.operation!=1 && p.operation!=2) || p.error || p.active || p.peak || p.capacity || p.count || p.storage_bytes) {
            p.error=411;return 0;
        }
        for(const auto& owner:p.owners) if(owner.owner || owner.active || owner.peak) { p.error=411;return 0; }
        if(p.operation==1) {
            if(packet->lease_owner || !session_leases.configure(p.limit,p.quota,p.reserve)) { p.error=403;return 0; }
        } else if(p.limit || p.quota || p.reserve) { p.error=411;return 0; }
        p.limit=session_leases.limit();p.quota=session_leases.quota();p.reserve=session_leases.reserve();
        p.active=session_leases.active();p.peak=session_leases.peak();p.capacity=session_leases.capacity();
        p.storage_bytes=session_leases.storage_bytes();
        session_leases.owner_statistics([&](uint64_t owner,uint32_t active,uint32_t peak) {
            p.owners[p.count++]={owner,active,peak};});
        return 0;
    }
#endif
#ifdef E33_CINEMATIC_WIDGET_SESSION
    case SessionCinematicWidget: {
        auto& wire=*reinterpret_cast<CinematicWidgetPacket*>(packet->console_text);
        if(wire.operation==2 && session_sequence.active()) { wire.error=1511;return 0; }
        session_widget_hook.command(runtime_base,lease_session,session_leases,session_sequence,wire);
        return 0;
    }
#endif
#ifdef E33_CINEMATIC_SOUND_EVENT_SESSION
    case SessionCinematicSoundEvent: {
        auto& wire=*reinterpret_cast<CinematicSoundEventPacket*>(packet->console_text);
        if(wire.operation==2 && session_sequence.active()) { wire.error=1501; return 0; }
        session_sound_event.command(runtime_base,lease_session,session_leases,session_sequence,session_music_audio,wire);
        return 0;
    }
#endif
#ifdef E33_MUSIC_AUDIO_SESSION
    case SessionMusicAudioOwner: {
        auto& wire=*reinterpret_cast<MusicAudioOwnerPacket*>(packet->console_text);
#ifdef E33_CINEMATIC_EPOCH_RETIRE_SESSION
        if(wire.operation==5) {
            session_music_audio.retire_command(runtime_base,lease_session,session_leases,session_override,wire);
            return 0;
        }
#endif
        if(wire.operation==2 && session_sequence.active()) { wire.error=1491; return 0; }
        session_music_audio.command(runtime_base,lease_session,session_leases,session_menu.menu.active(),wire,
            &session_menu.player,session_menu.owner);
        return 0;
    }
#endif
#ifdef E33_AUDIO_ISOLATION_SESSION
    case SessionPictoProgression: {
        auto& wire=*reinterpret_cast<PictoProgressionPacket*>(packet->console_text);
        if(session_sequence.active() || session_picto_batch.active()) { wire.error=1712; return 0; }
        picto_progression(runtime_base,wire);
        return 0;
    }
#ifdef E33_ZONE_TRAVEL_SESSION
    case SessionQAEncounter: {
        auto& wire=*reinterpret_cast<QAEncounterPacket*>(packet->console_text);
        if(session_sequence.active() || session_picto_batch.active()){wire.error=1905;return 0;}
        if(wire.operation==1)qa_encounter_reset(runtime_base,wire);else qa_mime_arena(runtime_base,wire);return 0;
    }
    case SessionZoneTravel: {
        auto& wire=*reinterpret_cast<ZoneTravelPacket*>(packet->console_text);
        if(session_sequence.active() || session_picto_batch.active() || (wire.operation==1 && session_menu.menu.active())){wire.error=1812;return 0;}
        zone_travel(runtime_base,wire);return 0;
    }
#endif
    case SessionPictoBatch: {
        auto& wire=*reinterpret_cast<PictoBatchPacket*>(packet->console_text);
        if(wire.operation==1 && session_sequence.active()){wire.error=1712;return 0;}
        session_picto_batch.command(runtime_base,packet->lease_owner,wire);
        return 0;
    }
    case SessionScopedAssignment: {
        auto& wire=*reinterpret_cast<ScopedAssignmentPacket*>(packet->console_text);
#ifdef E33_MUSIC_AUDIO_SESSION
        if(wire.operation==2 && session_music_audio.active()) { wire.error=1481; return 0; }
#endif
        if(wire.operation==2 && session_sequence.active()) { wire.error=1481; return 0; }
        session_override.command(runtime_base,lease_session,session_leases,session_menu.menu.active(),wire);
        return 0;
    }
#endif
#ifdef E33_SEQUENCE_PLAYER_SESSION
    case SessionSequenceOwner: {
        auto& wire=*reinterpret_cast<SequenceOwnerPacket*>(packet->console_text);
#ifdef E33_SEQUENCE_AUTHORED_BINDING_SESSION
        if(wire.operation==16 || wire.operation==17) {
            __try {session_sequence.authored_command(runtime_base,lease_session,session_leases,session_menu,wire);}
            __except(EXCEPTION_EXECUTE_HANDLER) {session_sequence.authored_fault(wire);}
            return 0;
        }
#endif
#ifdef E33_SEQUENCE_RETIREMENT_SESSION
        if(wire.operation==7) {
            __try {
#ifdef E33_CINEMATIC_EPOCH_RETIRE_SESSION
                if(!session_sequence.valid_retirement_request(wire)) {wire.error=1471;wire.state=session_sequence.current_state();return 0;}
                e33_retired_world::Snapshot source{};CallIdentity player{};
                auto error=session_sequence.retirement_authority(runtime_base,lease_session,session_leases,wire.owner,source,player);
                if(!error)error=retire_cinematic_menu_actions(source);
#ifdef E33_CINEMATIC_WIDGET_SESSION
                if(!error)error=session_widget_hook.retire(runtime_base,source,player);
#endif
#ifdef E33_CINEMATIC_SOUND_EVENT_SESSION
                if(!error)error=session_sound_event.retire(runtime_base,source,player);
#endif
#ifdef E33_MUSIC_AUDIO_SESSION
                if(!error)error=session_music_audio.retire_world(runtime_base,lease_session,session_leases,source,session_override,session_sequence.captured_menu_owner());
#endif
                if(error) {wire.error=error;wire.state=session_sequence.current_state();return 0;}
#endif
                session_sequence.retire(runtime_base,lease_session,session_leases,wire);
            }
            __except(EXCEPTION_EXECUTE_HANDLER) {wire.error=1596;wire.state=2;}
            return 0;
        }
#endif
        session_sequence.command(runtime_base,session_menu,wire,session_pod_validation);
#ifdef E33_CINEMATIC_WIDGET_SESSION
        if(wire.operation==2 && !wire.error && !wire.state) {
            // Use the common sequence-stopped cleanup, including independent
            // audio/reference restoration if widget detachment fails.
            wire.error=guarded_sequence_close();
        }
#else
#ifdef E33_CINEMATIC_SOUND_EVENT_SESSION
        if(wire.operation==2 && !wire.error && !wire.state) wire.error=session_sound_event.close(runtime_base);
#endif
#endif
#ifdef E33_AUDIO_CLEANUP_DIAGNOSTICS_SESSION
        if(wire.operation==2 && wire.error!=1470 && wire.error!=1471) {
            const auto diagnostic=session_music_audio.cleanup_diagnostics();
            std::memset(&wire.stop,0,sizeof(wire.stop)+sizeof(wire.destroy));
            std::memcpy(&wire.stop,&diagnostic,sizeof(diagnostic));
        }
#endif
        return 0;
    }
#endif
#ifdef E33_MEDIA_SESSION
    case SessionMediaOwner:
#ifdef E33_CINEMATIC_EPOCH_RETIRE_SESSION
        {
            auto& wire=*reinterpret_cast<MediaOwnerPacket*>(packet->console_text);
            if(wire.operation==4) {
                e33_retired_world::Snapshot source{};
                auto error=session_media.retirement_authority(runtime_base,lease_session,session_leases,wire,source);
                if(!error)error=retire_cinematic_menu_actions(source);
                if(!error)error=session_music_audio.retire_world(runtime_base,lease_session,session_leases,source,session_override,session_media.captured_menu_owner());
                if(error) {wire.error=error;wire.state=session_media.current_state();return 0;}
            }
        }
#endif
        session_media.command(runtime_base,lease_session,session_leases,session_menu,
            *reinterpret_cast<MediaOwnerPacket*>(packet->console_text));
        return 0;
#endif
#ifdef E33_PAUSE_MENU_SESSION
    case SessionPauseAttachment:
        pause_attachment.command(runtime_base,lease_session,session_leases,
            *reinterpret_cast<PauseAttachmentPacket*>(packet->console_text));
        return 0;
#endif
#ifdef E33_UI_BATCH_SESSION
    case e33_ui::Action:
        ui_batch_run(runtime_base,packet,backend_command);
        return 0;
#endif
#ifdef E33_KEYBIND_SESSION
    case SessionKeybind:
        session_keys.command(packet->keys, console_toggle_key);
        return 0;
#endif
#ifdef E33_TRACE_SESSION
    case SessionTrace:
        session_traces.command(packet->trace);
        return 0;
#endif
#ifdef E33_BUTTON_ACTION_SESSION
#ifdef E33_MULTI_BUTTON_SESSION
    case SessionMultiButton:
        guarded_multi_button(packet->multi_button);
        return 0;
#endif
    case SessionButtonAction:
        guarded_button_action(packet->button_action);
        return 0;
#endif
#ifdef E33_MENU_SESSION
    case SessionMenu:
        guarded_menu_command(packet->menu);
#ifdef E33_BUTTON_REFERENCE_SESSION
        packet->request.result=static_cast<uint32_t>(session_menu.child_slate.slate.state);
#endif
        return 0;
#endif
#ifdef E33_TEXT_SESSION
    case SessionTextInvoke: {
#ifdef E33_STRING_SESSION
        if(packet->text.retained.call.version==kStringCallVersion) {
            if(!session_string_frame.available()) { packet->text.retained.call.error=765; return 0; }
            session_string_packet=packet->text;
            CallRetention retention{&session_string_packet.retained,retain_preflight,retain_output};
            auto error=guarded_string_invoke(&retention);
            session_string_packet.retained.call.error=error;
            packet->text=session_string_packet;
            // Unknown dispatch remains in pinned native storage; never retry or free it.
            session_string_frame.reset();
            return 0;
        }
#endif
        if(!session_text.frame.available()) { packet->text.retained.call.error=230; return 0; }
        session_text_packet=packet->text;
        session_text.base=runtime_base;
        session_text.packet=&session_text_packet;
        CallRetention retention{&session_text_packet.retained,retain_preflight,retain_output};
        auto error=guarded_text_invoke(&retention);
        // Includes normal pre/post-dispatch rejection and guarded SEH failure.
        // Unknown dispatch ownership is quarantined, never destructed or retried.
        const auto cleaned=guarded_text_cleanup();
        if(!error) error=TargetTextCall::error(cleaned);
        session_text_packet.retained.call.error=error;
        packet->text=session_text_packet;
        // Reset only after all owners were released. A deferred or uncertain
        // frame rejects subsequent text calls and remains available for close.
        session_text.frame.reset();
        return 0;
    }
#endif
#ifdef E33_ASSIGNMENT_SESSION
    case SessionObjectAssign: {
#ifdef E33_SCALAR_ASSIGNMENT_SESSION
        if(packet->assignment.version==2) {
            auto& scalar=*reinterpret_cast<ScalarAssignmentPacket*>(&packet->assignment);
            if(!session_leases.owns_object(lease_session,scalar.token,scalar.target.address)) { scalar.error=7; return 0; }
            assign_scalar(runtime_base,scalar);
            return 0;
        }
#endif
        auto& wire=packet->assignment;
        auto& assignment=wire.assignment;
        if(wire.version!=1 || wire.error || !valid_object_assignment(assignment)) {
            wire.error=6; return 0;
        }
        if(!session_leases.owns_object(lease_session,wire.target_token,assignment.target.address) ||
           (assignment.expected.address ? !session_leases.owns_object(lease_session,wire.expected_token,assignment.expected.address) : wire.expected_token!=0) ||
           (assignment.value.address ? !session_leases.owns_object(lease_session,wire.value_token,assignment.value.address) : wire.value_token!=0)) {
            wire.error=7; return 0;
        }
        TargetObjectAssignmentOps ops{runtime_base};
        wire.error=static_cast<uint32_t>(assign_object_property(ops,assignment));
        return 0;
    }
#endif
#ifdef E33_RETAINED_SESSION
    case SessionRetainedInvoke: {
        auto& retained=packet->retained;
        if(!retained_call_empty(retained)) { retained.call.error=412; return 0; }
        CallRetention retention{&retained,retain_preflight,retain_output};
#ifdef E33_SEQUENCE_PLAYER_SESSION
        if(retained.call.version==kSequenceCallVersion) {
#ifdef E33_AUTHORED_CURVE_SESSION
            if(session_curve_patch.quarantined()){retained.call.error=3783;return 0;}
#endif
            retained.call.error=session_sequence.create(runtime_base,lease_session,session_leases,session_menu,
                retained,&retention,session_pod_validation,E33_TRACE_ENTRY_VALIDATION);
            return 0;
        }
#endif
#ifdef E33_OWNED_SOUND_SESSION
        if(retained.call.entry_rva==0x3736020) {
            retained.call.error=session_menu.menu.active() ? session_music_audio.create_sound(
                runtime_base,lease_session,session_leases,session_menu.player,retained,
                &retention,E33_TRACE_ENTRY_VALIDATION) : 1494;
            return 0;
        }
#endif
#ifdef E33_SEQUENCE_SESSION
        if(retained.call.version==kAssetCallVersion) {
            CallAssetValidation assets{&retained,validate_target_asset};
            retained.call.error=reflected_call(runtime_base,retained.call,&retention,session_pod_validation,
                nullptr,nullptr,false,E33_TRACE_ENTRY_VALIDATION,false,&assets);
            return 0;
        }
#endif
#ifdef E33_ENUM_SESSION
        if(retained.call.version==kEnumCallVersion) {
            CallEnumValidation enums{&retained,validate_target_enum};
            retained.call.error=reflected_call(runtime_base,retained.call,&retention,session_pod_validation,nullptr,&enums,false,E33_TRACE_ENTRY_VALIDATION);
            return 0;
        }
#endif
        retained.call.error=reflected_call(runtime_base,retained.call,&retention,session_pod_validation,nullptr,nullptr,false,E33_TRACE_ENTRY_VALIDATION);
        return 0;
    }
#endif
#ifdef E33_LEASE_SESSION
#ifdef E33_LEASE_RELEASE_BATCH_SESSION
    case e33_lease_batch::Action:
        lease_release_batch(*reinterpret_cast<e33_lease_batch::Packet*>(packet->console_text));return 0;
#endif
#ifdef E33_CONSOLE_COLORS_SESSION
    case e33_console_color::Action: {
        e33_console_color::Packet status;
        std::memcpy(&status,packet->console_text,sizeof(status));
        if(!e33_console_color::valid(status))return 1701;
        ConsoleColorsRuntime::status(status);
        std::memcpy(packet->console_text,&status,sizeof(status));return 0;
    }
#endif
#ifdef E33_METADATA_STABILIZE_SESSION
    case SessionStableLeaseAcquire: {
        auto& lease=packet->lease;
        TargetStrongReferenceOps ops{runtime_base,lease.object};
        stable_lease_acquire(lease,ops,session_leases,lease_session);return 0;
    }
#endif
    case SessionLeaseAcquire:
    case SessionLeaseRelease:
    case SessionLeaseStatus: {
        auto& lease=packet->lease;
        bool empty=lease.object.index==-1 && !lease.object.serial && !lease.object.address;
        if(lease.version!=kLeaseVersion || lease.error || lease.outcome || lease.active ||
           (packet->request.action==SessionLeaseAcquire &&
               (lease.token || lease.object.index<0 || !lease.object.address)) ||
           (packet->request.action!=SessionLeaseAcquire && !empty) ||
           (packet->request.action==SessionLeaseStatus && lease.token)) {
            lease.error=411; lease.outcome=LeaseNotDispatched; return 0;
        }
        TargetStrongReferenceOps ops{runtime_base,lease.object};
        lease.outcome=LeaseUnknown;
        StrongLeaseResult result=StrongLeaseResult::Ok;
        if(packet->request.action==SessionLeaseAcquire)
            result=session_leases.acquire(ops,lease_session,lease.object.address,lease.token);
        else if(packet->request.action==SessionLeaseRelease) {
            if(lease_release_protected(lease.token))result=StrongLeaseResult::Busy;
            else
            result=session_leases.release(ops,lease_session,lease.token);
        }
        lease.error=static_cast<uint32_t>(result);
        lease.active=session_leases.active();
        lease.outcome=LeaseCompleted;
        return 0;
    }
#endif
#ifdef E33_REFLECTED_SESSION
    case SessionReflectedInvoke:
        packet->call.error=reflected_call(runtime_base,packet->call,nullptr,session_pod_validation,nullptr,nullptr,false,E33_TRACE_ENTRY_VALIDATION);
        return 0; // A rejected plan is a normal response, not a transport failure.
#endif
    case SessionConsoleKey: {
        if (!attachment_valid(runtime_base)) return 132;
        wchar_t* end=nullptr;
        unsigned long key=wcstoul(packet->console_text,&end,10);
        if (!end || end==packet->console_text || *end || (key && (key<VK_F1 || key>VK_F12))) return 135;
#ifdef E33_KEYBIND_SESSION
        if(key && session_keys.contains(static_cast<uint32_t>(key))) return 135;
#endif
        if (!exact_name(runtime_base,runtime_base+0x94dfb50,"Typing") ||
            !exact_name(runtime_base,runtime_base+0x94dfb58,"Open")) return 136;
        console_toggle_key=static_cast<unsigned>(key); packet->request.result=key; return 0;
    }
    case SessionConsoleNames:
        if (!attachment_valid(runtime_base)) return 132;
        if (!set_console_names(packet->console_text)) return 134;
        packet->request.result=0; return 0;
    case SessionConsolePoll: {
        if (!attachment_valid(runtime_base)) return 132;
        packet->request.result=poll_console_command(packet->console_text)?1:0;
        packet->console_dropped=console_dropped; console_dropped=0;
#ifdef E33_CONSOLE_COLORS_SESSION
        // ConsolePoll does not use observer output. SessionDrain independently
        // copies session_events, so this view cannot enter observer delivery.
        static_assert(sizeof(e33_console_color::Packet)<=sizeof(packet->events));
        e33_console_color::Packet color_status;
        ConsoleColorsRuntime::status(color_status);
        std::memcpy(&packet->events,&color_status,sizeof(color_status));
#endif
        return 0;
    }
    case SessionConsoleExecute:
    case SessionConsolePrint: {
        if (!attachment_valid(runtime_base)) return 132;
        size_t length=wcsnlen_s(packet->console_text,32769);
        if (length>=32769 || (packet->request.action==SessionConsoleExecute && length>4096)) return 133;
        if (packet->request.action==SessionConsolePrint) console_write(attached_console,packet->console_text);
        else {
            ConsoleString value{packet->console_text,static_cast<int32_t>(length+1),static_cast<int32_t>(length+1)};
            console_original_command(reinterpret_cast<void*>(attached_console),&value);
        }
        packet->request.result=0; return 0;
    }
    case SessionConsoleAttach: {
        if (observing) return 120;
        uint32_t error=attach_console(runtime_base,&target);
        packet->request.result=attached_console;
        return error;
    }
    case SessionConsoleDetach: console_toggle_key=0; return detach_console(runtime_base,false);
    case SessionConsoleStatus:
        if (attached_console && !attachment_valid(runtime_base)) return 128;
        packet->request.result=attached_console; return 0;
    case SessionEnable:
        if (observing) return 0;
        { uint32_t error = invoke_fixed_guarded(&target); if (error) return error; }
        session_events = {};
        if (!install_observer(reinterpret_cast<void* volatile*>(target_function + 0xd8),
                reinterpret_cast<ObserverEntry>(runtime_base + 0x333be80), &session_events, target_object, target.target_tid)) return 62;
        observing = true; return 0;
    case SessionDisable:
        if (!remove_observer()) return 63;
        observing = false; return 0;
    case SessionInvoke: {
        uint32_t error = invoke_fixed_guarded(&target, observing ? reinterpret_cast<uint64_t>(&observe) : 0);
        packet->request.result = target.result; return error;
    }
    case SessionDrain: drain_observer(&packet->events); return 0;
    case SessionPing: packet->request.result = observing ? 1 : 0; return 0;
    default: return 64;
    }
}
#ifdef E33_LEASE_SESSION
static StrongLeaseResult guarded_lease_close() {
    __try {
        TargetStrongReferenceOps ops{runtime_base,{-1,0,0}};
        return session_leases.close(ops,lease_session);
    } __except(EXCEPTION_EXECUTE_HANDLER) { return StrongLeaseResult::Quarantined; }
}
#endif
#ifdef E33_MESH_SESSION
static uint32_t guarded_mesh_close() {
#if E33_RUNTIME_CINEMATIC_VERSION>=186
    __try {const auto e=session_encounter_tuning.close(runtime_base,lease_session,session_leases);if(e)return e;}
    __except(EXCEPTION_EXECUTE_HANDLER){return 3637;}
#endif
#ifdef E33_ENEMY_SPAWN_SESSION
#ifdef E33_BATTLE_PARAMETER_FRAME_RESEARCH
    __try {const auto e=session_parameter_research.close(runtime_base,lease_session,session_leases);if(e)return e;}
    __except(EXCEPTION_EXECUTE_HANDLER) {return 3056;}
#endif
#ifdef E33_NPC_PRESENTATION_RESEARCH
    __try {const auto e=session_npc_research.close(runtime_base,lease_session,session_leases);if(e)return e;}
    __except(EXCEPTION_EXECUTE_HANDLER){return 3453;}
#endif
#ifdef E33_TIMELINE_ACTOR_POOL_SESSION
    for(unsigned slot=e33_timeline_actor::capacity;slot-->0;){
        if(!session_timeline_slots.reserved(slot))continue;
        __try{
            auto& actor=session_timeline_actors[slot];
            const auto error=actor.close(runtime_base,lease_session,session_leases);if(error)return error;
            if(!session_timeline_slots.retired(slot,error,actor.has_work()))return 3771;
        }__except(EXCEPTION_EXECUTE_HANDLER){return 3772;}
    }
#endif
    __try {const auto e=session_enemy_spawn.close(runtime_base,lease_session,session_leases);if(e)return e;}
    __except(EXCEPTION_EXECUTE_HANDLER) {return 2910;}
#if E33_RUNTIME_CINEMATIC_VERSION>=177
#if E33_RUNTIME_CINEMATIC_VERSION>=191
    for(unsigned slot=e33_owned_arena::Slots::capacity;slot-->0;){
        __try {
            auto& arena=session_owned_battle_arenas[slot];
            const auto e=arena.close(runtime_base,lease_session,session_leases);if(e)return e;
            if(!session_owned_arena_slots.retired(slot,e,arena.has_work()))return 3641;
        }__except(EXCEPTION_EXECUTE_HANDLER){return 3602;}
    }
#else
    __try {const auto e=session_owned_battle_arena.close(runtime_base,lease_session,session_leases);if(e)return e;}
    __except(EXCEPTION_EXECUTE_HANDLER) {return 3602;}
#endif
#endif
#endif
#ifdef E33_MAP_LOAD_GATE_SESSION
    __try {const auto e=session_map_load_gate.close(runtime_base);if(e)return e;}
    __except(EXCEPTION_EXECUTE_HANDLER) {return 2142;}
#endif
    __try {const auto e=session_map_runtime.close(runtime_base,lease_session,session_leases);if(e)return e;}
    __except(EXCEPTION_EXECUTE_HANDLER) {return 2109;}
#ifdef E33_MAP_LOAD_GATE_SESSION
    __try {const auto e=session_map_assets.close(runtime_base,lease_session,session_leases);if(e)return e;}
    __except(EXCEPTION_EXECUTE_HANDLER) {return 2169;}
#endif
#ifdef E33_RUNTIME_CINEMATIC_SESSION
    __try {const auto e=session_runtime_cinematic.close(1);if(e)return e;}
    __except(EXCEPTION_EXECUTE_HANDLER) {return 2015;}
#endif
    __try {const auto e=session_builder.stop(runtime_base,lease_session,session_leases,true);if(e)return e;return session_mesh.close(runtime_base,lease_session,session_leases);}
    __except(EXCEPTION_EXECUTE_HANDLER) {return 1808;}
}
static uint32_t guarded_mesh_poll() {
    __try {return session_mesh.poll(runtime_base,lease_session,session_leases);}
    __except(EXCEPTION_EXECUTE_HANDLER) {return 1808;}
}
#endif
uint32_t backend_close() {
#ifdef E33_MESH_SESSION
    const auto mesh_cleanup=guarded_mesh_close();
    if(mesh_cleanup==407 && !backend_shutting_down())return kSessionCloseDeferred;
    if(mesh_cleanup)return mesh_cleanup;
#endif
#ifdef E33_AUDIO_ISOLATION_SESSION
    session_picto_batch.stop();
#endif
#ifdef E33_SEQUENCE_PLAYER_SESSION
    const auto sequence_cleanup=guarded_sequence_close();
    if(sequence_cleanup==407 && !backend_shutting_down()) return kSessionCloseDeferred;
    if(sequence_cleanup) return sequence_cleanup;
#endif
#ifdef E33_MEDIA_SESSION
    const auto media_cleanup=guarded_media_close();
    if(media_cleanup==407 && !backend_shutting_down()) return kSessionCloseDeferred;
    if(media_cleanup) return media_cleanup;
#endif
#ifdef E33_KEYBIND_SESSION
    session_keys.close(); // Revoke input even when other cleanup must defer.
#endif
#ifdef E33_ZONE_TRAVEL_SESSION
    if(!backend_shutting_down() && !qa_mime_restore(runtime_base))return kSessionCloseDeferred;
#endif
    uint32_t lease_cleanup_error=0;
#ifdef E33_AUTHORED_CURVE_SESSION
    if(session_curve_patch.quarantined())lease_cleanup_error=3783;
#endif
#ifdef E33_SEQUENCER_ARRAY_SESSION
    if(session_sequencer_array.quarantined())lease_cleanup_error=3743;
#endif
#ifdef E33_TRACE_SESSION
    const auto trace_result = session_traces.close(backend_shutting_down());
    if (trace_result == 934) return kSessionCloseDeferred;
    if (trace_result) trace_cleanup_error = trace_result;
    if(!lease_cleanup_error) lease_cleanup_error = trace_cleanup_error;
#endif
#ifdef E33_PAUSE_MENU_SESSION
    const auto pause_cleanup=guarded_pause_close(backend_shutting_down());
    if(pause_cleanup==kSessionCloseDeferred && !backend_shutting_down()) return kSessionCloseDeferred;
    if(pause_cleanup && !lease_cleanup_error) lease_cleanup_error=pause_cleanup;
#endif
#ifdef E33_TEXT_SESSION
    const auto text_cleanup=guarded_text_cleanup();
    if(text_cleanup==TextFrameResult::CleanupDeferred && !backend_shutting_down())
        return kSessionCloseDeferred;
    if(text_cleanup==TextFrameResult::Ok) session_text.frame.reset();
    else if(!backend_shutting_down() && !lease_cleanup_error) lease_cleanup_error=TargetTextCall::error(text_cleanup);
    // On terminal teardown or uncertain ownership, the pinned module retains
    // the bounded frame. It is not unloaded, reset, or reused by a new session.
#endif
#ifdef E33_LEASE_SESSION
#ifdef E33_MENU_SESSION
    const auto menu_cleanup=guarded_menu_close();
    if(menu_cleanup==MenuResult::Deferred && !backend_shutting_down()) return kSessionCloseDeferred;
    const bool menu_released=menu_cleanup==MenuResult::Ok && !session_menu.menu.active();
    if(!menu_released && !lease_cleanup_error) lease_cleanup_error=801;
    // An unresolved menu pins the pool. Continue detaching console/observer
    // hooks, but never release its widgets or adopt them in another session.
    if(lease_session && menu_released
#ifdef E33_AUTHORED_CURVE_SESSION
       && !session_curve_patch.quarantined()
#endif
#ifdef E33_SEQUENCER_ARRAY_SESSION
       && !session_sequencer_array.quarantined()
#endif
#ifdef E33_PAUSE_MENU_SESSION
       && !pause_cleanup
#endif
       ) {
#else
    if(lease_session
#ifdef E33_AUTHORED_CURVE_SESSION
       && !session_curve_patch.quarantined()
#endif
#ifdef E33_SEQUENCER_ARRAY_SESSION
       && !session_sequencer_array.quarantined()
#endif
       ) {
#endif
        auto result=guarded_lease_close();
        // A normal GC interval may defer release. Keep the GT cleanup hook and
        // owner tracking until a subsequent message can finish the close.
        if(result==StrongLeaseResult::Deferred && !backend_shutting_down())
            return kSessionCloseDeferred;
        if(result==StrongLeaseResult::Ok) lease_session=0;
        else if(!backend_shutting_down() && !lease_cleanup_error) lease_cleanup_error=static_cast<uint32_t>(result);
        // During terminal engine teardown, engine-owned vtables remain valid;
        // quarantined storage is bounded and never reused by another session.
    }
#endif
    console_toggle_key=0;
    uint32_t result = detach_console_guarded(runtime_base,backend_shutting_down());
    if(!result) result=lease_cleanup_error;
    if (observing) {
        if (backend_shutting_down()) detach_observer_storage();
        else if (!lifetime_valid()) { detach_observer_storage(); result = 65; }
        else if (!remove_observer()) result = 66;
    }
    observing = false; runtime_base = target_object = target_function = 0;
    return result;
}
#ifdef E33_MESH_SESSION
bool backend_mesh_wake_needed(){return session_mesh.animating() || session_builder.active()
#ifdef E33_MAP_LOAD_GATE_SESSION
    || session_map_load_gate.active()
#endif
#ifdef E33_RUNTIME_CINEMATIC_SESSION
    || session_runtime_cinematic.active()
#endif
#ifdef E33_SEQUENCE_FLIGHT_SESSION
    // Authored timelines also sample held input on the game thread. Keep the
    // bounded watcher awake even when no mouse or controller RPC arrives.
    || session_sequence.active()
#endif
    ;}
#endif
void backend_message(MSG* message) {
#ifdef E33_MAP_LOAD_GATE_SESSION
    __try{session_map_load_gate.poll(runtime_base,lease_session,session_leases);}
    __except(EXCEPTION_EXECUTE_HANDLER){session_map_load_gate.quarantine();}
#endif
#if E33_RUNTIME_CINEMATIC_VERSION>=186
    __try {session_encounter_tuning.poll(runtime_base,lease_session,session_leases);}
    __except(EXCEPTION_EXECUTE_HANDLER) {} // owner remains available for cleanup
#endif
#ifdef E33_NPC_PRESENTATION_RESEARCH
    __try {session_npc_research.poll_entry(runtime_base);}
    __except(EXCEPTION_EXECUTE_HANDLER) {} // Unknown startup/activity retains the NPC.
#endif
#ifdef E33_ENEMY_SPAWN_SESSION
    __try {session_enemy_spawn.poll_helper_entry(runtime_base);}
    __except(EXCEPTION_EXECUTE_HANDLER) {} // pending journal stays intact on uncertain reads
#if E33_RUNTIME_CINEMATIC_VERSION >= 195
    for(auto& arena:session_owned_battle_arenas){
        __try {arena.poll_helper_entry(runtime_base);}
        __except(EXCEPTION_EXECUTE_HANDLER) {} // retain its paired startup journal
    }
#endif
#endif
#ifdef E33_MESH_SESSION
#ifdef E33_RUNTIME_CINEMATIC_SESSION
#ifdef E33_RUNTIME_SCENE_EDITOR_SESSION
    session_runtime_cinematic.pointer_message(message);
#endif
    __try {if(session_runtime_cinematic.active())session_runtime_cinematic.poll();}
    __except(EXCEPTION_EXECUTE_HANDLER) {session_runtime_cinematic.quarantine();}
#endif
    if(session_builder.active())session_builder.poll(runtime_base,lease_session,session_leases,
        (!session_menu.menu.active() || session_builder.owns_menu(session_menu.widget)) && attachment_valid(runtime_base) && local_read<uint64_t>(attached_console+0xd8)==0);
    if(session_mesh.active())guarded_mesh_poll();
#endif
#ifdef E33_AUDIO_ISOLATION_SESSION
    if(session_picto_batch.active())session_picto_batch.tick(runtime_base,lifetime_valid() && !session_sequence.active());
#endif
#ifdef E33_SEQUENCE_PLAYER_SESSION
#ifdef E33_SEQUENCE_FLIGHT_SESSION
    __try {session_sequence.editor_tick(runtime_base,session_menu,session_pod_validation,lifetime_valid() && attachment_valid(runtime_base) && local_read<uint64_t>(attached_console+0xd8)==0);}
    __except(EXCEPTION_EXECUTE_HANDLER){session_sequence.editor_fault();}
#endif
    if(session_sequence.active()
#ifdef E33_AUDIO_ISOLATION_SESSION
       || session_override.active()
#endif
#ifdef E33_MUSIC_AUDIO_SESSION
       || session_music_audio.active()
#endif
#ifdef E33_CINEMATIC_SOUND_EVENT_SESSION
       || session_sound_event.active()
#endif
#ifdef E33_CINEMATIC_WIDGET_SESSION
       || session_widget_hook.active()
#endif
    ) {
        TargetMenuOps<StrongLeasePool<>> sequence_context{session_menu,session_leases};
        if(!session_menu.menu.active() || sequence_context.context()==MenuContext::Terminal)
            guarded_sequence_close();
    }
#endif
#ifdef E33_MEDIA_SESSION
    if(session_media.active()) {
        TargetMenuOps<StrongLeasePool<>> media_context{session_menu,session_leases};
        if(!session_menu.menu.active() || media_context.context()==MenuContext::Terminal)
            guarded_media_close();
    }
#endif
#ifdef E33_TRACE_SESSION
    session_traces.maintain();
#endif
#ifdef E33_KEYBIND_SESSION
#ifdef E33_KEY_CAPTURE_SESSION
    // Capture belongs exclusively to the active SDK menu. Consume the paired
    // release even after the Python owner restores normal routes.
    static bool capture_down[256]{};
    const auto capture_key=static_cast<uint32_t>(message->wParam);
    const bool capture_press=message->message==WM_KEYDOWN || message->message==WM_SYSKEYDOWN;
    const bool capture_release=message->message==WM_KEYUP || message->message==WM_SYSKEYUP;
    if(capture_key<256 && capture_release && capture_down[capture_key]) {
        capture_down[capture_key]=false; message->message=WM_NULL; return;
    }
    if(session_keys.capturing() && session_menu.menu.active() && capture_key<256 && capture_press) {
        DWORD capture_pid=0;
        GetWindowThreadProcessId(GetForegroundWindow(), &capture_pid);
        const bool eligible=capture_pid==GetCurrentProcessId() && lifetime_valid() &&
            attachment_valid(runtime_base) && local_read<uint64_t>(attached_console+0xd8)==0;
        if(eligible) {
            const bool modifiers=(GetKeyState(VK_CONTROL)&0x8000)||(GetKeyState(VK_MENU)&0x8000)||
                (GetKeyState(VK_SHIFT)&0x8000)||(GetKeyState(VK_LWIN)&0x8000)||(GetKeyState(VK_RWIN)&0x8000);
            session_keys.press(capture_key,(message->lParam & (LPARAM(1)<<30))!=0,!modifiers);
            capture_down[capture_key]=true; message->message=WM_NULL; return;
        }
    }
#endif
#ifdef E33_MENU_ESCAPE_SESSION
    // Route only this builder's visible panel. Keep ordinary SDK menus and
    // text-entry keys untouched, and swallow the release after async close.
    static bool builder_blocked_z=false,builder_blocked_y=false,builder_blocked_g=false;
    const bool key_down=message->message==WM_KEYDOWN||message->message==WM_SYSKEYDOWN;
    const bool key_up=message->message==WM_KEYUP||message->message==WM_SYSKEYUP;
#ifdef E33_RUNTIME_SCENE_EDITOR_SESSION
    static bool scene_backspace_down=false;
    if(message->wParam==VK_BACK){
        if(key_up && scene_backspace_down){scene_backspace_down=false;message->message=WM_NULL;return;}
        if(key_down && scene_backspace_down){message->message=WM_NULL;return;}
        DWORD scene_foreground=0;GetWindowThreadProcessId(GetForegroundWindow(),&scene_foreground);
        if(key_down && scene_foreground==GetCurrentProcessId() && lifetime_valid() && attachment_valid(runtime_base) && local_read<uint64_t>(attached_console+0xd8)==0 && session_menu.menu.accepts_actions() && session_runtime_cinematic.timeline_shortcuts(session_menu.widget) && session_keys.contains(VK_BACK) && !(GetKeyState(VK_CONTROL)&0x8000) && !(GetKeyState(VK_MENU)&0x8000) && !(GetKeyState(VK_SHIFT)&0x8000)){
            session_keys.press(VK_BACK,(message->lParam&(LPARAM(1)<<30))!=0,true);
            scene_backspace_down=true;message->message=WM_NULL;return;
        }
    }
    static e33_runtime_scene::GameplayShortcutFilter scene_shortcut_keys;
    const bool scene_shortcut_block=session_runtime_cinematic.blocks_gameplay_shortcuts() && !session_menu.menu.active() &&
        lifetime_valid() && attachment_valid(runtime_base) && local_read<uint64_t>(attached_console+0xd8)==0;
    if(scene_shortcut_keys.consume(static_cast<unsigned>(message->wParam),key_down,key_up,scene_shortcut_block)){
        message->message=WM_NULL;return;
    }
#endif
    if(message->wParam=='Z'||message->wParam=='Y'||message->wParam=='G') {
        auto& held=message->wParam=='G'?builder_blocked_g:message->wParam=='Z'?builder_blocked_z:builder_blocked_y;
        const bool alt=(message->lParam&(LPARAM(1)<<29))||(GetKeyState(VK_MENU)&0x8000);
        if(key_up&&held){held=false;message->message=WM_NULL;return;}
        if(key_down&&session_builder.active()&&!session_menu.menu.active()&&lifetime_valid()&&attachment_valid(runtime_base)&&local_read<uint64_t>(attached_console+0xd8)==0&&
           (message->wParam=='Z'||message->wParam=='G'||alt)) {
            if(alt&&message->wParam!='G'&&!(message->lParam&(LPARAM(1)<<30)))session_builder.request_history(message->wParam=='Y');
            held=true;message->message=WM_NULL;return;
        }
    }
    // Consume rotation chords before SDK keybind dispatch (P used to play).
    static bool rotation_key_down[5]{};
    const unsigned rotation_key=message->wParam=='Y'?0:message->wParam=='P'?1:message->wParam=='R'?2:message->wParam==VK_OEM_PLUS?3:message->wParam==VK_ADD?4:5;
    if(rotation_key<5){
        if(key_up&&rotation_key_down[rotation_key]){rotation_key_down[rotation_key]=false;message->message=WM_NULL;return;}
        if(key_down&&session_builder.active()&&!session_builder.preview_active()&&!session_menu.menu.active()&&
           lifetime_valid()&&attachment_valid(runtime_base)&&local_read<uint64_t>(attached_console+0xd8)==0&&
           !(GetKeyState(VK_MENU)&0x8000)&&!(GetKeyState(VK_CONTROL)&0x8000)&&(rotation_key>=3||!(GetKeyState(VK_SHIFT)&0x8000))){
            rotation_key_down[rotation_key]=true;message->message=WM_NULL;return;
        }
    }
    static bool builder_menu_key_down[3]{};
    const unsigned builder_key=message->wParam==VK_ESCAPE?0:message->wParam==VK_F7?1:message->wParam==VK_F8?2:3;
    if(builder_key<3) {
        if(message->message==WM_KEYUP && builder_menu_key_down[builder_key]) {
            builder_menu_key_down[builder_key]=false;message->message=WM_NULL;return;
        }
        if(message->message==WM_KEYDOWN && builder_menu_key_down[builder_key]) {
            message->message=WM_NULL;return;
        }
        DWORD builder_foreground_pid=0;GetWindowThreadProcessId(GetForegroundWindow(),&builder_foreground_pid);
        const bool builder_panel=session_menu.menu.accepts_actions() && session_builder.owns_menu(session_menu.widget);
        const bool builder_escape=builder_key==0 && session_builder.active() && !session_menu.menu.active();
        const auto routed_key=(builder_key==2 || (builder_escape&&!session_builder.preview_active()))?VK_F8:VK_F7;
        if(message->message==WM_KEYDOWN && builder_foreground_pid==GetCurrentProcessId() &&
           lifetime_valid() && attachment_valid(runtime_base) && local_read<uint64_t>(attached_console+0xd8)==0 &&
           (builder_panel || builder_escape) &&
           session_keys.contains(routed_key)) {
            if(builder_key==0&&routed_key==VK_F7)session_builder.request_menu_escape();
            session_keys.press(routed_key,(message->lParam & (LPARAM(1)<<30))!=0,true);
            builder_menu_key_down[builder_key]=true;message->message=WM_NULL;return;
        }
    }
    // Escape belongs to the visible SDK menu; consume repeats and the paired
    // release so the same press cannot dismiss the game's underlying Pause.
    static bool menu_escape_down=false;
    const bool escape=message->wParam==VK_ESCAPE;
    const bool console_closed=lifetime_valid() && attachment_valid(runtime_base) &&
        local_read<uint64_t>(attached_console+0xd8)==0;
    if(escape && message->message==WM_KEYUP && menu_escape_down) {
        menu_escape_down=false; message->message=WM_NULL; return;
    }
    if(escape && message->message==WM_KEYDOWN && console_closed &&
       session_menu.menu.active() && session_keys.contains(VK_ESCAPE)) {
        session_keys.press(VK_ESCAPE,(message->lParam & (LPARAM(1)<<30))!=0,true);
        menu_escape_down=true; message->message=WM_NULL; return;
    }
#endif
    // Windows delivers F10 as a system key. Route this builder shortcut
    // without activating the window menu, including its paired release.
    static bool builder_f10_down=false;
    if(message->wParam==VK_F10&&message->message==WM_SYSKEYUP&&builder_f10_down){builder_f10_down=false;message->message=WM_NULL;return;}
    if((message->message==WM_KEYDOWN || (message->message==WM_SYSKEYDOWN&&message->wParam==VK_F10&&session_builder.active())) && session_keys.contains(static_cast<uint32_t>(message->wParam))) {
        DWORD foreground_pid=0;
        GetWindowThreadProcessId(GetForegroundWindow(), &foreground_pid);
        const bool eligible=foreground_pid==GetCurrentProcessId() && lifetime_valid() &&
            attachment_valid(runtime_base) && local_read<uint64_t>(attached_console+0xd8)==0 &&
            !session_menu.menu.active() &&
            !(GetKeyState(VK_CONTROL)&0x8000) && !(GetKeyState(VK_MENU)&0x8000) &&
            !(GetKeyState(VK_SHIFT)&0x8000) && !(GetKeyState(VK_LWIN)&0x8000) && !(GetKeyState(VK_RWIN)&0x8000);
        session_keys.press(static_cast<uint32_t>(message->wParam),
            (message->lParam & (LPARAM(1)<<30))!=0, eligible);
        if(eligible&&message->wParam==VK_F10&&session_builder.active()){builder_f10_down=true;message->message=WM_NULL;return;}
        // Observe ordinary game input without consuming or rewriting it.
    }
#endif
    if (!console_toggle_key || message->wParam!=console_toggle_key ||
        (message->message!=WM_KEYDOWN && message->message!=WM_SYSKEYDOWN &&
         message->message!=WM_KEYUP && message->message!=WM_SYSKEYUP)) return;
    if ((GetKeyState(VK_CONTROL)&0x8000) || (GetKeyState(VK_MENU)&0x8000) || (GetKeyState(VK_SHIFT)&0x8000)) return;
    if (!lifetime_valid() || !attachment_valid(runtime_base)) { console_toggle_key=0; return; }
    bool pressed=message->message==WM_KEYDOWN || message->message==WM_SYSKEYDOWN;
    bool repeat=(message->lParam & (LPARAM(1)<<30))!=0;
    message->message=WM_NULL;
    if (!pressed || repeat) return;
    uint64_t current=local_read<uint64_t>(attached_console+0xd8);
    uint64_t open=local_read<uint64_t>(runtime_base+0x94dfb58);
    uint64_t typing=local_read<uint64_t>(runtime_base+0x94dfb50);
    uint64_t transition=local_read<uint64_t>(local_read<uint64_t>(attached_console)+0x3c8);
    if ((current && current!=open && current!=typing) || transition!=runtime_base+0x3dcff60) { console_toggle_key=0; return; }
    using Transition=void(__fastcall*)(void*,uint64_t);
    reinterpret_cast<Transition>(transition)(reinterpret_cast<void*>(attached_console),current?0:open);
}
#include "session_transport.h"

#ifdef E33_VIEWER_MENU_SESSION
uint64_t backend_menu_frame() {
    __try {
        return runtime_base && picto_frame_source(runtime_base) &&
            GetCurrentThreadId()==local_read<DWORD>(runtime_base+0x9272d30) ?
            local_read<uint64_t>(runtime_base+0x9272d10):0;
    } __except(EXCEPTION_EXECUTE_HANDLER) {return 0;}
}
#endif
