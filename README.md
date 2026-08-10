# Jetters-Eng

Bomberman Jetters v1.0
----------------------------------

Notes
------
trigger debug menu by setting 0300492c to 0x5A on boot or modify opcode at 08000392 to mov r0, 0x5A
CONTROL_CODE_E003 is some sort of set event flag command

# jetters
Bomberman Jetters Translation Project

# What is different from the previous project?
* Well for starters, i fixed a few script errors with lines running over one another in a few locations in the game or minor translation errors (I went and 100% the game to find them all).
* I translated the rest of the graphic screens i can find that players will run into. ex. Title screen, the entire multipalyer mode and even the debug menu.
* This was a very big learning experience for me from the nintendo switch hacking i do so i needed to learn lots and even make tools that may or may not be necessary due to my own ignorance but helped me get this job done.
* There are some graphic issues with disabled tile spots in multiplayer/minigame graphics so theres holes in my graphics but they work to convey what is needed.
* I cannot for the life of me get any debugger to work for gba so i cant fix these inactive tiles. (Offer help if you want/can)
* Tested on Nintendo Switch NSO custom injection, MGBA/Bizhawk, Official hardware.

## Start Here
To do anything, first place a copy of Bomberman Jetters as jetters.gba in the root.

### Build
Run build.bat and jetters_eng.gba will be produced. I will include all the patches producted you will need if you do not wish to build with the script into the releases.

You might need to install VC++ 10.0 to run Atlas: https://www.microsoft.com/en-us/download/details.aspx?id=26999

### Extract
Run extract.bat and extracted files will appear in the extract folder.

### Dump Script
Run dump_script\dump_script.bat.

## Credits
Original Translation Project: https://github.com/Normmatt/Bomberman-Jetters-GBA-Translation
Secondary Translation Project Attempt: https://github.com/stickteo/jetters
Final Translation Project Attempt: https://github.com/Arch9SK7/jetters-eng

Once again BIG Thanks to Everyone for their work here or this wouldn't have even been possible. Bomberman for life.

### Script
* Higsby - Translation and editing
* Lord Kuro - Translation
* Pablitox - Insertion
* Key Mace - Translation
* DiscoGentleman - Translation
* Rai - Initial script translation.
* Arch9SK7 - Translation and editing

### Hacking
* Normmatt
* Spikeman - Original VWF code.
* Teod

### Graphics Work
* Teod
* Arch9SK7

### Fonts
* Gemini | Melissa 8 : https://www.romhacking.net/fonts/23/
* Dragonsbrethren | Dragon Warrior VWF : https://www.romhacking.net/fonts/10/
* Damian Yerrick | Base Seven : https://www.romhacking.net/fonts/142/


### Tools
* Klarth | Atlas : https://www.romhacking.net/utilities/224/
* Mat | GBAmdc : https://www.romhacking.net/utilities/431/
* Kingcom | armips : https://github.com/Kingcom/armips
* Cue | lzss : https://www.romhacking.net/utilities/826/
* Alcaro | Flips : https://www.romhacking.net/utilities/1040/
* Arch9SK7 | B8/Build_Map/decopile_to_tileset/dump_raw/E8/G4Custom/G8/R4/lzssCustom : included in tools