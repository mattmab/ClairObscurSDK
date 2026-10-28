"""Scene-specific presenter over the SDK's existing WorldBuilder-style UI."""
import json
from dataclasses import replace
from expedition33.management_view import MenuControl
from expedition33.mods_workspace_scroll import ScrollWorkspaceView
from expedition33.management import ManagementError
from .scene import ROLES,CLIPS,CLIP_LABELS,MAX_ACTORS
from .palette import CHARACTERS,ANIMATIONS,animation_choices,animation_sets,actor_animation_owner,clip_set,library_roles,library_label,animation_inventory
from . import catalog

class SceneView(ScrollWorkspaceView):
    def __init__(self,registry,model):
        super().__init__(registry);self.model=model;self.screen=getattr(model,'next_screen',None) or 'scene';model.next_screen=None;self.status=model.message;self.actor_id='lune';self.event_id=None;self.edit_field=None;self.animation_query='';self.animation_group='character';self.saved_id=None;self.actor_catalog_all=False;self.actor_asset=None;self.actor_category=None;self.actor_catalog_review=False;self.catalog_asset=None
        self.authored_path=getattr(model,'authored_selected',None)
        if self.screen=='scene_authored' and getattr(model,'authored_browser_state',None):self.page,self.query=model.authored_browser_state
    @staticmethod
    def _map_name(path):return path.rsplit('.',1)[-1].replace('Level_','').replace('_',' ')
    def _summary(self,d):
        state='Unsaved changes' if self.model.dirty else 'Saved scene' if self.model.key else 'Sample / not saved'
        return d['name']+f"\n{d['duration']:g}s | {len(d['actors'])} characters\n"+f"{sum(e['type']=='animation' for e in d['events'])} animation clips | {sum(e['type']=='audio' for e in d['events'])} audio clips | {len(d.get('camera_keys',[]))} camera keys\nMap: "+self._map_name(d['target_map'])+'\n'+state
    def _rows(self):
        if not self.screen.startswith('scene'):return super()._rows()
        m=self.model;d=m.document;editable=m.runtime.scope is None and not m.want_play
        def row(label,op,arg=None,enabled=True):return (label,'scene_'+op,arg,enabled,None)
        title='Scene Editor';description='Create a scene or open Saved scenes. Photo mode uses the game camera; Flight editor is the fallback. End stops playback.'
        if self.screen=='scene':
            if d:description=self._summary(d)+"\n\nPhoto mode: open the game's photo mode first. Flight editor provides a separate editing camera.\nBackspace: Show / hide Scene Editor UI; press again to restore.\nEnd: stop | Insert: scene menu"
            rows=[row('New scene','new',enabled=editable),row('Saved scenes','page','scene_saved',editable),row('Game sequences','page','scene_authored',editable),row('Photo mode / timeline','photo',enabled=d is not None and editable),row('Flight editor / timeline','live',enabled=d is not None and editable),row('Actors / size / clips','page','scene_actors',d is not None and editable),row('Actor library','page','scene_add',d is not None and editable),row(f"Length: {d['duration']:g}s" if d else 'Scene length','edit',('duration',d['duration'] if d else 20,'float'),d is not None and editable),row('Scene settings / Save','page','scene_settings',d is not None),row('Playback controls','page','scene_playback',d is not None)]
        elif self.screen=='scene_authored':
            title='Game-authored sequences'
            sources=[source for source in m.authored.catalog if self.query.casefold() in (source['title']+' '+source['path']).casefold()]
            selected=getattr(self,'authored_path',None)
            loaded=m.authored.document is not None and m.authored.document['source']['sequence']==selected
            source=next((source for source in m.authored.catalog if source['path']==selected),None)
            description=(source['title']+'\n' if source else 'Select a sequence on the left.\n')
            description+=('Loaded\n'+'\n'.join(m.authored.summary().splitlines()[:2]) if loaded else 'Not loaded. Load source to inspect tracks without starting playback, or Open timeline to load and edit in one step.')
            if m.pending_authored is not None or m.pending_timeline_source is not None:description+='\nReading source; controls return when loading finishes.'
            description+=f'\n{len(sources)} matching sequences. Search filters the library.'
            if source:description+='\n\n'+source['path']
            rows=[row(('> ' if source['path']==selected else '')+source['title'],'authored_select',source['path']) for source in sources]
        elif self.screen=='scene_authored_nodes':
            title='Authored source tracks'
            description=m.authored.summary()+'\n\nSearch animation, camera or audio to filter. Select an object to inspect its copied fields and unsupported data.'
            rows=[row('Open timeline editor','authored_editor',enabled=m.authored.document is not None and editable),row('Game sequence library','page','scene_authored'),row('Timeline properties','page','scene_authored_timeline',m.authored.document is not None)]
            rows += [row(node['class_name'].removeprefix('MovieScene')+'\n'+path.rsplit('.',1)[-1],'authored_node',path) for path,node in m.authored.nodes(self.query)]
        elif self.screen=='scene_authored_node':
            title='Authored source object'
            path=getattr(self,'authored_node',None);node=m.authored.graph['nodes'].get(path) if m.authored.graph else None
            description=path+'\n\n'+json.dumps(node,indent=2,ensure_ascii=False)[:12000] if node else 'Source is no longer loaded.'
            rows=[row('Back to source tracks','page','scene_authored_nodes')]
        elif self.screen=='scene_authored_cast':
            title='Authored cast and components'
            description='Select an actor binding to replace its character Blueprint. Component paths and animations depend on Blueprint compatibility; replacements do not automatically retarget them. Replacements save with the timeline. The actor-pool runtime supports up to 32 replacements; older runtimes support one.'
            rows=[row('Back to authored timeline','page','scene_authored_timeline')]
            try:
                cast_rows=sorted(m.authored.cast(self.query),key=lambda c:not (c['template'] and c['template']['class'].startswith('BP_Cine_')))
                rows += [row(c['name']+' | '+c['kind']+' | '+c['sequence'].rsplit('.',1)[-1],
                             'authored_cast',(c['sequence'],c['guid'])) for c in cast_rows]
            except ValueError as error:description+='\n\nCast unavailable: '+str(error)
        elif self.screen=='scene_authored_cast_binding':
            title='Authored cast binding'
            selected=getattr(self,'authored_cast',None)
            cast=next((c for c in m.authored.cast() if (c['sequence'],c['guid'])==selected),None)
            description='Binding is no longer loaded.'
            if cast:
                template=cast['template'];children=[c['name'] for c in m.authored.cast() if c['sequence']==cast['sequence'] and c['guid'] in cast['children']]
                description=(cast['name']+'\nShot: '+cast['sequence'].rsplit('.',1)[-1]+'\n'+
                             (('Blueprint: '+template['class']+'\n') if template else
                              ('Source template unavailable; replacement disabled\n' if cast['kind']=='spawnable' else 'Component binding\n'))+
                             f"{len(cast['tracks'])} tracks | {len(cast['unread_tracks'])} unread\n"+
                             ('Components: '+', '.join(children)+'\n' if children else ''))
            rows=[row('Back to cast','page','scene_authored_cast')]
            if cast and cast['kind']=='spawnable' and cast['template'] and cast['template']['class'].startswith('BP_Cine_'):
                chosen=next((e['profile'] for e in m.authored.document.get('cast_edits',[]) if (e['sequence'],e['guid'])==selected),None)
                description='Replacement: '+(chosen.title() if chosen else 'Original character')+'\n\n'+description
                if chosen:
                    from expedition33.cinematics.authored_cast import replacement_overlap_warning
                    warning=replacement_overlap_warning(m.authored.cast(),m.authored.document.get('cast_edits',()),selected,chosen)
                    if warning:description+='\n\n'+warning
                rows.append(row('Use original character','authored_replace',None,editable))
                from expedition33.cinematics.blueprint_actor import available_profiles
                transport=getattr(getattr(m.session,'_session',None),'_transport',None)
                for profile in available_profiles(transport):
                    rows.append(row(('> ' if chosen==profile else '')+'Replace with '+profile.title(),'authored_replace',profile,editable))
                if chosen:
                    edit=next(e for e in m.authored.document['cast_edits'] if (e['sequence'],e['guid'])==selected)
                    placement=edit.get('placement',dict(offset=[300.,0.,0.],yaw=0.))
                    description+='\n\nBlueprint placement is relative to the preview anchor, in centimeters. Authored transform tracks can subsequently move the actor.'
                    for axis,index in zip('XYZ',range(3)):
                        rows.append(row(f"Offset {axis}: {placement['offset'][index]:g} cm",'edit',('authored_cast:'+axis,placement['offset'][index],'float'),editable))
                    rows.append(row(f"Yaw: {placement['yaw']:g} degrees",'edit',('authored_cast:yaw',placement['yaw'],'float'),editable))
                rows.append(row('Save authored timeline','authored_save',enabled=editable))
        elif self.screen=='scene_authored_timeline':
            title='Authored timeline'
            description=('Section ranges and curve keys use each source sequence\'s native integer ticks. Nested sequences keep their own time space. Edited preview applies changes to a private sequence copy.\n\n'+('Unsaved edits' if m.authored.dirty else 'Saved timeline'))
            from .authored_preview import preview_supported
            from expedition33.cinematics.authored_copy import curve_edits_available
            transport=getattr(getattr(m.session,'_session',None),'_transport',None)
            previewable=editable and preview_supported(m.authored.document)
            description+='\n\n'+('Preview adapter available.' if preview_supported(m.authored.document) else 'Playback is unavailable for this source. Open timeline editor to inspect and edit tracks, cast and NPCs without playback.')
            rows=[row('Open timeline editor','authored_editor',enabled=m.authored.document is not None and editable),row('Preview original source','authored_preview',enabled=previewable),
                  row('Preview edited timeline','authored_edited_preview',enabled=previewable and (not m.authored.document.get('key_edits') or curve_edits_available(transport))),
                  row('Save authored timeline','authored_save',enabled=m.authored.document is not None),row('Saved authored timelines','page','scene_authored_saved'),
                  row('Cast and component bindings','page','scene_authored_cast',m.authored.document is not None),
                  row('Blueprint NPC tracks','page','scene_authored_npcs',m.authored.document is not None)]
            rows += [row(r['kind']+'\n'+(f"{r['start']} to {r['end']} ticks" if r['start'] is not None and r['end'] is not None else 'Open / unspecified range'),'authored_section',r['path']) for r in m.authored.sections(self.query)]
        elif self.screen=='scene_authored_npcs':
            title='Blueprint NPC tracks'
            description='Independent NPCs use original character Blueprints in the QA map. Start is inclusive; end is exclusive, in native player frames. Playback pauses briefly for construction/retirement at observed interval changes. Seeking updates the actors too.'
            rows=[row('Back to authored timeline','page','scene_authored_timeline')]
            from expedition33.cinematics.blueprint_actor import available_profiles
            transport=getattr(getattr(m.session,'_session',None),'_transport',None)
            rows += [row('Add '+p.title()+' NPC','authored_npc_add',p,editable) for p in available_profiles(transport)]
            rows += [row(f"{r['name']} | {r['start']} to {r['end']}",'authored_npc',r['id'],editable) for r in m.authored.document.get('npc_tracks',[])]
        elif self.screen=='scene_authored_npc':
            title='Blueprint NPC track';description='Placement is relative to the preview anchor, in centimeters. This adds an independent actor; it does not replace an authored binding or start a battle.'
            track=next((r for r in m.authored.document.get('npc_tracks',[]) if r['id']==self.authored_npc),None)
            rows=[row('Back to NPC tracks','page','scene_authored_npcs')]
            if track:
                for field,label,kind in (('name','Name','text'),('start','Start frame','int'),('end','End frame','int')):
                    rows.append(row(f"{label}: {track[field]}",'edit',('authored_npc:'+field,track[field],kind),editable))
                for axis,index in zip('XYZ',range(3)):
                    rows.append(row(f"Offset {axis}: {track['placement']['offset'][index]:g} cm",'edit',('authored_npc:'+axis,track['placement']['offset'][index],'float'),editable))
                rows.append(row(f"Yaw: {track['placement']['yaw']:g}",'edit',('authored_npc:yaw',track['placement']['yaw'],'float'),editable))
                rows.append(row('Remove NPC track','authored_npc_remove',track['id'],editable))
                rows.append(row('Save authored timeline','authored_save',enabled=editable))
        elif self.screen=='scene_authored_section':
            path=getattr(self,'authored_section',None)
            section=next((r for r in m.authored.sections() if r['path']==path),None)
            title='Authored section range';description=(path or '')+'\n\nStart and end are native source ticks, not display frames. This changes the section bounds; its curve keys stay at their authored times.'
            rows=[row('Back to authored timeline','page','scene_authored_timeline')]
            if section:
                for field,label in (('start','Start tick'),('end','End tick')):
                    rows.append(row(f'{label}: {section[field]}','edit',('authored:'+field,section[field],'int'),editable and section[field] is not None))
                rows.append(row('Save authored timeline','authored_save',enabled=editable))
                rows += [row('Curve: '+'.'.join(map(str,c['path']))+f" | {len(c['keys'])} keys",'authored_channel',c['path']) for c in m.authored.channels(path)]
        elif self.screen=='scene_authored_channel':
            title='Authored curve keys';description='Select a key to edit its source tick and value. Original interpolation and tangent data are preserved.'
            curve=next((c for c in m.authored.channels(self.authored_section) if c['path']==self.authored_channel),None)
            rows=[row('Back to section','page','scene_authored_section')]
            if curve:rows += [row(f"Key {k['index']}: {k['at']} | {k['value']}",'authored_key',k['index']) for k in curve['keys']]
        elif self.screen=='scene_authored_key':
            title='Authored curve key';description='Times use the source sequence tick resolution. Keys must stay strictly ordered. Save keeps a separate edit document.'
            curve=next((c for c in m.authored.channels(self.authored_section) if c['path']==self.authored_channel),None)
            key=next((k for k in curve['keys'] if k['index']==self.authored_key),None) if curve else None
            rows=[row('Back to curve','page','scene_authored_channel')]
            if key:
                rows.append(row(f"Tick: {key['at']}",'edit',('authored_key:at',key['at'],'int'),editable))
                kind='bool' if curve['kind']=='MovieSceneBoolChannel' else 'int' if curve['kind'] in ('MovieSceneIntegerChannel','MovieSceneByteChannel') else 'float'
                rows.append(row(f"Value: {key['value']}",'edit',('authored_key:value',key['value'],kind),editable))
                rows.append(row('Save authored timeline','authored_save',enabled=editable))
        elif self.screen=='scene_authored_saved':
            title='Saved authored timelines';description='Load a saved edit document without playing a sequence. Native source assets are retained separately when needed for preview.'
            rows=[row(saved['name'],'authored_saved',saved['id'],editable) for saved in m.authored.store.list()]
        elif self.screen=='scene_setup':
            description=self._summary(d)+'\n\n1. Set cinematic length.\n2. Add actors from Actor library.\n3. Use Flight timeline, or open game Photo mode before Photo timeline.'
            rows=[row('Actor library','page','scene_add',editable),row('Current cast','page','scene_actors'),row(f"Length: {d['duration']:g}s",'edit',('duration',d['duration'],'float'),editable),row('Length -5 seconds','resize',-5,editable and d['duration']>2),row('Length +5 seconds','resize',5,editable and d['duration']<120),row('Flight editor / timeline','live',enabled=editable),row('Photo mode / timeline','photo',enabled=editable),row('Name / Save scene','page','scene_settings')]
        elif self.screen=='scene_settings':
            description=self._summary(d)+'\n\nLength: 2-120 seconds. Existing events must fit within the new length. Save As creates a separate scene.'
            rows=[row('Actor library','page','scene_add',editable),row('Current cast','page','scene_actors'),row('Timeline events','page','scene_events'),row('Name: '+d['name'],'edit',('name',d['name'],'text'),editable),row(f"Length: {d['duration']:g} seconds",'edit',('duration',d['duration'],'float'),editable),row('Save scene','save',enabled=editable),row('Save As...','save_as',enabled=editable),row('Load sample scene','sample',enabled=editable)]
        elif self.screen=='scene_photo_help':
            description='PHOTO TIMELINE\n\nOpen the game Photo mode first:\n1. Close this menu.\n2. Pause the game and choose Photo mode.\n3. Press Insert to return here.\n4. Choose Photo mode / timeline.\n\nFlight timeline works directly from normal exploration.'
            rows=[row('Try Photo timeline','photo',enabled=d is not None and editable),row('Flight editor / timeline','live',enabled=d is not None and editable),row('Scene setup','page','scene_setup')]
        elif self.screen=='scene_playback':
            description=self._summary(d)+'\n\nPlay begins the scene from its start. End stops playback and releases temporary scene actors.'
            rows=[row('Play scene','play',enabled=editable),row('Stop playback','stop')]
        elif self.screen=='scene_saved':
            saved=[r for r in m.store.list() if not self.query or self.query.casefold() in (r['name']+' '+r['target_map']).casefold()]
            selected=next((r for r in saved if r['id']==self.saved_id),None)
            rows=[row('Load selected scene','load',self.saved_id,editable and selected is not None),row('New scene','new',enabled=editable),row('Load sample scene','sample',enabled=editable)]+[row(('> ' if r['id']==self.saved_id else '')+r['name'],'saved_select',r['id']) for r in saved]
            description=f'{len(saved)} saved scenes. Search by name or map. Select a scene to inspect it, then Load selected scene. Loading never starts playback.'
            if selected:description=selected['name']+f"\n{selected['duration']:g}s | {selected['actors']} characters\n{selected['animations']} animation clips | {selected['audio']} audio clips\n{selected['camera_keys']} camera keys\nMap: "+self._map_name(selected['target_map'])+'\n\n'+description
        elif self.screen=='scene_actors':
            rows=[row('Add character...','page','scene_add',editable and len(d['actors'])<MAX_ACTORS)]+[row(a['name']+f" | {a['transform']['scale'][0]*100:g}% size",'actor',a['id']) for a in d['actors']]
            description='Choose a scene actor to change its size, animation or placement. Then open Flight editor / timeline to preview and scrub. Changes affect only the temporary scene actors.'
        elif self.screen=='scene_actor':
            a=m.actor(self.actor_id);p=a['transform'];assembly=d['assemblies'][a['assembly']]
            description=a['name']+f" | Size: {p['scale'][0]*100:g}%\n\nHalf / Double size changes this actor only. Exact size uses a multiplier: 1 = 100%, 0.01 = 1%.\nChoose Animation to browse this character's clips. Position / rotation controls its placement and orientation.\n\nOpen Flight editor / timeline from the scene menu to preview and scrub. Save scene keeps these changes."
            present=any(e['id']=='anim-'+a['id'] for e in d['events']);anim=next((e for e in d['events'] if e['id']=='anim-'+a['id']),dict(id='anim-'+a['id'],at=0.,params=dict(asset='bind_pose',loop=False)));clip='Bind pose (no animation)' if anim['params']['asset']=='bind_pose' else CLIP_LABELS[CLIPS.index(anim['params']['asset'])]
            rows=[row(f'Size: {p['scale'][0]*100:g}%','edit',(f'pose:{a["id"]}:scale:0',p['scale'][0],'float'),editable),row('Half size','size',0.5,editable),row('Double size','size',2.,editable),row('Position / rotation','page','scene_transform',editable),row('Animation: '+clip,'page','scene_animation',editable),row('Animation start: '+f'{anim["at"]:g}s','edit',('event:'+anim['id'],anim['at'],'float'),editable and present),row('Loop: '+('On' if anim['params']['loop'] else 'Off'),'loop',a['id'],editable and present),row('Remove character...','page','scene_remove',editable),row('Name: '+a['name'],'edit',('actor_name:'+a['id'],a['name'],'text'),editable)]
        elif self.screen=='scene_transform':
            a=m.actor(self.actor_id);p=a['transform']
            description=a['name']+' | Placement and orientation\nPositions use scene anchor coordinates. Rotation is in degrees.\nSize accepts 0.001 to 3 (0.1% to 300%).'
            rows=[row('Back to actor','actor',a['id'])]
            for field,labels in (('position',('Forward X','Right Y','Up Z')),('rotation',('Pitch','Yaw','Roll'))):
                for axis,label in enumerate(labels):rows.append(row(f'{label}: {p[field][axis]:g}','edit',(f'pose:{a["id"]}:{field}:{axis}',p[field][axis],'float'),editable))
            rows.append(row(f'Uniform scale: {p["scale"][0]:g}','edit',(f'pose:{a["id"]}:scale:0',p['scale'][0],'float'),editable))
        elif self.screen=='scene_add':
            title='Actor library'
            if self.actor_catalog_all:
                description=f"{len(d['actors'])} / {MAX_ACTORS} actors. All game meshes includes parts, outfits and unverified rigs. Inspect before adding. This fallback preserves the existing raw mesh catalog."
                rows=[row('Supported character catalog','actor_filter')]+[row(library_label(role),'actor_asset',role) for role in library_roles(True,self.query)]
            else:
                found=catalog.entries(self.actor_category,self.query,self.actor_catalog_review)
                description=f"{len(d['actors'])} / {MAX_ACTORS} actors | {len(found)} results\n"+('Discovery review: 150 provisional records, including aliases, body archetypes and wildlife. These are not 150 unique characters.' if self.actor_catalog_review else 'Supported catalog: 62 character families. Ready uses existing working recipes. Body only is an incomplete mesh preview; assembly pending is inspectable.')+'\n\nChoose a category or search names and asset paths. Select an entry for status, animation coverage and exact assets. Hiding unverified entries is never automatic.'
                rows=[row('Category: '+(self.actor_category or 'All supported'),'catalog_categories'),row('Supported catalog (62)' if self.actor_catalog_review else 'Discovery review (150)','catalog_review'),row('All game meshes','actor_filter')]
                for item in found:
                    ready=catalog.ready_roles(item)
                    # Preserve the existing one-role Add flow and labels.
                    rows.append(row(library_label(ready[0]),'actor_asset',ready[0]) if len(ready)==1 and not self.actor_catalog_review else row(catalog.label(item),'catalog_asset',item['id']))
        elif self.screen=='scene_catalog_categories':
            title='Actor categories'
            description='Categories organize both the supported catalog and discovery review. Unknown retains unresolved classifications. Main Characters is a browsing group; a Gestral may also be a playable main character.'
            rows=[row('All supported' if not self.actor_catalog_review else 'All review candidates','catalog_category',None)]+[row(name,'catalog_category',name) for name in catalog.CATEGORIES]
        elif self.screen=='scene_catalog_asset':
            item=catalog.entry(self.catalog_asset);title='Actor library'
            description=catalog.details(item)+f"\n\nScene cast: {len(d['actors'])} / {MAX_ACTORS}"
            enabled=editable and len(d['actors'])<MAX_ACTORS
            ready=catalog.ready_roles(item);candidates=catalog.candidate_roles(item);bodies=catalog.body_roles(item)
            rows=[row('Add: '+CHARACTERS[role]['label'],'add',role,enabled) for role in ready]
            rows += [row(catalog.candidate_action(role)+': '+CHARACTERS[role]['label'],'add',role,enabled) for role in candidates]
            rows += [row('Body only (incomplete): '+CHARACTERS[role]['label'],'add',role,enabled) for role in bodies]
            if not ready and not candidates and not bodies:rows.append(row('Assembly pending - inspect only','catalog_asset',item['id'],False))
            rows += [row('Back to Actor library','page','scene_add'),row('Current cast','page','scene_actors')]
        elif self.screen=='scene_actor_asset':
            asset=CHARACTERS[self.actor_asset];title='Actor library'
            description=asset['label']+'\n\n'+((asset.get('library_note','')+'\n'+str(asset['animation_count'])+' previewable character animations; '+str(asset.get('discovered_animation_count',asset['animation_count']))+' discovered. Starts with a matching clip.') if asset.get('main_actor') else 'Raw skeletal mesh: may be a body part. Starts in bind pose.' if asset.get('raw') else 'Assembled actor: uses the inspected body/hair/equipment recipe.')+f"\n\nScene cast: {len(d['actors'])} / {MAX_ACTORS}\n\n"+'\n'.join(part['path'] for part in asset['parts'] if part['path'])
            evidence=catalog.for_role(self.actor_asset)
            if evidence:description=catalog.details(evidence)+f"\n\nScene cast: {len(d['actors'])} / {MAX_ACTORS}"
            incomplete=asset.get('raw') and not asset.get('main_actor')
            action=catalog.candidate_action(self.actor_asset) if asset.get('library_kind')=='assembly_candidate' and incomplete else 'Body only (incomplete)' if incomplete else 'Add to scene'
            rows=[row(action,'add',self.actor_asset,editable and len(d['actors'])<MAX_ACTORS),row('Back to Actor library','page','scene_add'),row('Current cast','page','scene_actors')]
        elif self.screen=='scene_animation_inventory':
            role,skeleton=m.animation_context(self.actor_id)
            unavailable=[item for item in animation_inventory(role,skeleton) if not item['previewable']]
            description='Additional discovered clips for this character. These are listed for completeness but cannot run in the current isolated preview path. Gameplay notifies, root motion and additive poses need separate support.'
            rows=[row(item['path'].rsplit('.',1)[-1]+' | '+item['reason'],'page','scene_animation',False) for item in unavailable]
        elif self.screen in ('scene_animation','scene_animation_groups','scene_clips'):
            role,skeleton=m.animation_context(self.actor_id);name=m.actor(self.actor_id)['name']
            group='character' if self.screen=='scene_animation' else self.animation_group
            matches=animation_choices(role,skeleton,group,self.animation_query)
            title='Animations | '+name
            description=(f'{len(matches)} clips | Set: '+(actor_animation_owner(role) if group=='character' else group or 'All compatible')+' | Search: '+(self.animation_query or 'none')+'\nCharacter sets use the source asset, even if you rename the actor. Shared sets are listed separately. Only matching skeletons are selectable.')
            if not animation_choices(role,skeleton,None):description+='\nNo inspected compatible animations in this catalog for this mesh. Keep Bind pose or choose another actor; additional animation families may need inspection.'
            if self.screen=='scene_animation_groups':
                rows=[row('This character','animation_group','character'),row('All compatible animations','all_animations')]+[row(group+' ('+str(len(animation_choices(role,skeleton,group)))+')','animation_group',group) for group in animation_sets(role,skeleton)]
            else:
                rows=[row('Bind pose (no animation)','animation','bind_pose',editable),row('Clear incompatible clips','repair_animations',self.actor_id,editable),row('Character / shared sets','page','scene_animation_groups'),row('Other discovered clips','page','scene_animation_inventory'),row('All compatible animations','all_animations')]+[row(ANIMATIONS[k]['label'],'animation',k,editable) for k in matches]
        elif self.screen=='scene_remove':
            description='Remove '+m.actor(self.actor_id)['name']+'? Its animation and dependent sample attack events are removed too. The bundled sample stays unchanged; Load Sample restores it.'
            rows=[row('Remove this character','remove',self.actor_id,editable)]
        elif self.screen=='scene_events':
            description='Select an event to edit its start time. Audio, effects and recoil have separate events. The experimental v12 recoil curve is unchanged.'
            rows=[row(f'{e["at"]:6.3f}s  {e["type"]} / {e["target"]}','event',e['id']) for e in sorted(d['events'],key=lambda e:(e['at'],e['id']))]
        elif self.screen=='scene_event':
            e=m.event(self.event_id);description=e['id']+'\n'+e['type']+' -> '+e['target']+'\n\n'+json.dumps(e['params'],indent=2)
            rows=[row(f'Start time: {e["at"]:g} seconds','edit',('event:'+e['id'],e['at'],'float'),editable)]
        else:
            rows=[row(r['name'],'load',r['id'],editable) for r in m.store.list()]
            description='Select a saved scene. Loading never starts playback. The bundled sample is read-only and is stored separately from these user files.'
        if self.editing:
            option=self.editing[1];description='EDIT '+option['title']+'\n\nType a value into the input field, then click Apply. Cancel keeps the document unchanged.\n\n'+description
        return title,description,rows
    def render(self):
        frame=super().render()
        if self.screen!='scene_authored':return frame
        m=self.model;selected=getattr(self,'authored_path',None)
        loaded=m.authored.document is not None and m.authored.document['source']['sequence']==selected
        idle=m.runtime.scope is None and not m.want_play and m.authored_preview is None and m.pending_authored is None and m.pending_timeline_source is None and m.authored.loading is None
        from .authored_preview import preview_supported
        previewable=loaded and idle and preview_supported(m.authored.document)
        actions=(('Load source','authored_load',selected,selected is not None and idle),
                 ('Open timeline','authored_open_selected',selected,selected is not None and idle),
                 ('Source tracks','page','scene_authored_nodes',loaded and idle),
                 ('Timeline properties','page','scene_authored_timeline',loaded and idle),
                 ('Cast and bindings','page','scene_authored_cast',loaded and idle),
                 ('Blueprint NPC tracks','page','scene_authored_npcs',loaded and idle),
                 ('Preview source','authored_preview',None,previewable),
                 ('Save timeline','authored_save',None,loaded and idle))
        controls=list(frame.controls)
        for token,(label,op,arg,enabled) in enumerate(actions,56):
            controls[token]=MenuControl(token,label,enabled)
            self._commands[token]=('scene_'+op,arg,enabled)
        return replace(frame,controls=tuple(controls),status=m.message if 'failed' in m.message.casefold() else '')

    def activate(self,revision,token,*,value=None,reset=False):
        self._check()
        if revision!=self._revision or token not in self._commands or not self._commands[token][2]:raise ManagementError('Stale Scene Editor control')
        op,arg,_=self._commands[token]
        animation_search=op in ('search','clear') and self.screen in ('scene_animation','scene_animation_groups','scene_clips')
        character_search=op in ('search','clear') and self.screen in ('scene_add','scene_saved','scene_authored','scene_authored_nodes','scene_authored_timeline','scene_authored_cast')
        if op.startswith('scene_') or animation_search or character_search or (self.edit_field is not None and op in ('apply','reset','cancel')) or (op=='back' and self.screen.startswith('scene')):
            self._invalidate()
            try:
                if op=='scene_page':
                    if arg=='scene_saved' and hasattr(self.model,'want_saved'):self.model.want_saved=True
                    else:
                        self.screen=arg
                        if arg=='scene_animation':self.animation_group='character';self.animation_query=''
                    self.page=0;self.editing=None;self.edit_field=None;self.query=''
                elif op=='scene_sample':self.model.load_sample();self.screen='scene';self.page=0
                elif op=='scene_new':self.model.new_scene();self.model.next_screen=None;self.screen='scene_setup';self.page=0
                elif op=='scene_saved_select':self.saved_id=arg
                elif op=='scene_authored_select':self.authored_path=arg;self.model.authored_selected=arg
                elif op=='scene_authored_load':self.model.queue_authored(arg)
                elif op=='scene_authored_open_selected':
                    self.model.authored_return_screen='scene_authored';self.model.authored_browser_state=(self.page,self.query)
                    if self.model.authored.document is not None and self.model.authored.document['source']['sequence']==arg:self.model.queue_authored_preview(edited=True,editing_only=True)
                    else:self.model.load_timeline_source(arg,editing_only=True)
                elif op=='scene_authored_editor':self.model.queue_authored_preview(edited=True,editing_only=True)
                elif op=='scene_authored_preview':self.model.queue_authored_preview()
                elif op=='scene_authored_edited_preview':self.model.queue_authored_preview(edited=True)
                elif op=='scene_authored_unload':self.model.unload_authored();self.screen='scene_authored'
                elif op=='scene_authored_node':self.authored_node=arg;self.screen='scene_authored_node';self.page=0
                elif op=='scene_authored_cast':self.authored_cast=arg;self.screen='scene_authored_cast_binding';self.page=0
                elif op=='scene_authored_replace':
                    self.model.authored.replace_cast(*self.authored_cast,arg)
                    self.model.message='Character replacement changed. Save the authored timeline to keep it.'
                elif op=='scene_authored_npc_add':
                    self.authored_npc=self.model.authored.add_npc(arg);self.screen='scene_authored_npc';self.page=0
                elif op=='scene_authored_npc':self.authored_npc=arg;self.screen='scene_authored_npc';self.page=0
                elif op=='scene_authored_npc_remove':self.model.authored.remove_npc(arg);self.screen='scene_authored_npcs';self.page=0
                elif op=='scene_authored_section':self.authored_section=arg;self.screen='scene_authored_section';self.page=0
                elif op=='scene_authored_channel':self.authored_channel=arg;self.screen='scene_authored_channel';self.page=0
                elif op=='scene_authored_key':self.authored_key=arg;self.screen='scene_authored_key';self.page=0
                elif op=='scene_authored_save':self.model.authored.save();self.model.message='Authored timeline saved.'
                elif op=='scene_authored_saved':self.model.authored.load_saved(arg);self.model.message='Authored timeline loaded without playback.';self.screen='scene_authored_timeline';self.page=0
                elif op=='scene_actor_filter':self.actor_catalog_all=not self.actor_catalog_all;self.page=0
                elif op=='scene_catalog_review':self.actor_catalog_review=not self.actor_catalog_review;self.actor_catalog_all=False;self.page=0
                elif op=='scene_catalog_categories':self.screen='scene_catalog_categories';self.page=0
                elif op=='scene_catalog_category':self.actor_category=arg;self.actor_catalog_all=False;self.screen='scene_add';self.page=0
                elif op=='scene_catalog_asset':self.catalog_asset=arg;self.screen='scene_catalog_asset';self.page=0
                elif op=='scene_actor_asset':self.actor_asset=arg;self.screen='scene_actor_asset';self.page=0
                elif op=='scene_size':
                    a=self.model.actor(self.actor_id)
                    self.model.edit(f'pose:{self.actor_id}:scale:0',min(3.,max(.001,a['transform']['scale'][0]*arg)))
                elif op=='scene_actor':self.actor_id=arg;self.screen='scene_actor';self.page=0
                elif op=='scene_add':self.actor_id=self.model.add_character(arg);self.screen='scene_actor';self.page=0
                elif op=='scene_remove':self.model.remove_character(arg);self.screen='scene_actors';self.page=0
                elif op=='scene_repair_animations':self.model.clear_incompatible_clips(arg)
                elif op=='scene_animation':self.model.choose_animation(self.actor_id,arg);self.screen='scene_actor';self.page=0;self.query=''
                elif op=='scene_animation_group':self.animation_group=arg;self.animation_query='';self.screen='scene_clips';self.page=0
                elif op=='scene_all_animations':self.animation_group=None;self.animation_query='';self.screen='scene_clips';self.page=0
                elif animation_search:
                    query='' if op=='clear' else value or ''
                    if type(query) is not str or len(query)>256:raise ValueError('Search is limited to 256 characters')
                    self.animation_query=query.casefold();self.query=self.animation_query;self.screen='scene_clips';self.page=0
                elif character_search:
                    query='' if op=='clear' else value or ''
                    if type(query) is not str or len(query)>256:raise ValueError('Search is limited to 256 characters')
                    self.query=query.casefold();self.page=0
                elif op=='scene_resize':self.model.edit('duration',max(2,min(120,self.model.document['duration']+arg)))
                elif op=='scene_loop':self.model.toggle_loop(arg)
                elif op=='scene_event':self.event_id=arg;self.screen='scene_event';self.page=0
                elif op in ('scene_edit','scene_save_as'):
                    field,current,kind=arg if op=='scene_edit' else ('save_as',self.model.document['name']+' copy','text')
                    self.edit_field=field;self.editing=(self.registry.select('e33.scene-editor'),dict(id=field,title=field,kind=kind,value=current,default=current,minimum=None,maximum=None,choices=()))
                elif op in ('apply','reset'):
                    option=self.editing[1];parsed=option['default'] if op=='reset' else value if option['kind']=='text' else json.loads(value)
                    if self.edit_field.startswith('authored_key:'):
                        curve=next(c for c in self.model.authored.channels(self.authored_section) if c['path']==self.authored_channel)
                        key=next(k for k in curve['keys'] if k['index']==self.authored_key)
                        field=self.edit_field.split(':')[1];updated=dict(at=key['at'],value=key['value']);updated[field]=parsed
                        self.model.authored.edit_key(self.authored_section,self.authored_channel,self.authored_key,**updated)
                        self.model.message='Curve key edited. Apply rebuilds private playback; Save keeps changes.'
                    elif self.edit_field.startswith('authored_npc:'):
                        self.model.authored.edit_npc(self.authored_npc,self.edit_field.split(':')[1],parsed)
                        self.model.message='NPC track changed. Save the authored timeline to keep it.'
                    elif self.edit_field.startswith('authored_cast:'):
                        edit=next(e for e in self.model.authored.document['cast_edits'] if (e['sequence'],e['guid'])==self.authored_cast)
                        placement=edit.get('placement',dict(offset=[300.,0.,0.],yaw=0.))
                        offset=list(placement['offset']);yaw=placement['yaw'];field=self.edit_field.split(':')[1]
                        if field=='yaw':yaw=parsed
                        else:offset['XYZ'.index(field)]=parsed
                        self.model.authored.place_cast(*self.authored_cast,offset,yaw)
                        self.model.message='Blueprint placement changed. Save the authored timeline to keep it.'
                    elif self.edit_field.startswith('authored:'):self.model.edit_authored_range(self.authored_section,self.edit_field.split(':')[1],parsed)
                    elif self.edit_field=='save_as':self.model.save(parsed,save_as=True)
                    else:self.model.edit(self.edit_field,parsed)
                    self.editing=None;self.edit_field=None
                elif op=='cancel':self.editing=None;self.edit_field=None
                elif op=='scene_save':self.model.save()
                elif op=='scene_load':self.model.load(arg);self.screen='scene';self.page=0
                elif op in ('scene_live','scene_photo'):
                    if op=='scene_photo':
                        try:self.model.runtime.check_host(True)
                        except ValueError as error:self.model.message=str(error);self.screen='scene_photo_help'
                        else:self.model.photo_author=True;self.model.want_author=True
                    else:self.model.photo_author=False;self.model.want_author=True
                elif op=='scene_play':self.model.play()
                elif op=='scene_stop':self.model.stop()
                elif op=='back':
                    authored_back={'scene_authored_node':'scene_authored_nodes','scene_authored_nodes':'scene_authored',
                        'scene_authored_npc':'scene_authored_npcs','scene_authored_npcs':'scene_authored_timeline',
                        'scene_authored_key':'scene_authored_channel','scene_authored_channel':'scene_authored_section',
                        'scene_authored_timeline':'scene_authored','scene_authored_section':'scene_authored_timeline','scene_authored_saved':'scene_authored'}
                    self.screen=authored_back.get(self.screen,'scene_add' if self.screen in ('scene_actor_asset','scene_catalog_asset','scene_catalog_categories') else 'scene_animation' if self.screen in ('scene_clips','scene_animation_groups') else 'scene_actor' if self.screen in ('scene_animation','scene_animation_inventory','scene_remove') else 'scene_actor' if self.screen=='scene_transform' else 'scene_actors' if self.screen in ('scene_actor','scene_add') else 'scene_events' if self.screen=='scene_event' else 'scene')
                    self.page=0;self.editing=None;self.edit_field=None
                    if self.screen!='scene_clips':self.query=''
                    if self.screen=='scene_animation':self.animation_query='';self.animation_group='character'
                self.status=self.model.message
            except Exception as error:self.status=f'{type(error).__name__}: {error}'
            return self.render()
        if self.screen.startswith('scene') and op in ('tab','filter'):self.query=''
        return super().activate(revision,token,value=value,reset=reset)


from expedition33.widgets import OwnedMenuPanel
from expedition33.management_native import NativeManagementMenu,display_detail
from expedition33.management_view import MenuFrame,MenuControl

class SavedSceneView:
    def __init__(self,registry,model):
        self.registry=registry;self.model=model;self.closed=False;self.revision=0;self.query='';self.page=0;self.selected=None;self.choices=[]
    def render(self):
        self.revision+=1
        rows=[r for r in self.model.store.list() if self.query.casefold() in (r['name']+' '+r['target_map']).casefold()]
        pages=max(1,(len(rows)+7)//8);self.page=min(self.page,pages-1);self.choices=rows[self.page*8:self.page*8+8]
        labels=[(('> ' if r['id']==self.selected else '')+r['name']+f"\n{r['duration']:g}s | {r['actors']} characters\n{r['animations']} animations | {r['audio']} audio") for r in self.choices]
        enabled=[True]*len(labels);labels+=['']*(8-len(labels));enabled+=[False]*(8-len(enabled))
        labels+=['Load scene','New scene','Load sample','Back','Previous','Next','Search','Clear']
        enabled+=[any(r['id']==self.selected for r in rows),True,True,True,self.page>0,self.page<pages-1,True,True]
        selected=next((r for r in rows if r['id']==self.selected),None)
        detail='Select a scene card to inspect it.\nLoad scene opens it without playback.\n\nNew scene starts with an empty cast.\nScene settings changes its name and length.'
        if selected:detail=selected['name']+f"\n\nLength: {selected['duration']:g} seconds\nCharacters: {selected['actors']} / 6\nAnimation clips: {selected['animations']}\nAudio clips: {selected['audio']}\nCamera keys: {selected['camera_keys']} / 16\n\nMap: "+SceneView._map_name(selected['target_map'])+'\n\nLoad scene opens without playback.'
        return MenuFrame(self.revision,'SAVED SCENES',detail,tuple(MenuControl(i,label,enabled[i]) for i,label in enumerate(labels)),self.page,pages,f'{len(rows)} scenes | Page {self.page+1}/{pages}',self.closed)
    def activate(self,revision,token,**kwargs):
        if revision!=self.revision or token not in range(16):raise ManagementError('Stale saved scene control')
        if token<8:self.selected=self.choices[token]['id']
        elif token==8:self.model.load(self.selected);self.model.want_open=True;self.closed=True
        elif token in (9,10):
            (self.model.new_scene if token==9 else self.model.load_sample)();self.model.want_open=True;self.closed=True
        elif token==11:self.model.want_open=True;self.closed=True
        elif token in (12,13):self.page=max(0,self.page+(-1 if token==12 else 1))
        elif token==14:
            value=kwargs.get('value')
            if value is None:value=self.model.saved_menu.panel.read_field()
            if type(value) is not str or len(value)>160 or any(ord(c)<32 for c in value):raise ValueError('Search accepts up to160 characters')
            self.query=value;self.page=0
        elif token==15:self.query='';self.page=0
        return self.render()
    def close(self):self.closed=True

class SavedScenePanel(OwnedMenuPanel):
    BATCH_CONSTRUCTION=True
    EXTRA_NAMES=('EditableText','GetText','SetRenderScale','SetRenderTransformPivot')
    def __init__(self,session,**kwargs):super().__init__(session,controls=16,**kwargs)
    def _build_contents(self):
        self.title=self._label(45,24,1600,55)
        self.detail=self._label(1320,230,560,550)
        self.status=self._label(45,1020,1500,40)
        for label in (self.detail,self.status):
            self._call(label,'Widget','SetRenderTransformPivot',Pivot={'X':0.,'Y':0.})
            self._call(label,'Widget','SetRenderScale',Scale={'X':.65,'Y':.65})
        self.field=self._spawn('EditableText');self._place(self.field,55,115,1000,45)
        self.field_value=None
        for i in range(16):
            if i<8:x,y,w,h=45+(i%2)*610,225+(i//2)*175,575,145
            elif i<12:x,y,w,h=1320,230+550+(i-8)*55,530,48
            else:x,y,w,h=((45+(i-12)*220,945,205,48) if i<14 else (1080+(i-14)*230,110,210,48))
            button=self._spawn('Button');self._place(button,x,y,w,h);self.buttons.append(button)
            self._call(button,'Button','SetBackgroundColor',InBackgroundColor={'R':.08,'G':.12,'B':.17,'A':1.})
            label=self._label(x+15,y+8,w-30,h-12);self.labels.append(label)
            self._call(label,'Widget','SetRenderTransformPivot',Pivot={'X':0.,'Y':0.})
            self._call(label,'Widget','SetRenderScale',Scale={'X':.70 if i<8 else .65,'Y':.70 if i<8 else .65})
            self._visible[i]=self._enabled[i]=True
        self.labels.extend((self.title,self.detail,self.status))
    def read_field(self):
        with self._planner.prepare(self.field,self._function('EditableText','GetText')).invoke() as result:return str(result.return_value)

class SavedSceneMenu(NativeManagementMenu):
    def __init__(self,session,registry,model):
        super().__init__(session,registry,cached_planning=True,cached_construction=True,selected_results=True,reusable=True,view_factory=lambda registry:SavedSceneView(registry,model),panel_factory=SavedScenePanel)
    def _paint_frame(self):
        self.panel.set_text(self.panel.title,'SCENE EDITOR | SAVED SCENES')
        self.panel.set_text(self.panel.detail,display_detail(self.frame.description,width=30,height=18))
        self.panel.set_text(self.panel.status,self.error or self.frame.status)
        for control in self.frame.controls:
            self.panel.set_text(self.panel.labels[control.token],control.label);self.panel.set_visible(control.token,bool(control.label));self.panel.set_enabled(control.token,control.enabled)
        if self.panel.field_value!=self.view.query:
            queue,self.panel._paint_queue=self.panel._paint_queue,None
            try:self.panel._render_call(self.panel.field,'EditableText','SetText',InText=self.view.query)
            finally:self.panel._paint_queue=queue
            self.panel.field_value=self.view.query
