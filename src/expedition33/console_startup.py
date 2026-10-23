"""Read-only console prerequisites, independent of save and title widgets."""
import threading
from . import RuntimeQueryError
from ._reader import ReadBatch
from .catalog import capture_matching, capture_selected
from .values import read_values_many
from .cinematics.history import field


def _identity(obj):return obj.index,obj.serial,obj.address


def _targets(catalog):
    def exact(name, cls, path):
        rows=[obj for obj in catalog.objects if obj.name==name and obj.class_name==cls
              and not obj.object_flags & 0x40000000 and catalog.path_name(obj)==path]
        return rows[0] if len(rows)==1 else None
    console=exact('Console','Class','/Script/Engine.Console')
    library_class=exact('GameplayStatics','Class','/Script/Engine.GameplayStatics')
    library=exact('Default__GameplayStatics','GameplayStatics','/Script/Engine.Default__GameplayStatics')
    function=exact('SpawnObject','Function','/Script/Engine.GameplayStatics:SpawnObject')
    viewports=[obj for obj in catalog.objects if obj.class_name=='CustomGameViewportClient'
               and not obj.object_flags & 0x40000030]
    if not all((console,library_class,library,function)) or len(viewports)!=1:return None
    if not library.object_flags & 0x10 or library.class_index!=library_class.index:return None
    if function.outer_index!=library_class.index or function.outer_serial!=library_class.serial:return None
    return console,library_class,library,function,viewports[0]


def _empty_console(catalog, viewport):
    values=read_values_many(catalog,(viewport,),fields=('ViewportConsole',))[viewport.index]
    return field(values,'ViewportConsole','ObjectProperty') is None


class ConsolePrerequisiteObserver:
    """Worker owns its reader. True only schedules ONE native attach attempt.

    Native console-attach remains the authority for current unique viewport,
    game thread, GC, getter proof and SpawnObject's exact native schema. No
    world, GameInstance, player, controller or UMG dependency is observed here.
    """
    def __init__(self,pid):
        self.pid=pid;self._owner=threading.get_ident();self._reader=None

    def _check(self):
        if threading.get_ident()!=self._owner:raise RuntimeError('Console readiness reader owner thread')

    def observe(self):
        self._check()
        if self._reader is None:self._reader=ReadBatch(self.pid)
        try:
            with self._reader.bind():
                catalog=capture_matching(self.pid,names=('Console','GameplayStatics',
                    'Default__GameplayStatics','SpawnObject'),classes=('CustomGameViewportClient',))
                targets=_targets(catalog)
                if targets is None or not _empty_console(catalog,targets[-1]):return False
                identities=tuple(map(_identity,targets))
                fresh=capture_selected(self.pid,identities)
                after=_targets(fresh)
                if after is None or tuple(map(_identity,after))!=identities:return None
                return _empty_console(fresh,after[-1])
        except RuntimeQueryError as error:
            self.close()
            if any(reason in str(error) for reason in ('MATCH_RESULTS_EMPTY',
                    'SELECTED_DEPENDENCY_CHANGED','SELECTED_DEPENDENCY_NOT_REGISTERED',
                    'Object identity changed or belongs to another process','READ_FAILED')):
                return None
            raise
        except BaseException:
            self.close();raise

    def close(self):
        self._check()
        reader,self._reader=self._reader,None
        if reader is not None:reader.close()


class ConsoleReadiness:
    """One independent read worker; owner polls a copied, expiring boolean."""
    def __init__(self,pid):
        from .admission_monitor import ReadOnlyAdmissionMonitor
        self._monitor=ReadOnlyAdmissionMonitor(lambda:ConsolePrerequisiteObserver(pid),interval=.25)

    def ready(self):
        observation=self._monitor.snapshot()
        return observation.admission if observation is not None else None

    def close(self):
        return self._monitor.close(timeout=0)
