# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Thunderball
# v1.1
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

TR_ELIMINATED = "eliminated"
TR_SPAWNED = "spawned"
ALERT_COLOR = GEUtil.Color(255, 0, 0, 255)
RELIEF_COLOR = GEUtil.Color(150, 150, 150, 220)
SURVIVE_COLOR = GEUtil.Color(0, 190, 0, 220)
TIMER_COLOR = GEUtil.Color(200, 200, 200, 255)


class Thunderball(GEScenario):
    THUNDERBALL_OWNER = None  # UID of the Player with the Thunderball
    LAST_AGGRESSOR = None  # UID of the player to kill the Thunderball carrier
    PRIV_CARRIER = None
    PLTRACKER = None  # playertracker
    ASSIGNED_ONCE = False  # check that the Thunderball has been assigned at least once
    CAN_ASSIGN = False
    TIMER_ADJUST = False
    DETONATE_TIME = 15
    TIME_TRACK = DETONATE_TIME
    PLAYER_WAIT_TICKER = 0

    @staticmethod
    def initialAssignment(timer, type_):
        if type_ == Timer.UPDATE_FINISH:
            Thunderball.CAN_ASSIGN = True

    @staticmethod
    def detonator(timer, type_):  # method to handle when the timer finishes and the Thunderball has detonated
        if type_ == Timer.UPDATE_FINISH:
            if Thunderball.THUNDERBALL_OWNER is not None:  # this shouldn't happen but just in case
                player = GEPlayer.ToMPPlayer(Thunderball.THUNDERBALL_OWNER)  # convert UID back into a Player
                Thunderball.THUNDERBALL_OWNER = None  # This will be reset later
                Thunderball.PLTRACKER[player][TR_ELIMINATED] = True  # set the player as eliminated
                if not player.IsDead():  # check that they aren't already dead
                    if player.__class__.__name__ == "CGEBotPlayer":  # dirty bots just don't want to die
                        player.AddRoundScore(1)  # Give them an extra point to make up for the loss on forced suicide
                        player.CommitSuicide(True, True)  # undocumented args: explode, force  (not sure what they do)
                    else:
                        player.ForceRespawn()  # Basicly force them out without showing the commit suicide message
                GEUtil.PostDeathMessage("^r%s ^rwas knocked out for a bit!" % player.GetCleanPlayerName())  # let everyone know who was taken out by the thunderball
                GEUtil.PopupMessage(player, "KNOCKED OUT", "You've been temporarily knocked out and will have to wait for %i seconds" % Thunderball.DETONATE_TIME)  # and let the player know they were knocked out
                GEUtil.EmitGameplayEvent("tb_knocked_out", str(player.GetUID()), "", "", "", True)
                for ply in Thunderball.PLTRACKER.GetPlayers():
                    if ply.GetUID() == Thunderball.PRIV_CARRIER:
                        Thunderball.PLTRACKER[ply][TR_ELIMINATED] = False
                        ply.ChangeTeam(Glb.TEAM_NONE, True)
                        ply.ForceRespawn()
                        GEUtil.PostDeathMessage("%s ^1has revived!" % ply.GetCleanPlayerName())
                Thunderball.PRIV_CARRIER = player.GetUID()
            if Thunderball.TIMER_ADJUST:
                timer.Stop()
                Thunderball.TIME_TRACK = Thunderball.DETONATE_TIME
                timer.Start(Thunderball.DETONATE_TIME, True)
                Thunderball.TIMER_ADJUST = False

    def __init__(self):
        super(Thunderball, self).__init__()

        self.warmupTimer = GEWarmUp(self)  # init warm up timer
        self.timeTracker = TimerTracker(self)  # init timer tracker
        self.assignmentTimer = self.timeTracker.CreateTimer("assignmentTimer")  # initial timer to give players a chance to start, fixes an issue with server lag in most cases
        self.assignmentTimer.SetUpdateCallback(self.initialAssignment)
        self.thunderballTimer = self.timeTracker.CreateTimer("thunderballTimer")  # init timer
        self.thunderballTimer.SetUpdateCallback(self.detonator)  # add our callback method to the timer
        self.waitingForPlayers = True
        self.deathPause = False  # CVar Holder
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

        # GERules.AllowRoundTimer(False)

        self.CreateCVar("tb_detonator", "15",
                        "The amount of time in seconds the between Thunderball detonations (default=15)")
        self.CreateCVar("tb_death_pause", "0",
                        "Pauses the Thunderball timer on player death, set to 1 to enable (default 0 [disabled])")

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

    def OnCVarChanged(self, name, oldvalue, newvalue):
        if name == "tb_detonator":
            Thunderball.DETONATE_TIME = clamp(int(newvalue), 10, 60)
            Thunderball.TIMER_ADJUST = True
        elif name == "tb_death_pause":
            self.deathPause = int(newvalue) >= 1

    def OnPlayerConnect(self, player):
        Thunderball.PLTRACKER[player][TR_SPAWNED] = False
        Thunderball.PLTRACKER[player][TR_ELIMINATED] = False

    def CanPlayerChangeTeam(self, player, oldteam, newteam, wasforced):
        if newteam == Glb.TEAM_NONE and Thunderball.PLTRACKER[player][TR_ELIMINATED]:
            GEUtil.PopupMessage(player, "KNOCKED OUT", "You are currently knocked out")
            return False
        return True

    def OnPlayerSpawn(self, player):
        if player.GetTeamNumber() != Glb.TEAM_SPECTATOR:
            Thunderball.PLTRACKER[player][TR_SPAWNED] = True
        if not self.waitingForPlayers and not self.warmupTimer.IsInWarmup() and not GERules.IsIntermission():
            if player.GetUID() == Thunderball.THUNDERBALL_OWNER:
                # initialize or restart the time once the owner is spawned in
                if self.thunderballTimer.state == Timer.STATE_PAUSE:
                    self.thunderballTimer.Start()
                elif self.thunderballTimer.state == Timer.STATE_STOP:
                    self.thunderballTimer.Start(Thunderball.DETONATE_TIME, True)

    def OnRoundBegin(self):
        GEScenario.OnRoundBegin(self)

        # Reset all player's statistics
        Thunderball.PLTRACKER.SetValueAll(TR_ELIMINATED, False)
        GERules.ResetAllPlayerDeaths()
        GERules.ResetAllPlayersScores()

        if GERules.GetNumActivePlayers() <= 1:
            self.waitingForPlayers = True

        if self.warmupTimer.HadWarmup() and not self.waitingForPlayers:
            self.assignmentTimer.Start(5)  # start the initial assignment timer

    def OnRoundEnd(self):
        # Prepare for Reset
        self.thunderballTimer.Stop()
        Thunderball.THUNDERBALL_OWNER = None
        Thunderball.LAST_AGGRESSOR = None
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
            self.assignThunderball(self.chooserandom())
            return

        if self.warmupTimer.HadWarmup() and not self.waitingForPlayers and Thunderball.ASSIGNED_ONCE:
            if Thunderball.THUNDERBALL_OWNER is None:
                if Thunderball.LAST_AGGRESSOR is not None:  # Pass Thunderball to last Aggressor
                    aggressor = GEPlayer.ToMPPlayer(Thunderball.LAST_AGGRESSOR)
                    Thunderball.LAST_AGGRESSOR = None
                    if not Thunderball.PLTRACKER[aggressor][TR_ELIMINATED]:
                        self.assignThunderball(aggressor)
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
                owner = GEPlayer.ToMPPlayer(Thunderball.THUNDERBALL_OWNER)
                GEUtil.PlaySoundToPlayer(owner, "GEGamePlay.Level_Down")
                GEUtil.HudMessage(owner, "YOU HAVE THE THUNDERBALL!", -1, -1, ALERT_COLOR, 3.0, 6)
            self.chooserandom()  # this works to end the round

    def OnPlayerKilled(self, victim, killer, weapon):
        # Let the base scenario behavior handle scoring so we can just worry about the thunderball mechanics.
        GEScenario.OnPlayerKilled(self, victim, killer, weapon)

        if self.waitingForPlayers or self.warmupTimer.IsInWarmup() or GERules.IsIntermission() or not victim:
            return

        # Pass the thunderball off
        if killer.GetUID() == Thunderball.THUNDERBALL_OWNER:
            if self.isinplay(victim):  # Bots don't work well at getting removed
                # self.thunderballTimer.Pause()  # Give them a chance to respawn
                self.assignThunderball(victim, killer)
                Thunderball.LAST_AGGRESSOR = killer.GetUID()
                GEUtil.EmitGameplayEvent("tb_passed", str(killer.GetUID()), str(victim.GetUID()), "", "", True)
        if victim.GetUID() == Thunderball.THUNDERBALL_OWNER:
            if self.deathPause:
                self.thunderballTimer.Pause()  # Give them a chance to respawn
            if killer:
                Thunderball.LAST_AGGRESSOR = killer.GetUID()
                killer.AddRoundScore(1)  # Give the ballsy player an extra point for taking a risk at being the next ball carrier

    def CanPlayerRespawn(self, player):
        if Thunderball.PLTRACKER[player][TR_ELIMINATED]:
            return False
        return True

    def CalculateCustomDamage(self, victim, info, health, armor):
        if victim.GetUID() == Thunderball.THUNDERBALL_OWNER:
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
            if self.isinplay(player):
                iplayers.append(player)

        numplayers = len(iplayers)
        if numplayers == 0 and Thunderball.ASSIGNED_ONCE:
            # This shouldn't happen, but just in case it does we don't want to overflow the vector...
            GERules.EndRound()
            return None
        elif numplayers == 1 and Thunderball.ASSIGNED_ONCE:
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
        GEUtil.HudMessage(newowner, "You have been given Thunderball!", -1, -1, ALERT_COLOR, 3.0, 6)
        GEUtil.HudMessage(Glb.TEAM_OBS, self.scrubcolors(newowner.GetCleanPlayerName()) + " has the Thunderball!",
                          -1, 0.75, TIMER_COLOR, 5.0, 8)
        newowner.SetSpeedMultiplier(1.3)
        Thunderball.ASSIGNED_ONCE = True
        if self.thunderballTimer.state == Timer.STATE_PAUSE:
            self.thunderballTimer.Start()
        elif self.thunderballTimer.state == Timer.STATE_STOP:
            self.thunderballTimer.Start(Thunderball.DETONATE_TIME, True)
        if oldowner is not None:
            GEUtil.PlaySoundToPlayer(oldowner, "GEGamePlay.Woosh")
            GEUtil.HudMessage(oldowner, "You have passed the Thunderball!", -1, 0.73, RELIEF_COLOR, 5.0, 7)
            oldowner.SetSpeedMultiplier(1.0)
            Thunderball.LAST_AGGRESSOR = oldowner.GetUID()

    @staticmethod
    def isinplay(player):
        return player.GetTeamNumber() is not Glb.TEAM_SPECTATOR and Thunderball.PLTRACKER[player][TR_SPAWNED] \
               and not Thunderball.PLTRACKER[player][TR_ELIMINATED]

    @staticmethod
    def scrubcolors(msg):
        return re.sub('\^[A-Za-z0-9]', '', msg)
