# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Vampire
# Version 1.0.0 BETA
# Author: DarkDiplomat
# Based on an Idea from .xXAkelaXx. and Time Splitters 2
#
# Synopsis: You have to continue to kill so your blood doesn't run out.
# You respawn when killed or run out of blood
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

from . import GEScenario
from .Utils import clamp, GetPlayers
from .Utils.GEWarmUp import GEWarmUp
import GEEntity, GEPlayer, GEUtil, GEWeapon, GEMPGameRules as GERules, GEGlobal

USING_API = GEGlobal.API_VERSION_1_2_0


class Vampire(GEScenario):
    PLAYER_WAIT_TICKER = 0  # redisplay waiting for players timer

    def __init__(self):
        super(Vampire, self).__init__()

        self.blood_counter = {}
        self.lives_counter = {}
        self.warmupTimer = GEWarmUp(self)  # init warm up timer
        self.waitingForPlayers = True

        # CVars
        # Number of Lives
        self.max_lives = 5
        # Total Blood
        self.max_blood = 300.0
        # Blood Loss factor
        self.blood_factor = 0.8

    def GetPrintName(self):
        return "Vampire (BETA)"

    def GetGameDescription(self):
        if GERules.IsTeamplay():
            return "Team Vampire (BETA)"
        else:
            return "Vampire (BETA)"

    def GetScenarioHelp(self, help_obj):
        help_obj.SetDescription("Keep killing to stay alive! If you run out of blood or are ")

    def GetTeamPlay(self):
        return GEGlobal.TEAMPLAY_NONE  # Currently disabled, though technically functional

    def OnLoadGamePlay(self):
        self.CreateCVar("vampire_lives", "5",
                        "Sets the amount of lives to give the players to start, set to 0 to disable lives "
                        "(Default 5, minimum 0, max 10)")
        self.CreateCVar("vampire_max_blood", "300",
                        "Sets the amount of blood players start with "
                        "(Default 300, minimum 100, max 600)")
        self.CreateCVar("vampire_blood_loss", "8",
                        "The factor at which blood is lost. Higher the number, the more blood is lost each second. "
                        "(Default 8, minimum 1, max 10)")

    def OnUnloadGamePlay(self):
        super(Vampire, self).OnUnloadGamePlay()
        self.warmupTimer = None
        self.blood_counter.clear()
        self.lives_counter.clear()

    def OnCVarChanged(self, name, oldvalue, newvalue):
        if name == "vampire_lives":
            self.max_lives = clamp(newvalue, 0, 10)
        elif name == "vampire_max_blood":
            self.max_blood = clamp(newvalue, 100.0, 600.0)
        elif name == "vampire_blood_loss":
            self.blood_factor = clamp(newvalue / 10, 0.1, 1.0)

    def OnPlayerConnect(self, player):
        self.blood_counter.setdefault(player.GetUID(), 0)
        self.lives_counter.setdefault(player.GetUID(), 0)

    def OnPlayerDisconnect(self, player):
        self.lives_counter.pop(player.GetUID())

    def CanPlayerChangeTeam(self, player, oldteam, newteam, wasforced):
        if newteam == GEGlobal.TEAM_SPECTATOR:
            self.lives_counter[player.GetUID()] = 0
        return True

    def OnRoundBegin(self):
        super(Vampire, self).OnRoundBegin()
        if not self.warmupTimer.IsInWarmup() and self.warmupTimer.HadWarmup():
            GERules.LockRound()

            for player in GetPlayers():
                self.blood_counter[player.GetUID()] = self.max_blood

                GEUtil.InitHudProgressBar(player, 0, "Blood", 1, self.max_blood, -1, .04, 130, 12,
                                          GEUtil.Color(255, 0, 0, 255), self.max_blood)
                if self.max_lives > 0:
                    self.lives_counter[player.GetUID()] = self.max_lives
                    GEUtil.InitHudProgressBar(player, 1, "Lives", 2, self.max_lives, -1, .08, 130, 12,
                                              GEUtil.Color(255, 255, 255, 255), self.max_lives)

    def OnRoundEnd(self):
        GERules.UnlockRound()

    def OnPlayerKilled(self, victim, killer, weapon):
        if self.waitingForPlayers or self.warmupTimer.IsInWarmup() or GERules.IsIntermission() or not victim:
            # Nothing to do but wait...
            return

        if not killer == victim:
            self.blood_counter[killer.GetUID()] = self.max_blood
            self.lostALife(victim)
            GEUtil.EmitGameplayEvent("vampire_death", str(victim.GetUID))
            killer.AddRoundScore(1)
            killer.SetHealth(killer.GetMaxHealth())
            if GERules.IsTeamplay():
                GERules.GetTeam(killer.GetTeamNumber()).AddRoundScore(1)
        else:
            self.lostALife(victim)
            GEUtil.EmitGameplayEvent("vampire_death_blood", str(victim.GetUID))

    def CanPlayerRespawn(self, player):
        if self.warmupTimer.IsInWarmup() or not self.warmupTimer.HadWarmup():
            return True

        if self.max_lives > 0 >= self.lives_counter[player.GetUID()]:
            return False

        return True

    def OnThink(self):
        # Check to see if we can get out of warm-up
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
            return

        if GERules.GetNumActivePlayers() <= 1:
            self.waitingForPlayers = True

        if GERules.IsRoundLocked():
            for player in GetPlayers():
                if not player.IsInRound():
                    continue

                if not player.IsDead():  # Only update blood while the player is alive and active
                    blood = self.blood_counter[player.GetUID()] - self.blood_factor  # Reduce blood each tick (1 seemed a little fast)
                    self.blood_counter[player.GetUID()] = blood
                    if blood <= 0:  # Player has run out of blood
                        player.CommitSuicide(False, False)
                    else:
                        GEUtil.UpdateHudProgressBar(player, 0, blood)

            if self.max_lives > 0:
                if GERules.IsTeamplay():
                    mi6Lives = []
                    janusLives = []
                    for uid in self.lives_counter:
                        if self.lives_counter[uid] > 0:
                            player = GEPlayer.ToMPPlayer(uid)
                            if player.GetTeamNumber() == GEGlobal.TEAM_MI6:
                                mi6Lives.append(uid)
                            else:
                                janusLives.append(uid)

                    if len(mi6Lives) > 0 >= len(janusLives):  # MI6 Wins
                        GERules.SetTeamWinner(GEGlobal.TEAM_MI6)
                        GERules.EndRound()
                    elif len(mi6Lives) <= 0 < len(janusLives):  # Janus Wins
                        GERules.SetTeamWinner(GEGlobal.TEAM_JANUS)
                        GERules.EndRound()
                    elif len(mi6Lives) <= 0 >= len(janusLives):  # RIP ALL
                        GERules.EndRound()
                else:
                    hasLives = []
                    for uid in self.lives_counter:
                        if self.lives_counter[uid] > 0:
                            hasLives.append(uid)

                    if len(hasLives) == 1:
                        GERules.SetPlayerWinner(GEPlayer.ToMPPlayer(hasLives[0]))
                        GERules.EndRound()
                    elif len(hasLives) < 1:
                        GERules.EndRound()

    def checkEliminated(self, victim):
        if self.max_lives > 0 >= self.lives_counter[victim.GetUID()]:
            GEUtil.PopupMessage(victim, "#GES_GPH_ELIMINATED_TITLE", "#GES_GPH_ELIMINATED")
            victim.SetScoreBoardColor(GEGlobal.SB_COLOR_ELIMINATED)
            GEUtil.RemoveHudProgressBar(victim, 0)
            GEUtil.RemoveHudProgressBar(victim, 1)
            return True
        return False

    def lostALife(self, victim):
        if self.max_lives > 0:
            self.lives_counter[victim.GetUID()] -= 1
            GEUtil.UpdateHudProgressBar(victim, 1, self.lives_counter[victim.GetUID()])
            if not self.checkEliminated(victim):
                self.blood_counter[victim.GetUID()] = self.max_blood
