"""World retirement without restoring borrowed old-world game state."""
import struct


def revoke(mod, context):
    mod._retirement_token=context.previous_token
    mod._retirement_result=None;mod._native_retirement=None
    mod.held.clear();mod.dragging=False;mod.pending_catalog_asset=None
    for worker in (mod.templates,mod.ai.scanner):
        worker.job=None;worker.queue=[];worker.moves=[];worker.line_queue=[]
        if hasattr(worker,'line_moves'):worker.line_moves=[]
        if worker.scan_future is not None:worker.scan_future.cancel()
    mod.ai.queue=[]
    if mod.ai.picker is not None:mod.ai.picker.cancel()
    menu=mod.catalog_menu
    if menu is not None:
        menu.capture_queue=[];menu.batch_gallery.queue=[];menu.batch_gallery.paused=True
        menu.background.enabled=False
        futures=[job.get('future') for job in menu.processing]
        if menu.preview_job is not None:futures.append(menu.preview_job.get('future'))
        for future in futures:
            if future is not None:future.cancel()


def drain_workers(mod):
    futures=[]
    for scanner in (mod.templates,mod.ai.scanner):
        if scanner.scan_future is not None:futures.append(scanner.scan_future)
    if mod.ai.picker is not None:futures.append(mod.ai.picker)
    menu=mod.catalog_menu
    if menu is not None:
        futures.extend(job['future'] for job in menu.processing if job.get('future') is not None)
        if menu.preview_job is not None and menu.preview_job.get('future') is not None:
            futures.append(menu.preview_job['future'])
    if any(not future.done() for future in futures):return False
    for scanner in (mod.templates,mod.ai.scanner):
        scanner.scan_worker.shutdown(wait=False,cancel_futures=True)
        if scanner.planner is not None:scanner.planner.close();scanner.planner=None
        scanner.scan_future=None;scanner.draft=[];scanner.lines=[]
    if mod.ai.worker is not None:mod.ai.worker.shutdown(wait=False,cancel_futures=True)
    mod.ai.picker=None;mod.ai.worker=None
    if menu is not None:
        menu.preview_worker.shutdown(wait=False,cancel_futures=True)
        menu.preview_job=None;menu.processing=[];menu.map_job=None
    return True


def native_retire(mod):
    if mod._native_retirement in ('ack','unknown'):return mod._native_retirement
    if not mod.started:
        mod._native_retirement='ack';return 'ack'
    transport=mod.session._session._transport
    capability=getattr(transport,'builder_world_retirement_protocol',0)
    if type(capability) is not int or capability!=1:
        mod._native_retirement='unknown';return 'unknown'
    packet=bytearray(20984);struct.pack_into('<4IQ',packet,0,3,68,0,0,mod.owner)
    try:
        with mod.session._lease_context():reply=transport.command('mesh',bytes(packet))
        raw=bytes.fromhex(reply['mesh_packet'])
        if len(raw)!=len(packet):raise ValueError('Builder retirement response size')
        error,state=struct.unpack_from('<II',raw,8)
        copied=bytearray(raw);copied[8:16]=bytes(8);copied[80:84]=bytes(4)
        if copied!=packet:raise ValueError('Builder retirement response changed request fields')
        if error==407 and state in (0,1):outcome='pending'
        elif error==0 and state==0:outcome='ack'
        else:outcome='unknown'
    except Exception:outcome='unknown'
    mod._native_retirement=outcome
    return outcome


def poll(mod,context):
    if getattr(mod,'_retirement_token',None)!=context.previous_token:return 'unknown'
    if mod._retirement_result in ('ack','unknown'):return mod._retirement_result
    if not drain_workers(mod):return 'pending'
    outcome=native_retire(mod)
    if outcome!='ack':return outcome
    prepared=getattr(mod,'_loading_ui',None)
    if (prepared is not None and prepared.catalog is mod.catalog_menu and prepared.hud is mod.hud
            and prepared.context is not None):
        outcome=prepared.retire_world()
        if outcome!='ack':return outcome
    else:
        for panel in (mod.catalog_menu,mod.hud):
            if panel is None:continue
            outcome=panel.retire_world(native_retirement_ack=True)
            if outcome!='ack':return outcome
    if mod._menu_reader is not None:mod._menu_reader.close();mod._menu_reader=None
    mod.library._catalog=None;mod.library.owned.clear();mod.library.preview_key=None
    mod.library.selected=None;mod.library.world=None
    mod.active=mod.started=mod.booth_pending=False
    mod.catalog_menu=mod.hud=None;mod.session=None
    mod._retirement_result='ack'
    return 'ack'
