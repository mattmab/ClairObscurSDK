"""Acknowledged native epoch retirement followed by lease-only Python cleanup."""
from .._retired_tracking import close_lease_only_scope


def _protocol(transport, name):
    value=getattr(transport,name,0)
    return type(value) is int and value==1


def title_retirement_available(transport):
    return all(_protocol(transport,name) for name in
               ('sequence_retirement_protocol','music_audio_retirement_protocol','retired_world_cleanup_protocol'))


def media_retirement_available(transport):
    return all(_protocol(transport,name) for name in
               ('media_retirement_protocol','music_audio_retirement_protocol','retired_world_cleanup_protocol'))


def retire_owner_tracking(scope, owners):
    """Discard registered Python owners only after their native closed ACK.

    A new owner has never attempted registration; every armed owner must first
    receive its exact native retirement acknowledgement. Never query old owners.
    """
    owners=tuple(owner for owner in owners if owner is not None)
    for owner in owners:
        if owner.state=='new':
            continue
        if owner.state!='closed':return False
    for name in ('_audio_owners','_reference_owners'):
        current=getattr(scope,name)
        foreign=[owner for owner in current if all(owner is not expected for expected in owners)]
        if foreign:raise RuntimeError('Retired cinematic scope contains an unrelated native owner')
    for name in ('_audio_owners','_reference_owners'):
        getattr(scope,name).clear()
    return close_lease_only_scope(scope)


def retire_presentation(presentation):
    """Forget compensation plans only after the old panel retired positively."""
    if presentation is None:return
    if presentation.panel.state!='closed':
        raise RuntimeError('Retire the old cinematic panel before its presentation tracking')
    if presentation.planner is not None:presentation.planner.close()
    menu=presentation.menu
    if menu.panel is presentation.panel and getattr(menu,'_presentation_owner',None) is presentation:
        menu._presentation_owner=None
        menu._presentation_suspended=False
    presentation.state='retired'
