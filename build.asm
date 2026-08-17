
.gba

.open "jetters.gba","jetters_eng.gba",0x8000000


; Free Space (Block 1)
.defineregion 0x8420000, 0x40000, 0x00
.org 0x8420000 

; Free Space (Block 2 - Starts after Block 1 ends)
.defineregion 0x8460000, 0x1A0000, 0x00
.org 0x8460000


.include "asm\Font.asm"
.include "asm\SmallVWF.asm"
;.include "asm\ItemNamesVWF.asm"
.include "asm\vwf_routines.asm"
.include "asm\vwf_name_card.asm"
.include "asm\vwf_item_fusion.asm"

; Solo Battle Fontset
.org 0x08425000  
FontBattle:
.import "build\FontBattle_Tiles.bin"

.org 0x0800CE0C
.word FontBattle

; CARTRIDGE MODES MENU INJECTION
.org 0x0819E914
.import "build\CartModesTile.bin"

.org 0x081BA598
.import "build\Pause_Tiles.bin"


; Battle Menu Tileset
.org 0x81B04D4
.import "build\BattleMenuTile.bin"
.include "build\BattleMenuMap.asm"
.include "asm\BattleMenu.asm"

.include "asm\RMenu.asm"
.include "asm\SaveLoad.asm"
.include "asm\Radar.asm"
.include "asm\Enc.asm"
.include "asm\Album.asm"
.include "asm\HUD.asm"
.include "asm\Fusion.asm"
.include "asm\GameOver.asm"
.include "asm\HUD2.asm"
.include "asm\BomberHall.asm"
.include "asm\BHallCert.asm"
.include "asm\BHallBoard.asm"

; .include "asm\debug.asm"

; TitleScreen Bullsht
; Graphic Bug here. Will Fix.
.org 0x082411A4
.import "build\2411A4_p.bin"

.org 0x08700000
.import "build\241384_t.bin" 

.org 0x08710000
.import "extract\2447C4_m.bin"

; Point to the new Graphics
.org 0x0825FB70
.word 0x08700000 

; Point to the new Map
.org 0x0825F754
.word 0x08710000

; Secondary 4bpp Layer
.org 0x08245144
.import "build\245144_t.bin"
.org 0x08245254
.import "build\245144_m.bin"

; Title Screen Menu Sprites

.org 0x08245704
.import "build\245704_p.bin"
.org 0x08245784
.import "build\245784_t.bin"

.org 0x0805E494
.import "build\BattleTileSprite_p.bin"
.org 0x081B4488
.import "build\BattleTileSprite_t.bin"

; =====================================
; MULTIPLAYER BATTLE TEXT SPRITES
; =====================================

.org 0x08460000
New_MPText: 
.import "build\MPText_Tiles.bin"

.org 0x080F63DC 
.word New_MPText

.org 0x081AC810  
.word New_MPText

.org 0x080BFE58 
.word New_MPText

.org 0x080B59E4
.import "build\MPClear_Tiles.bin"

.org 0x081ACBD8
.import "build\DebugHurry_Tiles.bin"

.org 0x081ACEE0
.import "build\DebugTimeup_Tiles.bin"

.org 0x081AF9C0
.import "build\DebugDraw_Tiles.bin"

.org 0x08262E00
.import "build\StoryMini_Tiles.bin"

.org 0x080F1AD4
.import "build\CubRace_Tiles.bin"

.org 0x081D9950
.import "build\CubScoreTime_Tiles.bin"

.org 0x081D9D6C
.import "build\CubScoreTime_Pal.bin"

.org 0x08289F0C
.import "build\MotoJet_Tiles.bin"

.org 0x080D2F54
.import "build\MotoMini_Tiles.bin"

.org 0x0825EDD4
.import "build\EndCred_Tiles.bin"

.close