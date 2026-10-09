"""Explicit game-thread object-reference mutation for the experimental v10 host."""
from dataclasses import dataclass

from . import ObjectSnapshot, RuntimeQueryError
from . import _assignment_wire as wire
from .catalog import capture
from .reflection import describe
from .invocation import InvocationError


@dataclass(frozen=True)
class AssignmentResult:
    target: ObjectSnapshot
    owner: ObjectSnapshot
    name: str
    element: int
    before: object
    after: object
    outcome: str = 'dispatch_returned'


def assign(session, obj, owner, name, value, *, expected, element, allow_mutation):
    if allow_mutation is not True:
        raise ValueError('Object assignment requires literal allow_mutation=True')
    if not session.supports_object_assignment:
        raise ValueError('This session has no object assignment backend')
    if type(name) is not str or not name or type(element) is not int or element < 0:
        raise ValueError('Invalid property selector')
    for position, reference in enumerate((obj, owner, expected, value)):
        if reference is None and position >= 2:
            continue
        if not isinstance(reference, ObjectSnapshot) or reference.pid != session.pid:
            raise ValueError('Assignment references must belong to this session')
    catalog = capture()
    obj, owner = catalog.resolve(obj), catalog.resolve(owner)
    expected = catalog.resolve(expected) if expected is not None else None
    value = catalog.resolve(value) if value is not None else None
    if owner.index not in catalog.ancestors(obj.class_index):
        raise ValueError('Property owner is not in target ancestry')
    metadata = describe(catalog, [owner])[owner.index]
    matches = [p for p in metadata.properties if p['owner_index'] == owner.index and p['name'] == name]
    if len(matches) != 1:
        raise ValueError('Expected one property declared by this owner')
    prop = matches[0]
    if (prop['type'] != 'ObjectProperty' or prop['element_size'] != 8 or
            int(prop['vtable_rva'], 16) != 0x6e11d38 or
            not 1 <= prop['dimension'] <= 64 or element >= prop['dimension']):
        raise ValueError('Unsupported object property layout or element')
    if value is None and prop['flags'] & 0x1000:
        raise ValueError('Target property refuses null values')
    constraint = catalog.by_index[prop['property_class_index']]
    if value is not None and constraint.index not in catalog.ancestors(value.class_index):
        raise ValueError('Replacement object does not satisfy property class')
    # Encode once before acquiring any resources; only tokens change afterward.
    wire.request(obj, owner, constraint, expected, value, prop, element, (0, 0, 0))
    leases = []
    failure = None
    try:
        tokens = []
        for reference in (obj, expected, value):
            if reference is None:
                tokens.append(0)
            else:
                lease = session.retain(reference)
                leases.append(lease)
                tokens.append(lease._token)
        sent = wire.request(obj, owner, constraint, expected, value, prop, element, tokens)
        try:
            response = session._transport.command('object-assign', sent)
            error, outcome = wire.decode(sent, response['assignment_packet'])
        except (RuntimeQueryError, ValueError, KeyError) as error:
            session._abort_ownership()
            raise InvocationError(f'Assignment acknowledgement unavailable: {error}', outcome='unknown') from error
        if outcome == 'unknown':
            session._abort_ownership()
        if error:
            raise InvocationError('Native object assignment rejected or incomplete', outcome=outcome, native_error=error)
        return AssignmentResult(obj, owner, name, element, expected, value)
    except BaseException as error:
        failure = error
        raise
    finally:
        cleanup_errors = []
        for lease in reversed(leases):
            if lease.active:
                try:
                    lease.release()
                except BaseException as error:
                    cleanup_errors.append(error)
        if cleanup_errors:
            if failure is not None:
                failure.add_note(f'Assignment temporary lease cleanup failed: {cleanup_errors!r}')
            else:
                raise InvocationError('Assignment returned; temporary lease cleanup failed',
                                      outcome='dispatch_returned') from cleanup_errors[0]
