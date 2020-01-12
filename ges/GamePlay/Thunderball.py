# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Thunderball
# v1.3.1
# By: DarkDiplomat
#
# Based loosely on concepts layout at https://forums.geshl2.com/index.php/topic,5573.0.html
#
# Synopsis: The Thunderball is set to explode at a configurable interval!
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
TB_PREV = "tbprev"
ALERT_COLOR = GEUtil.Color(255, 80, 80, 255)
RELIEF_COLOR = GEUtil.Color(150, 150, 150, 220)
SURVIVE_COLOR = GEUtil.Color(0, 190, 0, 220)
TIMER_COLOR = GEUtil.Color(200, 200, 200, 255)


class Thunderball(GEScenario):
    PLTRACKER = None  # playertracker
    ASSIGNED_ONCE = False  # check that a Thunderball has been assigned at least once
    CAN_ASSIGN = False  # var to set whether we can assign the thunderball
    TIMER_ADJUST = False  # var to set whether the timer needs updated
    DETONATE_TIME = 15  # time before thunderball detonation
    KNOCKOUT_TIME = DETONATE_TIME - 5  # amount of time knocked out for
    TIME_TRACK = DETONATE_TIME  # time tracker for HUD messages
    PLAYER_WAIT_TICKER = 0  # redisplay waiting for players timer
    TB_CARRIER = None
    TIME_TRACKER = None

    @staticmethod
    def initialAssignment(timer, type_):
        if type_ == Timer.UPDATE_FINISH:
            Thunderball.CAN_ASSIGN = True

    @staticmethod
    def detonator(timer, type_):  # method to handle when the timer finishes and the Thunderball has detonated
        if type_ == Timer.UPDATE_FINISH:
            if Thunderball.TB_CARRIER is not None:
                player = GEPlayer.ToMPPlayer(Thunderball.TB_CARRIER)
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
                                    % Thunderball.KNOCKOUT_TIME)  # and let the player know they were knocked out
                GEUtil.EmitGameplayEvent("tb_knocked_out", str(player.GetUID()), "", "", "", True)
                Thunderball.PLTRACKER[player][TB_PREV] = True
                Thunderball.createReviveTimer(player.GetUID())

            if Thunderball.TIMER_ADJUST:
                timer.Stop()
                Thunderball.TIME_TRACK = Thunderball.DETONATE_TIME
                Thunderball.KNOCKOUT_TIME = Thunderball.DETONATE_TIME - 5
                timer.Start(Thunderball.DETONATE_TIME, True)
                Thunderball.TIMER_ADJUST = False

    @staticmethod
    def revive(timer, type_):
        if type_ == Timer.UPDATE_FINISH:
            reviving = GEPlayer.ToMPPlayer(int(timer.GetName()))
            if reviving is not None:
                if Thunderball.PLTRACKER[reviving.GetUID()][TB_PREV]:
                    Thunderball.PLTRACKER[reviving.GetUID()][TB_KNOCKEDOUT] = False
                    Thunderball.PLTRACKER[reviving.GetUID()][TB_PREV] = False
                    # set their speed multiplier back to normal
                    reviving.SetSpeedMultiplier(1.0)
                    reviving.ChangeTeam(Glb.TEAM_NONE, True)
                    reviving.ForceRespawn()
                    GEUtil.PostDeathMessage("%s ^1has revived!" % reviving.GetCleanPlayerName())

    def __init__(self):
        super(Thunderball, self).__init__()

        self.warmupTimer = GEWarmUp(self)  # init warm up timer
        Thunderball.TIME_TRACKER = TimerTracker(self)  # init timer tracker
        # initial timer to give players a chance to start, fixes an issue with server lag in most cases
        self.assignmentTimer = Thunderball.TIME_TRACKER.CreateTimer("assignmentTimer")
        self.assignmentTimer.SetUpdateCallback(self.initialAssignment)
        self.thunderballTimer = Thunderball.TIME_TRACKER.CreateTimer("thunderballTimer")  # init timer
        self.thunderballTimer.SetUpdateCallback(self.detonator)  # add our callback method to the timer
        self.waitingForPlayers = True
        Thunderball.PLTRACKER = GEPlayerTracker(self)  # init the player tracker

    def GetPrintName(self):
        return "Thunderball"

    def GetGameDescription(self):
        return "Thunderball"

    def GetTeamPlay(self):
        return Glb.TEAMPLAY_NONE

    def GetScenarioHelp(self, help_obj):
        help_obj.SetDescription("A sadistic game of hot potato! ThunderBall explodes at a set interval. If you have it,"
                                "kill to get rid of it. If you have it when it explodes, you are temporarily knocked "
                                "out. See https://git.io/JvfS9 for more information.")

    def OnLoadGamePlay( self ):
        # Ensure our sounds are pre-cached
        GEUtil.PrecacheSound("GEGamePlay.Level_Down")  # sound for time running out
        GEUtil.PrecacheSound("GEGamePlay.Woosh")  # sound for passing the thunderball

        self.CreateCVar("tb_detonator", "15",
                        "The amount of time in seconds the between Thunderball detonations (default=15)")

        # Make sure we don't start out in wait time or have a warm-up if we changed game play mid-match
        if GERules.GetNumActivePlayers() > 1:
            self.waitingForPlayers = False
            self.warmupTimer.StartWarmup(0)

    def OnUnloadGamePlay(self):
        super(Thunderball, self).OnUnloadGamePlay()
        del self.warmupTimer
        del Thunderball.PLTRACKER
        self.thunderballTimer.Stop()
        Thunderball.TIME_TRACKER.RemoveTimer()
        del self.thunderballTimer
        del Thunderball.TIME_TRACKER

    def OnCVarChanged(self, name, oldvalue, newvalue):
        if name == "tb_detonator":
            Thunderball.DETONATE_TIME = clamp(int(newvalue), 10, 60)
            Thunderball.TIMER_ADJUST = True

    def OnPlayerConnect(self, player):
        Thunderball.PLTRACKER[player][TR_SPAWNED] = False
        Thunderball.PLTRACKER[player][TB_KNOCKEDOUT] = False
        Thunderball.PLTRACKER[player][TB_PREV] = False

    def OnPlayerDisconnect(self, player):
        if player.GetUID() == Thunderball.TB_CARRIER:
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
        Thunderball.TB_CARRIER = None
        Thunderball.PLTRACKER.SetValueAll(TB_KNOCKEDOUT, False)
        Thunderball.PLTRACKER.SetValueAll(TB_PREV, False)
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
        Thunderball.TB_CARRIER = None

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
            self.assignThunderball(self.chooserandom())
            return

        if self.warmupTimer.HadWarmup() and not self.waitingForPlayers and Thunderball.ASSIGNED_ONCE:
            for player in Thunderball.PLTRACKER.GetPlayers():
                if player.GetUID() == Thunderball.TB_CARRIER and Thunderball.PLTRACKER[player][TB_KNOCKEDOUT]:
                    self.assignThunderball(self.chooserandom())
            remain = Thunderball.TIME_TRACK - int(self.thunderballTimer.GetCurrentTime())
            if remain <= 5:
                GEUtil.HudMessage(None, "Thunderball Detonation in %i sec" % remain, -1, 0.12, ALERT_COLOR, 1.0, 5)
            else:
                GEUtil.HudMessage(None, "Thunderball Detonation in %i sec" % remain, -1, 0.12, TIMER_COLOR, 1.0, 5)

            if remain == 6:  # it takes a moment to play the sound
                player = GEPlayer.ToMPPlayer(Thunderball.TB_CARRIER)
                GEUtil.PlaySoundToPlayer(player, "GEGamePlay.Level_Down")
                GEUtil.HudMessage(player, "YOU HAVE THE THUNDERBALL!", -1, -1, ALERT_COLOR, 3.0, 6)

            if remain < 0:
                # Timer broke, force it to die
                GEUtil.PostDeathMessage("The Thunderball has malfunctioned!")
                self.thunderballTimer.Stop()
                self.assignThunderball(self.chooserandom())

    def CanRoundEnd(self):
        return GERules.GetNumActivePlayers() <= 1 or GERules.GetRoundTimeLeft() <= 0

    def OnPlayerKilled(self, victim, killer, weapon):
        # Let the base scenario behavior handle scoring so we can just worry about the thunderball mechanics.
        GEScenario.OnPlayerKilled(self, victim, killer, weapon)

        if self.waitingForPlayers or self.warmupTimer.IsInWarmup() or GERules.IsIntermission() or not victim:
            return

        # Pass the thunderball off
        if killer.GetUID() == Thunderball.TB_CARRIER:
            if self.isinplay(victim):  # Bots don't work well at getting removed
                self.assignThunderball(victim, killer)
                GEUtil.EmitGameplayEvent("tb_passed", str(killer.GetUID()), str(victim.GetUID()), "", "", True)

    def CanPlayerRespawn(self, player):
        if Thunderball.PLTRACKER[player][TB_KNOCKEDOUT]:
            return False
        return True

    def CalculateCustomDamage(self, victim, info, health, armor):
        if victim.GetUID() == Thunderball.TB_CARRIER:
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
            if self.isinplay(player) and player.GetUID() != Thunderball.TB_CARRIER\
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

        Thunderball.TB_CARRIER = newowner.GetUID()
        GEUtil.PlaySoundToPlayer(newowner, "GEGamePlay.Woosh")
        GEUtil.HudMessage(newowner, "You have been given the Thunderball!", -1, -1, ALERT_COLOR, 3.0, 6)
        GEUtil.HudMessage(Glb.TEAM_SPECTATOR, self.scrubcolors(newowner.GetCleanPlayerName()) + " has a Thunderball!",
                          -1, 0.75, TIMER_COLOR, 5.0, 8)
        newowner.SetSpeedMultiplier(1.3)
        Thunderball.ASSIGNED_ONCE = True

        # Restart Timer on passing the ball
        self.thunderballTimer.Stop()
        self.thunderballTimer.Start(Thunderball.DETONATE_TIME, True)

        if oldowner is not None:
            GEUtil.PlaySoundToPlayer(oldowner, "GEGamePlay.Woosh")
            GEUtil.HudMessage(oldowner, "You have passed the Thunderball!", -1, 0.73, RELIEF_COLOR, 5.0, 7)
            oldowner.SetSpeedMultiplier(1.0)

    @staticmethod
    def createReviveTimer(uid):
        timer = Thunderball.TIME_TRACKER.CreateTimer(str(uid))
        timer.SetUpdateCallback(Thunderball.revive)
        timer.Start(Thunderball.KNOCKOUT_TIME)

    @staticmethod
    def isinplay(player):
        return player.GetTeamNumber() is not Glb.TEAM_SPECTATOR and Thunderball.PLTRACKER[player][TR_SPAWNED] \
               and not Thunderball.PLTRACKER[player][TB_KNOCKEDOUT]

    @staticmethod
    def scrubcolors(msg):
        return re.sub('\^[A-Za-z0-9]', '', msg)
