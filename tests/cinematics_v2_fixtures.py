from types import SimpleNamespace as N
from unittest.mock import Mock
from expedition33.cinematics.controller import StartResult,StopResult,ReplayObservation,BackendState

class Backend:
 def __init__(self):
  self.start=Mock(return_value=StartResult.STARTED)
  self.poll=Mock(return_value=ReplayObservation(BackendState.ACTIVE,'Playing'))
  self.status=Mock(return_value=ReplayObservation(BackendState.ACTIVE,'Playing'))
  self.stop=Mock(return_value=StopResult.STOPPED)
  self.close=Mock(return_value=True)

def ready_model(module,row):
 model=module.Mod();model.library=(dict(row),);model.show_all=False;model.filter='unlocked'
 model.discovery={'state':'history_verified','all':[dict(row)],'confirmed':[dict(row)]}
 model._context={'world':(7,1,1001,0x10000),'controller':(7,2,1002,0x20000),'world_path':'/Game/Fixture.Fixture'}
 model._last_epoch=module._epoch(model._context);model._slot=1
 model.session=N(pid=7,_check=Mock(),_session=N(_transport=N(_executable='candidate')))
 model._current_epoch=Mock(side_effect=lambda:model._last_epoch)
 model._refresh_now=Mock(side_effect=lambda:model.discovery)
 model.native=N(menu=N(panel=N(state='open'),view=object(),_presentation_suspended=False),
                parent=N(refresh=Mock(),close_menu=Mock()),poll=Mock(),close=Mock())
 return model

def poll(model):
 model._next_playback_poll=0.;model.poll()
