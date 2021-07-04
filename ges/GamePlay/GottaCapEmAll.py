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
import re

USING_API = Glb.API_VERSION_1_2_0


class GottaCapEmAll(GEScenario):
    PLAYER_WAIT_TICKER = 0  # redisplay waiting for players timer
    FIRST_KILL = False

    #  Character name dictionary. This is for the names in the target hud text
    CHARACTER_DICT = {
        '006_mi6': 'Trevelyan',
        'samedi': 'Samedi',
        'bond': 'Bond',
        'boris': 'Boris',
        'female_scientist': 'Scientist',
        'guard': 'Solider',
        'infantry': 'Infantry',
        'jaws': 'Jaws',
        'Mayday': 'Mayday',
        'Mishkin': 'Mishkin',
        'oddjob': 'Oddjob',
        'ourumov': 'Ourumov',
        'valentin': 'Valentin'
    }

    def __init__(self):
        super(GottaCapEmAll, self).__init__()

        self.pltracker = GEPlayerTracker(self)
        self.warmupTimer = GEWarmUp(self)  # init warm up timer
        self.waitingForPlayers = True
        self.targetTracker = {}

    def GetPrintName(self):
        return "Gotta Cap'em All (BETA)"

    def GetGameDescription(self):
        return "Gotta Cap'em All (BETA)"

    def GetTeamPlay(self):
        return Glb.TEAMPLAY_NONE  # Pending Support

    def GetScenarioHelp(self, help_obj):
        help_obj.SetDescription("You have to kill every other player once to win!\n"
                                "The first player to kill every other player wins the round.\n"
                                "You only score points for unique kills. Use !voodoo to see Targets.")

    def OnLoadGamePlay(self):
        GERules.AllowRoundTimer(False)

    def OnUnloadGamePlay(self):
        # Clean up
        self.targetTracker.clear()
        self.pltracker = None
        self.warmupTimer = None

    def OnPlayerSay(self, player, text):
        text = text.lower()

        # Commands
        if text == "!voodoo":
            self.showTargets(player)
            return True

    def OnRoundBegin(self):
        super(GottaCapEmAll, self).OnRoundBegin()
        if self.warmupTimer.IsInWarmup() and not self.warmupTimer.HadWarmup():
            return

        self.FIRST_KILL = False
        GERules.LockRound()

        initPly = []
        for ply in GetPlayers():
            if ply.IsInRound():
                self.pltracker.SetValueAll(ply.GetUID(), False)
                initPly.append(ply)
                self.targetTracker.setdefault(ply.GetUID(), "")

        for ply in initPly:
            self.showTargets(ply)

    def OnRoundEnd(self):
        self.targetTracker.clear()
        for ply in GetPlayers():  # Clear the target list
            self.pltracker.SetValueAll(ply.GetUID(), True)
        GERules.UnlockRound()

    def OnPlayerConnect(self, player):
        self.pltracker.SetValueAll(player.GetUID(), False)
        self.pltracker.SetValue(player, player.GetUID(), True)

    def OnPlayerDisconnect(self, player):
        self.pltracker.SetValueAll(player.GetUID(), True)

    def CanPlayerChangeTeam(self, player, oldteam, newteam, wasforced):
        if newteam == Glb.TEAM_SPECTATOR:
            self.pltracker.SetValueAll(player.GetUID(), True)
        return True

    def OnPlayerKilled(self, victim, killer, weapon):
        if not victim or GERules.GetNumInRoundPlayers() < 2:  # don't execute logic if there aren't enough players for it.
            return

        self.FIRST_KILL = True
        if not self.pltracker[killer].get(victim.GetUID(), False):
            # Capped a new one
            self.pltracker.SetValue(killer, victim.GetUID(), True)
            killer.AddRoundScore(1)
            self.showTargets(killer)

        if self.FIRST_KILL:
            # Check for winner only after a real round has started
            for ply in GetPlayers():
                if self.hasWon(ply):
                    GERules.EndRound()

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

    def hasWon(self, killer):
        for ply in GetPlayers():
            if ply.GetUID() == killer.GetUID() or ply.GetTeamNumber() == Glb.TEAM_SPECTATOR:
                continue

            if not self.pltracker[killer][ply.GetUID()]:
                return False
        return True

    def scrub(self, msg):
        return re.sub('\^[A-Za-z0-9]', '', msg)

    def nameGen(self, player):
        return self.scrub(player.GetCleanPlayerName()) +\
               " (" + str(self.CHARACTER_DICT.get(player.GetPlayerModel())) + ")"

    def targetsGen(self, player):
        targets = ""
        for ply in GetPlayers():
            if player == ply or not ply.IsInRound():
                continue  # remove self and spectators from targets
            if not self.pltracker[player][ply.GetUID()]:
                targets += self.nameGen(ply)+"\n"
        targets += "\n"  # extra new line to extend the name list box
        return targets

    def showTargets(self, player):
        GEUtil.PopupMessage(player, 'Targets Remaining:', self.targetsGen(player))  # Show list after each kill
