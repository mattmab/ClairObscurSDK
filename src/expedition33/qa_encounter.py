"""Narrow QA actor history reset, using engine-owned map removal."""
import struct
SIZE=104
def validate_request(data):
 if type(data) is not bytes or len(data)!=SIZE or struct.unpack_from('<4I',data) not in [(1,op,0,0) for op in (1,2,3,4)] or any(data[96:]):raise ValueError('Invalid QA encounter packet')
 for offset in range(16,96,16):
  i,s,a=struct.unpack_from('<iiQ',data,offset)
  if i<0 or s<0 or not a:raise ValueError('Invalid QA encounter identity')
def reset_enemy_history(scope,world,enemy,component,gi,function):
 scope._check()
 data=struct.pack('<4I',1,1,0,0)+b''.join(struct.pack('<iiQ',o.index,o.serial,o.address) for o in (world,enemy,component,gi,function))+bytes(8)
 validate_request(data)
 reply=scope._session._transport.command('qa-encounter-reset',data)
 result=bytes.fromhex(reply['qa_encounter_packet'])
 if len(result)!=SIZE or result[:8]!=data[:8] or result[16:96]!=data[16:96] or any(result[100:]):raise RuntimeError('QA reset acknowledgement mismatch; inspect before retrying')
 _,_,error,outcome=struct.unpack_from('<4I',result)
 if error or outcome!=1:raise RuntimeError(f'QA reset rejected/partial: error={error}, outcome={outcome}; not retried')
 return struct.unpack_from('<I',result,96)[0]

def mime_arena(scope,world,enemy,target,gi,function,operation=2):
 scope._check()
 data=struct.pack('<4I',1,operation,0,0)+b''.join(struct.pack('<iiQ',o.index,o.serial,o.address) for o in (world,enemy,target,gi,function))+bytes(8)
 validate_request(data)
 reply=scope._session._transport.command('qa-encounter-reset',data)
 result=bytes.fromhex(reply['qa_encounter_packet'])
 if len(result)!=SIZE or result[:8]!=data[:8] or result[16:]!=data[16:]:raise RuntimeError('Mime arena acknowledgement mismatch; do not retry')
 _,_,error,outcome=struct.unpack_from('<4I',result)
 if error or outcome!=1:raise RuntimeError(f'Mime arena rejected/partial: error={error}, outcome={outcome}; do not retry')
 return True
