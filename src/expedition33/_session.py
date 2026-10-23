"""Internal persistent native transport; public subscription API is a separate layer."""
import json
from pathlib import Path
import queue
import subprocess
import threading

from . import RuntimeQueryError, TargetExitedError

BUTTON_CAPABILITIES = ('button_action_protocol', 'button_reference_protocol', 'menu_protocol',
                       'enum_value_protocol', 'text_value_protocol', 'pod_value_protocol',
                       'object_assignment_protocol', 'stable_identity_protocol', 'retained_protocol',
                       'lease_protocol', 'reflected_protocol')


def supports_multi_controls(transport):
    protocols = BUTTON_CAPABILITIES + ('multi_button_protocol',)
    nonce = getattr(transport, 'button_action_session', 0)
    capacity = getattr(transport, 'multi_button_capacity', 0)
    return (all(type(getattr(transport, name, 0)) is int and getattr(transport, name, 0) == 1
                for name in protocols) and type(nonce) is int and 0 < nonce < 2**64 and
            type(capacity) is int and capacity in (16,64))


def supports_traces(transport):
    protocol = getattr(transport, 'trace_protocol', 0)
    capacity = getattr(transport, 'trace_capacity', 0)
    return (supports_multi_controls(transport) and
            type(protocol) is int and protocol == 1 and type(capacity) is int and capacity in (16,64))


def supports_keys(transport):
    return (supports_traces(transport) and
            type(getattr(transport, 'keybind_protocol', None)) is int and transport.keybind_protocol == 1 and
            type(getattr(transport, 'keybind_capacity', None)) is int and transport.keybind_capacity == 96)


class SessionTransport:
    def __init__(self, *, _executable=None):
        self._owner = threading.get_ident()
        self._closed = False
        self._terminal_failure = None
        self.target_exit_code = None
        self._lines = queue.Queue(maxsize=256)
        executable = _executable or Path(__file__).resolve().parents[2] / 'build/research-probe/research_probe.exe'
        self._executable = executable
        self._process = subprocess.Popen([str(executable), '--session'], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8',
            errors='strict', bufsize=1, creationflags=subprocess.CREATE_NO_WINDOW)
        process = self._process
        lines = self._lines
        def reader():
            try:
                for line in process.stdout:
                    lines.put(line)
            except (OSError, UnicodeError) as error:
                lines.put(error)
            finally:
                lines.put(None)
        self._reader = threading.Thread(target=reader, daemon=True, name='expedition33-session-output')
        self._reader.start()
        try:
            self.start = self._read()
            self.objects = [self._read(), self._read()]
            ready = self._read()
            self.mesh_protocol = ready.get('mesh_protocol', 0)
            self.enemy_spawn_protocol = ready.get('enemy_spawn_protocol', 0)
            self.enemy_trigger_anchor_research_protocol = ready.get('enemy_trigger_anchor_research_protocol', 0)
            self.enemy_trigger_parameter_research_protocol = ready.get('enemy_trigger_parameter_research_protocol', 0)
            self.enemy_trigger_entry_research_protocol = ready.get('enemy_trigger_entry_research_protocol', 0)
            self.enemy_combat_placement_protocol = ready.get('enemy_combat_placement_protocol', 0)
            self.battle_parameter_frame_research_protocol = ready.get('battle_parameter_frame_research_protocol', 0)
            self.battle_entry_preflight_research_protocol = ready.get('battle_entry_preflight_research_protocol', 0)
            self.battle_entry_arena_research_protocol = ready.get('battle_entry_arena_research_protocol', 0)
            self.battle_entry_dispatch_research_protocol = ready.get('battle_entry_dispatch_research_protocol', 0)
            self.battle_parameter_policy_research_protocol = ready.get('battle_parameter_policy_research_protocol', 0)
            self.enemy_retirement_protocol = ready.get('enemy_retirement_protocol', 0)
            self.enemy_pose_protocol = ready.get('enemy_pose_protocol', 0)
            self.enemy_arena_protocol = ready.get('enemy_arena_protocol', 0)
            self.enemy_arena_binding_protocol = ready.get('enemy_arena_binding_protocol', 0)
            self.enemy_clearance_protocol = ready.get('enemy_clearance_protocol', 0)
            self.enemy_grounded_spawn_protocol = ready.get('enemy_grounded_spawn_protocol', 0)
            self.enemy_visual_staging_research_protocol = ready.get('enemy_visual_staging_research_protocol', 0)
            self.enemy_visual_arena_research_protocol = ready.get('enemy_visual_arena_research_protocol', 0)
            self.enemy_helper_lookup_research_protocol = ready.get('enemy_helper_lookup_research_protocol', 0)
            self.enemy_geometry_placement_research_protocol = ready.get('enemy_geometry_placement_research_protocol', 0)
            self.enemy_authored_encounter_research_protocol = ready.get('enemy_authored_encounter_research_protocol', 0)
            self.npc_presentation_admission_research_protocol = ready.get('npc_presentation_admission_research_protocol', 0)
            self.npc_membership_observation_research_protocol = ready.get('npc_membership_observation_research_protocol', 0)
            self.npc_original_staging_research_protocol = ready.get('npc_original_staging_research_protocol', 0)
            self.npc_original_placement_research_protocol = ready.get('npc_original_placement_research_protocol', 0)
            self.npc_original_grounded_construction_research_protocol = ready.get('npc_original_grounded_construction_research_protocol', 0)
            self.npc_original_preview_research_protocol = ready.get('npc_original_preview_research_protocol', 0)
            self.npc_parameter_policy_research_protocol = ready.get('npc_parameter_policy_research_protocol', 0)
            self.npc_arena_value_research_protocol = ready.get('npc_arena_value_research_protocol', 0)
            self.npc_entry_preflight_research_protocol = ready.get('npc_entry_preflight_research_protocol', 0)
            self.npc_proximity_research_protocol = ready.get('npc_proximity_research_protocol', 0)
            self.npc_interaction_variants_protocol = ready.get('npc_interaction_variants_protocol', 0)
            self.npc_alicia_encounter_protocol = ready.get('npc_alicia_encounter_protocol', 0)
            self.npc_curator_encounter_protocol = ready.get('npc_curator_encounter_protocol', 0)
            self.npc_francois_encounter_protocol = ready.get('npc_francois_encounter_protocol', 0)
            self.enemy_current_world_staging_protocol = ready.get('enemy_current_world_staging_protocol', 0)
            self.enemy_extra_spots_protocol = ready.get('enemy_extra_spots_protocol', 0)
            self.map_runtime_protocol = ready.get('map_runtime_protocol', 0)
            self.retired_world_cleanup_protocol = ready.get('retired_world_cleanup_protocol', 0)
            self.builder_world_retirement_protocol = ready.get('builder_world_retirement_protocol', 0)
            self.runtime_cinematic_protocol = ready.get('runtime_cinematic_protocol', 0)
            self.runtime_scene_protocol = ready.get('runtime_scene_protocol', 0)
            self.native_visual_staging_protocol = ready.get('native_visual_staging_protocol', 0)
            self.native_visual_encounter_preflight_protocol = ready.get('native_visual_encounter_preflight_protocol', 0)
            self.native_visual_grounding_protocol = ready.get('native_visual_grounding_protocol', 0)
            self.reflected_protocol = ready.get('reflected_protocol', 0)
            self.lease_protocol = ready.get('lease_protocol', 0)
            self.console_color_status_protocol = ready.get('console_color_status_protocol', 0)
            self.lease_release_batch_protocol = ready.get('lease_release_batch_protocol', 0)
            self.metadata_stabilization_protocol = ready.get('metadata_stabilization_protocol',0)
            self.stable_lease_protocol = ready.get('stable_lease_protocol',0)
            self.lease_policy_protocol = ready.get('lease_policy_protocol', 0)
            self.lease_limit = 4096 if self.lease_policy_protocol==1 else 128
            self._lease_owner = 0
            self.retained_protocol = ready.get('retained_protocol', 0)
            self.blueprint_invocation_protocol = ready.get('blueprint_invocation_protocol', 0)
            self.stable_identity_protocol = ready.get('stable_identity_protocol', 0)
            self.object_assignment_protocol = ready.get('object_assignment_protocol', 0)
            self.menu_input_protocol = ready.get('menu_input_protocol', 0)
            self.menu_open_focus_protocol = ready.get('menu_open_focus_protocol', 0)
            self.scalar_assignment_protocol = ready.get('scalar_assignment_protocol', 0)
            self.pod_value_protocol = ready.get('pod_value_protocol', 0)
            self.string_value_protocol = ready.get("string_value_protocol", 0)
            self.text_value_protocol = ready.get('text_value_protocol', 0)
            self.enum_value_protocol = ready.get('enum_value_protocol', 0)
            self.menu_protocol = ready.get('menu_protocol', 0)
            self.media_owner_protocol = ready.get('media_owner_protocol', 0)
            self.sequence_player_protocol = ready.get('sequence_player_protocol', 0)
            self.scoped_assignment_protocol = ready.get('scoped_assignment_protocol', 0)
            self.music_audio_protocol = ready.get('music_audio_protocol', 0)
            self.owned_sound_protocol = ready.get('owned_sound_protocol', 0)
            self.owned_sound_capacity = ready.get('owned_sound_capacity', 16)
            self.owned_sound_volume_max = ready.get('owned_sound_volume_max', 1)
            self.cinematic_sound_event_protocol = ready.get('cinematic_sound_event_protocol', 0)
            self.cinematic_sound_diagnostics_protocol = ready.get('cinematic_sound_diagnostics_protocol', 0)
            self.cinematic_widget_protocol = ready.get('cinematic_widget_protocol', 0)
            self.cinematic_widget_diagnostics_protocol = ready.get('cinematic_widget_diagnostics_protocol', 0)
            self.cinematic_widget_animation_protocol = ready.get('cinematic_widget_animation_protocol', 0)
            self.audio_cleanup_diagnostics_protocol = ready.get('audio_cleanup_diagnostics_protocol', 0)
            self.owned_audio_cleanup_protocol = ready.get('owned_audio_cleanup_protocol', 0)
            self.original_audio_pause_protocol = ready.get('original_audio_pause_protocol', 0)
            self.asset_load_protocol = ready.get('asset_load_protocol', 0)
            self.generated_world_asset_load_protocol = ready.get('generated_world_asset_load_protocol', 0)
            self.owned_battle_arena_staging_protocol = ready.get('owned_battle_arena_staging_protocol', 0)
            self.owned_battle_arena_capacity = ready.get('owned_battle_arena_capacity', 1)
            self.owned_component_pose_protocol = ready.get('owned_component_pose_protocol', 0)
            self.owned_helper_component_pose_protocol = ready.get('owned_helper_component_pose_protocol', 0)
            self.owned_helper_parameter_preflight_protocol = ready.get('owned_helper_parameter_preflight_protocol', 0)
            self.owned_battle_arena_grounding_protocol = ready.get('owned_battle_arena_grounding_protocol', 0)
            self.owned_battle_arena_approach_protocol = ready.get('owned_battle_arena_approach_protocol', 0)
            self.owned_battle_arena_approach_diagnostics_protocol = ready.get('owned_battle_arena_approach_diagnostics_protocol', 0)
            self.owned_battle_arena_advisory_route_protocol = ready.get('owned_battle_arena_advisory_route_protocol', 0)
            self.encounter_tuning_protocol = ready.get('encounter_tuning_protocol', 0)
            self.encounter_tuning_max_health_multiplier = ready.get('encounter_tuning_max_health_multiplier', 100)
            self.encounter_retry_tuning_protocol = ready.get('encounter_retry_tuning_protocol', 0)
            self.owned_authored_entry_protocol = ready.get('owned_authored_entry_protocol', 0)
            self.owned_helper_source_frame_protocol = ready.get('owned_helper_source_frame_protocol', 0)
            for capability in ('qa_encounter_protocol', 'picto_edit_protocol', 'picto_progression_protocol',
                               'picto_class_load_protocol', 'picto_cost_protocol', 'picto_startup_protocol', 'picto_stat_clear_protocol', 'picto_stat_remove_protocol', 'picto_inventory_protocol', 'picto_batch_protocol', 'picto_level_batch_protocol', 'picto_mastery_batch_protocol'):
                setattr(self, capability, ready.get(capability, 0))
            self.ui_batch_protocol = ready.get('ui_batch_protocol', 0)
            self.ui_construction_protocol = ready.get('ui_construction_protocol', 0)
            self.layout_batch_protocol = ready.get('layout_batch_protocol', 0)
            self.timespan_values_protocol = ready.get('timespan_values_protocol', 0)
            self.frame_time_values_protocol = ready.get('frame_time_values_protocol', 0)
            self.cinematic_empty_title_protocol = ready.get('cinematic_empty_title_protocol', 0)
            self.sequence_camera_protocol = ready.get('sequence_camera_protocol', 0)
            self.sequence_binding_query_protocol = ready.get('sequence_binding_query_protocol', 0)
            self.original_game_action_protocol = ready.get('original_game_action_protocol', 0)
            self.zone_travel_protocol = ready.get('zone_travel_protocol', 0)
            profiles = ready.get('cinematic_title_profiles', [])
            if (type(profiles) is not list or len(profiles) > 32 or
                    any(type(value) is not str or not value or len(value) > 64 for value in profiles) or
                    len(set(profiles)) != len(profiles)):
                raise ValueError('Invalid native cinematic profile advertisement')
            self.cinematic_title_profiles = tuple(profiles)
            self.vector_value_protocol = ready.get('vector_value_protocol', 0)
            self.pause_attachment_protocol = ready.get('pause_attachment_protocol', 0)
            self.trace_renew_protocol = ready.get('trace_renew_protocol', 0)
            self.button_reference_protocol = ready.get('button_reference_protocol', 0)
            self.button_action_protocol = ready.get('button_action_protocol', 0)
            self.button_action_session = ready.get('button_action_session', 0)
            self.multi_button_protocol = ready.get('multi_button_protocol', 0)
            self.multi_button_capacity = ready.get('multi_button_capacity', 0)
            self.trace_protocol = ready.get('trace_protocol', 0)
            self.blueprint_trace_protocol = ready.get('blueprint_trace_protocol', 0)
            self.trace_capacity = ready.get('trace_capacity', 0)
            self.keybind_protocol = ready.get('keybind_protocol', 0)
            self.key_capture_protocol = ready.get('key_capture_protocol', 0)
            self.keybind_capacity = ready.get('keybind_capacity', 0)
            if (self.start.get('event') != 'snapshot_start' or
                any(row.get('event') != 'object' for row in self.objects) or
                ready.get('event') != 'session_ready' or ready['pid'] != self.start['pid'] or
                ready['game_thread_id'] != self.start['game_thread_id']):
                raise RuntimeQueryError('Incomplete native session handshake')
            identities = {(row['name'], row['class_name']) for row in self.objects}
            if identities != {('Default__Actor', 'Actor'), ('IsActorBeingDestroyed', 'Function')}:
                raise RuntimeQueryError('Native session target identity mismatch')
        except BaseException:
            self._abort()
            raise

    def _check_thread(self):
        if threading.get_ident() != self._owner:
            raise RuntimeError('Native sessions must be used on their owning Python thread')

    def _read(self):
        try:
            line = self._lines.get(timeout=15)
        except queue.Empty as error:
            raise RuntimeQueryError('Native session response timed out') from error
        if line is None:
            raise RuntimeQueryError('Native session ended before acknowledging the request')
        if isinstance(line, BaseException):
            raise RuntimeQueryError(f'Native session output failed: {line}')
        try:
            if len(line) > 1_000_000:
                raise ValueError('Oversized response')
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError('Expected a JSON object')
        except (ValueError, TypeError) as error:
            raise RuntimeQueryError(f'Invalid native session response: {error}') from error
        if value.get('event') == 'target_exited':
            code = value.get('exit_code')
            if type(code) is not int or not 0 <= code <= 0xffffffff:
                raise RuntimeQueryError('Invalid target exit report')
            self.target_exit_code = code
            raise TargetExitedError(code)
        if value.get('event') == 'error':
            raise RuntimeQueryError(value.get('message', 'Native session failed'))
        return value

    def command(self, command, payload=None):
        telemetry = getattr(self, '_workflow_telemetry', None)
        if telemetry is None:
            return self._command(command, payload)
        import time
        started, clock = time.time(), time.perf_counter()
        success = False
        try:
            result = self._command(command, payload)
            success = True
            return result
        finally:
            duration = time.perf_counter()-clock
            telemetry.record('native.'+command, 'native_transport', started, duration,
                success, ipc_round_trips=1, native_round_trip_ms=duration*1000)

    def _command(self, command, payload=None):
        self._check_thread()
        if self._closed:
            failure = getattr(self, '_terminal_failure', None)
            detail = f"; first failure in {failure['command']}: {failure['error']}" if failure else ''
            raise RuntimeQueryError('Native session is closed' + detail)
        reflected = command == 'reflected-invoke'
        retained = command == 'retained-invoke'
        assignment = command == 'object-assign'
        text = command == 'text-invoke'
        menu = command == 'menu'
        button_action = command == 'button-action'
        multi_button = command == 'multi-button'
        trace = command == 'trace'
        keys = command == 'keys'
        ui_batch = command == 'ui-batch'
        pause = command == 'pause-attachment'
        media = command == 'media-owner'
        override = command == 'scoped-assignment'
        music_audio = command == 'music-audio-owner'
        sound_event = command == 'cinematic-sound-event'
        widget_hook = command == 'cinematic-widget'
        zone = command == 'zone-travel'
        if zone and getattr(self,'zone_travel_protocol',0)!=2:
            raise ValueError('Normal zone travel requires the updated SDK runtime')
        picto_batch = command == 'picto-batch'
        if picto_batch and getattr(self,'picto_batch_protocol',0)!=1:
            raise ValueError('Picto batch capability unavailable')
        mesh = command == 'mesh'
        if mesh and getattr(self,'mesh_protocol',0)!=3:
            raise ValueError('Mesh candidate unavailable')
        qa_encounter = command == 'qa-encounter-reset'
        if qa_encounter and getattr(self,'qa_encounter_protocol',0)!=1:raise ValueError('Updated QA encounter runtime required')
        picto_progress = command == 'picto-progression'
        if picto_progress and getattr(self,'picto_progression_protocol',0)!=1:
            raise ValueError('Picto progression capability unavailable')
        lease_policy = command == 'lease-policy'
        if lease_policy and getattr(self,'lease_policy_protocol',0)!=1:
            raise ValueError('Native session does not support growing lease policy')
        if widget_hook and getattr(self,'cinematic_widget_protocol',0)!=1:
            raise ValueError('Native session does not support cinematic widget ownership')
        if widget_hook and payload is not None and len(payload)>=8 and payload[4:8]==b'\x04\x00\x00\x00' and getattr(self,'cinematic_widget_diagnostics_protocol',0)!=1:
            raise ValueError('Native session does not support widget route diagnostics')
        if sound_event and getattr(self,'cinematic_sound_event_protocol',0)!=1:
            raise ValueError('Native session does not support cinematic sound routing')
        if sound_event and payload is not None and len(payload)>=8 and payload[4:8]==b'\x04\x00\x00\x00' and getattr(self,'cinematic_sound_diagnostics_protocol',0)!=1:
            raise ValueError('Native session does not support sound route diagnostics')
        if music_audio and getattr(self, 'music_audio_protocol', 0) != 1:
            raise ValueError('Native session does not support music audio ownership')
        if override and getattr(self, 'scoped_assignment_protocol', 0) != 1:
            raise ValueError('Native session does not support scoped assignments')
        sequence = command == 'sequence-owner'
        if sequence and getattr(self,'sequence_player_protocol',0)!=1:
            raise ValueError('Native session does not support sequence ownership')
        if media and (type(getattr(self,'media_owner_protocol',0)) is not int or self.media_owner_protocol != 1):
            raise ValueError('Native session does not support media ownership')
        if pause and getattr(self, 'pause_attachment_protocol', 0) != 2:
            raise ValueError('Native session does not support pause attachments')
        if ui_batch and getattr(self, 'ui_batch_protocol', 0) != 1:
            raise ValueError('Native session does not support UI batching')
        if keys and not supports_keys(self):
            raise ValueError('Native session does not support keybinds')
        if trace and not supports_traces(self):
            raise ValueError('Native session does not support traces')
        if multi_button:
            if not supports_multi_controls(self):
                raise ValueError('Native session does not support multiple controls')
        if button_action or multi_button:
            capabilities = BUTTON_CAPABILITIES
            if any(type(getattr(self, name, 0)) is not int or getattr(self, name, 0) != 1 for name in capabilities):
                raise ValueError('Native session does not support button actions')
            nonce = getattr(self, 'button_action_session', 0)
            if type(nonce) is not int or not 0 < nonce < 2**64:
                raise ValueError('Native button action session identity is missing')
        if menu and any(getattr(self, name, 0) != 1 for name in
                        ('menu_protocol', 'enum_value_protocol', 'text_value_protocol', 'pod_value_protocol',
                         'object_assignment_protocol', 'stable_identity_protocol', 'retained_protocol',
                         'lease_protocol', 'reflected_protocol')):
            raise ValueError('Native session does not support menu ownership')
        if text and any(getattr(self, capability, 0) != 1 for capability in
                        ('text_value_protocol', 'pod_value_protocol', 'object_assignment_protocol',
                         'stable_identity_protocol', 'retained_protocol', 'lease_protocol', 'reflected_protocol')):
            raise ValueError('Native session does not support owned text invocation')
        if assignment and getattr(self, 'object_assignment_protocol', 0) != 1:
            raise ValueError('Native session does not support object assignment')
        if retained and getattr(self, 'retained_protocol', 0) != 1:
            raise ValueError('Native session does not support retained invocation')
        color_status = command == 'console-color-status'
        if color_status:
            cap = getattr(self, 'console_color_status_protocol', 0)
            if type(cap) is not int or cap != 1 or payload is not None:
                raise ValueError('Native console color status unavailable or invalid payload')
        metadata_stabilize=command=='metadata-stabilize'
        if metadata_stabilize:
            from ._metadata_stabilization import available
            if not available(self):raise ValueError('Metadata stabilization unavailable')
        lease_batch = command == 'lease-release-batch'
        if lease_batch:
            from ._lease_release_batch import available
            if not available(self):raise ValueError('Native lease release batching unavailable')
        leased = command in ('lease-acquire', 'stable-lease-acquire', 'lease-release', 'lease-status')
        if command=='stable-lease-acquire' and (type(getattr(self,'stable_lease_protocol',0)) is not int or self.stable_lease_protocol!=1):
            raise ValueError('Native stable acquisition unavailable')
        if leased and getattr(self, 'lease_protocol', 0) != 1:
            raise ValueError('Native session does not support object leases')
        if reflected and getattr(self, 'reflected_protocol', 0) != 1:
            raise ValueError('Native session does not support reflected invocation')
        if not metadata_stabilize and not color_status and not lease_batch and not qa_encounter and not zone and not mesh and not picto_batch and not picto_progress and not lease_policy and not widget_hook and not sound_event and not music_audio and not override and not sequence and not media and not pause and not ui_batch and not keys and not trace and not reflected and not leased and not retained and not assignment and not text and not menu and not button_action and not multi_button and command not in ('enable', 'disable', 'invoke', 'drain', 'ping', 'close', 'console-attach', 'console-detach', 'console-status', 'console-poll', 'console-execute', 'console-print', 'console-names', 'console-key'):
            raise ValueError('Unsupported native session command')
        suffix = ''
        if zone:
            from .zone_travel import validate_request
            validate_request(payload)
            suffix = ' ' + payload.hex()
        elif picto_batch:
            from .picto_batch import validate_request
            validate_request(payload)
            from .picto_batch import HEADER
            if HEADER.unpack_from(payload)[6]==2 and getattr(self,'picto_level_batch_protocol',0)!=1:
                raise ValueError('Picto level batch capability unavailable')
            if HEADER.unpack_from(payload)[6]==3 and getattr(self,'picto_mastery_batch_protocol',0)!=1:
                raise ValueError('Picto mastery batch capability unavailable')
            suffix = ' ' + payload.hex()
        elif mesh:
            parameter_mesh=(type(payload) is bytes and len(payload)>=8 and 124<=int.from_bytes(payload[4:8],'little')<=130)
            enemy_mesh=(type(payload) is bytes and len(payload)>=8 and (110<=int.from_bytes(payload[4:8],'little')<=123 or int.from_bytes(payload[4:8],'little') in (131,132,133)))
            map_mesh=(type(payload) is bytes and len(payload)>=8 and (93<=int.from_bytes(payload[4:8],'little')<=97 or
                    int.from_bytes(payload[:4],'little')==3 and int.from_bytes(payload[4:8],'little')==98))
            scene_mesh=(not map_mesh and type(payload) is bytes and len(payload)>=8 and getattr(self,'runtime_scene_protocol',0) in (1,2,3,4,5,6,7) and
                    (70<=int.from_bytes(payload[4:8],'little')<=92 or int.from_bytes(payload[4:8],'little')==98))
            npc_admission=(type(payload) is bytes and len(payload)>=8 and int.from_bytes(payload[4:8],'little')==134)
            npc_membership=(type(payload) is bytes and len(payload)>=8 and int.from_bytes(payload[4:8],'little')==135)
            npc_staging=(type(payload) is bytes and len(payload)>=8 and 136<=int.from_bytes(payload[4:8],'little')<=147)
            visual_staging=(type(payload) is bytes and len(payload)>=8 and int.from_bytes(payload[4:8],'little') in (148,149,150))
            arena_staging=(type(payload) is bytes and len(payload)>=8 and int.from_bytes(payload[4:8],'little') in (151,152,153,154,155,156))
            tuning=(type(payload) is bytes and len(payload)>=8 and 157<=int.from_bytes(payload[4:8],'little')<=159)
            if tuning:
                if getattr(self,'encounter_tuning_protocol',0)!=1:raise ValueError('Encounter tuning unavailable')
                from .encounter_tuning import validate_request
            elif arena_staging:
                capability=getattr(self,'owned_battle_arena_staging_protocol',0)
                if type(capability) is not int or capability!=1:raise ValueError('Owned battle arena staging unavailable')
                if int.from_bytes(payload[4:8],'little')==156:
                    capability=getattr(self,'owned_helper_source_frame_protocol',0)
                    if type(capability) is not int or capability!=1:raise ValueError('Owned helper source frame unavailable')
                if int.from_bytes(payload[4:8],'little')==155:
                    capability=getattr(self,'owned_battle_arena_grounding_protocol',0)
                    if type(capability) is not int or capability!=1:raise ValueError('Owned battle arena grounding unavailable')
                    if payload[24]:
                        capability=getattr(self,'owned_battle_arena_approach_protocol',0)
                        if type(capability) is not int or capability!=1:raise ValueError('Owned battle arena approach screening unavailable')
                    if payload[24]&2:
                        capability=getattr(self,'owned_battle_arena_approach_diagnostics_protocol',0)
                        if type(capability) is not int or capability!=1:raise ValueError('Owned battle arena approach diagnostics unavailable')
                    if payload[24]&4:
                        capability=getattr(self,'owned_battle_arena_advisory_route_protocol',0)
                        if type(capability) is not int or capability!=1:raise ValueError('Owned battle arena advisory route unavailable')
                if int.from_bytes(payload[4:8],'little')==154:
                    capability=getattr(self,'owned_component_pose_protocol',0)
                    if type(capability) is not int or capability!=1:raise ValueError('Owned component pose unavailable')
                    if payload[24]:
                        capability=getattr(self,'owned_helper_component_pose_protocol',0)
                        if type(capability) is not int or capability!=1:raise ValueError('Owned helper component pose unavailable')
                from .owned_battle_arena import validate_request
            elif visual_staging:
                capability=getattr(self,'native_visual_staging_protocol',0)
                if type(capability) is not int or capability!=1:raise ValueError('Native visual staging unavailable')
                if int.from_bytes(payload[4:8],'little')==149:
                    capability=getattr(self,'native_visual_encounter_preflight_protocol',0)
                    if type(capability) is not int or capability!=1:raise ValueError('Native visual arena preflight unavailable')
                if int.from_bytes(payload[4:8],'little')==150:
                    capability=getattr(self,'native_visual_grounding_protocol',0)
                    if type(capability) is not int or capability!=2:raise ValueError('Native visual grounding unavailable')
                from .native_visual_staging import validate_request
            elif npc_staging:
                capability=getattr(self,'npc_original_staging_research_protocol',0)
                if type(capability) is not int or capability!=1:raise ValueError('Original NPC staging research unavailable')
                if int.from_bytes(payload[4:8],'little') in (146,147):
                    capability=getattr(self,'npc_interaction_variants_protocol',0)
                    if type(capability) is not int or capability!=1:raise ValueError('NPC interaction variants unavailable')
                if int.from_bytes(payload[4:8],'little')==145:
                    capability=getattr(self,'npc_proximity_research_protocol',0)
                    if type(capability) is not int or capability!=1:raise ValueError('NPC proximity research unavailable')
                if int.from_bytes(payload[4:8],'little') in (143,144):
                    capability=getattr(self,'npc_arena_value_research_protocol',0)
                    if type(capability) is not int or capability!=1:raise ValueError('NPC arena value research unavailable')
                if int.from_bytes(payload[4:8],'little')==142:
                    capability=getattr(self,'npc_original_preview_research_protocol',0)
                    if type(capability) is not int or capability!=1:raise ValueError('Original NPC preview research unavailable')
                if int.from_bytes(payload[4:8],'little')==141:
                    capability=getattr(self,'npc_original_grounded_construction_research_protocol',0)
                    if type(capability) is not int or capability!=1:raise ValueError('Grounded NPC construction research unavailable')
                if int.from_bytes(payload[4:8],'little')>=139:
                    capability=getattr(self,'npc_original_placement_research_protocol',0)
                    if type(capability) is not int or capability!=1:raise ValueError('Original NPC placement research unavailable')
                from ._npc_staging_research import validate_request
            elif npc_membership:
                capability=getattr(self,'npc_membership_observation_research_protocol',0)
                if type(capability) is not int or capability!=1:raise ValueError('NPC membership observation research unavailable')
                from ._npc_membership_research import validate_request
            elif npc_admission:
                capability=getattr(self,'npc_presentation_admission_research_protocol',0)
                if type(capability) is not int or capability!=1:raise ValueError('Original NPC admission research unavailable')
                from ._npc_admission_research import validate_request
            elif parameter_mesh:
                capability=getattr(self,'battle_parameter_frame_research_protocol',0)
                if type(capability) is not int or capability!=1:
                    raise ValueError('Native session does not support original parameter research')
                if int.from_bytes(payload[4:8],'little')>=127:
                    policy_capability=getattr(self,'battle_parameter_policy_research_protocol',0)
                    if type(policy_capability) is not int or policy_capability!=1:
                        raise ValueError('Native session does not support owned policy research')
                if int.from_bytes(payload[4:8],'little')>=128:
                    entry_capability=getattr(self,'battle_entry_preflight_research_protocol',0)
                    if type(entry_capability) is not int or entry_capability!=1:
                        raise ValueError('Native session does not support owned entry preflight research')
                if int.from_bytes(payload[4:8],'little')>=129:
                    arena_capability=getattr(self,'battle_entry_arena_research_protocol',0)
                    if type(arena_capability) is not int or arena_capability!=2:
                        raise ValueError('Native session does not support owned parameter arena research')
                if int.from_bytes(payload[4:8],'little')==130:
                    dispatch_capability=getattr(self,'battle_entry_dispatch_research_protocol',0)
                    if type(dispatch_capability) is not int or dispatch_capability!=1:
                        raise ValueError('Native session does not support owned battle entry research')
                from ._battle_parameter_wire import validate_request
            elif enemy_mesh:
                capability=getattr(self,'enemy_spawn_protocol',0)
                operation=int.from_bytes(payload[4:8],'little')
                pose_capability=getattr(self,'enemy_pose_protocol',0)
                authored_capability=getattr(self,'enemy_authored_encounter_research_protocol',0)
                if operation==133 and (type(authored_capability) is not int or authored_capability not in (2,3,4,5,6,7) or (int.from_bytes(payload[32:36],'little')==2 and authored_capability<3) or (int.from_bytes(payload[32:36],'little')>=3 and authored_capability<4) or (int.from_bytes(payload[32:36],'little')>=7 and authored_capability<5) or (int.from_bytes(payload[32:36],'little')>=8 and authored_capability<6) or (int.from_bytes(payload[32:36],'little')>=12 and authored_capability<7)):
                    raise ValueError('Native session does not support authored instance encounters')
                if operation==132 and (type(getattr(self,'enemy_geometry_placement_research_protocol',0)) is not int or getattr(self,'enemy_geometry_placement_research_protocol',0)!=1):
                    raise ValueError('Native session does not support original helper geometry placement')
                if operation==131 and (type(getattr(self,'enemy_helper_lookup_research_protocol',0)) is not int or getattr(self,'enemy_helper_lookup_research_protocol',0)!=1):
                    raise ValueError('Native session does not support original helper lookup')
                if operation==123 and (type(getattr(self,'enemy_combat_placement_protocol',0)) is not int or self.enemy_combat_placement_protocol!=1):
                    raise ValueError('Native session does not support combat placement')
                if type(capability) is not int or capability not in (1,2,3) or operation==114 and capability<2 or operation==115 and capability<3 or operation==116 and (type(pose_capability) is not int or pose_capability!=1) or operation==117 and (type(getattr(self,'enemy_arena_protocol',0)) is not int or getattr(self,'enemy_arena_protocol',0)!=1) or operation==118 and (type(getattr(self,'enemy_arena_binding_protocol',0)) is not int or getattr(self,'enemy_arena_binding_protocol',0)!=1) or operation==119 and (type(getattr(self,'enemy_clearance_protocol',0)) is not int or getattr(self,'enemy_clearance_protocol',0)!=1) or operation in (120,121) and (type(getattr(self,'enemy_grounded_spawn_protocol',0)) is not int or getattr(self,'enemy_grounded_spawn_protocol',0)!=2) or operation==122 and (type(getattr(self,'enemy_extra_spots_protocol',0)) is not int or getattr(self,'enemy_extra_spots_protocol',0)!=1):
                    raise ValueError('Native session does not support this owned enemy operation')
                from ._enemy_spawn_wire import validate_request
            elif map_mesh:
                if getattr(self,'map_runtime_protocol',0)!=1:
                    raise ValueError('Native session does not support independent map ownership')
                if int.from_bytes(payload[4:8],'little')==98 and (type(getattr(self,'retired_world_cleanup_protocol',0)) is not int or self.retired_world_cleanup_protocol!=1):
                    raise ValueError('Native session does not support retired map ownership')
                from .map_runtime import validate_request
            elif scene_mesh:
                from ._runtime_scene_wire import validate_request
            elif (type(payload) is bytes and len(payload)>=8 and
                    70<=int.from_bytes(payload[4:8],'little')<=73):
                if getattr(self,'runtime_cinematic_protocol',0)!=2:
                    raise ValueError('Native session does not support the isolated cinematic adapter')
                from ._runtime_cinematic_wire import validate_request
            else:
                if (type(payload) is bytes and len(payload)>=8 and int.from_bytes(payload[4:8],'little')==68
                        and (type(getattr(self,'builder_world_retirement_protocol',0)) is not int or self.builder_world_retirement_protocol!=1)):
                    raise ValueError('Native session does not support World Builder retirement')
                from .procedural_mesh import validate_request
            if scene_mesh:validate_request(payload,protocol=self.runtime_scene_protocol,allow_retired=type(getattr(self,'retired_world_cleanup_protocol',0)) is int and self.retired_world_cleanup_protocol==1)
            else:validate_request(payload)
            suffix = ' ' + payload.hex()
        elif qa_encounter:
            from .qa_encounter import validate_request
            validate_request(payload)
            suffix = ' ' + payload.hex()
        elif picto_progress:
            from .picto_progression import validate_request
            validate_request(payload)
            suffix = ' ' + payload.hex()
        elif lease_policy:
            from .lease_policy import validate_request
            validate_request(payload)
            suffix = ' ' + payload.hex()
        elif widget_hook:
            from ._cinematic_widget import validate_request
            validate_request(payload)
            suffix = ' ' + payload.hex()
        elif sound_event:
            from ._cinematic_sound_event import validate_request
            validate_request(payload)
            suffix = ' ' + payload.hex()
        elif music_audio:
            from ._music_audio_owner import validate_request
            validate_request(payload)
            suffix = ' ' + payload.hex()
        elif override:
            from ._scoped_assignment import validate_request
            validate_request(payload)
            suffix = ' ' + payload.hex()
        elif sequence:
            from ._sequence_owner import validate_request
            validate_request(payload)
            suffix = ' ' + payload.hex()
        elif media:
            from ._media_owner import validate_request
            validate_request(payload)
            suffix = ' ' + payload.hex()
        elif pause:
            from ._pause_attachment import validate_request
            validate_request(payload,allow_retired=type(getattr(self,'retired_world_cleanup_protocol',0)) is int and self.retired_world_cleanup_protocol==1)
            suffix = ' ' + payload.hex()
        elif ui_batch:
            from ._ui_batch import validate_request
            validate_request(payload)
            suffix = ' ' + payload.hex()
        elif keys:
            from ._key_wire import validate_request
            validate_request(payload)
            suffix = ' ' + payload.hex()
        elif trace:
            from ._trace_wire import SIZE, HEADER
            if type(payload) is not bytes or len(payload) != SIZE or HEADER.unpack_from(payload)[0] != 1:
                raise ValueError('Invalid trace payload')
            if HEADER.unpack_from(payload)[1] == 6 and getattr(self, 'trace_renew_protocol', 0) != 1:
                raise ValueError('Native session does not support trace renewal')
            suffix = ' ' + payload.hex()
        elif multi_button:
            from ._multi_button_wire import validate_request
            validate_request(payload)
            suffix = ' ' + payload.hex()
        elif button_action:
            from ._button_action_wire import validate_request
            validate_request(payload)
            suffix = ' ' + payload.hex()
        elif menu:
            from ._menu_wire import SIZE, CALL_SIZE
            if getattr(self,'menu_input_protocol',0)==1: SIZE += 2*CALL_SIZE
            if type(payload) is not bytes or len(payload) != SIZE or int.from_bytes(payload[:4], 'little') != 1:
                raise ValueError('Invalid menu ownership payload')
            suffix = ' ' + payload.hex()
        elif text:
            from ._text_wire import SIZE, VERSION
            if type(payload) is bytes and int.from_bytes(payload[:4], 'little') == 5:
                if type(getattr(self, 'string_value_protocol', None)) is not int or self.string_value_protocol != 1:
                    raise ValueError('Native session does not support FString input')
                VERSION = 5
            if type(payload) is not bytes or len(payload) != SIZE or int.from_bytes(payload[:4], 'little') != VERSION:
                raise ValueError('Invalid owned text invocation payload')
            suffix = ' ' + payload.hex()
        elif assignment:
            from ._assignment_wire import SIZE
            if type(payload) is not bytes or len(payload) != SIZE:
                raise ValueError('Invalid object assignment payload')
            suffix = ' ' + payload.hex()
        elif retained:
            from ._retained_wire import SIZE
            if type(payload) is not bytes or len(payload) != SIZE:
                raise ValueError('Invalid retained invocation payload')
            if int.from_bytes(payload[:4], 'little') == 8 and (
                    type(getattr(self, 'blueprint_invocation_protocol', None)) is not int or
                    self.blueprint_invocation_protocol != 1):
                raise ValueError('Native session does not support typed Blueprint invocation')
            if int.from_bytes(payload[:4], 'little') == 4 and any(getattr(self, name, 0) != 1 for name in
                    ('enum_value_protocol', 'text_value_protocol', 'pod_value_protocol', 'object_assignment_protocol',
                     'stable_identity_protocol', 'retained_protocol', 'lease_protocol', 'reflected_protocol')):
                raise ValueError('Native session does not support enum invocation')
            suffix = ' ' + payload.hex()
        elif metadata_stabilize:
            from ._metadata_stabilization import validate_request
            validate_request(payload)
            suffix=' '+payload.hex()
        elif lease_batch:
            from ._lease_release_batch import validate_request
            validate_request(payload)
            suffix = ' ' + payload.hex()
        elif leased:
            from ._lease_wire import SIZE
            if type(payload) is not bytes or len(payload) != SIZE:
                raise ValueError('Invalid object lease payload')
            suffix = ' ' + payload.hex()
        elif reflected:
            from ._invocation_wire import SIZE
            if type(payload) is not bytes or len(payload) != SIZE:
                raise ValueError('Invalid reflected invocation payload')
            suffix = ' ' + payload.hex()
        elif payload is not None:
            if command not in ('console-execute', 'console-print', 'console-names', 'console-key') or not isinstance(payload, str) or '\0' in payload:
                raise ValueError('Invalid console payload')
            encoded = payload.encode('utf-16le')
            if len(encoded) > (8192 if command == 'console-execute' else 65536):
                raise ValueError('Console payload is too long')
            suffix = ' ' + encoded.hex()
        if (reflected or retained) and int.from_bytes(payload[:4], 'little') == 2:
            if getattr(self, 'pod_value_protocol', 0) != 1:
                raise ValueError('Native session does not support POD value invocation')
            from ._invocation_wire import FIELDS_AT, FIELD, MAX_FIELDS
            count = int.from_bytes(payload[24:28], 'little')
            if count > MAX_FIELDS:
                raise ValueError('Invalid invocation field count')
            if any(int.from_bytes(payload[FIELDS_AT+i*FIELD.size:FIELDS_AT+i*FIELD.size+4], 'little') == 19 for i in range(count)):
                cap = getattr(self, 'frame_time_values_protocol', 0)
                if type(cap) is not int or cap != 1:
                    raise ValueError('Native session does not support frame timing returns')
        if (reflected or retained) and int.from_bytes(payload[:4], 'little') == 2:
            if any(int.from_bytes(payload[FIELDS_AT+i*FIELD.size:FIELDS_AT+i*FIELD.size+4], 'little') == 20 for i in range(count)):
                cap = getattr(self, 'timespan_values_protocol', 0)
                if type(cap) is not int or cap != 1:
                    raise ValueError('Native session does not support media Timespan returns')
        try:
            prefix=''
            if getattr(self,'lease_policy_protocol',0)==1:
                owner=getattr(self,'_lease_owner',0)
                if type(owner) is not int or not 0<=owner<2**64:raise ValueError('Invalid lease owner')
                prefix=f'lease-owner {owner} '
            self._process.stdin.write(prefix + command + suffix + '\n')
            self._process.stdin.flush()
            response = self._read()
            if response.get('event') != 'session_response' or response.get('command') != command:
                raise RuntimeQueryError('Native session response does not match its command')
            if command == 'close':
                if response.get('closed') is not True or response.get('close_reason') != 1:
                    raise RuntimeQueryError('Native session close was not confirmed')
            elif response.get('closed') is not False:
                raise RuntimeQueryError('Native session closed unexpectedly')
            status_cap = getattr(self, 'console_color_status_protocol', 0)
            if color_status or (command == 'console-poll' and type(status_cap) is int and status_cap == 1):
                status = response.get('console_color_status')
                names = ('version', 'native_version', 'bound', 'disabled', 'unsupported', 'frames', 'fallbacks', 'faults')
                if (type(status) is not dict or set(status) != set(names) or
                        any(type(status[name]) is not int for name in names) or status['version'] != 1 or
                        not 1 <= status['native_version'] <= 1000000 or
                        any(status[name] not in (0, 1) for name in ('bound', 'disabled', 'unsupported')) or
                        any(not 0 <= status[name] < 2**64 for name in ('frames', 'fallbacks', 'faults'))):
                    raise RuntimeQueryError('Invalid native console color status')
            return response
        except BaseException as error:
            # Keep the first wire failure: a menu service can catch it before
            # a later key poll observes only the already-closed transport.
            # Never record payloads or retry a command with uncertain outcome.
            if getattr(self, '_terminal_failure', None) is None:
                self._terminal_failure = {'command': command, 'error': f'{type(error).__name__}: {error}'}
            self._abort()
            raise

    def _abort(self):
        # Only our controller subprocess. Its exit wakes the target-owned cleanup
        # watcher; never terminate or force-unload anything from the game here.
        self._closed = True
        if self._process.poll() is None:
            if self.target_exit_code is not None:
                try:
                    self._process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self._process.kill()
            else:
                self._process.kill()
        self._process.wait(timeout=10)
        try:
            self._process.stdin.close()
        except OSError:
            pass  # A dead controller can reject the buffered pipe flush.
        self._reader.join(timeout=2)
        self._process.stdout.close()

    def close(self):
        self._check_thread()
        if self._closed:
            return
        try:
            self.command('close')
            self._process.stdin.close()
            end = self._read()
            if end.get('event') != 'snapshot_end' or end.get('emitted') != 2:
                raise RuntimeQueryError('Native session final boundary is missing')
            if self._process.wait(timeout=10) != 0:
                raise RuntimeQueryError('Native session controller exited with an error')
            self._closed = True
            self._reader.join(timeout=2)
            self._process.stdout.close()
        except BaseException:
            self._abort()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.close()
