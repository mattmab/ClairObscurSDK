# Target button events and Python action callbacks

Build: Steam23765773, executable SHA256
218a2478aad5b3a1674b5d7097ec1ac4f994abb95466f9da1407fcd39d639618.
Investigation uses the live independent catalog and this executable's Ghidra
database. No button callback hook or delegate binding has been installed.

## Live reflected contract

Button has MulticastInlineDelegateProperty fields OnClicked at0x5a8,
OnPressed0x5b8, OnReleased0x5c8, OnHovered0x5d8 and OnUnhovered0x5e8,
each16 bytes. Their referenced signature UFunctions have zero parameters,
no return, flags0x130000 and shared entry RVA13937a0. That entry is a shared
script-dispatch path, not an independently callable click implementation.
Button's own reflected functions are IsPressed and setters for background/color,
click/press/touch methods and style. IsPressed is a state query, not a click event.

The exact live Button class constructor is RVA303ba80; its CDO vtable is737e700.
The constructor initializes the five delegate fields and the cached Slate shared
reference at5f8/600. IsPressed3095160 reads that cached widget and two state bits;
polling it would not establish delivery of every completed click.

Evidence: `button-events-live.json`, `button-thunks.json`,
`button-construction.json`. The independently verified IsPressed entry was
defined in Ghidra and the program saved (`button-analysis-save.json`).

## Concrete native path

The Button vtable slot300 points to RebuildWidget-like routine307c280. It creates
an SButton and five weak-UObject delegate instances, using the target weak
identity helper13c5c50. Click delegates have vtable7382098 and allocate3 units
of16 bytes. Their weak object identity is at18, member-function pointer at20 and
signed object adjustment at28. This is target-derived storage, not an assumed
portable layout or an exposed SDK ABI.

SButton construction16cc9a0 copies the five delegate arguments at220..260 into
live SButton delegate storage at2d8,2e8,2f8,308,318. Its click delegate execution
routine3059490 resolves the weak object, applies the stored adjustment and calls
the stored method with a result buffer. Click callback3089290 broadcasts the
UButton's OnClicked field through138eb60 and constructs a handled reply. The
press/release/hover/unhover callbacks are3089360/3089390/3089330/30893c0.

Broadcast138eb60 copies16-byte weak-object/name entries, resolves each receiver's
function and invokes its ProcessEvent slot268; stale bindings can be removed.
This is not a call through the signature UFunction's shared entry. A signature
hook or the existing fixed getter observer therefore does not supply this event.

Delegate clone3054a90 copies the weak identity, function pointer and adjustment.
Copy helper1122400 invokes that clone operation before replacing old storage.
Consequently, patching one delegate pointer and later restoring it is not by
itself proof that every copied callback was removed. Callback modules/storage
must outlive all possible calls, and unregistration needs a verified ownership
contract. The button releases its cached Slate shared reference in3080b90.

Evidence: `button-vtable.json`, `button-virtuals.json`,
`button-event-callbacks.json`, `button-delegate-broadcast.json`,
`button-delegate-vtable.json`, `button-delegate-execution.json`.

## Implementation implications and remaining gates

Use the actual event path for reusable mod actions; do not infer clicks from
IsPressed polling or execute signature functions as commands. Two candidates
need further ownership/ABI investigation: a real script-delegate receiver with
an SDK-owned reflected callback, or a narrowly owned Slate delegate adapter that
preserves the original reply and accounts for cloning. Neither is implemented.

Whichever path is verified must queue copied owner/action tokens on the game
thread, return immediately through the original engine path, and run Python
callbacks only in the persistent external controller's poll. It must revoke
delivery before menu detach/lease release, discard stale session registrations,
handle late or cloned callbacks safely, and bound the queue with explicit
overflow reporting. Required live tests include real mouse/keyboard activation,
one delivery per action, original reply preservation, callback exceptions,
unregistration, controller loss and relaunch. Menu lifecycle evidence alone
does not establish those capabilities.

## Live constructed-button corroboration

The first read-only pass found no constructed exact-base Button suitable for
corroboration. The bounded `inspect_button_events.py --owned-specimen` run then
created the previously verified disabled Button/tree and inspected it after
Slate creation. Button index96514/serial19372 had a cached SButton with vtable
6e6e7e0 and reference-controller vtable6e65f20. Its click delegate at SButton+2d8
had vtable7382098,3 allocation units, weak index/serial matching the Button,
callback3089290 and zero object adjustment. Repeated pointer/data reads agreed.
The trailing32-bit delegate-container word was observed as zero; its meaning is
unverified (the initial artifact labels it `capacity_observation`).

The specimen performed no click, callback replacement or delegate binding.
It removed the owned tree and restored the exact strong-holder baseline.
Evidence: `button-events-live.json`, `button-event-specimen-live.json`,
`button-event-specimen-run.log`. These corroborate live storage and identity,
not a validated event hook, callback ABI under execution or teardown adapter.
