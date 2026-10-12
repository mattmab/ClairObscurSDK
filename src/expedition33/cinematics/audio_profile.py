"""Decode bounded reviewed media-audio manifests; playback admission is separate."""
from .audio_curve import CubicKey,UnweightedCubicChannel,SectionGain
from .media_audio_timeline import Section

def decode_sections(profile):
    if profile.get('version')!=1 or profile.get('category')!='media_external_audio':
        raise ValueError('Unsupported audio profile')
    rate=profile.get('tick_rate')
    if type(rate) is not int or rate<=0:raise ValueError('Exact root rate required')
    rows=profile.get('sections')
    if not isinstance(rows,list) or not 1<=len(rows)<=64:raise ValueError('Bounded section list required')
    result=[];identities=set()
    for row in rows:
        identity=row['identity'];source=row['source'];offset=row['source_offset']
        if type(identity) is not str or not identity or identity in identities:raise ValueError('Unique section identity required')
        if type(source) is not str or not source.startswith('/Game/') or '..' in source:raise ValueError('Exact source path required')
        if type(offset) is not int or offset<0:raise ValueError('Exact source offset required')
        keys=row['keys']
        if not isinstance(keys,list) or len(keys)>64:raise ValueError('Bounded key list required')
        channel=UnweightedCubicChannel([CubicKey(**key) for key in keys],default=row['default'])
        gain=SectionGain(channel,row['lower'],row['upper'],row['ease_in'],row['ease_out'],rate)
        result.append(Section(identity,source,gain.lower/rate,gain.upper/rate,offset/rate,gain))
        identities.add(identity)
    return tuple(result)
