"""Catalog folders and persistent favorites."""
import json
from pathlib import Path
class Browser:
    def __init__(self,root):
        self.file=Path(root)/'favorites.json'
        self.metadata_file=Path(root)/'asset-metadata.json'
        try:self.metadata=json.loads(self.metadata_file.read_text(encoding='utf8'))
        except (OSError,ValueError):self.metadata={}
        if not isinstance(self.metadata,dict):self.metadata={}
        try:
            data=json.loads(self.file.read_text(encoding='utf8'))
            self.favorites={p for p in data if isinstance(p,str) and p.startswith('/Game/')} if isinstance(data,list) else set()
        except (OSError,ValueError):self.favorites=set()
    def tag(self,path,category,tags):
        self.metadata[path]=dict(category=category.strip()[:80],tags=tags.strip()[:512])
        tmp=self.metadata_file.with_suffix('.tmp');tmp.write_text(json.dumps(self.metadata),encoding='utf8');tmp.replace(self.metadata_file)
    def favorite(self,path):
        if path in self.favorites:self.favorites.remove(path)
        else:self.favorites.add(path)
        self.file.parent.mkdir(parents=True,exist_ok=True)
        temporary=self.file.with_suffix('.tmp');temporary.write_text(json.dumps(sorted(self.favorites)),encoding='utf8');temporary.replace(self.file)
    def rows(self,assets,query='',kind='mesh',folder='/Game/',folders=True,favorites=False):
        rows=[r for r in assets if (not kind or r['kind']==kind) and query.casefold() in (r['path']+' '+str(self.metadata.get(r['path'],{}))).casefold() and (not favorites or r['path'] in self.favorites)]
        if query or favorites or not folders:return rows
        grouped={};direct=[]
        for row in rows:
            if not row['path'].startswith(folder):continue
            rest=row['path'][len(folder):]
            if '/' not in rest:direct.append(row);continue
            name=rest.split('/',1)[0];prefix=folder+name+'/'
            group=grouped.setdefault(prefix,dict(kind='folder',name=name,path=prefix,count=0,cover=row['path'],children=[]));group['count']+=1;group['children'].append(row)
        folders_out=[]
        for group in grouped.values():
            children=group.pop('children')
            if len(children)<=4:direct.extend(children)
            else:folders_out.append(group)
        return sorted(folders_out,key=lambda r:r['name'].casefold())+sorted(direct,key=lambda r:(r['name'].casefold(),r['path']))
