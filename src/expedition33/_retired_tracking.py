"""Close a proved-retired lease-only scope without broad teardown/compensation."""
import threading
from ._scope import SessionScope
from . import TargetExitedError


def _raise_if_target_exited(scope):
    """A dead target is terminal, never an engine release acknowledgement."""
    transport=getattr(scope._session,'_transport',None)
    code=getattr(transport,'target_exit_code',None)
    if code is not None:
        if type(code) is not int or not 0<=code<=0xffffffff:
            raise RuntimeError('Invalid target exit evidence')
        raise TargetExitedError(code)


def close_lease_only_scope(scope, *, closed_sequence_owners=()):
    if not isinstance(scope, SessionScope):
        raise TypeError('A real SDK resource scope is required')
    if scope._closed:
        return True
    # Preserve thread affinity even when a closed transport already records
    # confirmed process exit. In that case report the terminal cause before
    # Session._check() can mask it with a generic closed-session error.
    if threading.get_ident()!=scope._owner:scope._check()
    _raise_if_target_exited(scope)
    scope._check()
    for name in ('_hooks', '_traces', '_reference_owners', '_audio_owners',
                 '_enemy_spawn_owners', '_native_owners', '_mesh_models'):
        if getattr(scope, name, ()):
            raise RuntimeError('Retired tracking still has an unresolved native domain: ' + name)
    if scope.actions is not None:
        raise RuntimeError('Retired tracking still has scoped actions')
    if any(owner not in closed_sequence_owners or owner.state != 'closed'
           for owner in scope._sequence_owners):
        raise RuntimeError('Retired sequence ownership is not acknowledged closed')
    if any(menu._state != 'closed' for menu in scope._menus):
        raise RuntimeError('Retired menu ownership is not acknowledged closed')
    for child in tuple(scope._children):
        if not close_lease_only_scope(child):
            return False
    # Only collector release is permitted. A known deferral leaves this scope
    # and every unresolved lease reachable; no SessionScope.close abort path.
    from ._lease_release_batch import available
    if available(getattr(scope._session,'_transport',None)):
        # Every domain above has acknowledged retirement. Release the remaining
        # collector leases in bounded native batches, retaining deferred rows.
        scope._session._release_leases(tuple(reversed(scope._leases)))
        _raise_if_target_exited(scope)
        scope._leases[:]=[lease for lease in scope._leases if lease._state!='released']
        if scope._leases:return False
    else:
        for lease in reversed(tuple(scope._leases)):
            released=lease.release()
            _raise_if_target_exited(scope)
            if released is True:
                scope._leases.remove(lease)
            else:
                return False
    scope.console._close()
    scope._sequence_owners.clear()
    scope._menus.clear()
    scope._closed = True
    if scope._parent is not None:
        parent = scope._parent()
        if parent is not None and scope in parent._children:
            parent._children.remove(scope)
        scope._parent = None
    scope._session = None
    return True
