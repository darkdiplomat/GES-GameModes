from . import GEScenario
import GEEntity, GEPlayer, GEUtil, GEWeapon, GEMPGameRules, GEGlobal

USING_API = GEGlobal.API_VERSION_1_2_0

auto = ["weapon_kf7", "weapon_rcp90", "weapon_AR33", "weapon_klobb", "weapon_zmg", "weapon_d5k", "weapon_phantom",
        "weapon_d5k_silenced"]
burst = ["weapon_golden_pp7", "weapon_silver_pp7", "weapon_pp7", "weapon_pp7_silenced", "weapon_dd44",
         "weapon_moonraker"]
single = ["weapon_auto_shotgun", "weapon_shotgun", "weapon_cmag", "weapon_sniper_rifle", "weapon_knife_throwing",
          "weapon_knife", "weapon_slappers"]


class Bypass(GEScenario):
    def GetPrintName(self):
        return "Bypass"

    def GetScenarioHelp(self, help_obj):
        help_obj.SetDescription(
            "You are no longer protected by invulnerability! Every bullet counts as a hit in this mode."
            "\n\nMost weapons don't do as much damage as they did before and Body Armor restores health in this mode.")

    def GetGameDescription(self):
        if GEMPGameRules.IsTeamplay():
            return "Team Bypass"
        else:
            return "Bypass"

    def GetTeamPlay(self):
        return GEGlobal.TEAMPLAY_TOGGLE

    def OnLoadGamePlay(self):
        GEMPGameRules.SetAllowTeamSpawns(False)
        self.CreateCVar("bp_autodamagescale", "0.35", "Damage scale for automatic weapons")
        self.CreateCVar("bp_pistoldamagescale", "0.5", "Damage scale for pistols")
        self.CreateCVar("bp_singledamagescale", "1",
                        "Damage scale for single fire weapons like the shotgun and sniper rifle.")
        self.CreateCVar("bp_specdamagescale", "0.5", "Damage scale for explosives.")

    def CalculateCustomDamage(self, victim, info, health, armour):
        killer = GEPlayer.ToMPPlayer(info.GetAttacker())
        target = GEEntity.GetUniqueId(victim)
        killerid = GEEntity.GetUniqueId(GEPlayer.ToMPPlayer(info.GetAttacker()))
        red = victim.GetHealth()
        combo = health + armour

        if info.GetWeapon() is not None:
            attackerwep = (info.GetWeapon()).GetClassname()
        else:
            attackerwep = "explosive"

        if killerid != target and killer is not None:
            damage = self.FindWeaponDamage(combo, attackerwep)
            victim.SetHealth(int(red - damage))

        else:
            return

        armour = 0
        health = 0
        return health, armour

    def CanPlayerHaveItem(self, player, item):
        if item.GetClassname().startswith("item_armorvest"):
            if player.GetHealth() < 160:
                player.SetHealth(160)
                player.SetArmor(-160)
                return True
            return False
        else:
            return True

    #######################

    def FindWeaponDamage(self, damage, attackerwep):
        if attackerwep in auto:
            damagescale = GEUtil.GetCVarValue("bp_autodamagescale")

        elif attackerwep in burst:
            damagescale = GEUtil.GetCVarValue("bp_pistoldamagescale")

        elif attackerwep in single:
            damagescale = GEUtil.GetCVarValue("bp_singledamagescale")

        else:
            damagescale = GEUtil.GetCVarValue("bp_specdamagescale")

        hurt = damage * float(damagescale)
        return hurt
