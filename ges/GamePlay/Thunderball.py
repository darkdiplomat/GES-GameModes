# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Thunderball
# v1.2
# By: DarkDiplomat
#
# Based loosely on concepts layout at https://forums.geshl2.com/index.php/topic,5573.0.html
#
# Synopsis: The Thunderball is set to explode every 25 seconds!
# To start, the Thunderball is given to a random player. The player has to kill an opponent to
# get rid of the Thunderball. If the player is unable to accomplish that they
# are temporarily knocked out and the last player to kill them takes ownership
# of the Thunderball; if no last killer, a new random player is selected.
# Survivors get a point each time the ball detonates. Scoring is deathmatch style, all kills gain points.
# The Thunderball carrier gets some advantages to help them transfer the
# Thunderball, such as, increased speed and taking less damage (like an
# adrenaline boost in the panic of being the Thunderball carrier)
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

from . import GEScenario
from .Utils import _, clamp
from .Utils.GEPlayerTracker import GEPlayerTracker
from .Utils.GEWarmUp import GEWarmUp
from .Utils.GETimer import TimerTracker, Timer
import random
import GEEntity, GEPlayer, GEUtil, GEWeapon, GEMPGameRules as GERules, GEGlobal as Glb
import re

USING_API = Glb.API_VERSION_1_2_0

TB_KNOCKEDOUT = "ko"
TR_SPAWNED = "spawned"
TB_CARRIER = "thunderball"
TB_PREV = "tbprev"
TB_AGGRESSOR = "tbaggro"
ALERT_COLOR = GEUtil.Color(255, 0, 0, 255)
RELIEF_COLOR = GEUtil.Color(150, 150, 150, 220)
SURVIVE_COLOR = GEUtil.Color(0, 190, 0, 220)
TIMER_COLOR = GEUtil.Color(200, 200, 200, 255)


class Thunderball(GEScenario):
    PLTRACKER = None  # playertracker
    ASSIGNED_ONCE = False  # check that a Thunderball has been assigned at least once
    CAN_ASSIGN = False  # var to set whether we can assign the thunderball(s)
    TIMER_ADJUST = False  # var to set whether the timer needs updated
    DETONATE_TIME = 15  # time before thunderball detonation
    TIME_TRACK = DETONATE_TIME  # time tracker for HUD messages
    PLAYER_WAIT_TICKER = 0  # redisplay waiting for players timer

    @staticmethod
    def initialAssignment(timer, type_):
        if type_ == Timer.UPDATE_FINISH:
            Thunderball.CAN_ASSIGN = True

    @staticmethod
    def detonator(timer, type_):  # method to handle when the timer finishes and the Thunderball has detonated
        if type_ == Timer.UPDATE_FINISH:
            plys = []
            for ply in Thunderball.PLTRACKER.GetPlayers():
                if Thunderball.PLTRACKER[ply][TB_CARRIER]:
                    plys.append(ply)

            for others in Thunderball.PLTRACKER.GetPlayers():
                if Thunderball.PLTRACKER[others][TB_PREV]:
                    Thunderball.PLTRACKER[others][TB_KNOCKEDOUT] = False
                    Thunderball.PLTRACKER[others][TB_PREV] = False
                    others.ChangeTeam(Glb.TEAM_NONE, True)
                    others.ForceRespawn()
                    GEUtil.PostDeathMessage("%s ^1has revived!" % others.GetCleanPlayerName())

            if len(plys) > 0:
                for player in plys:
                    Thunderball.PLTRACKER[player][TB_KNOCKEDOUT] = True  # set the player as eliminated
                    if not player.IsDead():  # check that they aren't already dead
                        if player.__class__.__name__ == "CGEBotPlayer":  # dirty bots just don't want to die
                            # Give them an extra point to make up for the loss on forced suicide
                            player.AddRoundScore(1)
                            player.CommitSuicide(True, True)
                        else:
                            player.ForceRespawn()  # Basicly force them out without showing the commit suicide message
                    # let everyone know who was taken out by the thunderball
                    GEUtil.PostDeathMessage("^r%s ^rwas knocked out for a bit!" % player.GetCleanPlayerName())
                    GEUtil.PopupMessage(player,
                                        "KNOCKED OUT",
                                        "You've been temporarily knocked out and will have to wait for %i seconds"
                                        % Thunderball.DETONATE_TIME)  # and let the player know they were knocked out
                    GEUtil.EmitGameplayEvent("tb_knocked_out", str(player.GetUID()), "", "", "", True)
                    Thunderball.PLTRACKER[player][TB_PREV] = True

            if Thunderball.TIMER_ADJUST:
                timer.Stop()
                Thunderball.TIME_TRACK = Thunderball.DETONATE_TIME
                timer.Start(Thunderball.DETONATE_TIME, True)
                Thunderball.TIMER_ADJUST = False

    def __init__(self):
        super(Thunderball, self).__init__()

        self.warmupTimer = GEWarmUp(self)  # init warm up timer
        self.timeTracker = TimerTracker(self)  # init timer tracker
        # initial timer to give players a chance to start, fixes an issue with server lag in most cases
        self.assignmentTimer = self.timeTracker.CreateTimer("assignmentTimer")
        self.assignmentTimer.SetUpdateCallback(self.initialAssignment)
        self.thunderballTimer = self.timeTracker.CreateTimer("thunderballTimer")  # init timer
        self.thunderballTimer.SetUpdateCallback(self.detonator)  # add our callback method to the timer
        self.waitingForPlayers = True
        self.multiball = False
        Thunderball.PLTRACKER = GEPlayerTracker(self)  # init the player tracker

    def GetPrintName(self):
        return "Thunderball"

    def GetGameDescription(self):
        return "Thunderball"

    def GetTeamPlay(self):
        return Glb.TEAMPLAY_NONE

    def GetScenarioHelp(self, help_obj):
        help_obj.SetDescription("The Thunderball is set to explode at a set interval! "
                                "To start, the ball is given to a random player. "
                                "The player has to kill an opponent to get rid of the ball. "
                                "If the player is unable to do that they are knocked out until the next detonation "
                                "and the last player to kill them takes the ball; if no last killer, "
                                "a new random player is selected. Survivors are awarded a point after each detonation. "
                                "Scoring is death match style, all kills gain points. The ball carrier gets "
                                "some advantages to help them transfer the ball, such as, increased speed and taking "
                                "less damage.")

    def OnLoadGamePlay( self ):
        # Ensure our sounds are pre-cached
        GEUtil.PrecacheSound("GEGamePlay.Level_Down")  # sound for time running out
        GEUtil.PrecacheSound("GEGamePlay.Woosh")  # sound for passing the thunderball

        self.CreateCVar("tb_detonator", "15",
                        "The amount of time in seconds the between Thunderball detonations (default=15)")
        self.CreateCVar("tb_multiball", "1",
                        "Enables adding a ball for each 4 players (up to 4 active balls), set to 0 to disable")

        # Make sure we don't start out in wait time or have a warmup if we changed gameplay mid-match
        if GERules.GetNumActivePlayers() > 1:
            self.waitingForPlayers = False
            self.warmupTimer.StartWarmup(0)

    def OnUnloadGamePlay(self):
        super(Thunderball, self).OnUnloadGamePlay()
        del self.warmupTimer
        del Thunderball.PLTRACKER
        self.thunderballTimer.Stop()
        self.timeTracker.RemoveTimer()
        del self.thunderballTimer
        del self.timeTracker

    def OnCVarChanged(self, name, oldvalue, newvalue):
        if name == "tb_detonator":
            Thunderball.DETONATE_TIME = clamp(int(newvalue), 10, 60)
            Thunderball.TIMER_ADJUST = True
        elif name == "tb_multiball":
            self.multiball = int(newvalue) >= 1

    def OnPlayerConnect(self, player):
        Thunderball.PLTRACKER[player][TR_SPAWNED] = False
        Thunderball.PLTRACKER[player][TB_KNOCKEDOUT] = False
        Thunderball.PLTRACKER[player][TB_PREV] = False
        Thunderball.PLTRACKER[player][TB_CARRIER] = False

    def OnPlayerDisconnect(self, player):
        if Thunderball.PLTRACKER[player][TB_CARRIER]:
            aggressor = GEPlayer.ToMPPlayer(Thunderball.PLTRACKER[player][TB_AGGRESSOR])
            if aggressor is not None:
                self.assignThunderball(aggressor)
            else:
                self.assignThunderball(self.chooserandom())

    def CanPlayerChangeTeam(self, player, oldteam, newteam, wasforced):
        if newteam == Glb.TEAM_NONE and Thunderball.PLTRACKER[player][TB_KNOCKEDOUT]:
            GEUtil.PopupMessage(player, "KNOCKED OUT", "You are currently knocked out")
            return False
        return True

    def OnPlayerSpawn(self, player):
        if player.GetTeamNumber() != Glb.TEAM_SPECTATOR:
            Thunderball.PLTRACKER[player][TR_SPAWNED] = True

    def OnRoundBegin(self):
        GEScenario.OnRoundBegin(self)

        # Reset all player's statistics
        Thunderball.PLTRACKER.SetValueAll(TB_KNOCKEDOUT, False)
        Thunderball.PLTRACKER.SetValueAll(TB_CARRIER, False)
        Thunderball.PLTRACKER.SetValueAll(TB_PREV, False)
        Thunderball.PLTRACKER.SetValueAll(TB_AGGRESSOR, None)
        GERules.ResetAllPlayerDeaths()
        GERules.ResetAllPlayersScores()

        if GERules.GetNumActivePlayers() <= 1:
            self.waitingForPlayers = True

        if self.warmupTimer.HadWarmup() and not self.waitingForPlayers:
            self.assignmentTimer.Start(5)  # start the initial assignment timer

    def OnRoundEnd(self):
        # Prepare for Reset
        self.thunderballTimer.Stop()
        Thunderball.ASSIGNED_ONCE = False
        Thunderball.CAN_ASSIGN = False
        GEUtil.RemoveHudProgressBar(None, 5)

    def OnThink(self):
        # Check to see if we can get out of warmup
        if self.waitingForPlayers:
            if GERules.GetNumActivePlayers() > 1:
                self.waitingForPlayers = False
                Thunderball.PLTRACKER.SetValueAll(TR_SPAWNED, True)
                if not self.warmupTimer.HadWarmup():
                    self.warmupTimer.StartWarmup(15, True)
                else:
                    GERules.EndRound(False)
            elif GEUtil.GetTime() > self.PLAYER_WAIT_TICKER:
                GEUtil.HudMessage(None, "#GES_GP_WAITING", -1, -1, GEUtil.Color(255, 255, 255, 255), 2.5, 1)
                self.PLAYER_WAIT_TICKER = GEUtil.GetTime() + 12.5

        # check if we can do the initial assignment of the Thunderball
        if Thunderball.CAN_ASSIGN and not Thunderball.ASSIGNED_ONCE:
            if self.multiball:
                plyn = GERules.GetNumActivePlayers()
                if plyn > 4:  # 4 or more
                    self.assignThunderball(self.chooserandom())
                if plyn > 9:  # 8 or more
                    self.assignThunderball(self.chooserandom())
            self.assignThunderball(self.chooserandom())
            return

        if self.warmupTimer.HadWarmup() and not self.waitingForPlayers and Thunderball.ASSIGNED_ONCE:
            for player in Thunderball.PLTRACKER.GetPlayers():
                if Thunderball.PLTRACKER[player][TB_CARRIER] and Thunderball.PLTRACKER[player][TB_KNOCKEDOUT]:
                    Thunderball.PLTRACKER[player][TB_CARRIER] = False
                    prevaggro = GEPlayer.ToMPPlayer(Thunderball.PLTRACKER[player][TB_AGGRESSOR])
                    if prevaggro is not None:
                        if not Thunderball.PLTRACKER[prevaggro][TB_CARRIER] and not Thunderball.PLTRACKER[prevaggro][TB_KNOCKEDOUT]:
                            self.assignThunderball(prevaggro)
                        else:
                            self.assignThunderball(self.chooserandom())
                    else:
                        self.assignThunderball(self.chooserandom())
            remain = Thunderball.TIME_TRACK - int(self.thunderballTimer.GetCurrentTime())
            if remain <= 5:
                GEUtil.HudMessage(None, "Thunderball Detonation in %i sec" % remain, -1, 0.12, ALERT_COLOR, 1.0, 5)
            else:
                GEUtil.HudMessage(None, "Thunderball Detonation in %i sec" % remain, -1, 0.12, TIMER_COLOR, 1.0, 5)

            if remain == 6:  # it takes a moment to play the sound
                for player in Thunderball.PLTRACKER.GetPlayers():
                    if Thunderball.PLTRACKER[player][TB_CARRIER]:
                        GEUtil.PlaySoundToPlayer(player, "GEGamePlay.Level_Down")
                        GEUtil.HudMessage(player, "YOU HAVE A THUNDERBALL!", -1, -1, ALERT_COLOR, 3.0, 6)

    def CanRoundEnd(self):
        return GERules.GetNumActivePlayers() <= 1 or GERules.GetRoundTimeLeft() <= 0

    def OnPlayerKilled(self, victim, killer, weapon):
        # Let the base scenario behavior handle scoring so we can just worry about the thunderball mechanics.
        GEScenario.OnPlayerKilled(self, victim, killer, weapon)

        if self.waitingForPlayers or self.warmupTimer.IsInWarmup() or GERules.IsIntermission() or not victim:
            return

        # Pass the thunderball off
        if Thunderball.PLTRACKER[killer][TB_CARRIER] and not Thunderball.PLTRACKER[victim][TB_CARRIER]:
            if self.isinplay(victim):  # Bots don't work well at getting removed
                self.assignThunderball(victim, killer)
                GEUtil.EmitGameplayEvent("tb_passed", str(killer.GetUID()), str(victim.GetUID()), "", "", True)

    def CanPlayerRespawn(self, player):
        if Thunderball.PLTRACKER[player][TB_KNOCKEDOUT]:
            return False
        return True

    def CalculateCustomDamage(self, victim, info, health, armor):
        if Thunderball.PLTRACKER[victim][TB_CARRIER]:
            killer = GEPlayer.ToMPPlayer(info.GetAttacker())
            # If being attacked reduce damage by 30%
            if killer is not None:
                armor -= armor * 0.3
                health -= health * 0.3
        return health, armor

    def chooserandom(self):
        # Check to see if more than one player is around
        iplayers = []

        for player in Thunderball.PLTRACKER.GetPlayers():
            if self.isinplay(player) and not Thunderball.PLTRACKER[player][TB_CARRIER]\
                    and not Thunderball.PLTRACKER[player][TB_KNOCKEDOUT]:
                iplayers.append(player)

        numplayers = len(iplayers)
        if numplayers == 0 and Thunderball.ASSIGNED_ONCE:
            return None
        elif numplayers == 1 and Thunderball.ASSIGNED_ONCE:
            return None
        else:
            i = random.randint(1, numplayers) - 1
            return iplayers[i]

    def assignThunderball(self, newowner, oldowner=None):
        if not newowner or not self.isinplay(newowner):
            return

        Thunderball.PLTRACKER[newowner][TB_CARRIER] = True
        GEUtil.PlaySoundToPlayer(newowner, "GEGamePlay.Woosh")
        GEUtil.HudMessage(newowner, "You have been given a Thunderball!", -1, -1, ALERT_COLOR, 3.0, 6)
        GEUtil.HudMessage(Glb.TEAM_SPECTATOR, self.scrubcolors(newowner.GetCleanPlayerName()) + " has a Thunderball!",
                          -1, 0.75, TIMER_COLOR, 5.0, 8)
        newowner.SetSpeedMultiplier(1.3)
        Thunderball.ASSIGNED_ONCE = True
        if self.thunderballTimer.state == Timer.STATE_PAUSE:
            self.thunderballTimer.Start()
        elif self.thunderballTimer.state == Timer.STATE_STOP:
            self.thunderballTimer.Start(Thunderball.DETONATE_TIME, True)
        if oldowner is not None:
            Thunderball.PLTRACKER[newowner][TB_AGGRESSOR] = oldowner.GetUID()
            Thunderball.PLTRACKER[oldowner][TB_CARRIER] = False
            GEUtil.PlaySoundToPlayer(oldowner, "GEGamePlay.Woosh")
            GEUtil.HudMessage(oldowner, "You have passed a Thunderball!", -1, 0.73, RELIEF_COLOR, 5.0, 7)
            oldowner.SetSpeedMultiplier(1.0)

    @staticmethod
    def isinplay(player):
        return player.GetTeamNumber() is not Glb.TEAM_SPECTATOR and Thunderball.PLTRACKER[player][TR_SPAWNED] \
               and not Thunderball.PLTRACKER[player][TB_KNOCKEDOUT]

    @staticmethod
    def scrubcolors(msg):
        return re.sub('\^[A-Za-z0-9]', '', msg)
