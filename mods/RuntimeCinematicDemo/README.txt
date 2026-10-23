RuntimeCinematicDemo - experimental isolated native candidate

Twenty-second scene: Lune and Maelle loop notify-free attack animations
around a temporary Petank mesh while a temporary camera circles them.
Native Niagara systems provide Lune's attached trail and electric impacts,
Maelle's attached sword effect and petal impact bursts. The target recoils
and settles after each of the nine authored hits. Recoil is a bounded actor
motion, not damage, combat AI, or the game's reaction Blueprint.
Nine short UI-routed whooshes accompany the repeated attacks, at 35% gain.
Lune kick cues repeat with her 3.3667-second clip; additional cues accompany
Maelle's longer attack sequence. These are authored timing cues, not notifies.
This is visual choreography; no damage, AI combat, dialogue or lip sync.

Requires the cinematic candidate backend (protocol 2); the normal installed
SDK backend refuses this mod before allocation. Do not run two controllers.
Stop the normal SDK with `mods shutdown` before using the isolated runner.

From the development checkout, run with its bundled Python:
scripts/run_runtime_cinematic_demo.py --sdk-root <installed SDK directory>
  --pid <current game PID> --candidate-version 12 --mode play --output <report.json>
Use --mode interrupt for the explicit early-stop cleanup check.
When loaded in the candidate controller, console actions are:
  cine.demo start
  cine.demo stop
  cine.demo status
The runner automatically starts, observes and closes the scene/controller.

Actors, Niagara components, camera and audio are private temporary resources.
Impact effects are destroyed after 0.9 seconds; attached effects are destroyed
when the scene ends or is interrupted. Effect components are never pooled.
The previous view target and balanced move/look input locks are restored.
Native map/controller/pawn changes request cleanup. Actual map travel and
abrupt controller termination have not been live-tested for this demo.

Lune hair reproduces the actual game-assembled canonical hair setup:
Face component / Head socket; location (17.65,2.83,0) cm;
pitch/yaw/roll (-90,0,0) degrees; uniform scale 1.055.
Maelle uses the independently verified leader-pose setup.
Her sword uses the live weapon_r attachment and its native grip rotation.
No general reflection codec changes, cooked asset edits or Sequencer authoring.
