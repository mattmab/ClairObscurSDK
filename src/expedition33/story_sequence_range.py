"""Reversible selected-save endpoints for the two inspected reference movies."""
import struct
from .story_original import _Owner
from ._story_original_wire import identity,put_id,OriginalNarrativeError
SIZE=20984
PROFILES={
    'gommage':dict(path='/Game/Cinematics/Lumiere/Act01/TheGommage/MCS_TheGommageP2_PreRender.MCS_TheGommageP2_PreRender',expected=6493600,replacement=7261600,minimum_protocol=1),
    'departure-beach':dict(path='/Game/Cinematics/DarkShores/TheEndOfExpedition33/MCS_TheEndOfExpedition33.MCS_TheEndOfExpedition33',expected=5501600,replacement=5885600,minimum_protocol=2),
}

def packet(owner,scene,gi,key,mode=0,*,sequence="gommage"):
    profile=PROFILES[sequence]
    data=bytearray(SIZE);struct.pack_into('<4IQ',data,0,3,252,0,0,owner)
    put_id(data,24,scene.object);put_id(data,40,gi.object)
    struct.pack_into('<2Q',data,56,scene._token,gi._token)
    if len(key)!=32:raise ValueError('Selected-save key length')
    struct.pack_into('<4I4I',data,72,*(int(key[i:i+8],16) for i in range(0,32,8)),mode,profile["expected"],profile["replacement"],0)
    result=bytes(data);validate(result);return result
def validate(data):
    if type(data) is not bytes or len(data)!=SIZE:raise ValueError('Story sequence range packet size')
    version,op,error,state,owner=struct.unpack_from('<4IQ',data)
    if (version,op,error,state)!=(3,252,0,0) or not owner:raise ValueError('Story sequence range header')
    identity(data,24);identity(data,40)
    if not all(struct.unpack_from('<2Q',data,56)) or struct.unpack_from('<I',data,72)[0]!=0xe33c5701:raise ValueError('Story sequence selected-save leases')
    mode,old,new,readback=struct.unpack_from('<4I',data,88)
    if mode>2 or readback or (old,new) not in {(r['expected'],r['replacement']) for r in PROFILES.values()} or any(data[104:]):raise ValueError('Story sequence exact reference range')
def decode(sent,reply):
    validate(sent)
    if type(reply) is not bytes or len(reply)!=SIZE:raise RuntimeError('Story sequence range acknowledgement size')
    error,state=struct.unpack_from('<2I',reply,8);mode=struct.unpack_from('<I',sent,88)[0]
    compare=bytearray(reply);compare[8:16]=sent[8:16];compare[100:104]=sent[100:104]
    if bytes(compare)!=sent:raise RuntimeError('Story sequence range acknowledgement context changed')
    if error:raise OriginalNarrativeError(error)
    readback=struct.unpack_from('<I',reply,100)[0]
    old,new=struct.unpack_from('<2I',sent,92)
    restored=mode==1 and state==4
    if (state!=mode+1 and not restored) or readback!=(old if mode==2 or restored else new):raise RuntimeError('Story sequence range readback mismatch')
    return readback
class StorySequenceRange(_Owner):
    def __init__(self,parent,key,*,resources=None,sequence='gommage'):
        if sequence not in PROFILES:raise ValueError('Unknown authored sequence range')
        capability=getattr(parent._session._transport,'story_sequence_range_protocol',0)
        if type(capability) is not int or capability<PROFILES[sequence]['minimum_protocol']:
            raise RuntimeError('This authored sequence range requires SDK range protocol '+str(PROFILES[sequence]['minimum_protocol']))
        self.sequence=sequence
        super().__init__(parent,key,resources=resources)

    def prepare(self):
        from .catalog import capture_selected
        from .values import read_values_with_references
        from ._reader import shared_operation
        from .story_save_identity import observe
        if self.started or self.held:raise RuntimeError('Story sequence range preparation is one-shot')
        with shared_operation(self.scope.pid):
            # A movie range owns no dialogue system. Preserve the fresh save/GI
            # observation used by _Owner.context, without its unrelated global
            # dialogue-component/function discovery. Native still validates the
            # exact selected save before changing the retained MovieScene.
            gi=self.scene.gi if self.scene is not None else observe(self.scope)[4]
            self.gi=self.hold(gi)
            seq=self.hold(self.resources.load(PROFILES[self.sequence]['path']))
            c=capture_selected(self.scope.pid,((seq.object.index,seq.object.serial,seq.object.address),))
            values,c=read_values_with_references(c,seq.object,fields=('MovieScene',))
            if values.errors:raise RuntimeError('Authored MovieScene unavailable')
            self.scene=self.hold(next(v for k,v in values.values.items() if k[1]=='MovieScene'))
            self.send(0);self.started=True
        return self
    def send(self,mode):
        sent=packet(self.owner,self.scene,self.gi,self.key,mode,sequence=self.sequence)
        try:
            reply=self.scope._session._transport.command('mesh',sent)
            return decode(sent,bytes.fromhex(reply['mesh_packet']))
        except OriginalNarrativeError as error:
            if error.code==4221:self.unknown=True
            raise
        except BaseException:self.unknown=True;raise
    def active(self):
        """Inspect the retained journal, including native save-change restore."""
        if self.closed:return False
        if not self.started or self.unknown:raise RuntimeError('Sequence range owner is incomplete or uncertain')
        return self.send(1)==PROFILES[self.sequence]['replacement']
    def close(self):
        if self.closed:return True
        if self.unknown:return False
        if self.started:self.send(2);self.started=False
        self.scope.close();self.closed=True;return True


def ensure_process_range(parent,key,*,resources,sequence='departure-beach'):
    """Retain a selected-save asset range across native World travel.

    Only process assets and GI are retained; no World, pawn or controller is
    leased. Native protocol 2 keeps the exact range through map loading and
    restores it on a proven title/other-save context. The native journal stays
    owned until acknowledged here or by explicit mod/process shutdown.
    """
    from ._metadata_stabilization import process_preparation
    session=getattr(parent,'_session',parent)
    session._check()
    if getattr(session._transport,'story_sequence_range_protocol',0)!=2:
        raise RuntimeError('Persistent authored sequence ranges require SDK range protocol 2')
    if sequence not in PROFILES:raise ValueError('Unknown authored sequence range')
    owners=getattr(session,'_story_process_ranges',None)
    if owners is None:owners={};session._story_process_ranges=owners
    previous=owners.get(sequence)
    if previous is not None:
        if previous.unknown or (not previous.started and not previous.closed):
            raise RuntimeError('Incomplete sequence preparation remains owned; no automatic retry')
        if not previous.closed and previous.key==key and previous.active():return previous
        if not previous.close():raise RuntimeError('Previous selected-save sequence range cleanup pending')
        del owners[sequence]
    owner=StorySequenceRange(process_preparation(session).scope,key,resources=resources,sequence=sequence)
    # Publish ownership before preparing so a rejected or uncertain attempt
    # cannot be repeated by constructing a fresh owner on the next poll.
    owners[sequence]=owner
    return owner.prepare()


def close_process_ranges(parent):
    """Explicit mod disable cleanup; ordinary World retirement must not call."""
    session=getattr(parent,'_session',parent);session._check()
    owners=getattr(session,'_story_process_ranges',{})
    for sequence,owner in tuple(owners.items()):
        if not owner.close():return False
        del owners[sequence]
    return True
