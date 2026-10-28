"""Game sequence tracks projected into the Scene Editor's shared picker."""
import json
from .authored import AuthoredWorkspace


class SequenceProperties:
    def __init__(self,document,workspace=None):
        self.workspace=workspace or AuthoredWorkspace()
        if workspace is None:
            from expedition33.cinematics.authored_timeline import validate
            self.workspace.document=validate(document)
        self.category='sections';self.selected=None;self.key_section=None;self.property_index=0;self.revision=0
    @property
    def document(self):return self.workspace.document
    def rows(self):
        if self.category=='scene':return (('origin','Whole scene | world position (cm)'),)
        if self.category=='sections':
            return tuple((r['path'],r['kind']+' | '+r['path'].rsplit('.',1)[-1]) for r in self.workspace.sections())
        if self.category=='cast':
            return tuple(((r['sequence'],r['guid']),r['name']+' | '+r['sequence'].rsplit('.',1)[-1])
                         for r in self.workspace.cast() if r['kind']=='spawnable' and r['template'] and r['template']['class'].startswith('BP_Cine_'))
        if self.category=='keys':
            return tuple(((tuple(channel['path']),key['index']),
                '.'.join(str(part) for part in channel['path'])+f" | key {key['index']} @ {key['at']} ticks")
                for channel in self.workspace.channels(self.key_section) for key in channel['keys'])
        return tuple((r['id'],r['name']+' | '+r['profile']) for r in self.document.get('npc_tracks',()))
    def open_keys(self):
        if self.category!='sections' or self.selected is None:raise ValueError('Select a section first')
        if not self.workspace.channels(self.selected):raise ValueError('This section has no complete editable channels')
        self.key_section=self.selected;self.category='keys';self.selected=None;self.property_index=0;self.revision+=1
    def back_to_section(self):
        if self.category!='keys' or self.key_section is None:raise ValueError('Open section keys first')
        section=self.key_section;self.category_changed('sections');self.select(section)
    def select(self,key):
        if key not in {row[0] for row in self.rows()}:raise ValueError('Choose an existing sequence track')
        self.selected=key;self.property_index=0;self.revision+=1
    def category_changed(self,category):
        if category not in ('sections','cast','npc','scene'):raise ValueError('Unknown sequence track category')
        self.category=category;self.selected=None;self.property_index=0;self.revision+=1
    def properties(self):
        key=self.selected
        if key is None:return ()
        if self.category=='scene':return (('world position (cm)',self.document.get('scene_position')),('scene yaw (degrees)',self.document.get('scene_yaw',0.)))
        if self.category=='sections':
            row=next(r for r in self.workspace.sections() if r['path']==key)
            if row['start'] is None or row['end'] is None:
                return (('range (source ticks)',[row['start'],row['end']]),)
            return (('start (source ticks)',row['start']),('end (source ticks)',row['end']))
        if self.category=='keys':
            path,index=key
            curve=next(c for c in self.workspace.channels(self.key_section) if tuple(c['path'])==path)
            row=next(k for k in curve['keys'] if k['index']==index)
            return (('time (source ticks)',row['at']),('value',row['value']))
        if self.category=='cast':
            row=next((r for r in self.document.get('cast_edits',()) if (r['sequence'],r['guid'])==key),None)
            values=[('profile',row['profile'] if row else 'original')]
            if row:
                placement=row.get('placement',dict(offset=[300.,0.,0.],yaw=0.))
                values.extend((axis,placement['offset'][i]) for i,axis in enumerate('XYZ'))
                values.append(('yaw',placement['yaw']))
            return tuple(values)
        row=next(r for r in self.document['npc_tracks'] if r['id']==key)
        return tuple((k,row[k]) for k in ('name','profile','start','end'))+tuple(
            (axis,row['placement']['offset'][i]) for i,axis in enumerate('XYZ'))+(('yaw',row['placement']['yaw']),)
    def field(self):
        fields=self.properties()
        if not fields:return None
        self.property_index%=len(fields)
        name,value=fields[self.property_index]
        return name,json.dumps(value) if value is None or type(value) in (bool,list) else str(value)
    def cast_overlap_warning(self):
        if self.category!='cast' or self.selected is None:return ''
        edit=next((e for e in self.document.get('cast_edits',()) if (e['sequence'],e['guid'])==self.selected),None)
        if edit is None:return ''
        from expedition33.cinematics.authored_cast import replacement_overlap_warning
        return replacement_overlap_warning(self.workspace.cast(),self.document['cast_edits'],self.selected,edit['profile'])
    def move_property(self,delta):
        if self.properties():self.property_index=(self.property_index+delta)%len(self.properties());self.revision+=1
    def edit(self,text):
        field=self.field()
        if field is None:raise ValueError('Select a track first')
        name=field[0]
        value=text if name in ('name','profile') else json.loads(text)
        if self.category=='scene':
            if name=='scene yaw (degrees)':self.workspace.rotate_scene(value)
            else:self.workspace.place_scene(value)
        elif self.category=='sections':
            row=next(r for r in self.workspace.sections() if r['path']==self.selected)
            if name=='range (source ticks)':
                if type(value) is not list or len(value)!=2 or any(type(v) is not int for v in value):
                    raise ValueError('Enter both finite section bounds as [start, end] in source ticks')
                self.workspace.retime(self.selected,*value)
            else:
                self.workspace.retime(self.selected,value if name.startswith('start') else row['start'],value if name.startswith('end') else row['end'])
        elif self.category=='keys':
            path,index=self.selected;current=dict(self.properties())
            self.workspace.edit_key(self.key_section,list(path),index,
                at=value if name.startswith('time') else current['time (source ticks)'],
                value=value if name=='value' else current['value'])
        elif self.category=='cast':
            if name=='profile':self.workspace.replace_cast(*self.selected,None if value=='original' else value)
            else:
                row=next(r for r in self.document['cast_edits'] if (r['sequence'],r['guid'])==self.selected)
                placement=row.get('placement',dict(offset=[300.,0.,0.],yaw=0.));offset=list(placement['offset']);yaw=placement['yaw']
                if name=='yaw':yaw=value
                else:offset['XYZ'.index(name)]=value
                self.workspace.place_cast(*self.selected,offset,yaw)
        else:self.workspace.edit_npc(self.selected,name,value)
        self.revision+=1
    def add_npc(self,profile):
        key=self.workspace.add_npc(profile);self.category='npc';self.select(key)
    def remove_npc(self):
        if self.category!='npc' or self.selected is None:raise ValueError('Select an NPC track first')
        self.workspace.remove_npc(self.selected);self.selected=None;self.property_index=0;self.revision+=1
    def reset_key(self):
        if self.category!='keys' or self.selected is None:raise ValueError('Select a source key first')
        path,index=self.selected;self.workspace.reset_key(self.key_section,list(path),index);self.revision+=1
