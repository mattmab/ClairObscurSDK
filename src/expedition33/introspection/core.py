"""Bounded reflected exploration. All entry points run on the game thread."""
from __future__ import annotations

from collections import deque
from itertools import islice
import math
import time


def bounded(value, default=100, maximum=1000):
    return max(1, min(int(default if value is None else value), maximum))


class Explorer:
    def __init__(self, sdk):
        self.sdk = sdk
        self.traces = {}
        self.snapshots = {}
        self.values = {}
        self.value_deadlines = {}

    def ref(self, obj):
        return {"$object": obj._path_name(), "class": obj.Class._path_name()}

    def resolve(self, spec):
        obj = self.sdk.find_object(spec.get("class", "Object"), spec["$object"])
        if obj is None:
            raise ValueError("Object no longer exists")
        return obj

    def encode(self, value, depth=2, budget=None):
        budget = [500] if budget is None else budget
        budget[0] -= 1
        if budget[0] < 0:
            return {"$truncated": "node budget"}
        if isinstance(value, float) and not math.isfinite(value):
            return {"$float": str(value)}
        if value is None or isinstance(value, (bool, int, float)):
            return value
        if isinstance(value, str):
            return value[:4096]
        handle_type = getattr(self.sdk.unreal, "FGameDataHandle", ())
        if isinstance(value, handle_type):
            return {"$gamedata": {"type": int(value._type_handle), "name": str(value._name)}}
        if isinstance(value, self.sdk.unreal.UObject):
            return self.ref(value)
        if depth <= 0:
            return {"$type": type(value).__name__, "$truncated": "depth"}
        if isinstance(value, self.sdk.unreal.WrappedStruct):
            result = {}
            for prop in islice(value._type._properties(), 64):
                name = str(prop.Name)
                try:
                    result[name] = self.encode(getattr(value, name), depth - 1, budget)
                except Exception as exc:
                    result[name] = {"$error": str(exc)[:500]}
            encoded = {"$struct": str(value._type.Name), "fields": result}
            if not result:
                encoded.update(opaque=True, text=str(value)[:500])
            return encoded
        if isinstance(value, dict):
            return {str(k): self.encode(v, depth - 1, budget) for k, v in islice(value.items(), 64)}
        if isinstance(value, (list, tuple, self.sdk.unreal.WrappedArray)):
            return {"items": [self.encode(v, depth - 1, budget) for v in islice(value, 64)],
                    "length": len(value), "truncated": len(value) > 64}
        return {"$type": type(value).__name__, "text": str(value)[:500]}

    def decode(self, value):
        if isinstance(value, dict):
            if '$value' in value:
                self.expire()
                spec=value['$value']
                if not isinstance(spec,dict) or not isinstance(spec.get('name'),str):
                    raise ValueError('$value requires a retained name and optional index path')
                result=self.values[spec['name']]
                path=spec.get('path',[])
                if not isinstance(path,list) or len(path)>8 or any(type(i) is not int or not 0<=i<1000 for i in path):
                    raise ValueError('$value path must contain up to 8 nonnegative array indexes')
                for index in path: result=result[index]
                # Keep the function-owned native value intact: opaque structs cannot
                # be reconstructed by reflected field copies (JunkId has no fields).
                return result
            if '$gbxdef' in value:
                spec=value['$gbxdef']
                if not isinstance(spec,dict) or set(spec)!={'name','type'} or any(not isinstance(v,str) or not v or len(v)>1024 or '\0' in v for v in spec.values()):
                    raise ValueError('$gbxdef requires bounded name and reflected struct type strings')
                struct=self.sdk.find_object('ScriptStruct',spec['type'])
                return self.sdk.unreal.FGbxDefPtr(spec['name'],struct)
            if "$gamedata" in value:
                spec = value["$gamedata"]
                if not isinstance(spec, dict) or set(spec) != {"type", "name"}:
                    raise ValueError("$gamedata requires type and name")
                type_id, name = spec["type"], spec["name"]
                if type(type_id) is not int or not 0 <= type_id <= 0xFFFFFFFF:
                    raise ValueError("Game-data type must be an unsigned 32-bit integer from schema")
                if not isinstance(name, str) or not name or len(name) > 1024 or "\0" in name:
                    raise ValueError("Game-data name must be 1-1024 non-NUL characters")
                return self.sdk.unreal.FGameDataHandle(type_id, name)
            if "$object" in value:
                return self.resolve(value)
            if "$struct" in value:
                return self.sdk.make_struct(value["$struct"], **{k: self.decode(v) for k, v in value.get("fields", {}).items()})
            raise ValueError("Use $object, $struct, $gamedata, $gbxdef or $value for typed arguments")
        if isinstance(value, list):
            return [self.decode(v) for v in value]
        return value

    def properties(self, cls):
        seen = set()
        for owner in islice(cls._superfields(), 64):
            for prop in islice(owner._properties(), 4096):
                name = str(prop.Name)
                if name not in seen:
                    seen.add(name)
                    yield prop

    def prop_schema(self, prop):
        flags = int(prop.PropertyFlags)
        result = {"name": str(prop.Name), "type": str(prop.Class.Name), "flags": flags,
                "array_dim": int(prop.ArrayDim), "offset": int(prop.Offset_Internal),
                "direction": "return" if flags & 0x400 else "ref" if flags & 0x8000000 else "out" if flags & 0x100 else "in"}
        if result["type"] == "GameDataHandleProperty":
            result["TypeHandle"] = int(prop.TypeHandle)
        # Expose referenced types so agents can follow structs, enums and containers.
        for attr in ("Struct", "Enum", "PropertyClass", "MetaClass", "Inner", "KeyProp", "ValueProp", "SignatureFunction"):
            try:
                value = getattr(prop, attr)
                if value is not None:
                    result[attr] = {"name": str(value.Name), "type": type(value).__name__}
                    if hasattr(value, "_path_name"):
                        result[attr]["path"] = value._path_name()
            except Exception:
                pass
        return result

    def functions(self, cls):
        seen = set()
        for owner in islice(cls._superfields(), 64):
            for field in islice(owner._fields(), 4096):
                name = str(field.Name)
                if isinstance(field, self.sdk.unreal.UFunction) and name not in seen:
                    seen.add(name)
                    yield field

    def inspect(self, request):
        obj = self.resolve(request["target"])
        offset = max(0, min(int(request.get("offset", 0)), 100000))
        limit = bounded(request.get("limit"))
        properties = self.properties(obj.Class)
        if "members" in request:
            members = request["members"]
            if not isinstance(members, list) or len(members) > 64 or not all(isinstance(n, str) for n in members):
                raise ValueError("members must be a list of up to 64 property names")
            properties = (p for p in properties if str(p.Name) in members)
        props = list(islice(properties, offset, offset + limit + 1))
        values = {}
        budget = [2000]
        for prop in props[:limit]:
            name = str(prop.Name)
            try:
                values[name] = self.encode(getattr(obj, name), bounded(request.get("depth"), 2, 4), budget)
            except Exception as exc:
                values[name] = {"$error": str(exc)[:500]}
        return {"target": self.ref(obj), "values": values,
                "next_offset": offset + limit if len(props) > limit else None}

    def stop(self, name):
        trace = self.traces[name]
        if trace["active"]:
            self.sdk.hooks.remove_hook(trace["path"], self.sdk.hooks.Type.POST, trace["hook"])
            trace["active"] = False

    def close(self):
        for name in list(self.traces):
            self.stop(name)
        self.traces.clear()
        self.snapshots.clear()
        self.values.clear()
        self.value_deadlines.clear()

    def expire(self):
        for name,deadline in list(self.value_deadlines.items()):
            if time.monotonic()>=deadline:
                self.values.pop(name,None)
                self.value_deadlines.pop(name,None)
        for name, trace in list(self.traces.items()):
            if trace["active"] and (time.monotonic() >= trace["deadline"] or trace["count"] >= trace["events"].maxlen):
                self.stop(name)

    def dispatch(self, r):
        op = r["op"]
        if op == "status":
            return {"sdk": str(getattr(self.sdk, "__version__", "unknown")),
                    "operations": ["status", "roots", "search", "schema", "inspect", "snapshot", "diff", "trace_start", "trace_read", "trace_stop", "invoke", "set", "gamedata", "release_value"],
                    "argument_types": ["$object", "$struct", "$gamedata", "$gbxdef", "$value"],
                    "retained_values": list(self.values),
                    "traces": {k: {"active": v["active"], "count": v["count"]} for k, v in self.traces.items()}}
        if op == 'release_value':
            self.values.pop(r['name'],None)
            self.value_deadlines.pop(r['name'],None)
            return {'retained_values':list(self.values)}
        if op == "roots":
            result = {}
            for cls in ("World", "GameInstance", "LocalPlayer", "PlayerController", "Pawn"):
                try:
                    result[cls] = [self.ref(o) for o in islice(self.sdk.find_all(cls, exact=False), 32)
                                   if not str(o.Name).startswith("Default__")]
                except Exception as exc:
                    result[cls] = {"$error": str(exc)}
            return result
        if op == "search":
            offset = max(0, min(int(r.get("offset", 0)), 1000000))
            scan = bounded(r.get("scan"), 5000, 20000)
            limit = bounded(r.get("limit"))
            query = str(r.get("query", "")).lower()
            rows, consumed = [], 0
            objects = iter(self.sdk.find_all(r.get("class", "Object"), exact=False))
            for obj in islice(objects, offset, offset + scan):
                consumed += 1
                ref = self.ref(obj)
                if query in ref["$object"].lower():
                    rows.append(ref)
                    if len(rows) >= limit:
                        break
            return {"objects": rows, "scanned": consumed,
                    "next_offset": offset + consumed if consumed == scan or len(rows) == limit else None,
                    "consistency": "Live iteration; objects may change between pages"}
        if op == "schema":
            cls = self.sdk.find_object("Struct", r["struct"]) if "struct" in r else self.sdk.find_class(r["class"])
            offset = max(0, int(r.get("offset", 0)))
            limit = bounded(r.get("limit"))
            props = list(islice(self.properties(cls), offset, offset + limit + 1))
            funcs = list(islice(self.functions(cls), offset, offset + limit + 1))
            return {"class": self.ref(cls), "parents": [str(c.Name) for c in islice(cls._superfields(), 64)],
                    "properties": [self.prop_schema(p) for p in props[:limit]],
                    "functions": [{"name": str(f.Name), "path": f._path_name(),
                                   "parameters": [self.prop_schema(p) for p in islice(f._properties(), 128) if int(p.PropertyFlags) & 0x80]}
                                  for f in funcs[:limit]],
                    "next_offset": offset + limit if max(len(props), len(funcs)) > limit else None}
        if op == "inspect":
            return self.inspect(r)
        if op == "gamedata":
            handle = self.decode({"$gamedata": r["handle"]})
            fields = r.get("fields", [])
            if not isinstance(fields, list) or len(fields) > 64 or not all(isinstance(n, str) and 0 < len(n) <= 128 and not n.startswith("_") for n in fields):
                raise ValueError("fields must contain up to 64 public game-data field names")
            values = {}
            for name in fields:
                try:
                    values[name] = self.encode(getattr(handle, name), bounded(r.get("depth"), 3, 6))
                except Exception as exc:
                    values[name] = {"$error": str(exc)[:500]}
            available = [n for n in dir(handle) if not n.startswith('_')]
            return {"handle": self.encode(handle), "values": values,
                    "available_fields": available[:64], "fields_truncated": len(available) > 64,
                    "note": "Construction alone does not prove that a named definition exists"}
        if op == "snapshot":
            name = str(r["name"])
            if name not in self.snapshots and len(self.snapshots) >= 32:
                raise ValueError("32 snapshot limit; reuse a name")
            self.snapshots[name] = self.inspect(r)
            return self.snapshots[name]
        if op == "diff":
            a = self.snapshots[r["before"]]["values"]
            b = self.snapshots[r["after"]]["values"]
            return {k: {"before": a.get(k), "after": b.get(k), "before_present": k in a, "after_present": k in b}
                    for k in sorted(a.keys() | b.keys()) if k not in a or k not in b or a[k] != b[k]}
        if op == "trace_start":
            name, path = str(r["name"]), str(r["function"])
            if name in self.traces or len(self.traces) >= 16:
                raise ValueError("Trace name exists or 16 trace limit reached; trace_stop with forget first")
            self.sdk.find_object("Function", path)
            cap = bounded(r.get("limit"), 100, 1000)
            trace = {"path": path, "hook": "BL4Introspection.trace." + name,
                     "active": True, "events": deque(maxlen=cap), "count": 0,
                     "deadline": time.monotonic() + bounded(r.get("seconds"), 30, 300)}
            def callback(obj, args, ret, fn):
                if trace["count"] >= cap or time.monotonic() >= trace["deadline"]:
                    return None
                try:
                    if r.get("target") and obj._path_name() != r["target"]["$object"]:
                        return None
                    trace["count"] += 1
                    trace["events"].append({"sequence": trace["count"], "time": time.time(),
                                            "target": self.ref(obj), "args": self.encode(args), "return": self.encode(ret)})
                except Exception as exc:
                    trace["events"].append({"error": str(exc)[:500]})
                return None
            self.sdk.hooks.add_hook(path, self.sdk.hooks.Type.POST, trace["hook"], callback)
            if not self.sdk.hooks.has_hook(path, self.sdk.hooks.Type.POST, trace["hook"]):
                raise RuntimeError("Trace hook registration failed")
            self.traces[name] = trace
            return {"name": name, "limit": cap, "seconds": bounded(r.get("seconds"), 30, 300)}
        if op in ("trace_read", "trace_stop"):
            name = r["name"]
            if op == "trace_stop":
                self.stop(name)
            trace = self.traces[name]
            result = {"active": trace["active"], "count": trace["count"], "events": list(trace["events"])}
            if op == "trace_stop" and r.get("forget"):
                del self.traces[name]
            return result
        if op in ("invoke", "set"):
            if r.get("allow_mutation") is not True:
                raise ValueError("Explicit allow_mutation:true required for set/invoke")
            obj = self.resolve(r["target"])
            name = r["member"]
            if op == "set":
                obj.Class._find_prop(name)
                before = self.encode(getattr(obj, name))
                setattr(obj, name, self.decode(r["value"]))
                return {"before": before, "after": self.encode(getattr(obj, name))}
            if not any(str(f.Name) == name for f in self.functions(obj.Class)):
                raise ValueError("Not a reflected function on this target")
            retain=r.get('retain')
            if retain is not None and (not isinstance(retain,str) or not 1<=len(retain)<=64 or (retain not in self.values and len(self.values)>=16)):
                raise ValueError('retain requires a 1-64 character name; maximum 16 retained results')
            result=getattr(obj, name)(**{k: self.decode(v) for k, v in r.get("args", {}).items()})
            if retain is not None:
                # Function return allocations are owned by SDK wrappers. Retain that
                # owner together with its opaque payload, not a reflected field copy.
                self.values[retain]=result
                self.value_deadlines[retain]=time.monotonic()+60.
            return self.encode(result, bounded(r.get("depth"), 4, 6))
        raise ValueError("Unknown operation: " + str(op))
