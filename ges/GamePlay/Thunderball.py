# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Thunderball
# Beta v1.0
# By: DarkDiplomat
#
# Based loosely on concepts layout at https://forums.geshl2.com/index.php/topic,5573.0.html
#
# Synopsis: The Thunderball is set to explode every 25 seconds!
# To start, the Thunderball is given to a random player. The player has to kill an opponent to
# get rid of the Thunderball. If the player is unable to accomplish that they
# are eliminated from the round and the last player to kill them takes ownership
# of the Thunderball; if no last killer, a new random player is selected.
# Survivors get a point each time the ball detonates. Scoring is deathmatch style, all kills gain points.
# The Thunderball carrier gets some advantages to help them transfer the
# Thunderball, such as, increased speed and taking less damage (like an
# adrenaline boost in the panic of being the Thunderball carrier)
#
# Note: Sometimes when a new round starts the timer has already started running
# before the player gains control. This doesn't appear to be something correctable
# in the script unfortunately
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

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
ALERT_COLOR = GEUtil.Color(139, 0, 0, 220)
RELIEF_COLOR = GEUtil.Color(170, 170, 170, 220)
SURVIVE_COLOR = GEUtil.Color(0, 170, 0, 220)
DETONATE_TIME = 25


class Thunderball(GEScenario):
    THUNDERBALL_OWNER = None  # UID of the Player with the Thunderball
    LAST_AGGRESSOR = None  # UID of the player to kill the Thunderball carrier
    PLTRACKER = None  # playertracker
    ASSIGNED_ONCE = False  # check that the Thunderball has been assigned at least once
    CAN_ASSIGN = False

    @staticmethod
    def initialAssignment(timer, type_):
        if type_ == Timer.UPDATE_FINISH:
            Thunderball.CAN_ASSIGN = True

    @staticmethod
    def detonator(timer, type_):  # method to handle when the timer finishes and the Thunderball has detonated
        if type_ == Timer.UPDATE_FINISH:
            if not GERules.IsRoundLocked():  # If this is the first Thunderball death, lock the round
                GERules.LockRound()
            if Thunderball.THUNDERBALL_OWNER is not None:  # this shouldn't happen but just in case
                player = GEPlayer.ToMPPlayer(Thunderball.THUNDERBALL_OWNER)  # convert UID back into a Player
                Thunderball.THUNDERBALL_OWNER = None  # This will be reset later
                Thunderball.PLTRACKER[player][TR_ELIMINATED] = True  # set the player as eliminated
                if not player.IsDead():  # check that they aren't already dead
                    player.AddRoundScore(1)  # Give them an extra point to make up for the loss on forced suicide
                    player.CommitSuicide(True, True)  # undocumented args: explode, force  (not sure what they do)
                player.SetScoreBoardColor(Glb.SB_COLOR_ELIMINATED)  # set the scoreboard color of the player
                GEUtil.PostDeathMessage(_("#GES_GP_YOLT_ELIMINATED", player.GetCleanPlayerName()))  # let everyone know who was taken out by the thunderball
                GEUtil.PopupMessage(player, "#GES_GPH_ELIMINATED_TITLE", "#GES_GPH_ELIMINATED")  # and let the player know they were eliminated
                GEUtil.EmitGameplayEvent("tb_eliminated", str(player.GetUID()), "", "", "", True)
                for player in Thunderball.PLTRACKER.GetPlayers():
                    if Thunderball.isinplay(player):
                        player.AddRoundScore(1)
                        GEUtil.HudMessage(player, "Have a point for surviving!", -1, 0.70, SURVIVE_COLOR, 5.0)

    def __init__(self):
        super(Thunderball, self).__init__()

        self.warmupTimer = GEWarmUp(self)  # init warm up timer
        self.timeTracker = TimerTracker(self)  # init timer tracker
        self.assignmentTimer = self.timeTracker.CreateTimer("assignmentTimer")  # initial timer to give players a chance to start, fixes an issue with server lag in most cases
        self.assignmentTimer.SetUpdateCallback(self.initialAssignment)
        self.thunderballTimer = self.timeTracker.CreateTimer("thunderballTimer")  # init timer
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
        help_obj.SetDescription("The Thunderball is set to explode every 25 seconds! "
                                "To start, the ball is given to a random player. "
                                "The player has to kill an opponent to get rid of the ball. "
                                "If the player is unable to do that they are eliminated from the round "
                                "and the last player to kill them takes the ball; if no last killer, "
                                "a new random player is selected. Survivors are awarded a point after each detonation. "
                                "Scoring is death match style, all kills gain points. The ball carrier gets "
                                "some advantages to help them transfer the ball, such as, increased speed and taking "
                                "less damage.")

    def OnLoadGamePlay( self ):
        # Ensure our sounds are pre-cached
        GEUtil.PrecacheSound("GEGamePlay.Level_Down")  # sound for time running out
        GEUtil.PrecacheSound("GEGamePlay.Woosh")  # sound for passing the thunderball

        GERules.AllowRoundTimer(False)
        self.warmupTimer.Reset()

        # Make sure we don't start out in wait time or have a warmup if we changed gameplay mid-match
        if GERules.GetNumActivePlayers() > 1:
            self.waitingForPlayers = False
            self.warmupTimer.StartWarmup(0)

    def OnUnloadGamePlay(self):
        super(Thunderball, self).OnUnloadGamePlay()
        self.warmupTimer.Reset()
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
            Thunderball.PLTRACKER[player][self.TR_ELIMINATED] = True

    def OnPlayerSpawn(self, player):
        if player.GetTeamNumber() != Glb.TEAM_SPECTATOR:
            Thunderball.PLTRACKER[player][TR_SPAWNED] = True
        if not self.waitingForPlayers and not self.warmupTimer.IsInWarmup() and not GERules.IsIntermission():
            if player.GetUID() == Thunderball.THUNDERBALL_OWNER:
                # initialize or restart the time once the owner is spawned in
                if self.thunderballTimer.state == Timer.STATE_PAUSE:
                    self.thunderballTimer.Start()
                elif self.thunderballTimer.state == Timer.STATE_STOP:
                    self.thunderballTimer.Start(DETONATE_TIME, True)
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
        if self.waitingForPlayers and GERules.GetNumActivePlayers() > 1:
            self.waitingForPlayers = False
            Thunderball.PLTRACKER.SetValueAll(TR_SPAWNED, True)
            if not self.warmupTimer.HadWarmup():
                self.warmupTimer.StartWarmup(15, True)
            else:
                GERules.EndRound(False)

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
            remain = DETONATE_TIME - int(self.thunderballTimer.GetCurrentTime())
            GEUtil.HudMessage(None, "Thunderball Detonation in %0.0f sec" % remain, -1, 0.12, ALERT_COLOR, 1.0, 5)
            if remain == 6:  # it takes a moment to play the sound
                owner = GEPlayer.ToMPPlayer(Thunderball.THUNDERBALL_OWNER)
                GEUtil.PlaySoundToPlayer(owner, "GEGamePlay.Level_Down")
            self.countplayers()

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
            # self.thunderballTimer.Pause()  # Give them a chance to respawn
            if killer:
                Thunderball.LAST_AGGRESSOR = killer.GetUID()
                killer.AddRoundScore(1)  # Give the ballsy player an extra point for taking a risk at being the next ball carrier

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
        if self.thunderballTimer.state == Timer.STATE_PAUSE:
            self.thunderballTimer.Start()
        elif self.thunderballTimer.state == Timer.STATE_STOP:
            self.thunderballTimer.Start(DETONATE_TIME, True)
        if oldowner is not None:
            GEUtil.PlaySoundToPlayer(oldowner, "GEGamePlay.Woosh")
            GEUtil.HudMessage(oldowner, "You have passed the Thunderball!", -1, 0.75, RELIEF_COLOR, 5.0)
            oldowner.SetSpeedMultiplier(1.0)
            Thunderball.LAST_AGGRESSOR = oldowner.GetUID()

    def countplayers(self):
        # Check to see if more than one player is around
        iplayers = []

        for player in Thunderball.PLTRACKER.GetPlayers():
            if self.isinplay(player):
                iplayers.append(player)

        numplayers = len(iplayers)
        # This shouldn't happen, but just in case it does we don't want to overflow the vector...
        if numplayers == 0 and Thunderball.ASSIGNED_ONCE:
            GERules.EndRound()
            return None
        # Only 1 player left standing!
        elif numplayers == 1 and Thunderball.ASSIGNED_ONCE:
            GERules.EndRound()
            return None

    @staticmethod
    def isinplay(player):
        return player.GetTeamNumber() is not Glb.TEAM_SPECTATOR and Thunderball.PLTRACKER[player][TR_SPAWNED] \
               and not Thunderball.PLTRACKER[player][TR_ELIMINATED]
