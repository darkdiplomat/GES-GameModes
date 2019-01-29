#
# Updated by darkdiplomat
#
# NOTE: REQUIRES COMPATIBLE MAPS TO WORK PROPERLY
#
from . import GEScenario
from .Utils.GEPlayerTracker import GEPlayerTracker
import random
import GEEntity, GEPlayer, GEUtil, GEWeapon, GEMPGameRules, GEGlobal

USING_API = GEGlobal.API_VERSION_1_2_0


class WarpModule(GEScenario):
    warpDelay = "DelayForWarp"
    charged = "MeterFull"
    energy = "MeterPoints"

    def __init__(self):
        super(WarpModule, self).__init__()
        self.pltracker = GEPlayerTracker(self)

    def Cleanup(self):
        super(WarpModule, self).Cleanup()
        self.pltracker = None

    def GetPrintName(self):
        return "Warp Module"

    def GetScenarioHelp(self, help_obj):
        help_obj.SetDescription("Press G to travel through dimensions!  Occasionally you get stuck, get over it.")

    def GetGameDescription(self):
        if GEMPGameRules.IsTeamplay():
            return "Team Warp Module"
        else:
            return "Warp Module"

    def GetTeamPlay(self):
        return GEGlobal.TEAMPLAY_TOGGLE

    def OnLoadGamePlay(self):
        GEMPGameRules.SetAllowTeamSpawns(False)
        self.CreateCVar("wm_teledelay", "12", "Maximum power, in seconds, of the teleport module.")
        self.CreateCVar("wm_telecost", "7", "Cost, in seconds, of each teleport.")

        GEUtil.PrecacheSound("GEGamePlay.Token_Chime")
        GEUtil.PrecacheSound("Buttons.beep_denied")
        GEUtil.PrecacheSound("GEGamePlay.Token_Knock")

    def OnCVarChanged(self, name, oldvalue, newvalue):
        if name == "wm_teledelay":
            for i in range(32):
                if GEPlayer.IsValidPlayerIndex(i):
                    player = GEPlayer.GetMPPlayer(i)

                    GEUtil.RemoveHudProgressBar(player, 0)
                    GEUtil.InitHudProgressBar(player, 0, "Warp", GEGlobal.HUDPB_SHOWBAR,
                                              int(GEUtil.GetCVarValue("wm_teledelay")), -1, .76, 100, 10,
                                              GEUtil.CColor(220, 220, 220, 220))
                    GEUtil.UpdateHudProgressBar(player, 0, int(GEUtil.GetCVarValue("wm_teledelay")))

    def OnRoundBegin(self):
        for i in range(32):
            if GEPlayer.IsValidPlayerIndex(i):
                player = GEPlayer.GetMPPlayer(i)

                GEUtil.RemoveHudProgressBar(player, 0)
                GEUtil.InitHudProgressBar(player, 0, "Warp", GEGlobal.HUDPB_SHOWBAR,
                                          int(GEUtil.GetCVarValue("wm_teledelay")), -1, .76, 100, 10,
                                          GEUtil.CColor(220, 220, 220, 220))
                self.pltracker.SetValue(player, self.charged, True)
                GEUtil.UpdateHudProgressBar(player, 0, int(GEUtil.GetCVarValue("wm_teledelay")))

        GEMPGameRules.ResetAllPlayerDeaths()
        GEMPGameRules.ResetAllPlayersScores()

    def OnPlayerSpawn(self, player):
        if player.IsInitialSpawn():
            GEUtil.InitHudProgressBar(player, 0, "Warp", GEGlobal.HUDPB_SHOWBAR,
                                      int(GEUtil.GetCVarValue("wm_teledelay")), -1, .76, 100, 10,
                                      GEUtil.CColor(220, 220, 220, 220))

        self.pltracker.SetValue(player, self.charged, True)
        self.pltracker.SetValue(player, self.warpDelay, 0)
        self.pltracker.SetValue(player, self.energy, int(GEUtil.GetCVarValue("wm_teledelay")))
        GEUtil.UpdateHudProgressBar(player, 0, int(GEUtil.GetCVarValue("wm_teledelay")))

        markSpawn = random.randint(0, 1)

        if markSpawn == 1:
            player.SetTargetName("Mark1")
        else:
            player.SetTargetName("Mark2")

    def OnPlayerSay(self, player, text):
        if text == "!voodoo":
            if self.checkenergy(player):
                curname = player.GetTargetName()
                GEUtil.PlaySoundToPlayer(player, "GEGamePlay.Token_Knock")
                self.setwarpdelay(player)
                if curname == "Mark1":
                    player.SetTargetName("Mark2")
                else:
                    player.SetTargetName("Mark1")
            else:
                GEUtil.PlaySoundToPlayer(player, "Buttons.beep_denied")
            return True

    def OnThink(self):
        maxpower = int(GEUtil.GetCVarValue("wm_teledelay"))
        warpcost = int(GEUtil.GetCVarValue("wm_telecost"))
        time = int(GEUtil.GetTime())

        for i in range(32):
            if GEPlayer.IsValidPlayerIndex(i):
                player = GEPlayer.GetMPPlayer(i)
                if not player.IsDead():
                    warpdelay = int(self.pltracker.GetValue(player, self.warpDelay))
                    warpenergy = self.calcenergy(player)
                    if warpenergy <= maxpower:
                        if not self.pltracker.GetValue(player, self.charged):
                            if warpcost <= warpenergy:
                                GEUtil.PlaySoundToPlayer(player, "GEGamePlay.Token_Chime")
                                self.pltracker.SetValue(player, self.charged, True)
                            else:
                                GEUtil.UpdateHudProgressBar(player, 0, warpenergy)
                        else:
                            GEUtil.UpdateHudProgressBar(player, 0, warpenergy)

    #########################################

    def setwarpdelay(self, player):
        maxpower = int(GEUtil.GetCVarValue("wm_teledelay"))
        warpcost = int(GEUtil.GetCVarValue("wm_telecost"))
        warpenergy = int(self.pltracker.GetValue(player, self.energy)) - warpcost
        self.pltracker.SetValue(player, self.energy, warpenergy)

        GEUtil.UpdateHudProgressBar(player, 0, warpenergy)
        self.pltracker.SetValue(player, self.warpDelay,
                                GEUtil.GetTime() + (int(GEUtil.GetCVarValue("wm_teledelay")) - warpenergy))

        self.checkenergy(player)
        return

    def checkenergy(self, player):
        warpcost = int(GEUtil.GetCVarValue("wm_telecost"))
        warpenergy = int(self.pltracker.GetValue(player, self.energy))

        if warpenergy < warpcost:
            self.pltracker.SetValue(player, self.charged, False)
            return False
        else:
            self.pltracker.SetValue(player, self.charged, True)
            return True

    def calcenergy(self, player):
        warpenergy = int(GEUtil.GetCVarValue("wm_teledelay")) - (
                    int(self.pltracker.GetValue(player, self.warpDelay)) - int(GEUtil.GetTime()))
        if warpenergy > int(GEUtil.GetCVarValue("wm_teledelay")):
            warpenergy = int(GEUtil.GetCVarValue("wm_teledelay"))
        self.pltracker.SetValue(player, self.energy, warpenergy)
        return warpenergy
