# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Pop-A-Cap
# v1.0
# By: DarkDiplomat
#
# Based on the concept of the original Perfect Dark Game Mode
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

from . import GEScenario
from .Utils import GetPlayers, clamp
from .Utils.GEWarmUp import GEWarmUp
from .Utils.GETimer import TimerTracker, Timer
import random
import GEEntity, GEPlayer, GEUtil, GEWeapon, GEMPGameRules as GERules, GEGlobal as Glb
import re

VICTIM_ALERT_COLOR = GEUtil.Color(250, 0, 0, 255)
SURVIVE_COLOR = GEUtil.Color(0, 150, 0, 200)
GET_VICTIM_COLOR = GEUtil.Color(170, 170, 170, 150)
CAP_OBJECTIVE = GEUtil.Color(128, 128, 0, 255)
USING_API = Glb.API_VERSION_1_2_0


class PopACap(GEScenario):
    VICTIM = None
    PRV_VIC1 = None
    PRV_VIC2 = None
    PLAYER_WAIT_TICKER = 0

    @staticmethod
    def caplived(timer, type_):
        if type_ == Timer.UPDATE_FINISH:
            survivor = GEPlayer.ToMPPlayer(PopACap.VICTIM)
            if survivor is None:
                return
            GEUtil.HudMessage(survivor, "Have a point for living!", -1, 0.75, SURVIVE_COLOR, 5.0, 1)
            survivor.AddRoundScore(1)

    def __init__(self):
        super(PopACap, self).__init__()

        self.warmupTimer = GEWarmUp(self)  # init warm up timer
        self.timerTracker = TimerTracker(self)  # init timer tracker
        self.capSurviveTimer = self.timerTracker.CreateTimer("capSurvive")
        self.capSurviveTimer.SetUpdateCallback(self.caplived)
        self.waitingForPlayers = True  # need more than 1 player for this mode

        # CVars
        self.reduceDamage = True
        self.surviveTime = 30
        self.victimScores = False
        self.classicMode = False

    def GetPrintName(self):
        return "Pop-A-Cap"

    def GetGameDescription(self):
        return "Pop-A-Cap"

    def GetTeamPlay(self):
        return Glb.TEAMPLAY_NONE  # I don't think TeamPlay will work well here

    def GetScenarioHelp(self, help_obj):
        help_obj.SetDescription("Track down the target and blast them to score points. "
                                "Selected randomly, one player will be selected as the 'victim' which everyone has to "
                                "try and track down. Whoever blasts the target will score 2 points, then another "
                                "player will become the target. If you're the target, you'll score 1 point if you "
                                "survive for a period of time.")

    def OnLoadGamePlay(self):
        # Pre-cache the popped a cap sound
        GEUtil.PrecacheSound("GEGamePlay.Token_Grab")  # sound for popping the cap
        GEUtil.PrecacheSound("GEGamePlay.Level_Down")  # sound for becoming the victim

        self.CreateCVar("pac_reduced_damage", "1",
                        "Reduces the damage to non-victim players by 99% (0 to disable, 1 to enable)")
        self.CreateCVar("pac_survive_time", "30",
                        "The amount of time in seconds the victim should survive before being awarded a point "
                        "(default=30, range 5 - 60)")
        self.CreateCVar("pac_victim_scoring", "1",
                        "Enables the victim to score (all kills score) (1 to enable, 0 to disable)")
        self.CreateCVar("pac_classic_mode", "0",
                        "Enables the original Perfect Dark Settings (ie: 1 minute survive timer, normal damage, and "
                        "death match scoring [all kills score]. Overrides Timer and Reduced Damage settings)")

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

    def OnCVarChanged( self, name, oldvalue, newvalue ):
        if name == "pac_reduced_damage":
            if not self.classicMode:
                self.reduceDamage = int(newvalue) >= 1
        elif name == "pac_survive_time":
            if not self.classicMode:
                self.surviveTime = clamp(int(newvalue), 5, 60)
        elif name == "pac_victim_scoring":
            if not self.classicMode:
                self.victimScores = True
        elif name == "pac_classic_mode":
            self.classicMode = int(newvalue) >= 1
            if self.classicMode:
                # set classic mode settings if enabled
                self.surviveTime = 60
                self.reduceDamage = False

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
        PopACap.PRV_VIC1 = None
        PopACap.PRV_VIC2 = None

    def OnThink(self):
        # Check to see if we can get out of warmup
        if self.waitingForPlayers:
            if GERules.GetNumActivePlayers() > 1:
                self.waitingForPlayers = False
                if not self.warmupTimer.HadWarmup():
                    self.warmupTimer.StartWarmup(15, True)
                else:
                    GEUtil.HudMessage(None, "#GES_GP_GETREADY", -1, -1, GEUtil.Color(255, 255, 255, 255), 2.5, 1)
                    GERules.EndRound(False)
            elif GEUtil.GetTime() > self.PLAYER_WAIT_TICKER:
                need = 2 - GERules.GetNumActivePlayers()
                GEUtil.HudMessage(None, "#GES_GP_WAITING", -1, -1, GEUtil.Color(255, 255, 255, 255), 2.5, 1)
                GEUtil.HudMessage(None, "Need %i more players" % need, -1, -1.3, GEUtil.Color(255, 255, 255, 255), 2.5, 2)
                self.PLAYER_WAIT_TICKER = GEUtil.GetTime() + 12.5
        if not self.waitingForPlayers and GERules.GetNumActivePlayers() < 2:
            self.waitingForPlayers = True
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

            # If victim didn't kill thyself then award points
            if killer != victim:
                name = self.scrubcolors(killer.GetCleanPlayerName())
                GEUtil.PlaySoundToPlayer(killer, "GEGamePlay.Token_Grab")
                GEUtil.HudMessage(killer, "Well Done! You Popped a Cap!", -1, 0.72, SURVIVE_COLOR, 5.0, 2)
                GEUtil.HudMessage(killer, "Have 2 points...", -1, 0.75, SURVIVE_COLOR, 5.0, 3)
                GEUtil.HudMessage(Glb.TEAM_OBS, name + " popped the cap!", -1, 0.75, SURVIVE_COLOR, 5.0, 8)
                self.notifyothers(name + " popped the cap!", killer)
                if self.classicMode:
                    killer.AddRoundScore(1)  # death match scoring adds the second point
                else:
                    killer.AddRoundScore(2)

            # reset radar and scoreboard, pick new victim
            GERules.GetRadar().DropRadarContact(victim)
            victim.SetScoreBoardColor(Glb.SB_COLOR_NORMAL)
            self.choosenewvictim()
        if self.victimScores and not self.classicMode and killer.GetUID() == self.VICTIM:
            # Victim scoring is enabled
            GEScenario.OnPlayerKilled(self, victim, killer, weapon)

        # Classic Mode is enabled
        if self.classicMode:
            GEScenario.OnPlayerKilled(self, victim, killer, weapon)

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

    def CalculateCustomDamage(self, victim, info, health, armor):
        # if reduced non-victim damage is enable, reduce damage by 99%
        if self.reduceDamage and not self.classicMode:
            killer = GEPlayer.ToMPPlayer(info.GetAttacker())
            if killer.GetUID() == self.VICTIM:
                return health, armor
            if victim.GetUID() != self.VICTIM:
                if killer is not None:
                    armor -= armor * 0.99
                    health -= health * 0.99
                    return health, armor
        return health, armor

    def choosenewvictim(self):
        # Check to see if more than one player is around
        iplayers = []

        for player in GetPlayers():
            if player.IsInRound() and player.GetUID() != PopACap.VICTIM\
                    and player.GetUID() != PopACap.PRV_VIC1\
                    and player.GetUID() != PopACap.PRV_VIC2:
                iplayers.append(player)

        if len(iplayers) == 0:
            # No victim available
            GERules.EndRound()

        numplayers = len(iplayers)
        i = random.randint(1, numplayers) - 1
        newvictim = iplayers[i]
        iplayers.remove(newvictim)

        # If enough players, avoid making a previous victim a victim again soon
        if numplayers >= 4:
            PopACap.PRV_VIC2 = PopACap.PRV_VIC1
        if numplayers >= 2:
            PopACap.PRV_VIC1 = PopACap.VICTIM
        # # #

        PopACap.VICTIM = newvictim.GetUID()
        GEUtil.PlaySoundToPlayer(newvictim, "GEGamePlay.Level_Down")
        GEUtil.HudMessage(newvictim, "You are the victim", -1, 0.69, VICTIM_ALERT_COLOR, 5.0, 4)
        for player in iplayers:
            GEUtil.HudMessage(player, "Get %s" % self.scrubcolors(newvictim.GetCleanPlayerName()),
                              -1, -1, GET_VICTIM_COLOR, 5.0, 5)
        GEUtil.HudMessage(Glb.TEAM_OBS, "%s is the victim" % self.scrubcolors(newvictim.GetCleanPlayerName()),
                          -1, 0.69, GET_VICTIM_COLOR, 5.0, 6)
        self.capSurviveTimer.Start(self.surviveTime, True)
        if GERules.GetRadar() is None:
            # Round of bots which no player left
            return

        GERules.GetRadar().AddRadarContact(newvictim, Glb.RADAR_TYPE_PLAYER, True, "sprites/hud/radar/xsm")
        GERules.GetRadar().SetupObjective(newvictim, Glb.TEAM_NONE, "", "VICTIM", CAP_OBJECTIVE, 0)
        newvictim.SetScoreBoardColor(Glb.SB_COLOR_GOLD)

    @staticmethod
    def notifyothers(msg, omit=None):
        for player in GetPlayers():
            if omit is not None:
                if omit.GetUID() == player.GetUID():
                    continue
            if player.GetUID() != PopACap.VICTIM:
                GEUtil.HudMessage(player, msg, -1, 0.75, SURVIVE_COLOR, 5.0, 7)

    @staticmethod
    def scrubcolors(msg):  # cause GetCleanPlayerName isn't perfect
        return re.sub('\^[A-Za-z0-9]', '', msg)
