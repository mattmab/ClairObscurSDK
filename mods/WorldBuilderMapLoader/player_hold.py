"""Exact-pawn movement hold while an assigned map restores its collision."""
import logging
from expedition33._reader import ReadBatch
from expedition33.catalog import capture_matching
from expedition33.values import read_values
from expedition33.map_runtime import context


class PlayerHold:
    def __init__(self, session, expected):
        self.session=session;self.expected=expected;self.planner=None
        self.held=False;self.closed=False

    def acquire(self):
        with ReadBatch(self.session.pid):
            if context(self.session)!=self.expected:
                raise RuntimeError('Map restoration pawn changed before movement hold')
            c=capture_matching(self.session.pid,names=('CharMoveComp','SetMovementMode','EMovementMode'))
            pawn=self.expected['pawn']
            moves=[o for o in c.objects if o.name=='CharMoveComp' and o.outer_index==pawn[0]]
            if len(moves)!=1:raise RuntimeError('Map restoration movement component unavailable')
            movement=moves[0]
            owner=c.find_class('CharacterMovementComponent').index
            values=read_values(c,movement).values
            mode=values.get((owner,'MovementMode'));custom=values.get((owner,'CustomMovementMode'))
            if mode==0:
                from expedition33.ui_shell_proof import UiProofPending
                raise UiProofPending('Waiting for the game to enable pawn movement')
            if type(mode) is not int or not 1<=mode<=6 or type(custom) is not int:
                raise RuntimeError('Map restoration movement mode unavailable')
            self.planner=self.session.invocation_planner(catalog=c,selected_results=True)
            fn=c.find_path('/Script/Engine.CharacterMovementComponent:SetMovementMode')
            self.restore=self.planner.prepare(movement,fn,NewMovementMode=mode,NewCustomMode=custom)
            stop=self.planner.prepare(movement,fn,NewMovementMode=0,NewCustomMode=0)
            # MOVE_None clears velocity as well as disabling gravity/movement.
            # Native invocation validates the exact component and schema.
            current=context(self.session)
            if current is None:
                self.discard();raise RuntimeError('Map restoration pawn observation pending')
            if current!=self.expected:
                self.discard();raise RuntimeError('Map restoration pawn changed during preparation')
            with stop.invoke():pass
            self.held=True
            logging.getLogger('expedition33.worldbuilder_map_loader').info('Player movement held for map collision restoration')
        return self

    def close(self):
        if self.closed:return
        if self.held:
            # Never restore movement on a different visit or replacement pawn.
            current=context(self.session)
            if current is None:
                raise RuntimeError('Map restoration movement release awaits a fresh pawn observation')
            if current!=self.expected:
                self.discard();return
            with self.restore.invoke():pass
            self.held=False
            logging.getLogger('expedition33.worldbuilder_map_loader').info('Player movement released after map collision restoration')
        self.discard()

    def discard(self):
        # Old-world retirement revokes plans without dispatching old callbacks.
        if self.planner is not None:self.planner.close();self.planner=None
        self.held=False;self.closed=True
