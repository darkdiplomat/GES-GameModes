# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# FOR YOUR EYES ONLY
# Version 1.2.0
# Originally by: WNxVirtualMark
# Updated to GE:S v5.0 (API 1.2.0) by: DarkDiplomat
#
# Synopsis: A Briefcase is spawned somewhere on the map at the round
# start. Whoever picks up the Briefcase will be able to eliminate
# other players by killing them. Only the current Briefcase holder
# can eliminate players: if you are killed by anyone else, you will
# respawn normally. (You will also be eliminated if you commit
# suicide.) If the Briefcase holder is killed by another player, he
# or she will drop the Briefcase and respawn, and another player can
# pick up the Briefcase. The last player remaining wins the round!
#
# To score points, you must have the Briefcase. You score 1 point for
# every elimination you make while holding the Briefcase. If you win
# the round, your score will be doubled for the round!
#
# If you pick up the Briefcase, you will also be given some buffs.
# First, you will be given full health and armor upon picking up the
# Briefcase, and your speed will be slightly increased. Second, when
# you eliminate a player, you will regain 1 bar of health (or 1 bar
# of armor, if health is full).
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

from . import GEScenario
from .Utils import _
from .Utils.GEPlayerTracker import GEPlayerTracker
from .Utils.GEWarmUp import GEWarmUp
import GEEntity, GEPlayer, GEUtil, GEWeapon, GEMPGameRules, GEGlobal

USING_API = GEGlobal.API_VERSION_1_2_0


class ForYourEyesOnly(GEScenario):
    TR_ELIMINATED = "eliminated"
    TR_SPAWNED = "spawned"
    CASE_CLASS = 'token_deathmatch'
    CASE_GLOW = GEUtil.Color(14, 139, 237, 200)
    CASE_COLOR = GEUtil.Color(94, 171, 231, 255)

    def __init__(self):
        super(ForYourEyesOnly, self).__init__()

        self.CaseOwnerID = None
        self.waitingForPlayers = True
        self.dmBounty = 0
        self.pltracker = GEPlayerTracker(self)
        self.warmupTimer = GEWarmUp(self)

        # CVars
        self.allScore = True
        self.caseEliminate = True

    def GetPrintName(self):
        return "For Your Eyes Only"

    def GetScenarioHelp(self, help_obj):
        help_obj.SetDescription("At the beginning of the round, a Briefcase is spawned somewhere on the map "
                                "(blue square on the radar). Whoever picks up the Briefcase "
                                "will get full health and armor, increased speed, and will eliminate "
                                "players he or she kills. You will respawn normally if killed by someone without "
                                "the Briefcase. For every elimination you make while holding the Briefcase, you will "
                                "score 1 point (extra if allScore enabled0 and regain 1 bar of health (or armor, "
                                "if health is full). The last remaining player will win the round, and have his or her "
                                "score doubled for the round!")

    def GetGameDescription(self):
        return "For Your Eyes Only"

    def GetTeamPlay(self):
        return GEGlobal.TEAMPLAY_NONE

    def OnLoadGamePlay(self):
        # Spawn a Briefcase token where DM tokens normally spawn, and force radar on.
        GEMPGameRules.GetTokenMgr().SetupToken(self.CASE_CLASS,
                                               team=GEGlobal.TEAM_NONE,
                                               limit=1,
                                               location=GEGlobal.SPAWN_TOKEN,
                                               glow_color=self.CASE_GLOW,
                                               glow_dist=450.0,
                                               allow_switch=True,
                                               respawn_delay=30,
                                               view_model="models/weapons/tokens/v_briefcasetoken.mdl",
                                               world_model="models/weapons/tokens/w_briefcasetoken.mdl",
                                               print_name="Briefcase")
        GEMPGameRules.GetRadar().SetForceRadar(True)

        # Precache all necessary sounds
        GEUtil.PrecacheSound("GEGamePlay.Token_Chime")
        GEUtil.PrecacheSound("GEGamePlay.Token_Capture_Enemy")
        GEUtil.PrecacheSound("GEGamePlay.Token_Drop_Friend")
        GEUtil.PrecacheSound("GEGamePlay.Token_Grab")

        # Help list, to keep track of which players have seen the Briefcase help popups upon case pickup.
        # When a player picks up the case, they will be added to this list.
        self.helplist = []

        self.CreateCVar("fyeo_case_carrier_elimination", "1",
                        "Allows the briefcase holder to be eliminated if killed (0 to disable, 1 to enable)")
        self.CreateCVar("fyeo_all_score", "1",
                        "Allows all players to score points for kills (0 to disable, 1 to enable)")

        # Make sure we don't start out in wait time or have a warm-up if we changed game play mid-match
        if GEMPGameRules.GetNumActivePlayers() >= 2:
            self.waitingForPlayers = False
            self.warmupTimer.StartWarmup(0)

    def OnUnloadGamePlay(self):
        super(ForYourEyesOnly, self).OnUnloadGamePlay()
        self.warmupTimer = None
        self.pltracker = None
        self.warmupTimer.Reset()

    def OnCVarChanged(self, name, oldvalue, newvalue):
        if name == "fyeo_case_carrier_elimination":
            self.caseEliminate = int(newvalue) >= 1
        elif name == "fyeo_all_score":
            self.allScore = int(newvalue) >= 1

    def OnPlayerConnect(self, player):
        self.pltracker[player][self.TR_SPAWNED] = False
        self.pltracker[player][self.TR_ELIMINATED] = False
        if GEMPGameRules.IsRoundLocked():
            self.pltracker[player][self.TR_ELIMINATED] = True

    def OnPlayerDisconnect(self, player):
        if GEMPGameRules.IsRoundLocked() and player.IsActive() and not self.pltracker[player][self.TR_ELIMINATED]:
            self.UpdatePlayerBounty(player)

    def OnPlayerTeamChange(self, player, oldTeam, newTeam):
        if GEMPGameRules.IsRoundLocked():
            if self.IsInPlay(player) and oldTeam != GEGlobal.TEAM_SPECTATOR:
                self.UpdatePlayerBounty(player)
            elif oldTeam == GEGlobal.TEAM_SPECTATOR:
                GEUtil.PopupMessage(player, "#GES_GPH_CANTJOIN_TITLE", "#GES_GPH_CANTJOIN")
            else:
                GEUtil.PopupMessage(player, "#GES_GPH_ELIMINATED_TITLE", "#GES_GPH_ELIMINATED")

            # Changing teams will automatically eliminate you
            self.pltracker[player][self.TR_ELIMINATED] = True

    def OnRoundBegin(self):
        self.dmBounty = 0

        # Reset all player's statistics
        self.pltracker.SetValueAll(self.TR_ELIMINATED, False)

        GEMPGameRules.UnlockRound()
        GEMPGameRules.ResetAllPlayerDeaths()
        GEMPGameRules.ResetAllPlayersScores()

    def OnRoundEnd(self):
        GEMPGameRules.GetRadar().DropAllContacts()
        GEUtil.RemoveHudProgressBar(None, 0)

    def OnPlayerSpawn(self, player):
        if player.GetTeamNumber() != GEGlobal.TEAM_SPECTATOR:
            self.pltracker[player][self.TR_SPAWNED] = True

        # Reset scoreboard color and max speed for player, and make sure they can't go above max health and armor.
        player.SetScoreBoardColor(GEGlobal.SB_COLOR_NORMAL)
        player.SetMaxHealth(int(GEGlobal.GE_MAX_HEALTH))
        player.SetMaxArmor(int(GEGlobal.GE_MAX_ARMOR))
        player.SetSpeedMultiplier(1.0)

        if player.IsInitialSpawn():
            if not self.IsInPlay(player):
                GEUtil.PopupMessage(player, "#GES_GPH_CANTJOIN_TITLE", "#GES_GPH_CANTJOIN")

            GEUtil.PopupMessage(player, "#GES_GPH_OBJECTIVE",
                                        "Pick up the Briefcase, then kill other players to eliminate them. "
                                        "\nLast agent standing wins the round!")
            GEUtil.PopupMessage(player, "#GES_GPH_RADAR",
                                        "Dropped Briefcase = Blue Square \nBriefcase Holder = Blue Dot")

    def OnPlayerKilled(self, victim, killer, weapon):
        if not victim:
            return

        # Let the base scenario behavior handle scoring when the mode isn't in effect
        if self.waitingForPlayers or self.warmupTimer.IsInWarmup() or GEMPGameRules.IsIntermission():
            GEScenario.OnPlayerKilled(self, victim, killer, weapon)
            return

        # Initialize the bounty (if we need to)
        self.InitializePlayerBounty()

        if self.allScore:  # Do death match scoring
            GEScenario.OnPlayerKilled(self, victim, killer, weapon)

        # If someone is killed by the person with the case, they are eliminated.
        if killer.GetUID == self.CaseOwnerID:
            GEMPGameRules.LockRound()
            GEUtil.PostDeathMessage(_("#GES_GP_YOLT_ELIMINATED", victim.GetCleanPlayerName()))
            GEUtil.EmitGameplayEvent("fyeo_eliminated", str(victim.GetUID()), str(killer.GetUID() if killer else ""),
                                     "", "", True)
            GEUtil.PopupMessage(victim, "#GES_GPH_ELIMINATED_TITLE", "#GES_GPH_ELIMINATED")
            GEUtil.PlaySoundToPlayer(killer, "GEGamePlay.Token_Chime")
            GEUtil.PlaySoundToPlayer(victim, "GEGamePlay.Token_Capture_Enemy")

            # Officially eliminate the player
            self.pltracker[victim][self.TR_ELIMINATED] = True
            # Initialize the bounty (if we need to)
            self.InitializePlayerBounty()
            # Update the bounty
            self.UpdatePlayerBounty(victim)

        # Death by world
        if not killer:
            if victim.GetUID == self.CaseOwnerID:
                GEUtil.EmitGameplayEvent("fyeo_suicide", str(victim.GetUID()), "", "", "", True)
                GEUtil.PostDeathMessage("^rThe Briefcase holder committed suicide.")
                GEUtil.PlaySoundToPlayer(victim, "GEGamePlay.Token_Capture_Enemy")

                # Eliminate player on suicide if they are the case holder,
                # unless game is currently "Waiting For Players"
                GEMPGameRules.LockRound()
                GEUtil.PostDeathMessage(_("#GES_GP_YOLT_ELIMINATED", victim.GetCleanPlayerName()))
                GEUtil.EmitGameplayEvent("fyeo_eliminated", str(victim.GetUID()),
                                         str(killer.GetUID if killer else ""), "", "", True)
                GEUtil.PopupMessage(victim, "#GES_GPH_ELIMINATED_TITLE", "#GES_GPH_ELIMINATED")

                # Officially eliminate the player
                self.pltracker[victim][self.TR_ELIMINATED] = True
                # Initialize the bounty (if we need to)
                self.InitializePlayerBounty()
                # Update the bounty
                self.UpdatePlayerBounty(victim)
            return

        if victim == killer:
            # Suicide
            if not self.allScore:
                killer.IncrementScore(-1)
        else:
            if killer.GetUID == self.CaseOwnerID:
                # Case holder scores for every kill he or she gets, double if its with the Briefcase
                if weapon.GetClassname().lower() == "token_deathmatch":
                    killer.IncrementScore(1)  # Add an extra point
                # if death match scoring isn't enabled, give the killer a point
                if not self.allScore:
                    killer.IncrementScore(1)

                # If case holder gets a kill, he/she regains a bar of health (or armor, if health is full).
                if killer.GetHealth() >= killer.GetMaxHealth():
                    killer.SetArmor(int(killer.GetArmor() + killer.GetMaxArmor() / 8))
                else:
                    killer.SetHealth(int(killer.GetHealth() + killer.GetMaxHealth() / 8))

                # If case holder has greater than max health/armor, reset it to max.
                # (Not sure if this is necessary if max health/armor is set to GEglobal.GE_MAX_HEALTH
                # and GEGlobal.GE_MAX_ARMOR on spawn, but just in case...)
                if killer.GetHealth() > killer.GetMaxHealth():
                    killer.SetHealth(int(killer.GetMaxHealth()))
                if killer.GetArmor() > killer.GetMaxArmor():
                    killer.SetArmor(int(killer.GetMaxArmor()))

            elif victim.GetUID == self.CaseOwnerID:
                GEUtil.EmitGameplayEvent("fyeo_caseholder_killed", str(victim.GetUID), str(killer.GetUID))
                GEUtil.PostDeathMessage("^1"+killer.GetPlayerName()+" ^4killed the Briefcase holder.")
                GEUtil.PlaySoundToPlayer(victim, "GEGamePlay.Token_Drop_Friend")
                if self.caseEliminate:
                    GEMPGameRules.LockRound()
                    GEUtil.PostDeathMessage(_("#GES_GP_YOLT_ELIMINATED", victim.GetCleanPlayerName()))
                    GEUtil.EmitGameplayEvent("fyeo_eliminated", str(victim.GetUserID()),
                                             str(killer.GetUserID() if killer else ""), "", "", True)
                    GEUtil.PopupMessage(victim, "#GES_GPH_ELIMINATED_TITLE", "#GES_GPH_ELIMINATED")
                    # Officially eliminate the player
                    self.pltracker[victim][self.TR_ELIMINATED] = True
                    # Initialize the bounty (if we need to)
                    self.InitializePlayerBounty()
                    # Update the bounty
                    self.UpdatePlayerBounty(victim)

    def OnThink(self):
        if GEMPGameRules.GetNumActivePlayers() < 2:
            GEMPGameRules.UnlockRound()
            self.waitingForPlayers = True
            return

        if self.waitingForPlayers and GEMPGameRules.GetNumActivePlayers() > 1:
            self.waitingForPlayers = False
            if not self.warmupTimer.HadWarmup():
                self.warmupTimer.StartWarmup(15.0, True)
            else:
                GEUtil.HudMessage(None, "#GES_GP_GETREADY", -1, -1, GEUtil.Color(255, 255, 255, 255), 2.5)
                GEMPGameRules.EndRound(False)

        if self.warmupTimer.IsInWarmup():
            return

        # Check to see if more than one player is around
        iPlayers = []

        for player in self.pltracker.GetPlayers():
            if self.IsInPlay(player):
                iPlayers.append(player)

        numPlayers = len(iPlayers)

        if numPlayers == 0:
            # This shouldn't happen, but just in case it does we don't want to overflow the vector...
            GEMPGameRules.EndRound()
        if numPlayers == 1:
            # Make last remaining player the winner, and double his or her score.
            GEMPGameRules.SetPlayerWinner(iPlayers[0])
            iPlayers[0].IncrementScore(iPlayers[0].GetScore())
            GEMPGameRules.EndRound()

    def CanPlayerRespawn(self, player):
        if GEMPGameRules.IsRoundLocked():
            if self.pltracker[player][self.TR_ELIMINATED]:
                player.SetScoreBoardColor(GEGlobal.SB_COLOR_ELIMINATED)
                return False

        player.SetScoreBoardColor(GEGlobal.SB_COLOR_NORMAL)
        return True

    def InitializePlayerBounty(self):
        if self.dmBounty == 0:
            self.dmBounty = GEMPGameRules.GetNumInRoundPlayers() - 1
            # Subtract one because we don't count the local player as a "foe"
            GEUtil.InitHudProgressBar(GEGlobal.TEAM_NONE, 0, "#GES_GP_FOES", GEGlobal.HUDPB_SHOWVALUE,
                                      self.dmBounty, -1, 0.02, 0, 10, GEUtil.Color(170, 170, 170, 220),
                                      self.dmBounty)

    def UpdatePlayerBounty(self, victim):
        self.dmBounty -= 1

        # Remember, we take 1 off to account for the local player
        GEUtil.UpdateHudProgressBar(GEGlobal.TEAM_NONE, 0, self.dmBounty)

    def IsInPlay(self, player):
        return player.GetTeamNumber() is not GEGlobal.TEAM_SPECTATOR \
               and self.pltracker[player][self.TR_SPAWNED] and not self.pltracker[player][self.TR_ELIMINATED]

    def OnTokenSpawned(self, token):
        GEMPGameRules.GetRadar().AddRadarContact(token, GEGlobal.RADAR_TYPE_TOKEN, True, "", self.CASE_COLOR)

    def OnTokenPicked(self, token, player):
        radar = GEMPGameRules.GetRadar()
        radar.DropRadarContact(token)
        radar.AddRadarContact(player, GEGlobal.RADAR_TYPE_PLAYER, True, "", self.CASE_COLOR)

        GEUtil.PlaySoundToPlayer(player, "GEGamePlay.Token_Grab")
        GEUtil.PostDeathMessage("^1"+player.GetPlayerName()+" ^ipicked up the Briefcase!")
        GEUtil.HudMessage(player, "You have the Briefcase!", -1, 0.75, self.CASE_COLOR, 3.0)
        GEUtil.EmitGameplayEvent("fyeo_case_picked", str(player.GetUserID()), "", "", "", True)

        player.SetScoreBoardColor(GEGlobal.SB_COLOR_GOLD)
        self.CaseOwnerID = player.GetUID

        # Case holder gets full health and armor upon case pickup, and gets slightly increased speed.
        player.SetHealth(int(GEGlobal.GE_MAX_HEALTH))
        player.SetArmor(int(GEGlobal.GE_MAX_ARMOR))
        player.SetSpeedMultiplier(1.15)

        # Explain to player what to do, now that he or she has the case. Will only show on first case pickup.
        if self.helplist.count(player.GetUID):
            return

        GEUtil.PopupMessage(player, "Briefcase", "You have the Briefcase! \nKill other players to eliminate them.")
        GEUtil.PopupMessage(player, "Scoring",
                                    "You score 1 point for every player you eliminate. "
                                    "\nIf you win the round, your score will be doubled for the round!")
        GEUtil.PopupMessage(player, "Buffs",
                                    "Upon picking up the Briefcase, you received full health and armor, "
                                    "plus increased speed. "
                                    "\nFor every player you eliminate, 1 bar of health (or armor, if health is full) "
                                    "will be restored.")
        self.helplist.append(player.GetUID)

    def OnTokenDropped(self, token, player):
        radar = GEMPGameRules.GetRadar()
        radar.DropRadarContact(player)
        radar.AddRadarContact(token, GEGlobal.RADAR_TYPE_TOKEN, True, "", self.CASE_COLOR)

        GEUtil.PostDeathMessage("^1"+player.GetCleanPlayerName()+" ^idropped the Briefcase!")
        player.SetScoreBoardColor(GEGlobal.SB_COLOR_NORMAL)
        self.CaseOwnerID = None

    def OnTokenRemoved(self, token):
        GEMPGameRules.GetRadar().DropRadarContact(token)
        GEMPGameRules.GetRadar().DropRadarContact(token.GetOwner())
        self.CaseOwnerID = None
