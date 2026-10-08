# FUNCTION_INVOCATION

Updated: 2026-10-08

Evidence labels: OBSERVED = directly seen; PROVEN = reproduced with a stated test; INFERRED = supported interpretation; HYPOTHESIS = untested; STALE/DISPROVEN = superseded or contradicted.

## Status

Dispatch and function metadata are identified and corroborated against live objects. No game function has been invoked by our code yet.

## Evidence discipline

Record source or command, artifact path, game fingerprint, confidence, and reproduction steps with each finding. Reference SDK behavior is not target-game evidence.

## Dispatch evidence, build23765773 / SHA256218a2478...39618

OBSERVED: ScriptCore.cpp xref leads to141391a40, which resolves a name through14127bb80 using object.class+0x10. Lookup traverses class+0x40 parents and locked name/function maps. Independent callers1420ac400 and1429507a0 pass the resolved function and a parameter buffer to object.vtable+0x268.

PROVEN by read-only live observation: Default__Object dispatch slot contains RVA0x1393330; Default__Actor and Default__HUD contain RVA0x332bb90. Ghidra14332bb90 delegates to141393330 after world/default-object and engine-state checks. These are research identities, not original recovered symbols.

OBSERVED in141393330: function flags+0xb0; parameter buffer length ushort+0xb6; return offset ushort+0xb8, with0xffff meaning absent. It constructs a frame, copies parameters, initializes locals, calls141280940 and handles copyback/destruction. 141280940 calls the entry pointer at function+0xd8, temporarily storing the function in frame+0x90. Do not replace this with an arbitrary native thunk call.

PROVEN: Python reflect_function resolves owner-qualified live functions. Actor.IsActorBeingDestroyed: index10700, flags0x54020401, params_size1, return_offset0, entryRVA0x333be80. Actor.GetActorEnableCollision: index10654, flags0x54020403, size1, return0, entryRVA0x3339a70. Each has one ReturnValue BoolProperty, flags0x18001040000780, encoding0xff010001. Actor.K2_GetActorLocation has24-byte StructProperty return, not a guessed12-byte vector.

OBSERVED: Ghidra initially lacked boundaries for the boolean entry pointers. Creating functions at those independently observed pointers produced31/32-byte thunks. 14333be80 advances frame.code when nonnull and returns object byte+0x5d bit0. 143339a70 returns object byte+0x5c bit7. Neither modifies the object. Evidence: mcp-harmless-thunks-created.json. They are candidates for the first harmless invocation, not evidence of execution.

## Thread identity and next experiment

OBSERVED:141082dd0 returns the literal GameThread when a supplied OS thread ID equals DWORD149272d30. Independent stack-report routine14107b770 labels that same ID GameThread. PROVEN live: RVA0x9272d30 holds27548; Windows OpenThread/GetProcessIdOfThread confirms it belongs to game PID25988. All values are tied to the executable fingerprint, not assumed across builds or restarts.

NEXT: test a removable same-thread native scheduling bridge in an independent message-pump fixture; verify callback thread identity, result transfer, timeout handling and removal before installing it in the game. Then prove the Python -> bridge -> reflected dispatcher -> boolean return chain. In-process lifecycle and GC/reentrancy remain unproven. No injection or invocation has occurred yet.

Reproduce read-only metadata with scripts/verify_live_functions.py. Evidence: mcp-scriptcore-functions.json, mcp-function-lookup.json, mcp-dispatch-callers.json, live-dispatch-candidates.json, mcp-dispatcher-functions.json, mcp-function-invoke.json, mcp-game-thread-functions.json, python-live-functions.json.
