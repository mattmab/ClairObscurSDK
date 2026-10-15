"""Bounded no-output menu updates over the existing validated dispatchers."""
import re
import struct

HEADER = struct.Struct('<5I')
ITEM = struct.Struct('<2I')
CAPACITY, LIMIT = 65536, 48
TYPES = {'retained-invoke': (104, 26192, 'retained_packet'),
         'text-invoke': (106, 91800, 'text_packet'),
         'multi-button': (109, 2648, 'multi_button_packet')}
ZERO_RUN = re.compile(b'\x00{16,}')
LAYOUT_SETTERS = frozenset(('SetPosition', 'SetSize', 'SetAnchors', 'SetHorizontalAlignment',
    'SetVerticalAlignment', 'SetJustification', 'SetStyle', 'SetBrushColor',
    'SetBackgroundColor', 'SetOwningPlayer'))
EXTENDED_LAYOUT_SETTERS = frozenset(('SetMinDimensions', 'SetIsSelectable', 'SetIsToggleable',
    'SetRenderScale', 'SetRenderTransformPivot', 'SetPadding', 'SetLayer'))

def extended_layout_available(session):
    return available(session) and getattr(session._transport, 'layout_batch_protocol', 0) in (2, 3)

def layout_available(session):
    version = getattr(session._transport, 'layout_batch_protocol', 0)
    return available(session) and type(version) is int and version in (1, 2, 3)

def pack_sparse(data):
    chunks, start = [], 0
    for match in ZERO_RUN.finditer(data):
        if match.start() > start:
            chunks.extend((ITEM.pack(start, match.start() - start), data[start:match.start()]))
        start = match.end()
    if start < len(data):
        chunks.extend((ITEM.pack(start, len(data) - start), data[start:]))
    return b''.join(chunks)

def unpack_sparse(data, extent):
    result, at, end = bytearray(extent), 0, 0
    while at < len(data):
        if len(data) - at < ITEM.size:
            raise ValueError('Truncated UI sparse block')
        offset, count = ITEM.unpack_from(data, at); at += ITEM.size
        if not count or offset < end or offset > extent or count > extent - offset or count > len(data) - at:
            raise ValueError('Invalid UI sparse block')
        result[offset:offset+count] = data[at:at+count]
        at += count; end = offset + count
    return bytes(result)

def encode(requests):
    if not 1 <= len(requests) <= LIMIT:
        raise ValueError('UI batch requires 1 to 48 operations')
    parts = []
    for command, payload in requests:
        action, size, _ = TYPES[command]
        if type(payload) is not bytes or len(payload) != size:
            raise ValueError('Invalid UI operation payload')
        packed = pack_sparse(payload)
        parts.extend((ITEM.pack(action, len(packed)), packed))
    body = b''.join(parts)
    size = HEADER.size + len(body)
    if size > CAPACITY - LIMIT * 64:
        raise ValueError('UI batch exceeds bounded scratch capacity')
    return HEADER.pack(1, len(requests), size, 0, 0) + body

def validate_request(payload):
    if type(payload) is not bytes or not HEADER.size <= len(payload) <= CAPACITY - LIMIT * 64:
        raise ValueError('Invalid UI batch length')
    version, count, size, done, error = HEADER.unpack_from(payload)
    if version != 1 or not 1 <= count <= LIMIT or size != len(payload) or done or error:
        raise ValueError('Invalid UI batch header')

def decode(requests, response):
    data = bytes.fromhex(response)
    if not HEADER.size <= len(data) <= CAPACITY:
        raise ValueError('Invalid UI batch acknowledgement length')
    version, count, size, done, error = HEADER.unpack_from(data)
    if (version, count, size, done, error) != (1, len(requests), len(data), len(requests), 0):
        raise ValueError(f'UI batch failed or incomplete: completed={done}, error={error}; no retry')
    replies, at = [], HEADER.size
    for command, _ in requests:
        expected, extent, key = TYPES[command]
        if len(data) - at < ITEM.size:
            raise ValueError('Truncated UI batch acknowledgement')
        action, size = ITEM.unpack_from(data, at); at += ITEM.size
        if action != expected or size > len(data) - at:
            raise ValueError('Unexpected UI batch operation')
        replies.append({key: unpack_sparse(data[at:at+size], extent).hex()})
        at += size
    if at != len(data):
        raise ValueError('Trailing UI batch acknowledgement data')
    return replies

def available(session):
    return getattr(session._transport, 'ui_batch_protocol', 0) == 1

def execute(session, requests):
    session._check()
    sent = encode(requests)  # Local failure does not dispatch or retry.
    try:
        response = session._transport.command('ui-batch', sent)
        return decode(requests, response['ui_batch_packet'])
    except BaseException:
        session._abort_ownership()
        raise

def invoke_setters(scope, prepared):
    from . import _retained_wire, _text_wire, _enum_wire
    from .invocation import decode_result
    requests, calls = [], []
    for call in prepared:
        planner, session = call._check()
        plan = call._plan
        if plan.function.name not in ('SetText', 'SetIsEnabled', 'SetVisibility'):
            allowed = (frozenset(('SetBrushResourceObject',)) if getattr(session._transport, 'layout_batch_protocol', 0) == 3 else frozenset()) | LAYOUT_SETTERS | (EXTENDED_LAYOUT_SETTERS if extended_layout_available(session) else frozenset())
            if not layout_available(session) or plan.function.name not in allowed:
                raise ValueError('Only supported menu setters can be batched')
        if any(parameter.flags & 0x500 for parameter in plan.parameters):
            raise ValueError('UI setters cannot return outputs')
        wire = _text_wire if plan.wire_version == 3 else _enum_wire if plan.wire_version == 4 else _retained_wire
        payload = wire.encode_plan(plan, dict(plan.texts)) if plan.wire_version == 3 else wire.encode_plan(plan)
        requests.append(('text-invoke' if plan.wire_version == 3 else 'retained-invoke', payload))
        calls.append((plan, planner._catalog, wire))
        if session is not scope._session:
            raise ValueError('UI call belongs to another session')
    if not requests:
        return
    replies = execute(scope._session, requests)
    try:
        for (plan, catalog, wire), (_, sent), response in zip(calls, requests, replies):
            if plan.wire_version == 3:
                decoded = wire.decode_reply(sent, response['text_packet'])
                reply, leases, texts = decoded.call, decoded.leases, decoded.texts
            else:
                reply, leases = wire.decode_reply(sent, response['retained_packet'])
                texts = ()
            if leases:
                raise ValueError('UI setter unexpectedly returned owned outputs')
            # Class/object inputs (SetStyle, SetOwningPlayer) are echoed as
            # identities, not owned outputs. Decode them against the supplied
            # planning catalog; no new reference or lease may be introduced.
            decode_result(plan, reply, catalog, texts=texts)
    except BaseException:
        scope._session._abort_ownership()
        raise
