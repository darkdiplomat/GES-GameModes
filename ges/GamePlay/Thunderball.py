# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Thunderball
# Alpha 1.0
# By: DarkDiplomat
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

from . import GEScenario
from .Utils import _
from .Utils.GEPlayerTracker import GEPlayerTracker
from .Utils.GEWarmUp import GEWarmUp
from .Utils.GETimer import TimerTracker, Timer
import random
import GEEntity, GEPlayer, GEUtil, GEWeapon, GEMPGameRules as GERules, GEGlobal as Glb

USING_API = Glb.API_VERSION_1_2_0

TR_ELIMINATED = "eliminated"
TR_SPAWNED = "spawned"
ALERT_COLOR = GEUtil.Color(139, 0, 0, 230)
RELIEF_COLOR = GEUtil.Color(170, 170, 170, 230)


class Thunderball(GEScenario):
    THUNDERBALL_OWNER = None
    LAST_AGGRESSOR = None
    PLTRACKER = None
    ASSIGNED_ONCE = False

    @staticmethod
    def detonator(timer, type_):
        if type_ == Timer.UPDATE_FINISH:
            if not GERules.IsRoundLocked():
                GERules.LockRound()
            if Thunderball.THUNDERBALL_OWNER is not None:  # this shouldn't happen but just in case
                player = GEPlayer.ToMPPlayer(Thunderball.THUNDERBALL_OWNER)
                Thunderball.THUNDERBALL_OWNER = None  # This will be reset later
                Thunderball.PLTRACKER[player][TR_ELIMINATED] = True
                if not player.IsDead():
                    # explode, force
                    player.CommitSuicide(True, True)
                player.SetScoreBoardColor(Glb.SB_COLOR_ELIMINATED)
                GEUtil.PostDeathMessage(_("#GES_GP_YOLT_ELIMINATED", player.GetCleanPlayerName()))
                GEUtil.PopupMessage(player, "#GES_GPH_ELIMINATED_TITLE", "#GES_GPH_ELIMINATED")

    def __init__(self):
        super(Thunderball, self).__init__()

        self.warmupTimer = GEWarmUp(self)
        self.timeTracker = TimerTracker(self)
        self.thunderballTimer = self.timeTracker.CreateTimer("thunderballTimer")
        self.thunderballTimer.SetUpdateCallback(self.detonator)
        self.waitingForPlayers = True
        Thunderball.PLTRACKER = GEPlayerTracker(self)

    def GetPrintName(self):
        return "Thunderball"

    def GetGameDescription(self):
        return "Thunderball"

    def GetTeamPlay(self):
        return Glb.TEAMPLAY_NONE

    def GetScenarioHelp(self, help_obj):
        help_obj.SetDescription("The Thunderball is set to explode every 20 seconds! Pass the Thunderball off by"
                                "killing another player before it explodes in your pocket! If you have the"
                                "Thunderball you get increased speed and take reduced damage to help you pass it off. "
                                "Scoring is like regular death match. Be the last man standing to gain the most points "
                                "(and a bonus doubling of your round points!)")

    def OnLoadGamePlay( self ):
        # Ensure our sounds are pre-cached
        GEUtil.PrecacheSound("GEGamePlay.Level_Down")
        GEUtil.PrecacheSound("GEGamePlay.Woosh")

        GERules.AllowRoundTimer(False)

        # Make sure we don't start out in wait time or have a warmup if we changed gameplay mid-match
        if GERules.GetNumActivePlayers() > 1:
            self.waitingForPlayers = False
            self.warmupTimer.StartWarmup(0)

    def OnUnloadGamePlay(self):
        super(Thunderball, self).OnUnloadGamePlay()
        self.warmupTimer = None
        Thunderball.PLTRACKER = None
        self.timeTracker = None
        self.thunderballTimer.Stop()
        self.thunderballTimer = None

    def OnPlayerConnect(self, player):
        Thunderball.PLTRACKER[player][TR_SPAWNED] = False
        Thunderball.PLTRACKER[player][TR_ELIMINATED] = False
        if GERules.IsRoundLocked():
            Thunderball.PLTRACKER[player][TR_ELIMINATED] = True

    def OnPlayerTeamChange(self, player, oldTeam, newTeam):
        if GERules.IsRoundLocked():
            if oldTeam == Glb.TEAM_SPECTATOR:
                GEUtil.PopupMessage(player, "#GES_GPH_CANTJOIN_TITLE", "#GES_GPH_CANTJOIN")
            else:
                GEUtil.PopupMessage(player, "#GES_GPH_ELIMINATED_TITLE", "#GES_GPH_ELIMINATED")

            # Changing teams will automatically eliminate you
            self.pltracker[player][self.TR_ELIMINATED] = True

    def OnPlayerSpawn(self, player):
        if player.GetTeamNumber() != Glb.TEAM_SPECTATOR:
            Thunderball.PLTRACKER[player][TR_SPAWNED] = True
        if not self.waitingForPlayers and not self.warmupTimer.IsInWarmup() and not GERules.IsIntermission():
            if player.GetUID() == Thunderball.THUNDERBALL_OWNER:
                # initialize or restart the time once the owner is spawned in
                if self.thunderballTimer.state == Timer.STATE_PAUSE:
                    self.thunderballTimer.Start()
                else:
                    self.thunderballTimer.Start(20, True)
            if player.IsInitialSpawn() and not self.isinplay(player):
                GEUtil.PopupMessage(player, "#GES_GPH_CANTJOIN_TITLE", "#GES_GPH_CANTJOIN")

    def OnRoundBegin(self):
        GEScenario.OnRoundBegin(self)

        # Reset all player's statistics
        Thunderball.PLTRACKER.SetValueAll(TR_ELIMINATED, False)
        GERules.UnlockRound()
        GERules.ResetAllPlayerDeaths()
        GERules.ResetAllPlayersScores()

        if GERules.GetNumActivePlayers() <= 1:
            self.waitingForPlayers = True

        if self.warmupTimer.HadWarmup() and not self.waitingForPlayers:
            self.assignThunderball(self.chooserandom())

    def OnRoundEnd(self):
        # Prepare for Reset
        self.thunderballTimer.Stop()
        Thunderball.THUNDERBALL_OWNER = None
        Thunderball.LAST_AGGRESSOR = None
        Thunderball.ASSIGNED_ONCE = False
        GEUtil.RemoveHudProgressBar(None, 5)

    def OnThink(self):
        # Check to see if we can get out of warmup
        if self.waitingForPlayers and GERules.GetNumActivePlayers() > 1:
            self.waitingForPlayers = False
            Thunderball.PLTRACKER.SetValueAll(TR_SPAWNED, True)
            if not self.warmupTimer.HadWarmup():
                self.warmupTimer.StartWarmup(15, True)
            else:
                GERules.EndRound(False)

        if self.warmupTimer.HadWarmup() and not self.waitingForPlayers and Thunderball.ASSIGNED_ONCE:
            if Thunderball.THUNDERBALL_OWNER is None:
                if Thunderball.LAST_AGGRESSOR:  # Pass Thunderball to last Aggressor
                    aggressor = GEPlayer.ToMPPlayer(Thunderball.LAST_AGGRESSOR)
                    Thunderball.LAST_AGGRESSOR = None
                    if not Thunderball.PLTRACKER[aggressor][TR_ELIMINATED]:
                        self.assignThunderball(aggressor)
                    else:
                        self.assignThunderball(self.chooserandom())
                else:
                    self.assignThunderball(self.chooserandom())
            remain = 20 - int(self.thunderballTimer.GetCurrentTime())
            GEUtil.HudMessage(None, "Thunderball Detonation in %0.0f sec" % remain, -1, -2.75, ALERT_COLOR, 1.0, 5)
            if remain == 6:  # it takes a moment to play the sound
                owner = GEPlayer.ToMPPlayer(Thunderball.THUNDERBALL_OWNER)
                GEUtil.PlaySoundToPlayer(owner, "GEGamePlay.Level_Down")
            # Sometimes you have to give the timer a kick in the ass
            if Thunderball.THUNDERBALL_OWNER is not None:
                if self.thunderballTimer.state == Timer.STATE_STOP \
                        and not GEPlayer.ToMPPlayer(Thunderball.THUNDERBALL_OWNER).IsDead():
                    self.thunderballTimer.Start(20, True)
                elif self.thunderballTimer.state == Timer.STATE_PAUSE \
                        and not GEPlayer.ToMPPlayer(Thunderball.THUNDERBALL_OWNER).IsDead():
                    self.thunderballTimer.Start()

    def OnPlayerKilled(self, victim, killer, weapon):
        # Let the base scenario behavior handle scoring so we can just worry about the thunderball mechanics.
        GEScenario.OnPlayerKilled(self, victim, killer, weapon)

        if self.waitingForPlayers or self.warmupTimer.IsInWarmup() or GERules.IsIntermission() or not victim:
            return

        # Pass the thunderball off
        if killer.GetUID() == Thunderball.THUNDERBALL_OWNER:
            if self.isinplay(victim):  # Bots don't work well at getting removed
                self.thunderballTimer.Pause()  # Give them a chance to respawn
                self.assignThunderball(victim, killer)
                Thunderball.LAST_AGGRESSOR = killer.GetUID()
        if victim.GetUID() == Thunderball.THUNDERBALL_OWNER:
            self.thunderballTimer.Pause()  # Give them a chance to respawn
            if killer:
                Thunderball.LAST_AGGRESSOR = killer.GetUID()

    def CanPlayerRespawn(self, player):
        if GERules.IsRoundLocked() and Thunderball.PLTRACKER[player][TR_ELIMINATED]:
            return False
        return True

    def CalculateCustomDamage(self, victim, info, health, armor):
        if victim.GetUID() == Thunderball.THUNDERBALL_OWNER:
            killer = GEPlayer.ToMPPlayer(info.GetAttacker())
            # If being attacked reduce damage by 20% (i think)
            if killer is not None:
                armor -= armor * 0.2
                health -= health * 0.2
        return health, armor

    def chooserandom(self):
        # Check to see if more than one player is around
        iplayers = []

        for player in Thunderball.PLTRACKER.GetPlayers():
            if self.isinplay(player):
                iplayers.append(player)

        numplayers = len(iplayers)

        if numplayers == 0 and Thunderball.ASSIGNED_ONCE:
            # This shouldn't happen, but just in case it does we don't want to overflow the vector...
            GERules.EndRound()
            return None
        elif numplayers == 1 and Thunderball.ASSIGNED_ONCE:
            # Make last remaining player the winner, and double his or her score.
            GERules.SetPlayerWinner(iplayers[0])
            iplayers[0].IncrementScore(iplayers[0].GetScore())
            GERules.EndRound()
            return None
        else:
            i = random.randint(1, numplayers) - 1
            return iplayers[i]

    def assignThunderball(self, newowner, oldowner=None):
        if not newowner or not self.isinplay(newowner):
            return

        Thunderball.THUNDERBALL_OWNER = newowner.GetUID()
        GEUtil.PlaySoundToPlayer(newowner, "GEGamePlay.Woosh")
        GEUtil.HudMessage(newowner, "You have been given Thunderball!", -1, 0.75, ALERT_COLOR, 5.0)
        newowner.SetSpeedMultiplier(1.25)
        Thunderball.ASSIGNED_ONCE = True
        if oldowner is not None:
            GEUtil.PlaySoundToPlayer(oldowner, "GEGamePlay.Woosh")
            GEUtil.HudMessage(oldowner, "You have passed the Thunderball!", -1, 0.75, RELIEF_COLOR, 5.0)
            oldowner.SetSpeedMultiplier(1.0)
            Thunderball.LAST_AGGRESSOR = oldowner.GetUID()

    @staticmethod
    def isinplay(player):
        return player.GetTeamNumber() is not Glb.TEAM_SPECTATOR  and Thunderball.PLTRACKER[player][TR_SPAWNED] \
               and not Thunderball.PLTRACKER[player][TR_ELIMINATED]
