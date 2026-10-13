"""Durable pre-override snapshots. Never treat a hot-reloaded session as fresh."""
from datetime import datetime, timezone
from .settings import SettingsStore
from .picto_preferences import MOD_ID
from .picto_inventory import owned_pictos, DEFINITION_TABLE, one
from .catalog import capture_matching
from .picto_restore import field
from .values import read_values, read_values_many, read_table_rows
from .picto_details import COST, PASSIVE_TABLE


class Baselines:
    def __init__(self, path):
        self.store=SettingsStore(path)
        self.data=self.store.get(MOD_ID).get('options',{})
        if self.data and self.data.get('schema') not in (1,2):raise ValueError('Unsupported Picto baseline schema')

    def capture(self, scope, catalog):
        # The game PID guard persists across controller and mod reloads.
        if self.data.get('pid')==scope.pid:return self.data.get('profiles',{})
        # Baselines never grant inventory: the grant/static-asset table and its
        # hundreds of asset references are unnecessary here. Read definition
        # IDs and the authoritative owned map directly, retaining all 342 rows.
        catalog=catalog.with_observations(capture_matching(scope.pid,names=('DT_PictosDefinitions',)))
        definitions=read_table_rows(catalog,one(o for o in catalog.objects if catalog.path_name(o)==DEFINITION_TABLE))
        catalog,owned=owned_pictos(scope.pid,catalog=catalog)
        gi=one(o for o in catalog.select('BP_jRPG_GI_Custom_C') if not o.object_flags&0x30)
        table=next(o for o in catalog.objects if catalog.path_name(o)==PASSIVE_TABLE)
        passives=read_table_rows(catalog,table)
        progress=field(read_values_many(catalog,(gi,),fields=('SharedPassiveEffectProgression',))[gi.index],'SharedPassiveEffectProgression').items
        values=read_values_many(catalog,[v[0] for v in owned.values()],fields=('BaseStatsMultipliers','CurrentStats'))
        profiles={}
        steps={}
        for key in definitions:
            profile={'owned':key in owned}
            if key in owned:
                item,level=owned[key]
                current=field(values[item.index],'BaseStatsMultipliers').items
                profile.update(level=level,multipliers={str(stat):current.get(stat,0.) for stat in (1,6,8,9)},
                               multiplier_keys=sorted(current),stat_keys=sorted(field(values[item.index],'CurrentStats').items))
            if key in passives:profile['cost']=field(passives[key],COST)
            row=progress.get(key)
            profile['mastered']=row.fields['IsLearnt_9_2561000E49D90653437DE9A45BE2A86D'] if row else False
            steps[key]=row.fields['LearntSteps_6_A14D681549E830249C77BD95F2B4CF3F'] if row else 0
            profiles[key]=profile
        document={'schema':2,'pid':scope.pid,'captured_utc':datetime.now(timezone.utc).isoformat(),
                  'source':'before SDK Picto startup restoration','profiles':profiles,'mastery_steps':steps}
        self.store.save(MOD_ID,{'options':document})
        self.data=document
        return profiles

    def targets(self,pid,identities):
        if self.data.get('pid')!=pid or not self.data.get('profiles'):
            raise RuntimeError('No pre-edit baseline: restart game first')
        missing=set(identities)-self.data['profiles'].keys()
        if missing:raise RuntimeError('No baseline for selected Picto')
        if any(self.data['profiles'][key].get('owned') and 'stat_keys' not in self.data['profiles'][key] for key in identities):
            raise RuntimeError('Exact stat baseline unavailable: restart game first')
        import copy
        return {key:{**copy.deepcopy(self.data['profiles'][key]),'mastery_steps':self.data['mastery_steps'][key]} for key in identities}
