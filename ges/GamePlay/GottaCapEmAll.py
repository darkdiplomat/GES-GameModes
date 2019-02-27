# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Gotta Cap'em All
# Version 1.0.0 BETA
# Author: DarkDiplomat
# Based on an Idea from ShempHamward
#
# Synopsis: You have to kill every player at least once to win.
# The first player to kill every other player wins the round.
# You only score points for unique kills.
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

from . import GEScenario
from .Utils import GetPlayers
from .Utils.GEPlayerTracker import GEPlayerTracker
from .Utils.GEWarmUp import GEWarmUp
import GEEntity, GEPlayer, GEUtil, GEWeapon, GEMPGameRules as GERules, GEGlobal as Glb

USING_API = Glb.API_VERSION_1_2_0


class GottaCapEmAll(GEScenario):
    PLAYER_WAIT_TICKER = 0  # redisplay waiting for players timer

    def __init__(self):
        super(GottaCapEmAll, self).__init__()

        self.pltracker = GEPlayerTracker(self)
        self.warmupTimer = GEWarmUp(self)  # init warm up timer
        self.waitingForPlayers = True

    def GetPrintName(self):
        return "Gotta Cap'em All (BETA)"

    def GetGameDescription(self):
        return "Gotta Cap'em All (BETA)"

    def GetTeamPlay(self):
        return Glb.TEAMPLAY_NONE  # Maybe in the future

    def GetScenarioHelp(self, help_obj):
        help_obj.SetDescription("You have to kill every other player once to win!\n"
                                "The first player to kill every other player wins the round.\n"
                                "You only score points for unique kills.")

    def OnRoundBegin(self):
        GERules.ResetAllPlayerDeaths()
        GERules.ResetAllPlayersScores()
        GERules.LockRound()
        for ply in GetPlayers():
            self.pltracker.SetValueAll(ply.GetUID(), False)

    def OnRoundEnd( self ):
        GERules.UnlockRound()

    def OnPlayerConnect(self, player):
        self.pltracker.SetValueAll(player.GetUID(), False)
        self.pltracker.SetValue(player, player.GetUID(), True)

    def OnPlayerDisconnect(self, player):
        self.pltracker.SetValueAll(player.GetUID(), True)

    def OnPlayerKilled(self, victim, killer, weapon):
        if self.waitingForPlayers or self.warmupTimer.IsInWarmup() or GERules.IsIntermission() or not victim:
            # Nothing to do but wait...
            return

        if not self.pltracker[killer].get(victim.GetUID(), False):
            # Capped a new one
            self.pltracker.SetValue(killer, victim.GetUID(), True)
            killer.AddRoundScore(1)

    def OnThink(self):
        # Check to see if we can get out of warmup
        if self.waitingForPlayers:
            if GERules.GetNumActivePlayers() > 1:
                self.waitingForPlayers = False
                if not self.warmupTimer.HadWarmup():
                    self.warmupTimer.StartWarmup(15, True)
                else:
                    GERules.EndRound(False)
            elif GEUtil.GetTime() > self.PLAYER_WAIT_TICKER:
                GEUtil.HudMessage(None, "#GES_GP_WAITING", -1, -1, GEUtil.Color(255, 255, 255, 255), 2.5, 1)
                self.PLAYER_WAIT_TICKER = GEUtil.GetTime() + 12.5
        elif not self.warmupTimer.IsInWarmup() or GERules.IsIntermission():
            # Check for winner only after a real round has started
            for ply in GetPlayers():
                if self.HasWon(ply):
                    GERules.EndRound()

    def HasWon(self, killer):
        for ply in GetPlayers():
            if ply.GetUID() == killer.GetUID():
                continue
            if not self.pltracker[killer][ply.GetUID()]:
                return False
        return True
