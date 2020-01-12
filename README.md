# GES-GameModes
GoldenEye: Source game modes created or updated and maintained by DarkDiplomat

## [Agent Under Fire](../ges/GamePlay/AgentUnderFire.py)  
Created by: Troy  
Updated by: DarkDiplomat  

**REQUIRES STAR graphics for Radar found in [materials/sprites/hud/radar](../materials/sprites/hud/radar)**
At the start of the round, a player is randomly selected from MI6 and Janus to be their team's VIP. (Bond or Ourumov)  
The VIPs are given a shotgun and a usable adrenaline shot, while their bodyguards are given a level 1 weapon.  
In order for the guards to level up to the next weapon, their VIP must kill an opponent.  
If a VIP dies, they will be eliminated and one of their guards will take their place.  
The first team to kill all of their opposing team's VIPs wins the round.  
Type !level to print your team's current level. Type !weapons to print your team's weapon levels.

## [Bypass](../master/ges/GamePlay/Bypass.py)
Created by: *unknown*  
Updated by: DarkDiplomat

You are no longer protected by invulnerability! Every bullet counts as a hit in this mode.  
Most weapons don't do as much damage as they did before and Body Armor restores health in this mode.  

## [For Your Eyes Only](../master/ges/GamePlay/ForYourEyesOnly.py)
Created by: WNxVirtualMark  
Updated by: DarkDiplomat  

A Briefcase is spawned somewhere on the map at the round start.  
Whoever picks up the Briefcase will be able to eliminate  
other players by killing them. Only the current Briefcase holder  
can eliminate players: if you are killed by anyone else, you will  
respawn normally. (You will also be eliminated if you commit  
suicide.) If the Briefcase holder is killed by another player, he  
or she will drop the Briefcase and respawn, and another player can  
pick up the Briefcase. The last player remaining wins the round!  
  
If you pick up the Briefcase, you will also be given some buffs.  
First, you will be given full health and armor upon picking up the  
Briefcase, and your speed will be slightly increased. Second, when  
you eliminate a player, you will regain 1 bar of health (or 1 bar  
of armor, if health is full).  

## [Gotta Cap'em All](../master/ges/GamePlay/GottaCapEmAll.py)
Created by: DarkDiplomat  
Based on concept ideas from Shemp Hamward  

You have to kill every player at least once to win.  
The first player to kill every other player wins the round.  
You only score points for unique kills.  

## [LaunchCode](../master/ges/GamePlay/LaunchCode.py)
Created by: *unknown*  
Updated by: DarkDiplomat  
  
One team has a hacker who they must protect, the other must stop that hacker from hacking all the points.  
The hacker is the only one who can hack points or collect the Insta-Hack Key.  
To use the Insta-Hack Key, press the key bound to the command !voodoo

## [Pop-A-Cap](../master/ges/GamePlay/PopACap.py)
Created by: DarkDiplomat  
Based on the concept of the Perfect Dark game mode  

Track down the target and blast them to score points.
Selected randomly, one player will be selected as the 'victim' which everyone has to 
try and track down. Whoever blasts the target will score 2 points, then another 
player will become the target. If you're the target, you'll score 1 point if you 
survive for a period of time. 

## [Thunderball](../master/ges/GamePlay/Thunderball.py)
Created by: DarkDiplomat  
Based loosely on concepts laid out at [GESHL2 Forums](https://forums.geshl2.com/index.php/topic,5573.0.html)

The Thunderball is set to explode at a set interval!
To start, the Thunderball is given to a random player. The player has to kill an opponent to
get rid of the Thunderball. If the player is unable to accomplish that they
are temporarily knocked out and the last player to kill them takes ownership
of the Thunderball; if no last killer, a new random player is selected.
survivors get a point each time the ball detonates. Scoring is deathmatch style, all kills gain points.
The Thunderball carrier gets some advantages to help them transfer the
Thunderball, such as, increased speed and taking less damage (like an
adrenaline boost in the panic of being the Thunderball carrier)

## [WarpModule](../master/ges/GamePlay/WarpModule.py)
Created by: Entropy-Soldier  
Updated by: DarkDiplomat

**NOTE: REQUIRES COMPATIBLE [MAPS](https://forums.geshl2.com/index.php?topic=7419.msg77440#msg77440) TO WORK PROPERLY**  
Press the key bound to the command !voodoo to travel through dimensions!  Occasionally you get stuck, get over it.