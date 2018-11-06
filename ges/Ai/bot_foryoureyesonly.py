# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# FOR YOUR EYES ONLY BOT AI
# Bots will seek out the briefcase
# Version 1.0.0
# By: DarkDiplomat
# Based on bot_mwgg by Team GoldenEye: Source
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
################ Copyright 2005-2013 Team GoldenEye: Source #################
#
# This file is based on bot_mwgg.py from the GoldenEye: Source's Python Library.
#
# GoldenEye: Source's Python Library is free software: you can redistribute
# it and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the License,
# or(at your option) any later version.
#
# GoldenEye: Source's Python Library is distributed in the hope that it will
# be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GoldenEye: Source's Python Library.
# If not, see <http://www.gnu.org/licenses/>.
#############################################################################
from GEAiConst import State
from .bot_deathmatch import bot_deathmatch
from .Schedules import BaseCondition, Sched, Cond
from .Tasks import Task
import GEGlobal as Glb
import random

USING_API = Glb.API_VERSION_1_1_0


class bot_foryoureyesonly(bot_deathmatch):
    def __init__(self, parent):
        bot_deathmatch.__init__(self, parent)
        self.SetCustomConditions(FYEO_Cond)

    def GatherConditions(self):
        bot_deathmatch.GatherConditions(self)

        if self.HasWeapon("token_deathmatch"):
            self.SetCondition(FYEO_Cond.FYEO_HAS_BRIEFCASE)
            self.SetTokenTarget(None)
        else:
            self.ClearCondition(FYEO_Cond.FYEO_HAS_BRIEFCASE)
            self.SetTokenTarget("token_deathmatch")

    def SelectSchedule( self ):
        sched = bot_deathmatch.SelectSchedule( self )

        if self.GetState() != State.COMBAT:
            if random.random() < 0.6 and not self.HasCondition(FYEO_Cond.FYEO_HAS_BRIEFCASE):
                return Sched.BOT_SEEK_TOKEN

        return sched


# Schedule and condition declarations
class FYEO_Cond(Cond):
    FYEO_HAS_BRIEFCASE = BaseCondition()

