from . import GEScenario
from .Utils.GEWarmUp import GEWarmUp
from .Utils.GEPlayerTracker import GEPlayerTracker
from .Utils import GetPlayers
from GEUtil import Color
from random import choice
import GEPlayer, GEUtil, GEMPGameRules as GERules, GEGlobal, GEWeapon

# Agent Under Fire
# Coded by Troy
# Updated by DarkDiplomat
#/////////////////////////// Scenario Data ///////////////////////////

USING_API = GEGlobal.API_VERSION_1_2_0

mi6WeaponList = [( "weapon_pp7", "PP7s", 100 ), ( "weapon_zmg", "ZMGs", 400 ), ( "weapon_kf7", "KF7s", 400 ), ( "weapon_ar33", "AR33s", 400 ), ( "weapon_moonraker", "Moonraker Lasers", 0 )]
janusWeaponList = [( "weapon_dd44", "DD44s", 100 ), ( "weapon_d5k", "D5Ks", 400 ), ( "weapon_kf7", "KF7s", 400 ), ( "weapon_rcp90", "RC-P90s", 400 ), ( "weapon_moonraker", "Moonraker Lasers", 0 )]
mi6MaxLevel = len( mi6WeaponList ) - 1
janusMaxLevel = len( janusWeaponList ) - 1


class AgentUnderFire( GEScenario ):
    TR_ELIMINATED = "eliminated"
    TR_SPAWNED = "spawned"
    TR_GUARDHELP = "guardhelp"
    TR_VIPHELP = "viphelp"
    TR_ADRENALINE = "adrenaline"

    def __init__( self ):
        super( AgentUnderFire, self ).__init__()

        #///// Team Variables /////

        # Levels
        self.MI6Level = 0
        self.JanusLevel = 0

        # Default Costumes
        self.MI6DefaultCostume = "006_mi6"
        self.JanusDefaultCostume = "boris"

        #///// VIP Variables /////

        # Costumes
        self.BondCostume = "bond"
        self.OurumovCostume = "ourumov"

        # Costume Caches
        self.BondCostumeCache = ""
        self.OurumovCostumeCache = ""

        # Skin Caches
        self.BondSkinCache = 0
        self.OurumovSkinCache = 0

        # Costume Overrides
        self.BondCostumeOverride = 0
        self.OurumovCostumeOverride = 0

        # UIDs
        self.BondUID = 0
        self.OurumovUID = 0

        # Previous UIDs
        self.BondPreviousUID = 0
        self.OurumovPreviousUID = 0

        # Adrenaline Timers
        self.BondAdrenalineTimer = 100
        self.OurumovAdrenalineTimer = 100

        # Adrenaline Timer Copies
        self.BondAdrenalineTimerCopy = self.BondAdrenalineTimer
        self.OurumovAdrenalineTimerCopy = self.OurumovAdrenalineTimer

        # Objective Colors
        self.BondObjective = Color( 94, 171, 231, 255 )
        self.OurumovObjective = Color( 206, 43, 43, 255 )

        # HUD Colors
        self.HudShout = Color( 240, 200, 120, 170 )
        self.HudAdrenaline = Color( 220, 220, 220, 240 )

        #///// Miscellaneous Variables /////

        # Warmup
        self.WaitingForPlayers = True
        self.notice_WaitingForPlayers = 0
        self.warmupTimer = GEWarmUp( self )

        # End Round
        self.EndRoundTimer = 0
        self.EndRoundTime = 34
        self.EndRound = False
        self.RoundActive = False
        self.HasEnded = False

        # Player Tracker
        self.pltracker = GEPlayerTracker( self )

        # CVar Holder
        self.Adrenaline = True
        self.leveldown = True

    def OnUnloadGamePlay( self ):
        super(AgentUnderFire, self).OnUnloadGamePlay()
        self.warmupTimer = None
        self.pltracker = None

    def GetPrintName( self ):
        return "Agent Under Fire"

    def GetScenarioHelp( self, help_obj ):
        help_obj.SetDescription( "At the start of the round, a player is randomly selected from MI6 and Janus to be their team's VIP. The VIPs are given a shotgun and a usable adrenaline shot, while their bodyguards are given a level 1 weapon. In order for the guards to level up to the next weapon, their VIP must kill an opponent. If a VIP dies, they will be eliminated and one of their guards will take their place. The first team to kill all of their opposing team's VIPs wins the round.\n\nType !level to print your team's current level.\nType !weapons to print your team's weapon levels.\n\nTeamplay: Always" )

    def GetGameDescription( self ):
        return "Agent Under Fire"

    def GetTeamPlay( self ):
        return GEGlobal.TEAMPLAY_ALWAYS

    def OnLoadGamePlay( self ):
        GEUtil.PrecacheSound( "GEGamePlay.Token_Drop_Friend" )
        GEUtil.PrecacheSound( "GEGamePlay.Token_Grab" )
        GEUtil.PrecacheSound( "GEGamePlay.Token_Grab_Enemy" )
        GEUtil.PrecacheSound("GEGamePlay.Level_Up")
        GEUtil.PrecacheSound("GEGamePlay.Level_Down")

        self.CreateCVar( "auf_adrenaline", "1", "Give the VIPs a usable adrenaline shot. (Use 0 to disable)" )
        self.CreateCVar( "auf_warmuptime", "20", "The warmup time in seconds. (Use 0 to disable)" )
        self.CreateCVar("auf_leveldown", "1", "Level down the team when they kill the opposing VIP (Use 0 to disable)")

        GERules.SetExcludedCharacters( "bond, ourumov" )

    def OnCVarChanged( self, name, oldvalue, newvalue ):
        if name == "auf_adrenaline":
            val = int( newvalue )
            if val == 0 and self.Adrenaline:
                self.Adrenaline = False
                GEUtil.HudMessage( None, "Adrenaline was disabled!", -1, -1, Color( 255, 255, 255, 255 ), 4.0 )
                if not self.WaitingForPlayers and not self.warmupTimer.IsInWarmup():
                    if not self.HasEnded:
                        self.HasEnded = True
                        GERules.EndRound()
            elif val != 0 and not self.Adrenaline:
                self.Adrenaline = True
                GEUtil.HudMessage( None, "Adrenaline was enabled!", -1, -1, Color( 255, 255, 255, 255 ), 4.0 )
                if not self.WaitingForPlayers and not self.warmupTimer.IsInWarmup():
                    if not self.HasEnded:
                        self.HasEnded = True
                        GERules.EndRound()
        elif name == "auf_warmuptime":
            if self.warmupTimer.IsInWarmup():
                val = int( newvalue )
                self.warmupTimer.StartWarmup( val )
                if val <= 0:
                    if not self.HasEnded:
                        self.HasEnded = True
                        GERules.EndRound( False )
        elif name == "auf_leveldown":
            val = int(newvalue)
            if val >= 1:
                self.leveldown = True

    def OnRoundBegin( self ):
        GEScenario.OnRoundBegin( self )

        GERules.AllowRoundTimer( False )
        GERules.UnlockRound()
        GERules.DisableWeaponSpawns()
        GERules.DisableAmmoSpawns()

        # Reset the variables
        self.MI6Level = 0
        self.JanusLevel = 0
        self.EndRoundTimer = 0
        self.EndRound = False
        self.RoundActive = True
        self.HasEnded = False

        for player in GetPlayers():
            self.pltracker.SetValue( player, self.TR_ADRENALINE, False )
            self.pltracker.SetValue( player, self.TR_ELIMINATED, False )
            if player.GetTeamNumber() != GEGlobal.TEAM_SPECTATOR:
                self.PrintCurLevel( player )

        # VIPs
        self.DisemBond()
        self.DisemOurumov()
        self.EmBondRandomly()
        self.EmOurumovRandomly()

    def OnRoundEnd( self ):
        self.HasEnded = True
        self.RoundActive = False

    def OnPlayerConnect( self, player ):
        # Ensures that the tracker values are set appropriately
        self.pltracker.SetValue( player, self.TR_SPAWNED, False )
        self.pltracker.SetValue( player, self.TR_GUARDHELP, False )
        self.pltracker.SetValue( player, self.TR_VIPHELP, False )
        self.pltracker.SetValue( player, self.TR_ADRENALINE, False )

        if GERules.IsRoundLocked():
            self.pltracker.SetValue( player, self.TR_ELIMINATED, True )
        else:
            self.pltracker.SetValue( player, self.TR_ELIMINATED, False )

    def OnPlayerDisconnect( self, player ):
        if player.GetUID() == self.BondUID:
            self.DisemBond()
            self.EmBondRandomly()
        elif player.GetUID() == self.OurumovUID:
            self.DisemOurumov()
            self.EmOurumovRandomly()

    def OnPlayerSpawn( self, player ):
        if player.GetUID() == self.BondUID or player.GetUID() == self.OurumovUID:
            self.GiveEquipment( player )
            player.SetSpeedMultiplier( 1.0 )
        else:
            # Costume prevention
            if player.GetPlayerModel() == self.BondCostume:
                player.SetPlayerModel( self.MI6DefaultCostume, 0 )
            elif player.GetPlayerModel() == self.OurumovCostume:
                player.SetPlayerModel( self.JanusDefaultCostume, 0 )

            self.GivePlayerWeapons( player )
            player.SetSpeedMultiplier( 1.0 )
            player.SetScoreBoardColor( GEGlobal.SB_COLOR_NORMAL )
            # Show the bodyguard's help
            if not self.WaitingForPlayers and not self.warmupTimer.IsInWarmup() and not self.pltracker.GetValue( player, self.TR_GUARDHELP ):
                if player.GetTeamNumber() == GEGlobal.TEAM_MI6:
                    GEUtil.PopupMessage( player, "Guard's Objective", "You are James Bond's bodyguard. Protect him from physical harm." )
                    GEUtil.PopupMessage( player, "#GES_GPH_RADAR", "James Bond = Blue Star" )
                    self.pltracker.SetValue( player, self.TR_GUARDHELP, True )
                elif player.GetTeamNumber() == GEGlobal.TEAM_JANUS:
                    GEUtil.PopupMessage( player, "Guard's Objective", "You are General Ourumov's bodyguard. Protect him from physical harm." )
                    GEUtil.PopupMessage( player, "#GES_GPH_RADAR", "General Ourumov = Red Star" )
                    self.pltracker.SetValue( player, self.TR_GUARDHELP, True )

        if player.GetTeamNumber() != GEGlobal.TEAM_SPECTATOR:
            self.pltracker.SetValue( player, self.TR_SPAWNED, True )

    def CanPlayerChangeTeam( self, player, oldteam, newteam, wasforced ):
        if player.GetUID() == self.BondUID or player.GetUID() == self.OurumovUID:
            GEUtil.HudMessage( player, "You cannot change teams.", -1, 0.1, self.HudShout, 2.0 )
            return False
        elif GERules.IsRoundLocked():
            if oldteam == GEGlobal.TEAM_SPECTATOR:
                GEUtil.PopupMessage( player, "#GES_GPH_CANTJOIN_TITLE", "#GES_GPH_CANTJOIN" )
            else:
                GEUtil.PopupMessage( player, "#GES_GPH_ELIMINATED_TITLE", "#GES_GPH_ELIMINATED" )

            # Changing teams will automatically eliminate you
            self.pltracker.SetValue( player, self.TR_ELIMINATED, True )

        return True

    def OnPlayerKilled( self, victim, killer, weapon ):
        if self.EndRound or not victim:
            return

        if victim == self.BondUID or victim == self.OurumovUID:
            GERules.LockRound()
            GEUtil.ClientPrint( None, GEGlobal.HUD_PRINTTALK, "#GES_GP_YOLT_ELIMINATED", victim.GetPlayerName() )
            GEUtil.EmitGameplayEvent( "auf_eliminated", "%i" % victim.GetUserID(), "%i" % ( killer.GetUserID() if killer else -1 ) )
            GEUtil.PopupMessage( victim, "#GES_GPH_ELIMINATED_TITLE", "#GES_GPH_ELIMINATED" )

            # Officially eliminate the player
            self.pltracker.SetValue( victim, self.TR_ELIMINATED, True )

        if not killer or victim == killer:
            # World kill or suicide
            if victim == self.BondUID:
                GEUtil.EmitGameplayEvent( "auf_bond_suicide", "%i" % victim.GetUserID() )
                victim.AddRoundScore( -2 )
                self.DisemBond()
                self.EmBondRandomly()
            elif victim == self.OurumovUID:
                GEUtil.EmitGameplayEvent( "auf_ourumov_suicide", "%i" % victim.GetUserID() )
                victim.AddRoundScore( -2 )
                self.DisemOurumov()
                self.EmOurumovRandomly()
            else:
                victim.AddRoundScore( -1 )
        elif GERules.IsTeamplay() and killer.GetTeamNumber() == victim.GetTeamNumber():
            # Same-team kill
            if victim == self.BondUID:
                GEUtil.EmitGameplayEvent( "auf_bond_team_kill", "%i" % victim.GetUserID(), "%i" % killer.GetUserID() )
                killer.AddRoundScore( -2 )
                self.DisemBond()
                self.EmBondRandomly()
            elif victim == self.OurumovUID:
                GEUtil.EmitGameplayEvent( "auf_ourumov_team_kill", "%i" % victim.GetUserID(), "%i" % killer.GetUserID() )
                killer.AddRoundScore( -2 )
                self.DisemOurumov()
                self.EmOurumovRandomly()
            else:
                killer.AddRoundScore( -1 )
        else:
            # Normal kill
            team = GERules.GetTeam( killer.GetTeamNumber() )
            if victim == self.BondUID:
                GEUtil.EmitGameplayEvent( "auf_bond_killed", "%i" % victim.GetUserID(), "%i" % killer.GetUserID() )
                self.DoScoring(killer, team, 2)
                self.DisemBond()
                self.EmBondRandomly()
                if killer == self.OurumovUID:
                    GEUtil.EmitGameplayEvent( "auf_janus_level_up", "%i" % killer.GetUserID(), "%i" % victim.GetUserID() )
                    self.IncrementJanus()
                else:
                    self.DecrementJanus()
            elif victim == self.OurumovUID:
                GEUtil.EmitGameplayEvent( "auf_ourumov_killed", "%i" % victim.GetUserID(), "%i" % killer.GetUserID() )
                self.DoScoring(killer, team, 2)
                self.DisemOurumov()
                self.EmOurumovRandomly()
                if killer == self.BondUID:
                    GEUtil.EmitGameplayEvent( "auf_mi6_level_up", "%i" % killer.GetUserID(), "%i" % victim.GetUserID() )
                    self.IncrementMI6()
                else:
                    self.DecrementMI6()
            elif killer == self.BondUID:
                GEUtil.EmitGameplayEvent( "auf_mi6_level_up", "%i" % killer.GetUserID(), "%i" % victim.GetUserID() )
                self.DoScoring(killer, team, 1)
                self.IncrementMI6()
            elif killer == self.OurumovUID:
                GEUtil.EmitGameplayEvent( "auf_janus_level_up", "%i" % killer.GetUserID(), "%i" % victim.GetUserID() )
                self.DoScoring(killer, team, 1)
                self.IncrementJanus()
            else:
                self.DoScoring(killer, team, 1)

    def OnThink( self ):
        # Check for insufficient player count
        if GERules.GetNumActiveTeamPlayers( GEGlobal.TEAM_MI6 ) < 2 or GERules.GetNumActiveTeamPlayers( GEGlobal.TEAM_JANUS ) < 2:
            if not self.WaitingForPlayers:
                self.notice_WaitingForPlayers = 0
                if not self.HasEnded:
                    self.HasEnded = True
                    GERules.EndRound()
            elif GEUtil.GetTime() > self.notice_WaitingForPlayers:
                GEUtil.HudMessage( None, "#GES_GP_WAITING", -1, -1, Color( 255, 255, 255, 255 ), 2.5, 1 )
                self.notice_WaitingForPlayers = GEUtil.GetTime() + 12.5

            self.warmupTimer.Reset()
            self.WaitingForPlayers = True
            return
        elif self.WaitingForPlayers:
            self.WaitingForPlayers = False
            if not self.warmupTimer.HadWarmup():
                self.warmupTimer.StartWarmup( int( GEUtil.GetCVarValue( "auf_warmuptime" ) ), True )
                if self.warmupTimer.IsInWarmup():
                    GEUtil.EmitGameplayEvent( "auf_startwarmup" )
            else:
                if not self.HasEnded:
                    self.HasEnded = True
                    GERules.EndRound( False )
            return

        # Bond Adrenaline
        if self.BondUID != 0:
            player = GEPlayer.ToMPPlayer( self.BondUID )
            if player is not None and self.pltracker.GetValue( player, self.TR_ADRENALINE ):
                self.BondAdrenalineTimer -= 1
                GEUtil.UpdateHudProgressBar( player, 0, self.BondAdrenalineTimer )
                if self.BondAdrenalineTimer == 0:
                    player.SetSpeedMultiplier( 1.0 )
                    self.pltracker.SetValue( player, self.TR_ADRENALINE, False )

        # Ourumov Adrenaline
        if self.OurumovUID != 0:
            player = GEPlayer.ToMPPlayer( self.OurumovUID )
            if player is not None and self.pltracker.GetValue( player, self.TR_ADRENALINE ):
                self.OurumovAdrenalineTimer -= 1
                GEUtil.UpdateHudProgressBar( player, 1, self.OurumovAdrenalineTimer )
                if self.OurumovAdrenalineTimer == 0:
                    player.SetSpeedMultiplier( 1.0 )
                    self.pltracker.SetValue( player, self.TR_ADRENALINE, False )

        # Check to see if the round is over!
        if GERules.IsTeamplay() and not self.EndRound:
            iMI6Players = []
            iJanusPlayers = []

            for player in GetPlayers():
                if self.IsInPlay( player ):
                    if player.GetTeamNumber() == GEGlobal.TEAM_MI6:
                        iMI6Players.append( player )
                    elif player.GetTeamNumber() == GEGlobal.TEAM_JANUS:
                        iJanusPlayers.append( player )

            numMI6Players = len( iMI6Players )
            numJanusPlayers = len( iJanusPlayers )

            # The VIPs cannot be chosen
            if numMI6Players == 0 and numJanusPlayers == 0:
                GEUtil.HudMessage( None, "Stalemate", -1, -1, self.HudShout, 2.0 )
                self.EndRound = True
                self.EndRoundTimer = self.EndRoundTime
            # MI6's VIP cannot be chosen
            elif numMI6Players == 0 and numJanusPlayers > 0:
                GEUtil.HudMessage( None, "MI6 concedes.", -1, -1, self.HudShout, 2.0 )
                janus = GERules.GetTeam( GEGlobal.TEAM_JANUS )
                janus.AddRoundScore( 5 )
                GERules.SetTeamWinner( janus )
                self.EndRound = True
                self.EndRoundTimer = self.EndRoundTime
            # Janus' VIP cannot be chosen
            elif numMI6Players > 0 and numJanusPlayers == 0:
                GEUtil.HudMessage( None, "Janus concedes.", -1, -1, self.HudShout, 2.0 )
                mi6 = GERules.GetTeam( GEGlobal.TEAM_MI6 )
                mi6.AddRoundScore( 5 )
                GERules.SetTeamWinner( mi6 )
                self.EndRound = True
                self.EndRoundTimer = self.EndRoundTime

        # End Round Timer
        if self.EndRoundTimer > 0:
            self.EndRoundTimer -= 1
            if self.EndRoundTimer == 0:
                if not self.HasEnded:
                    self.HasEnded = True
                    GERules.EndRound()

    def CanPlayerRespawn( self, player ):
        if self.pltracker.GetValue( player, self.TR_ELIMINATED ):
            player.SetScoreBoardColor( GEGlobal.SB_COLOR_ELIMINATED )
            return False
        return True

    def CanPlayerChangeChar( self, player, ident ):
        if player is None:
            return False

        if player.GetUID() == self.BondUID and self.BondCostumeOverride == 0 or player.GetUID() == self.OurumovUID and self.OurumovCostumeOverride == 0:
            return ident == self.BondCostume if ( player.GetUID() == self.BondUID ) else ident == self.OurumovCostume

        return True

    def CanPlayerHaveItem( self, player, item ):
        weapon = GEWeapon.ToGEWeapon( item )
        if weapon:
            name = weapon.GetClassname().lower()

            if player.GetUID() == self.BondUID or player.GetUID() == self.OurumovUID:
                if name == "weapon_shotgun" or name == "weapon_knife" or name == "weapon_slappers":
                    return True
            elif player.GetTeamNumber() == GEGlobal.TEAM_MI6:
                lvl = self.MI6Level
                if name == mi6WeaponList[lvl][0] or name == "weapon_knife" or name == "weapon_slappers":
                    return True
            elif player.GetTeamNumber() == GEGlobal.TEAM_JANUS:
                lvl = self.JanusLevel
                if name == janusWeaponList[lvl][0] or name == "weapon_knife" or name == "weapon_slappers":
                    return True

            return False

        return True

    def OnPlayerSay( self, player, text ):
        text = text.lower()

        if text == "!level":
            self.PrintCurLevel( player )
            return True
        elif text == "!weapons":
            self.PrintWeapons( player )
            return True
        elif text == "!voodoo":
            if self.Adrenaline:
                if player.GetUID() == self.BondUID:
                    if self.BondAdrenalineTimer < self.BondAdrenalineTimerCopy:
                        GEUtil.ClientPrint( player, GEGlobal.HUD_PRINTTALK, "^lYour adrenaline shot is depleted." )
                    elif not self.RoundActive:
                        GEUtil.ClientPrint( player, GEGlobal.HUD_PRINTTALK, "^lThe round is inactive." )
                    else:
                        player.SetSpeedMultiplier( 1.5 )
                        self.pltracker.SetValue( player, self.TR_ADRENALINE, True )
                        GEUtil.ClientPrint( None, GEGlobal.HUD_PRINTTALK, "^iJames Bond ^1injected an adrenaline shot!" )
                        GEUtil.PlaySoundToPlayer( player, "GEGamePlay.Token_Grab_Enemy" )
                    return True
                elif player.GetUID() == self.OurumovUID:
                    if self.OurumovAdrenalineTimer < self.OurumovAdrenalineTimerCopy:
                        GEUtil.ClientPrint( player, GEGlobal.HUD_PRINTTALK, "^lYour adrenaline shot is depleted." )
                    elif not self.RoundActive:
                        GEUtil.ClientPrint( player, GEGlobal.HUD_PRINTTALK, "^lThe round is inactive." )
                    else:
                        player.SetSpeedMultiplier( 1.5 )
                        self.pltracker.SetValue( player, self.TR_ADRENALINE, True )
                        GEUtil.ClientPrint( None, GEGlobal.HUD_PRINTTALK, "^rGeneral Ourumov ^1injected an adrenaline shot!" )
                        GEUtil.PlaySoundToPlayer( player, "GEGamePlay.Token_Grab_Enemy" )
                    return True
                else:
                    GEUtil.ClientPrint( player, GEGlobal.HUD_PRINTTALK, "^lYou are not the VIP." )
                    return True
            elif not self.Adrenaline:
                if player.GetUID() == self.BondUID or player.GetUID() == self.OurumovUID:
                    GEUtil.ClientPrint( player, GEGlobal.HUD_PRINTTALK, "^lAdrenaline is disabled." )
                else:
                    GEUtil.ClientPrint( player, GEGlobal.HUD_PRINTTALK, "^lYou are not the VIP." )
                return True

        return False

    def CanRoundEnd( self ):
        return self.EndRound

    def CanMatchEnd( self ):
        return not self.RoundActive

    def IsInPlay( self, player ):
        return player.GetTeamNumber() != GEGlobal.TEAM_SPECTATOR and self.pltracker.GetValue( player, self.TR_SPAWNED ) and not self.pltracker.GetValue( player, self.TR_ELIMINATED )

#/////////////////////////// VIP Functions ///////////////////////////

    def DisemBond( self ):
        if self.BondUID != 0:
            player = GEPlayer.ToMPPlayer( self.BondUID )
            if player is not None:
                # Override the costume control
                self.BondCostumeOverride = 1
                player.SetPlayerModel( self.BondCostumeCache, self.BondSkinCache )
                self.BondCostumeOverride = 0
                GEUtil.RemoveHudProgressBar(player, 0)
            # Finally, set the previous UID and reset the UID
            self.BondPreviousUID = self.BondUID
            self.BondUID = 0

    def DisemOurumov( self ):
        if self.OurumovUID != 0:
            player = GEPlayer.ToMPPlayer( self.OurumovUID )
            if player is not None:
                # Override the costume control
                self.OurumovCostumeOverride = 1
                player.SetPlayerModel( self.OurumovCostumeCache, self.OurumovSkinCache )
                self.OurumovCostumeOverride = 0
                GEUtil.RemoveHudProgressBar(player, 1)
            # Finally, set the previous UID and reset the UID
            self.OurumovPreviousUID = self.OurumovUID
            self.OurumovUID = 0

    def EmBondRandomly( self ):
        if self.WaitingForPlayers or self.EndRound:
            return

        players = self.ListPlayers( GEGlobal.TEAM_MI6, self.BondPreviousUID )
        if len( players ) > 0:
            self.BondUID = choice( players )
            self.EmBond()

    def EmOurumovRandomly( self ):
        if self.WaitingForPlayers or self.EndRound:
            return

        players = self.ListPlayers( GEGlobal.TEAM_JANUS, self.OurumovPreviousUID )
        if len( players ) > 0:
            self.OurumovUID = choice( players )
            self.EmOurumov()

    def EmBond( self ):
        player = GEPlayer.ToMPPlayer( self.BondUID )
        if player is not None:
            # Setup the VIP
            self.BondCostumeCache = player.GetPlayerModel()
            self.BondSkinCache = player.GetSkin()
            player.SetPlayerModel( self.BondCostume, 0 )
            if self.Adrenaline:
                self.BondAdrenalineTimer = self.BondAdrenalineTimerCopy
                GEUtil.InitHudProgressBar( player, 0, "Adrenaline", 1, self.BondAdrenalineTimer, -1, .04, 130, 12, self.HudAdrenaline )
                GEUtil.UpdateHudProgressBar( player, 0, self.BondAdrenalineTimer )
            GERules.GetRadar().AddRadarContact( player, GEGlobal.RADAR_TYPE_PLAYER, True, "sprites/hud/radar/star" )
            GERules.GetRadar().SetupObjective( player, GEGlobal.TEAM_NONE, "", "James Bond", self.BondObjective, 300 )
            self.GiveEquipment( player )
            player.SetScoreBoardColor( GEGlobal.SB_COLOR_WHITE )
            # Show the VIP's help
            if not self.pltracker.GetValue( player, self.TR_VIPHELP ):
                GEUtil.PopupMessage( player, "Bond's Objective", "You are the VIP. You must prolong your life as long as possible." )
                if self.Adrenaline:
                    GEUtil.PopupMessage( player, "Adrenaline", "Once per round, you have the ability to temporarily increase your walking speed by pressing your voodoo key (default g)." )
                GEUtil.PopupMessage( player, "Level Ups", "Killing an opponent will level up your guard's weapons." )
                self.pltracker.SetValue( player, self.TR_VIPHELP, True )

    def EmOurumov( self ):
        player = GEPlayer.ToMPPlayer( self.OurumovUID )
        if player is not None:
            # Setup the VIP
            self.OurumovCostumeCache = player.GetPlayerModel()
            self.OurumovSkinCache = player.GetSkin()
            player.SetPlayerModel( self.OurumovCostume, 0 )
            if self.Adrenaline:
                self.OurumovAdrenalineTimer = self.OurumovAdrenalineTimerCopy
                GEUtil.InitHudProgressBar( player, 1, "Adrenaline", 1, self.OurumovAdrenalineTimer, -1, .04, 130, 12, self.HudAdrenaline )
                GEUtil.UpdateHudProgressBar( player, 1, self.OurumovAdrenalineTimer )
            GERules.GetRadar().AddRadarContact( player, GEGlobal.RADAR_TYPE_PLAYER, True, "sprites/hud/radar/star" )
            GERules.GetRadar().SetupObjective( player, GEGlobal.TEAM_NONE, "", "General Ourumov", self.OurumovObjective, 300 )
            self.GiveEquipment( player )
            player.SetScoreBoardColor( GEGlobal.SB_COLOR_WHITE )
            # Show the VIP's help
            if not self.pltracker.GetValue( player, self.TR_VIPHELP ):
                GEUtil.PopupMessage( player, "Ourumov's Objective", "You are the VIP. You must prolong your life as long as possible." )
                if self.Adrenaline:
                    GEUtil.PopupMessage( player, "Adrenaline", "Once per round, you have the ability to temporarily increase your walking speed by pressing your voodoo key (default g)." )
                GEUtil.PopupMessage( player, "Level Ups", "Killing an opponent will level up your guard's weapons." )
                self.pltracker.SetValue( player, self.TR_VIPHELP, True )

    def GiveEquipment( self, player ):
        if not player:
            return

        player.StripAllWeapons()
        startArmed = int( GEUtil.GetCVarValue( "ge_startarmed" ) )

        if startArmed == 0:
            player.GiveNamedWeapon( "weapon_slappers", 0 )
        else:
            player.GiveNamedWeapon( "weapon_slappers", 0 )
            player.GiveNamedWeapon( "weapon_knife", 0 )

        player.GiveNamedWeapon( "weapon_shotgun", 80 )
        player.WeaponSwitch( "weapon_shotgun" )
        player.SetArmor( int( GEGlobal.GE_MAX_ARMOR ) )

    def ListPlayers( self, team, ignore ):
        listing = []
        for i in range( 32 ):
            player = GEPlayer.GetMPPlayer( i )
            if player and self.IsInPlay( player ) and player.GetTeamNumber() == team and player.GetUID() != ignore:
                listing.append( player.GetUID() )

        return listing

#/////////////////////////// Utility Functions ///////////////////////////

    def IncrementMI6( self ):
        if self.MI6Level == mi6MaxLevel or GERules.GetNumInRoundTeamPlayers( GEGlobal.TEAM_MI6 ) == 1:
            return

        # Increment MI6's level
        self.MI6Level += 1

        for player in GetPlayers():
            if player.GetUID() == self.BondUID:
                self.PrintCurLevel( player )
                GEUtil.PlaySoundToPlayer( player, "GEGamePlay.Token_Grab" )
            elif self.IsInPlay( player ):
                if player.GetTeamNumber() == GEGlobal.TEAM_MI6:
                    self.PrintCurLevel( player )
                    self.GivePlayerWeapons( player )
                    GEUtil.PlaySoundToPlayer( player, "GEGamePlay.Level_Up" )
                elif player.GetTeamNumber() == GEGlobal.TEAM_JANUS:
                    lvl = self.MI6Level
                    GEUtil.ClientPrint( player, GEGlobal.HUD_PRINTTALK, "^iMI6 ^1leveled up: ^y%s" % mi6WeaponList[lvl][1] )
                    GEUtil.PlaySoundToPlayer( player, "GEGamePlay.Token_Drop_Friend" )

    def DecrementMI6( self ):
        if self.MI6Level == 0 or GERules.GetNumInRoundTeamPlayers( GEGlobal.TEAM_MI6 ) == 1:
            return

        # Decrement MI6's level
        self.MI6Level -= 1

        for player in GetPlayers():
            if player.GetUID() == self.BondUID:
                self.PrintCurLevel( player )
                GEUtil.PlaySoundToPlayer( player, "GEGamePlay.Token_Grab" )
            elif self.IsInPlay( player ):
                if player.GetTeamNumber() == GEGlobal.TEAM_MI6:
                    self.PrintCurLevel( player )
                    self.GivePlayerWeapons( player )
                    GEUtil.PlaySoundToPlayer( player, "GEGamePlay.Level_Down" )
                elif player.GetTeamNumber() == GEGlobal.TEAM_JANUS:
                    lvl = self.MI6Level
                    GEUtil.ClientPrint( player, GEGlobal.HUD_PRINTTALK, "^iMI6 ^1spent a level: ^y%s" % mi6WeaponList[lvl][1] )
                    GEUtil.PlaySoundToPlayer( player, "GEGamePlay.Token_Drop_Friend" )

    def IncrementJanus( self ):
        if self.JanusLevel == janusMaxLevel or GERules.GetNumInRoundTeamPlayers( GEGlobal.TEAM_JANUS ) == 1:
            return

        # Increment Janus' level
        self.JanusLevel += 1

        for player in GetPlayers():
            if player.GetUID() == self.OurumovUID:
                self.PrintCurLevel( player )
                GEUtil.PlaySoundToPlayer( player, "GEGamePlay.Token_Grab" )
            elif self.IsInPlay( player ):
                if player.GetTeamNumber() == GEGlobal.TEAM_JANUS:
                    self.PrintCurLevel( player )
                    self.GivePlayerWeapons( player )
                    GEUtil.PlaySoundToPlayer( player, "GEGamePlay.Level_Up" )
                elif player.GetTeamNumber() == GEGlobal.TEAM_MI6:
                    lvl = self.JanusLevel
                    GEUtil.ClientPrint( player, GEGlobal.HUD_PRINTTALK, "^rJanus ^1leveled up: ^y%s" % janusWeaponList[lvl][1] )
                    GEUtil.PlaySoundToPlayer( player, "GEGamePlay.Token_Drop_Friend" )

    def DecrementJanus( self ):
        if self.JanusLevel == 0 or GERules.GetNumInRoundTeamPlayers( GEGlobal.TEAM_JANUS ) == 1:
            return

        # Decrement Janus' level
        self.JanusLevel -= 1

        for player in GetPlayers():
            if player.GetUID() == self.OurumovUID:
                self.PrintCurLevel( player )
                GEUtil.PlaySoundToPlayer( player, "GEGamePlay.Token_Grab" )
            elif self.IsInPlay( player ):
                if player.GetTeamNumber() == GEGlobal.TEAM_JANUS:
                    self.PrintCurLevel( player )
                    self.GivePlayerWeapons( player )
                    GEUtil.PlaySoundToPlayer( player, "GEGamePlay.Level_Down" )
                elif player.GetTeamNumber() == GEGlobal.TEAM_MI6:
                    lvl = self.JanusLevel
                    GEUtil.ClientPrint( player, GEGlobal.HUD_PRINTTALK, "^rJanus ^1spent a level: ^y%s" % janusWeaponList[lvl][1] )
                    GEUtil.PlaySoundToPlayer( player, "GEGamePlay.Token_Drop_Friend" )

    def PrintCurLevel( self, player ):
        if not player:
            return

        if player.GetTeamNumber() == GEGlobal.TEAM_MI6:
            lvl = self.MI6Level
            GEUtil.ClientPrint( player, GEGlobal.HUD_PRINTTALK, "^lLevel %i: ^y%s" % ( lvl + 1, mi6WeaponList[lvl][1] ) )
        elif player.GetTeamNumber() == GEGlobal.TEAM_JANUS:
            lvl = self.JanusLevel
            GEUtil.ClientPrint( player, GEGlobal.HUD_PRINTTALK, "^lLevel %i: ^y%s" % ( lvl + 1, janusWeaponList[lvl][1] ) )
        elif player.GetTeamNumber() == GEGlobal.TEAM_SPECTATOR:
            GEUtil.ClientPrint( player, GEGlobal.HUD_PRINTTALK, "^lYou are not in play." )

    def GivePlayerWeapons( self, player ):
        if not player or player.IsDead():
            return

        player.StripAllWeapons()
        startArmed = int( GEUtil.GetCVarValue( "ge_startarmed" ) )

        if startArmed == 0:
            player.GiveNamedWeapon( "weapon_slappers", 0 )
        else:
            player.GiveNamedWeapon( "weapon_slappers", 0 )
            player.GiveNamedWeapon( "weapon_knife", 0 )

        if player.GetTeamNumber() == GEGlobal.TEAM_MI6:
            weap = mi6WeaponList[self.MI6Level]
            player.GiveNamedWeapon( weap[0], weap[2] )
            player.WeaponSwitch( weap[0] )
        elif player.GetTeamNumber() == GEGlobal.TEAM_JANUS:
            weap = janusWeaponList[self.JanusLevel]
            player.GiveNamedWeapon( weap[0], weap[2] )
            player.WeaponSwitch( weap[0] )

    def PrintWeapons( self, player ):
        if not player:
            return

        if player.GetTeamNumber() == GEGlobal.TEAM_MI6:
            mi6Weapons = ""
            for i in range( len( mi6WeaponList ) ):
                mi6Weapons += "Level %i: %s\n" % ( i + 1, mi6WeaponList[i][1] )
            GEUtil.PopupMessage( player, "MI6's Weapons", mi6Weapons )
        elif player.GetTeamNumber() == GEGlobal.TEAM_JANUS:
            janusWeapons = ""
            for i in range( len( janusWeaponList ) ):
                janusWeapons += "Level %i: %s\n" % ( i + 1, janusWeaponList[i][1] )
            GEUtil.PopupMessage( player, "Janus' Weapons", janusWeapons )
        elif player.GetTeamNumber() == GEGlobal.TEAM_SPECTATOR:
            GEUtil.ClientPrint( player, GEGlobal.HUD_PRINTTALK, "^lYou are not in play." )

    def DoScoring(self, player, team, score):
        player.AddRoundScore(score)
        team.AddRoundScore(score)
