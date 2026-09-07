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
* Well for starters, I fixed a few script errors with lines running over one another in a few locations in the game or minor translation errors (I went and 100% the game to find them all).
* I translated the rest of the graphic screens I could find that players will run into. ex. Title screen, the entire multiplayer mode and even the debug menu.
* This was a very big learning experience for me from the Nintendo Switch hacking I do, so I needed to learn lots and even make tools that may or may not be necessary due to my own ignorance but helped me get this job done.
* There are some graphic issues with disabled tile spots in multiplayer/minigame graphics so there are holes in my graphics, but they work to convey what is needed.
* I cannot for the life of me get any debugger to work for GBA so I can't fix these inactive tiles. (Offer help if you want/can)
* Tested on Nintendo Switch NSO custom injection, mGBA/BizHawk, and Official hardware.

## 🛠 Prerequisites
To build the ROM from source, your system requires:
* **Python 3.x:** Required to execute the graphic extraction and recompression scripts.
* **A Clean ROM:** A legally obtained, unmodified `Bomberman Jetters - Densetsu no Bomberman (Japan).gba` ROM file.
* **VC++ 10.0:** Windows users may need this to run Atlas: [Download Here](https://www.microsoft.com/en-us/download/details.aspx?id=26999).

## 🚀 Automated ROM Rebuilding
All active, stripped graphics and modified assets are pre-configured in this repository. You do not need to manually inject individual files. You can fully rebuild the ROM in a single run using the provided build scripts.

**Start Here:** Place a clean copy of the ROM named `jetters.gba` in the root folder.

**For Windows:**
1. Double-click `build.bat`. 
2. The script will automatically process the Python graphic injections, compile the text, and output `jetters_eng.gba`.

**For macOS & Linux:**
Because this project utilizes a mix of Python scripts and Windows binaries (`.exe` utilities like Atlas and armips), you will need [Wine](https://www.winehq.org/) installed to run the compilation tools.
1. Open your terminal and navigate to the project directory.
2. Execute the build process via Wine: `wine cmd /c build.bat`
3. The patched `jetters_eng.gba` will be generated in the root folder.

### Additional Scripts
* **Extract:** Run `extract.bat` and extracted files will appear in the extract folder.
* **Dump Script:** Run `dump_script\dump_script.bat`.

## 💾 Manual Patching Guide
If you prefer to skip the build process and just patch a clean ROM yourself, pre-compiled patches are available in multiple formats in the Releases section. 

**Web-Based Alternative (All OS):**
For macOS, Linux, or mobile users who cannot run executable patchers, [ROM Patcher JS](https://www.marcrobledo.com/RomPatcher.js/) is a free, browser-based tool that natively supports `.ups`, `.bps`, and `.ips` files.

| Patch Format | What it does | Recommended Windows Tools | Recommended Mac/Linux Tools |
| :--- | :--- | :--- | :--- |
| **.bps** | The modern standard. Highly compressed and strictly verifies ROM checksums to prevent you from breaking the ROM if you use the wrong dump. | **Floating IPS (Flips)** | MultiPatch (Mac), Flips (Linux) |
| **.ups** | An older standard. Also verifies ROM checksums and safely reverts changes, but files are slightly larger than `.bps`. | **NUPS** or **Tsukuyomi** | MultiPatch (Mac), NUPS via Wine |
| **.ips** | The legacy standard. Does not verify if your base ROM is correct and can permanently break your file if applied to the wrong version. | **Lunar IPS** or **Flips** | MultiPatch (Mac) |
| **delta.bps** | A differential patch format (using xdelta/bps architecture) designed for injecting specific binary differences. | **Delta Patcher** or **Flips** | MultiPatch (Mac), xdelta3 (Terminal) |

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
