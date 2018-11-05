# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Pop-A-Cap
# Beta v1.0
# By: DarkDiplomat
#
# Based on the Perfect Dark Game Mode
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

from . import GEScenario
from .Utils import GetPlayers
from .Utils.GEWarmUp import GEWarmUp
from .Utils.GETimer import TimerTracker, Timer
import random
import GEEntity, GEPlayer, GEUtil, GEWeapon, GEMPGameRules as GERules, GEGlobal as Glb

VICTIM_ALERT_COLOR = GEUtil.Color(139, 0, 0, 255)
SURVIVE_COLOR = GEUtil.Color(0, 170, 0, 200)
GET_VICTIM_COLOR = GEUtil.Color(170, 170, 170, 144)
CAP_OBJECTIVE = GEUtil.Color(128, 128, 0, 255)
USING_API = Glb.API_VERSION_1_2_0


class PopACap(GEScenario):
    VICTIM = None

    @staticmethod
    def caplived(timer, type_):
        if type_ == Timer.UPDATE_FINISH:
            survivor = GEPlayer.ToMPPlayer(PopACap.VICTIM)
            if survivor is None:
                return
            GEUtil.HudMessage(survivor, "Have a point for living!", -1, 0.75, SURVIVE_COLOR, 5.0)
            survivor.AddRoundScore(1)

    def __init__(self):
        super(PopACap, self).__init__()

        self.warmupTimer = GEWarmUp(self)  # init warm up timer
        self.timerTracker = TimerTracker(self)  # init timer tracker
        self.capSurviveTimer = self.timerTracker.CreateTimer("capSurvive")
        self.capSurviveTimer.SetUpdateCallback(self.caplived)
        self.waitingForPlayers = True  # need more than 1 player for this mode

    def GetPrintName(self):
        return "Pop-A-Cap"

    def GetGameDescription(self):
        return "Pop-A-Cap"

    def GetTeamPlay(self):
        return Glb.TEAMPLAY_NONE  # I don't think TeamPlay will work well here

    def GetScenarioHelp(self, help_obj):
        help_obj.SetDescription("")

    def OnLoadGamePlay(self):
        # Pre-cache the popped a cap sound
        GEUtil.PrecacheSound("GEGamePlay.Token_Grab")

        # Make sure we don't start out in wait time or have a warmup if we changed gameplay mid-match
        if GERules.GetNumActivePlayers() > 1:
            self.waitingForPlayers = False
            self.warmupTimer.StartWarmup(0)

    def OnUnloadGamePlay(self):
        super(PopACap, self).OnUnloadGamePlay()
        self.warmupTimer.Reset()
        self.warmupTimer = None
        self.timerTracker = None
        self.capSurviveTimer.Stop()
        self.capSurviveTimer = None
        PopACap.VICTIM = None

    def OnRoundBegin(self):
        GEScenario.OnRoundBegin(self)
        GERules.ResetAllPlayerDeaths()
        GERules.ResetAllPlayersScores()

        if GERules.GetNumActivePlayers() <= 1:
            self.waitingForPlayers = True

        if self.warmupTimer.HadWarmup() and not self.waitingForPlayers:
            self.choosenewvictim()

    def OnRoundEnd(self):
        # Prepare for Reset
        self.capSurviveTimer.Stop()
        GERules.GetRadar().DropRadarContact(GEPlayer.ToMPPlayer(self.VICTIM))
        PopACap.VICTIM = None

    def OnThink(self):
        # Check to see if we can get out of warmup
        if self.waitingForPlayers and GERules.GetNumActivePlayers() > 1:
            self.waitingForPlayers = False
            if not self.warmupTimer.HadWarmup():
                self.warmupTimer.StartWarmup(15, True)
            else:
                GEUtil.HudMessage(None, "#GES_GP_GETREADY", -1, -1, GEUtil.Color(255, 255, 255, 255), 2.5)
                GERules.EndRound(False)
        # Did players leave?
        if not self.waitingForPlayers and GERules.GetNumActivePlayers() <= 1:
            GERules.EndRound()

    def OnPlayerKilled(self, victim, killer, weapon):
        if not victim:
            return

        # Let the base scenario behavior handle scoring when the mode isn't in effect
        if self.waitingForPlayers or self.warmupTimer.IsInWarmup() or GERules.IsIntermission():
            GEScenario.OnPlayerKilled(self, victim, killer, weapon)
            return

        if victim.GetUID() == self.VICTIM and killer is not None:
            self.capSurviveTimer.Stop()  # Victim didn't survive
            GEUtil.HudMessage(killer, "Well Done! You Popped a Cap!", -1, 0.73, SURVIVE_COLOR, 5.0, 5)
            GEUtil.HudMessage(killer, "Have 2 points...", -1, 0.75, SURVIVE_COLOR, 5.0, 6)
            killer.AddRoundScore(2)
            GERules.GetRadar().DropRadarContact(victim)
            victim.SetScoreBoardColor(Glb.SB_COLOR_WHITE)
            self.choosenewvictim()

    def OnPlayerDisconnect(self, player):
        if player.GetUID() == PopACap.VICTIM:
            # victim left, reassign
            self.capSurviveTimer.Stop()
            self.choosenewvictim()

    def CanPlayerChangeTeam(self, player, oldTeam, newTeam, wasforced):
        if newTeam == Glb.TEAM_SPECTATOR and player.GetUID() == PopACap.VICTIM:
            # victim wants to leave, reassign
            self.capSurviveTimer.Stop()
            self.choosenewvictim()
        return True

    def choosenewvictim(self):
        # Check to see if more than one player is around
        iplayers = []

        for player in GetPlayers():
            if not player.IsDead() and player.IsInRound():
                iplayers.append(player)

        numplayers = len(iplayers)
        if numplayers <= 1:
            # not enough players to continue
            GERules.EndRound()
        else:
            i = random.randint(1, numplayers) - 1
            newvictim = iplayers[i]
            iplayers.remove(newvictim)
            PopACap.VICTIM = newvictim.GetUID()
            GEUtil.HudMessage(newvictim, "You are the victim", -1, 0.65, VICTIM_ALERT_COLOR, 5.0, 7)
            for player in iplayers:
                GEUtil.HudMessage(player, "Get %s" % newvictim.GetCleanPlayerName(),
                                  -1, 0.65, GET_VICTIM_COLOR, 5.0, 7)
            self.capSurviveTimer.Start(30, True)  # TODO: Configurable timer?
            GERules.GetRadar().AddRadarContact(newvictim, Glb.RADAR_TYPE_PLAYER, True, "sprites/hud/radar/star")
            GERules.GetRadar().SetupObjective(newvictim, Glb.TEAM_NONE, "", "VICTIM", CAP_OBJECTIVE, 300)
            newvictim.SetScoreBoardColor(Glb.SB_COLOR_GOLD)
