from expedition33.management import ManagementError
from expedition33.management_view import MenuControl,MenuFrame

class BrowserView:
    def __init__(self,registry,model):
        self.registry=registry;self.model=model;self.page=0;self.selected=None;self.closed=False;self.revision=0;self.tokens=set()
    def render(self):
        self.registry._check()
        if self.closed:raise ManagementError('Catalog browser is closed')
        self.revision+=1;rows=self.model.entries;pages=max(1,(len(rows)+5)//6);self.page=min(self.page,pages-1)
        description='Static models only. Quarantined entries excluded. Select a model to spawn it on nearby ground.'
        if self.selected is None:
            controls=[MenuControl(100+i,row['name']+' — '+row['id'].split('__')[-1] if '__' in row['id'] else row['name']) for i,row in enumerate(rows) if self.page*6<=i<(self.page+1)*6]
            controls += [MenuControl(1,'Previous',self.page>0),MenuControl(2,'Next',self.page+1<pages)]
        else:
            row=next(r for r in rows if r['id']==self.selected)
            description=f"{row['name']}\n{row.get('sections','?')} sections, {row.get('vertices','?')} vertices\n{row['reason']}\nEXPERIMENTAL: animation is not 1:1. Loading needs improvement; meshes may lag."
            controls=[MenuControl(3,'Spawn on ground',row['available'] and not self.model.busy),MenuControl(4,'Back to catalog')]
            if row.get('replacement'):controls.insert(1,MenuControl(8,'Replace current character',row['available']))
        controls += [MenuControl(5,'Destroy current model',self.model.busy),MenuControl(6,'Refresh status'),MenuControl(7,'Close')]
        self.tokens={c.token for c in controls if c.enabled}
        return MenuFrame(self.revision,'Model Catalog',description,tuple(controls),self.page,pages,self.model.summary(),False)
    def activate(self,revision,token,**_):
        self.registry._check()
        if self.closed or revision!=self.revision or token not in self.tokens:raise ManagementError('Stale catalog control')
        if token>=100:self.selected=self.model.entries[token-100]['id']
        elif token==1:self.page-=1
        elif token==2:self.page+=1
        elif token==3:self.model.spawn(self.selected)
        elif token==4:self.selected=None
        elif token==5:self.model.destroy()
        elif token==8:self.model.select_replacement(self.selected)
        elif token==7:
            self.close();return MenuFrame(self.revision,'Model Catalog','',(),0,1,'',True)
        return self.render()
    def close(self):self.closed=True;self.revision+=1;self.tokens.clear()
