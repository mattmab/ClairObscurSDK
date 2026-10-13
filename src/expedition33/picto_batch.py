"""One native ownership queue, frame-gated mutations, one final readback."""
import secrets
import struct
from time import monotonic
from .picto_progression import IDENTITY

HEADER=struct.Struct('<4IQ4I')
ENTRY=struct.Struct('<iiQIIQ')
CAPACITY=342
SIZE=104+CAPACITY*ENTRY.size

def validate_request(data):
    if type(data) is not bytes or len(data)!=SIZE:raise ValueError('Picto batch packet size')
    version,op,error,state,token,count,desired,processed,reserved=HEADER.unpack_from(data)
    if version!=1 or op not in (1,2,3) or not token or error or state or processed or desired not in (0,1,2,3) or count>CAPACITY:
        raise ValueError('Picto batch header')
    if (not 1<=reserved<=33) if desired==2 else (reserved not in (0,1) if desired==3 else reserved!=0):raise ValueError('Picto batch target')
    for offset in range(40,104,16):
        index,serial,address=IDENTITY.unpack_from(data,offset)
        if (index<0 or not address) if op==1 else (index or serial or address):raise ValueError('Picto batch dependency')
    if op!=1 and (count or desired):raise ValueError('Picto batch query arguments')
    addresses=set()
    for i in range(CAPACITY):
        index,serial,address,error,outcome,frame=ENTRY.unpack_from(data,104+i*ENTRY.size)
        if error or outcome or frame:raise ValueError('Picto batch entry output')
        if i<count:
            if index<0 or not address or address in addresses:raise ValueError('Picto batch entry identity')
            addresses.add(address)
        elif index or serial or address:raise ValueError('Picto batch unused entry')

class FrameBulkTransaction:
    native=True
    def __init__(self,transaction,*,clock=monotonic,level=None,mastery=None,identities=None):
        self.transaction=transaction;self.clock=clock;self.started=None
        self.level=level;self.mastery=mastery
        if mastery is not None and (level is not None or type(mastery[0]) is not bool):raise ValueError('Picto batch mastery')
        self.mode=3 if mastery is not None else 2 if level else int(transaction.desired)
        self.target=int(mastery[0]) if mastery is not None else level[0] if level else 0
        if level is not None and (type(level[0]) is not int or not 1<=level[0]<=33):raise ValueError('Picto batch level')
        owner=transaction.ownership
        self.queue=sorted(owner.owned) if level or mastery is not None else sorted(key for key,row in owner.rows.items() if row.get('normal') and (key in owner.owned)!=transaction.desired)
        if identities is not None:
            requested=tuple(identities)
            if len(set(requested))!=len(requested) or not set(requested)<=set(self.queue):
                raise ValueError('Picto batch subset must contain unique eligible identities')
            self.queue=sorted(requested)
        if len(self.queue)>CAPACITY:raise ValueError('Picto batch exceeds native capacity')
        self.total=len(self.queue);self.completed=[];self.skipped=[];self.failed={}
        self.done=False;self.error=None;self.future=None;self.phase=None;self.cancelled=False
        self.token=secrets.randbits(64) or 1;self.dispatched=False;self.result=None
        self.processed=0;self.frames=[];self.ids=[];self.request=None

    def start(self):
        if self.started is not None:return
        self.started=self.clock();self.phase='preflight'
        self.transaction.state=('Mastering' if self.mastery[0] else 'Unmastering') if self.mastery is not None else 'Leveling' if self.level else 'Unlocking' if self.transaction.desired else 'Removing'
        self.future=self.transaction.submit_read(self._refresh)

    def _refresh(self):
        owned=self.transaction._refresh()
        if self.mastery is None:return owned
        from .values import read_values_many
        from .picto_restore import field
        owner=self.transaction.ownership
        shared=field(read_values_many(owner.catalog,(owner.gi,),fields=('SharedPassiveEffectProgression',))[owner.gi.index],'SharedPassiveEffectProgression').items
        progress={key:(value.fields['LearntSteps_6_A14D681549E830249C77BD95F2B4CF3F'],value.fields['IsLearnt_9_2561000E49D90653437DE9A45BE2A86D']) for key,value in shared.items()}
        return owned,progress

    def _mastery_matches(self,key,progress):
        steps,learnt=progress.get(key,(0,False))
        return learnt==self.mastery[0] and (learnt or steps==0)

    def _command(self,operation):
        owner=self.transaction.ownership;owner.scope._check()
        if operation==1:
            if self.level:deps=(self.level[1],self.level[2],owner.table,owner.gi)
            elif self.mastery is not None:deps=(self.mastery[1],self.mastery[2],self.mastery[3],owner.gi)
            else:deps=(owner.manager,owner.function('AC_jRPG_InventoryManager_C','AddItemToInventory' if self.transaction.desired else 'RemoveItemFromInventory'),owner.table,owner.gi)
            data=HEADER.pack(1,1,0,0,self.token,len(self.ids),self.mode,0,self.target)
            data+=b''.join(IDENTITY.pack(o.index,o.serial,o.address) for o in deps)
            for key in self.ids:
                if self.level or self.mastery is not None:o=self.level_items[key][0]
                else:
                    row=owner.rows[key];o=row['asset']
                    if not row.get('normal') or o is None:raise ValueError('Unverified Picto in batch')
                data+=ENTRY.pack(o.index,o.serial,o.address,0,0,0)
            data+=bytes((CAPACITY-len(self.ids))*ENTRY.size)
            self.request=data
        else:data=HEADER.pack(1,operation,0,0,self.token,0,0,0,0)+bytes(SIZE-40)
        validate_request(data)
        reply=owner.scope._session._transport.command('picto-batch',data)
        result=bytes.fromhex(reply['picto_batch_packet'])
        if len(result)!=SIZE:raise RuntimeError('Picto batch acknowledgement size mismatch')
        version,op,error,state,token,count,desired,processed,reserved=HEADER.unpack_from(result)
        if version!=1 or op!=operation or token!=self.token or reserved!=self.target or count>CAPACITY or processed>count:
            raise RuntimeError('Picto batch acknowledgement mismatch')
        if state not in (1,2,3,4):raise RuntimeError(f'Picto batch rejected: {error}')
        if self.request is None or result[40:104]!=self.request[40:104] or count!=len(self.ids) or desired!=self.mode:
            raise RuntimeError('Picto batch dependencies changed')
        frames=[]
        for i in range(count):
            offset=104+i*ENTRY.size
            if result[offset:offset+16]!=self.request[offset:offset+16]:raise RuntimeError('Picto batch asset changed')
            _,_,_,entry_error,outcome,frame=ENTRY.unpack_from(result,offset)
            if i<processed:
                if not frame or (frames and frame<=frames[-1]):raise RuntimeError('Picto batch frame order invalid')
                frames.append(frame)
            elif entry_error or outcome or frame:raise RuntimeError('Unprocessed Picto has output')
        self.result=result;self.processed=processed;self.frames=frames
        if error:self.error=f'Native batch stopped: {error}'
        return state

    def stop(self):
        self.cancelled=True
        if self.dispatched and self.phase=='running':
            try:self._command(3)
            except Exception as error:self.error=str(error)
            self._reconcile()

    def _reconcile(self):
        self.phase='verify';self.future=self.transaction.submit_read(self._refresh)

    def poll(self):
        if self.done or self.started is None:return
        try:
            if self.phase=='running':
                state=self._command(2)
                if state!=1:self._reconcile()
                return
            if not self.future.done():return
            snapshot=self.future.result();self.future=None
            if self.mastery is not None:owned,progress=snapshot
            else:owned=snapshot
            owned=dict(owned)
            if self.phase=='preflight':
                if self.level or self.mastery is not None:
                    self.level_items=owned
                    self.skipped=[key for key in self.queue if key in owned and (self._mastery_matches(key,progress) if self.mastery is not None else owned[key][1]==self.level[0])]
                    self.failed={key:'No longer owned' for key in self.queue if key not in owned}
                else:self.skipped=[key for key in self.queue if (key in owned)==self.transaction.desired]
                self.ids=[key for key in self.queue if key not in self.skipped and key not in self.failed]
                if self.cancelled:
                    self.transaction.owned=owned;self._finish();return
                self.dispatched=True;self.phase='running'
                state=self._command(1)
                if state!=1:self._reconcile()
            else:
                self.transaction.owned=owned
                # Only attempted identities can have their persisted state changed.
                for i,key in enumerate(self.ids[:self.processed]):
                    confirmed=(key in owned and owned[key][1]==self.level[0]) if self.level else (key in owned)==self.transaction.desired
                    if self.mastery is not None:confirmed=key in owned and self._mastery_matches(key,progress)
                    if confirmed:self.completed.append(key)
                    else:
                        code=ENTRY.unpack_from(self.result,104+i*ENTRY.size)[3]
                        self.failed[key]='Equipped Picto protected' if code==1759 else f'Picto state not confirmed (native {code})'
                self._finish()
        except Exception as error:
            self.error=str(error)
            if self.phase=='running':
                # Never repeat submission. Stop this token, then reconcile even
                # when the initial acknowledgement was lost.
                try:self._command(3)
                except Exception:pass
                self._reconcile()
            else:self._finish()

    def _finish(self):
        self.done=True;self.transaction.state='Ready';self.phase='done'
