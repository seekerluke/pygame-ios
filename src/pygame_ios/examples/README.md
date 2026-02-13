# Examples

A list of example projects designed for pygame-ios. If an example runs on desktop, you'll be able to run it using `python -m pygame_ios.examples.<scriptname>`. For example the `rpg.py` example can be run with `python -m pygame_ios.examples.rpg`.

## rpg

This example showcases the following features:

- Cross platform support for both desktop and iOS. Keyboard input is used on desktop, on-screen joystick on iOS. Finger events are used to support multitouch.
- Pixel perfect rendering. Everything is blitted to a "canvas" surface, before scaling that canvas up by `SCALE_FACTOR` and blitting that to the window surface. Float positions are also rounded before blit.
- [Sprite Fusion](https://www.spritefusion.com/) tilemap parsing and drawing. No external modules needed.
- UI drawn relative to the safe area insets. This is important on iOS to avoid drawing UI under the notch, the rounded corners, or the home indicator. The safe area insets are only accessible from the native iOS APIs, `rubicon-objc` is used to show how those APIs can be accessed from Python code.
- Animated player sprite that moves, with a camera following it.
- Background music and footstep sounds.

It uses the following assets, all of which are CC0:

- [Tiny Town by Kenney](https://kenney.nl/assets/tiny-town), used for the tilemap spritesheet
- [UI Pack - Pixel Adventure by Kenney](https://kenney.nl/assets/ui-pack-pixel-adventure), used for the health pip in the UI
- [RPG Character Sprites by GrafxKid](https://opengameart.org/content/rpg-character-sprites), used for the player spritesheet
- [Town Theme RPG by cynicmusic](https://opengameart.org/content/town-theme-rpg), used for the music track
- [Hiking Boot Footsteps on Grass by Fission9](https://freesound.org/people/Fission9/sounds/521587/), used for the footstep sound effects

I made the Sprite Fusion tilemap data and the shadow image.
