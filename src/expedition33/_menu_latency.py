"""Bounded owner-thread menu timings; no text, UObject identities or arguments."""
from contextlib import contextmanager
from functools import wraps
import time

class MenuLatency:
    LIMIT=128
    def __init__(self,clock=None):self._clock=clock or time.perf_counter;self._times={};self._counts={}
    def _label(self,label):
        if type(label) is not str or not label or len(label)>80:return 'other'
        if label not in self._times and label not in self._counts and len(self._times)+len(self._counts)>=self.LIMIT:return 'other'
        return label
    def count(self,label,amount=1):
        label=self._label(label);self._counts[label]=self._counts.get(label,0)+amount
    @contextmanager
    def measure(self,label):
        label=self._label(label);start=self._clock();failed=False
        try:yield
        except BaseException:failed=True;raise
        finally:
            ms=max(0.,(self._clock()-start)*1000)
            row=self._times.setdefault(label,dict(count=0,failed=0,total_ms=0.,max_ms=0.,last_ms=0.))
            row['count']+=1;row['failed']+=int(failed);row['total_ms']+=ms;row['max_ms']=max(row['max_ms'],ms);row['last_ms']=ms
    def snapshot(self):
        return dict(timings={k:dict(v) for k,v in sorted(self._times.items())},counts=dict(sorted(self._counts.items())))

def measure_method(label):
    def decorate(method):
        @wraps(method)
        def measured(self,*args,**kwargs):
            latency=getattr(self,'latency',None)
            if latency is None:
                latency=MenuLatency();self.latency=latency
            with latency.measure(label):return method(self,*args,**kwargs)
        return measured
    return decorate
