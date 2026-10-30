"""Pure cinematic-library presenter over copied model snapshots.

Rendering never discovers assets, reads native state, starts playback or polls
cleanup. The shared native renderer owns widgets. Six bounded rows remain the
fallback until that renderer supplies a dedicated cinematic scroll layout.
"""
from collections.abc import Mapping
from dataclasses import fields, is_dataclass

from ..management import ManagementError
from ..management_view import MenuControl, MenuEditor, MenuFrame

FILTERS = ('playable', 'unlocked', 'all', 'clips', 'full')
FILTER_LABELS = {'playable':'Playable', 'unlocked':'Unlocked', 'clips':'Movie clips',
                 'full':'Full scenes in this map', 'all':'All cinematics'}
ACTION_LABELS = {1:'Play', 14:'Play full scene here', 2:'Pause / Resume', 3:'Restart', 4:'Stop', 5:'Playback speed',
                 11:'Preview at current location', 13:'Play original story action — save effects'}
ACTION_NAMES = {'play':1, 'pause':2, 'resume':2, 'restart':3, 'stop':4,
                'rate':5, 'speed':5, 'preview':11,'full':14}


def _row(value):
    if isinstance(value, Mapping):
        result = dict(value)
    elif is_dataclass(value) and not isinstance(value, type):
        result = {item.name:getattr(value, item.name) for item in fields(value)}
    else:
        raise ManagementError('Cinematic library contains an unsupported record')
    if type(result.get('id')) is not str or not result['id'] or len(result['id']) > 2048:
        raise ManagementError('Cinematic library requires stable scene identities')
    result.setdefault('title', result['id'])
    result.setdefault('reason', '')
    if type(result['title']) is not str or type(result['reason']) is not str:
        raise ManagementError('Cinematic library contains invalid display text')
    return result


def _tokens(value, default):
    if value is None:
        return tuple(default)
    if type(value) not in (tuple, list):
        return ()
    result = []
    for item in value:
        token = ACTION_NAMES.get(item) if type(item) is str else item
        if type(token) is int and token in ACTION_LABELS and token not in result:
            result.append(token)
    return tuple(result)


def _capabilities(scene):
    kind = scene.get('replay_kind')
    unlocked = scene.get('unlocked') is True
    supported = scene.get('supported') is True
    actions = []
    if kind == 'portable' and supported and unlocked:
        actions.extend((14,4))
    elif kind == 'movie_clip' and supported:
        actions.extend((1, 4))
    elif kind in ('title', 'movie', 'media') and supported and unlocked:
        actions.extend(token for token in _tokens(scene.get('controls'), (1,4)) if token in (1,4))
    elif kind == 'preview' and supported and unlocked:
        actions.extend(token for token in _tokens(scene.get('preview_controls', scene.get('controls')),
                                                 (11,2,3,4,5)) if token in (11,2,3,4,5))
    elif kind == 'original_action' and supported:
        # The model alone admits explicit original-story effects. Never inherit
        # a permission from a prior conversation or offer an unsupported Stop.
        actions.append(1)
    if scene.get('preview_supported') is True and unlocked and 11 not in actions:
        actions.insert(0,11)
    if kind == 'preview' and scene.get('original_supported') is True and 1 not in actions:
        actions.append(1)
    if kind in ('title', 'movie', 'media') and scene.get('original_supported') is True:
        actions.append(13)
    if kind=='portable' and scene.get('original_supported') is True:actions.append(13)
    return tuple(actions)


def availability_label(scene):
    if not _capabilities(scene):
        return 'Unavailable'
    if scene.get('validation') in ('live_partial','partial'):
        return 'Available - partial'
    if scene.get('validation') in ('live_mechanism_verified','live_verified','live_accepted'):
        return 'Available - tested'
    return 'Available - unverified'


def _title(scene):
    title = scene['title']
    for suffix in (' [unlocked]', ' [locked]', ' [unlock unknown]'):
        title = title.removesuffix(suffix)
    return title


def menu_scene_label(scene):
    return f'[{availability_label(scene)}] {_title(scene)}'


def _fingerprint(scene):
    return (scene['id'], scene['title'], scene.get('unlocked'), scene.get('supported'),
            scene.get('replay_kind'), scene.get('preview_supported'), scene.get('original_supported'),
            scene.get('portable_supported'),
            scene.get('definition_sha256',scene.get('sha256')), scene.get('revision'),
            scene.get('sequence'),scene.get('world_path'),scene.get('exact_map'),
            scene.get('original_destination'),scene.get('action_path'),
            scene.get('original_destination'),scene.get('original_action_path'),
            scene.get('title_profile'),scene.get('media_profile'),
            _capabilities(scene))


class BrowserView:
    PAGE_SIZE = 6

    def __init__(self, registry, model):
        self.registry, self.model = registry, model
        self.closed, self.revision = False, 0
        self.status, self.query = '', ''
        self.page, self.selected = 0, None
        self.filter = getattr(model, 'filter', None)
        if self.filter not in FILTERS:
            self.filter = 'all' if getattr(model, 'show_all', False) else 'unlocked'
        self._commands = {}

    def _check(self):
        self.registry._check()
        if self.closed:
            raise ManagementError('Cinematics browser is closed')

    def _library(self):
        library = getattr(self.model, 'library', None)
        if library is None:
            discovery = getattr(self.model, 'discovery', {})
            library = discovery.get('all') or discovery.get('confirmed', ())
        elif not isinstance(library, (Mapping, tuple, list)):
            library = getattr(library, 'records', None)
            if library is None:
                raise ManagementError('Cinematic library snapshot is unavailable')
        if isinstance(library, Mapping):
            library = library.values()
        rows = tuple(_row(row) for row in library)
        if len(rows) > 4096 or len({row['id'] for row in rows}) != len(rows):
            raise ManagementError('Cinematic library identities are duplicated or exceed the bound')
        return rows

    def scenes(self):
        rows = self._library()
        query = self.query.casefold()
        # Older facade snapshots already separated confirmed display rows. A
        # missing flag may keep such a row visible in that legacy list, but it
        # never grants playback or substitutes for an explicit boolean unlock.
        confirmed = set()
        if getattr(self.model,'library',None) is None:
            confirmed = {row.get('id') for row in getattr(self.model,'discovery',{}).get('confirmed',())
                         if isinstance(row,Mapping)}
        return tuple(row for row in rows
            if (self.filter == 'all' or
                self.filter == 'clips' and row.get('replay_kind') == 'movie_clip' or
                self.filter == 'full' and (row.get('original_supported') is True or row.get('portable_supported') is True) or
                self.filter == 'unlocked' and (row.get('unlocked') is True or
                    'unlocked' not in row and row['id'] in confirmed) or
                self.filter == 'playable' and bool(_capabilities(row)))
            and query in (' '.join((row['title'], row['id'], str(row.get('saved_id') or '')))).casefold())

    def search(self, query):
        self._check()
        if type(query) is not str or len(query) > 256 or any(character in query for character in '\0\r\n'):
            raise ManagementError('Search must be one line of at most256 characters')
        self.query, self.page, self.selected = query, 0, None
        return self.render()

    def _add(self, controls, token, label, operation, argument=None, enabled=True, editor=None):
        controls.append(MenuControl(token,label,enabled,editor))
        self._commands[token] = operation, argument, enabled

    def render(self):
        self._check()
        self.revision += 1
        self._commands.clear()
        controls = []
        library = self._library()
        by_id = {scene['id']:scene for scene in library}
        if self.selected is not None and self.selected not in by_id:
            self.selected, self.page = None, 0
            self.status = 'The selected cinematic is no longer in the library.'
        scenes = self.scenes()
        pages = max(1,(len(scenes)+self.PAGE_SIZE-1)//self.PAGE_SIZE)
        self.page = min(max(0,self.page),pages-1)
        if self.selected is None:
            self._add(controls,0,'Refresh current-save history','refresh')
            self._add(controls,10,'Show: '+FILTER_LABELS[self.filter],'filter',
                      editor=MenuEditor('choice',self.filter,choices=FILTERS))
            for index in range(self.page*self.PAGE_SIZE,min(len(scenes),(self.page+1)*self.PAGE_SIZE)):
                scene = scenes[index]
                self._add(controls,100+index,menu_scene_label(scene),'select',
                          (scene['id'],_fingerprint(scene)))
            self._add(controls,7,'Previous','page',-1,enabled=self.page>0)
            self._add(controls,8,'Next','page',1,enabled=self.page+1<pages)
            if getattr(self.model,'frontend_supports_search',False) is True:
                self._add(controls,12,'Search cinematics','search',editor=MenuEditor('text',self.query))
            description = (f'{len(scenes)} cinematics shown. Unlock history and playback support are separate.\n'
                           'Choose a cinematic to inspect its supported playback routes.')
            if self.query:
                description += '\nSearch: '+self.query
            if not scenes:
                description += '\nNo cinematics match this filter.'
            reason = getattr(self.model,'reason','')
            if type(reason) is str and reason:
                description += '\n\n'+reason
        else:
            scene = by_id[self.selected]
            unlock = ('Standalone clip — save unlock not required' if scene.get('replay_kind') == 'movie_clip' else
                      'Unlocked' if scene.get('unlocked') is True else 'Locked' if scene.get('unlocked') is False else 'Unlock unknown')
            description = f'{availability_label(scene)}\n{_title(scene)}\n{unlock}\n\n{scene["reason"]}'
            actions = _capabilities(scene)
            if self.filter == 'full' and scene.get('original_supported') is True and scene.get('portable_supported') is not True:
                actions = (13,) if 13 in actions else (1,)
                description = (f'Original in-engine story scene\n{_title(scene)}\n\n'
                    'Uses the authored actors, lighting and audio in the original map: '
                    + str(scene.get('original_destination', 'current map')) +
                    '\nOriginal story/save effects apply. The game controls completion; SDK Stop is unavailable.')
            for token in actions:
                label = ACTION_LABELS[token]
                if token == 1 and scene.get('replay_kind') in ('original_action','preview'):
                    label = 'Play original story action — save effects'
                self._add(controls,token,label,'control',(scene['id'],_fingerprint(scene)))
            if not actions:
                self._add(controls,1,'Playback unavailable','control',
                          (scene['id'],_fingerprint(scene)),enabled=False)
            self._add(controls,9,'Back to cinematics','back')
        self._add(controls,6,'Close','close')
        playback = getattr(self.model,'playback_status','')
        status = self.status or (playback if type(playback) is str else '')
        return MenuFrame(self.revision,'Cinematics',description,tuple(controls),self.page,pages,status,False)

    def _matching_scene(self, argument):
        scene_id, fingerprint = argument
        scene = next((row for row in self._library() if row['id']==scene_id),None)
        if scene is None or _fingerprint(scene) != fingerprint:
            raise ManagementError('Cinematic selection changed; refresh before using this control')
        return scene

    def activate(self, revision, token, *, value=None, **_):
        self._check()
        if type(revision) is not int or revision != self.revision or type(token) is not int:
            raise ManagementError('Stale cinematic control')
        command = self._commands.get(token)
        if command is None:
            selected = next((row for row in self._library() if row['id']==self.selected),None)
            if token in (2,3,5) and selected is not None and selected.get('replay_kind') in ('title','movie','media'):
                raise ManagementError('Reviewed replay supports only Play and Stop')
            raise ManagementError('Cinematic control is not available on this screen')
        operation, argument, enabled = command
        if not enabled:
            raise ManagementError('This cinematic control is unavailable')
        if operation == 'select':
            self.selected = self._matching_scene(argument)['id']
        elif operation == 'control':
            scene = self._matching_scene(argument)
            if token not in _capabilities(scene):
                raise ManagementError('Cinematic playback capability changed')
            self.model.control(scene['id'],token)
            if self.closed:
                return MenuFrame(self.revision,'Cinematics','',(),0,1,'Playback requested',True)
            self.status = getattr(self.model,'playback_status','')
        elif operation == 'filter':
            selected = value if value is not None else FILTERS[(FILTERS.index(self.filter)+1)%len(FILTERS)]
            if selected not in FILTERS:
                raise ManagementError('Unknown cinematic filter')
            self.filter, self.page, self.selected = selected, 0, None
            self.model.show_all = selected == 'all'
            self.model.filter = selected
        elif operation == 'page':
            pages = max(1,(len(self.scenes())+self.PAGE_SIZE-1)//self.PAGE_SIZE)
            if not 0 <= self.page+argument < pages:
                raise ManagementError('Cinematic page is unavailable')
            self.page += argument
        elif operation == 'search':
            return self.search(value)
        elif operation == 'refresh':
            self.model.discover()
            self.status = 'Refreshing current-save history'
        elif operation == 'back':
            stop = getattr(self.model,'stop',None)
            if callable(stop) and stop() is False:
                self.status = 'Finishing cinematic cleanup'
                return self.render()
            self.selected = None
        elif operation == 'close':
            self.close()
            return MenuFrame(self.revision,'Cinematics','',(),0,1,'',True)
        return self.render()

    def close(self):
        if self.closed:
            return
        self.registry._check()
        stop = getattr(self.model,'stop',None)
        if callable(stop) and stop() is False:
            self.status = 'Finishing cinematic cleanup'
            raise ManagementError('Cinematic cleanup is still finishing; keep this browser open')
        self.closed = True
        self.selected = None
        self.revision += 1
        self._commands.clear()

# Production integration preserves the pure presenter's logical token space.
from dataclasses import replace
from ..mods_workspace_scroll import ScrollWorkspaceView


class WorkspaceBrowserView(BrowserView, ScrollWorkspaceView):
    """Bounded cinematic pages laid out by the real workspace renderer.

    Logical scene IDs/tokens never become widget indices. Each frame maps at
    most eight body controls onto the first cell of each physical row.
    """
    def __init__(self, registry, model):
        ScrollWorkspaceView.__init__(self,registry)
        BrowserView.__init__(self,registry,model)
        self.screen='cinematics'
        self._base_revision=0
        self.PAGE_SIZE=5 if getattr(model,'frontend_supports_search',False) is True else 6

    def bindable_tokens(self):
        return set(self._commands)

    def _normalize(self, frame):
        self._revision=self._base_revision=self.revision
        if len(frame.controls)==105:return frame
        controls=[MenuControl(-1,'',False) for _ in range(105)]
        body=[control for control in frame.controls if control.token not in (6,7,8,9)]
        if len(body)>8:raise ManagementError('Cinematic body exceeds the workspace row capacity')
        self.total_rows=len(body)
        for index,control in enumerate(body):controls[index*6]=control
        navigation={9:48,7:49,8:50,6:51}
        for control in frame.controls:
            if control.token in navigation:controls[navigation[control.token]]=control
        return replace(frame,controls=tuple(controls))

    def render(self):
        return self._normalize(BrowserView.render(self))

    def activate(self, revision, token, **submission):
        # BrowserView dispatch renders through self.render(); normalize only
        # its short terminal frame, never remap an already normalized frame.
        return self._normalize(BrowserView.activate(self,revision,token,**submission))

    def suspend_frame(self, frame):
        self._check()
        if not isinstance(frame,MenuFrame) or frame.closed or frame.revision!=self.revision:
            raise ManagementError('Native cinematic frame is stale')
        self.revision+=1
        self._revision=self._base_revision=self.revision
        return replace(frame,revision=self.revision)
