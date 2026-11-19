"""Scoped FileMediaSource path overrides; the original game owns playback."""
from .catalog import capture_matching,capture_selected
from .values import read_values_with_references

class StoryMediaSource:
    def __init__(self,scope,resources):self.scope=scope;self.resources=resources;self.original=None;self.source=None;self.planner=None;self.unknown=False
    def prepare(self,asset,path):
        if self.source is not None:raise RuntimeError('Media override already prepared')
        self.source=self.resources.load(asset)
        if self.source.class_name!='FileMediaSource':raise ValueError('Original FileMediaSource required')
        metadata=getattr(getattr(self.scope,'_session',None),'_file_audio_metadata',None)
        planner=None
        try:
            if metadata is not None:
                # Exact immutable FileMediaSource schema is already retained
                # at title. The source and its current path remain fresh.
                planner=metadata.planner(self.scope,(self.source,));c=planner._catalog
            else:
                c=capture_matching(self.scope.pid,names=('SetFilePath',)).with_observations(capture_selected(self.scope.pid,((self.source.index,self.source.serial,self.source.address),)))
            values,c=read_values_with_references(c,self.source,fields=('FilePath',))
            rows=[v for k,v in values.values.items() if k[1]=='FilePath']
            if values.errors or values.truncated or len(rows)!=1 or type(rows[0]) is not str:raise RuntimeError('Media path observation incomplete')
            self.original=rows[0]
            self.planner=planner if planner is not None else self.scope.invocation_planner(catalog=c,selected_results=True)
        except BaseException:
            if planner is not None:planner.close()
            raise
        self.function=c.find_path('/Script/MediaAssets.FileMediaSource:SetFilePath')
        self._set(str(path))
        return self
    def _set(self,path):
        call=self.planner.prepare(self.source,self.function,Path=path)
        self.unknown=True
        with call.invoke():pass
        values,_=read_values_with_references(self.planner._catalog,self.source,fields=('FilePath',))
        observed=[v for k,v in values.values.items() if k[1]=='FilePath']
        if values.errors or observed!=[path]:raise RuntimeError('Media path override not acknowledged')
        self.unknown=False
    def close(self):
        if self.unknown:return False
        if self.planner is not None:
            self._set(self.original);self.planner.close();self.planner=None
        return True
