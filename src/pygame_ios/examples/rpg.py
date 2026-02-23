import json
import os
import random
import sys

import pygame
from pygame.math import Vector2


# Get the active UIWindow using native platform APIs, rubicon-objc allows you to do this from Python code
# Returns None if the window hasn't been created yet
def get_ios_window():
    from rubicon.objc import ObjCClass

    UIApplication = ObjCClass("UIApplication")
    UIWindowScene = ObjCClass("UIWindowScene")

    window_scene = None
    scenes = UIApplication.sharedApplication.connectedScenes
    for scene in scenes.allObjects():
        if scene.isKindOfClass(UIWindowScene):
            window_scene = scene
            break

    return window_scene.keyWindow


def get_safe_area_insets(ui_window) -> tuple[float, float, float, float]:
    r = ui_window.safeAreaInsets
    return (r.top, r.left, r.bottom, r.right)


def draw_tilemap(
    surf: pygame.Surface, map_image: pygame.Surface, map_data: dict, image_cell_width: int, pos: Vector2
):
    for layer in reversed(map_data["layers"]):
        if layer["name"] != "entities":
            for tile in layer["tiles"]:
                srcx = int(tile["id"]) % image_cell_width * map_data["tileSize"]
                srcy = int(tile["id"]) // image_cell_width * map_data["tileSize"]
                surf.blit(
                    map_image,
                    (
                        # round pixel positions to avoid drawing subpixels
                        round(pos.x + tile["x"] * map_data["tileSize"]),
                        round(pos.y + tile["y"] * map_data["tileSize"]),
                    ),
                    (srcx, srcy, map_data["tileSize"], map_data["tileSize"]),
                )


def create_tilemap_collision(map_data: dict) -> list[pygame.FRect]:
    rects = []
    for layer in map_data["layers"]:
        if layer["collider"]:
            for tile in layer["tiles"]:
                rect = pygame.FRect(
                    tile["x"] * map_data["tileSize"],
                    tile["y"] * map_data["tileSize"],
                    map_data["tileSize"],
                    map_data["tileSize"],
                )
                rects.append(rect)
    return rects


# The Sprite Fusion tilemap has a custom attribute for the player spawn position
def get_player_spawn(map_data: dict) -> Vector2:
    for layer in map_data["layers"]:
        if layer["name"] == "entities":
            for tile in layer["tiles"]:
                if tile["attributes"]["type"] == "player_spawn":
                    return Vector2(
                        tile["x"] * map_data["tileSize"],
                        tile["y"] * map_data["tileSize"],
                    )
    return Vector2()


class Game:
    # Get assets relative to the script location
    ASSETS_PATH = os.path.join(os.path.dirname(__file__), "assets")
    
    # Define a scale factor based on the width of the game's visible contents (usually called logical size)
    # The scale factor scales the canvas, but some positions also need to be divided by this scale factor to be converted to canvas coordinates
    # It is also rounded for integer scaling, important for pixel art
    LOGICAL_WIDTH = 300
    
    # Size of a single frame of the player
    PLAYER_SIZE = 16

    def __init__(self):
        # Game initialisation
        pygame.init()
        self.screen = pygame.display.set_mode((874, 402))
        pygame.display.set_caption("Mobile Pixel Art Example")
        self.clock = pygame.Clock()
        
        # Get the window size after set_mode, because SDL automatically changes this to the full screen size on iOS
        Game.SCREEN_WIDTH, Game.SCREEN_HEIGHT = pygame.display.get_window_size()
        Game.SCALE_FACTOR = round(self.SCREEN_WIDTH / self.LOGICAL_WIDTH)
        
        # Create a tiny canvas to draw the tiny pixel art to, scale it up and blit to the window surface later
        self.canvas = pygame.Surface((self.SCREEN_WIDTH / self.SCALE_FACTOR, self.SCREEN_HEIGHT / self.SCALE_FACTOR))

        # Separate canvas for mobile joystick that supports transparency
        self.controls_canvas = pygame.Surface(self.canvas.size, pygame.SRCALPHA)

        # Load the tilemap and its spritesheet, and generate collision rects
        with open(os.path.join(self.ASSETS_PATH, "map.json")) as f:
            self.map_data = json.load(f)

        self.map_collisions = create_tilemap_collision(self.map_data)
        self.map_image = pygame.image.load(
            os.path.join(self.ASSETS_PATH, "spritesheet.png")
        ).convert_alpha()
        self.map_image_width = self.map_image.width // self.map_data["tileSize"]

        # Load health pips for the UI
        self.health_pip_image = pygame.image.load(
            os.path.join(self.ASSETS_PATH, "health_pip.png")
        ).convert_alpha()
        self.health_pips = []
        self.max_health = 4

        # Load the player sprite sheet
        self.player_image = pygame.image.load(os.path.join(self.ASSETS_PATH, "player.png")).convert()
        self.player_image.set_colorkey((255, 0, 255))

        # Load a shadow to display under the player
        self.shadow_image = pygame.image.load(
            os.path.join(self.ASSETS_PATH, "shadow.png")
        ).convert_alpha()

        # Animation variables, including source rectangles for blitting the player
        self.player_anim_timer = 0.0
        self.player_anim_index = 0

        self.player_srcrects = [
            # first row
            (0, 0, self.PLAYER_SIZE, self.PLAYER_SIZE),
            (16, 0, self.PLAYER_SIZE, self.PLAYER_SIZE),
            (32, 0, self.PLAYER_SIZE, self.PLAYER_SIZE),
            (48, 0, self.PLAYER_SIZE, self.PLAYER_SIZE),
            # second row
            (0, 16, self.PLAYER_SIZE, self.PLAYER_SIZE),
            (16, 16, self.PLAYER_SIZE, self.PLAYER_SIZE),
            (32, 16, self.PLAYER_SIZE, self.PLAYER_SIZE),
            (48, 16, self.PLAYER_SIZE, self.PLAYER_SIZE),
            # third row
            (0, 32, self.PLAYER_SIZE, self.PLAYER_SIZE),
            (16, 32, self.PLAYER_SIZE, self.PLAYER_SIZE),
            (32, 32, self.PLAYER_SIZE, self.PLAYER_SIZE),
            (48, 32, self.PLAYER_SIZE, self.PLAYER_SIZE),
        ]

        # Each animation contains a list of indices, used to index into player_srcrects
        self.player_anim_set = {
            "idledown": [0],
            "idleright": [1],
            "idleup": [2],
            "idleleft": [3],
            "walkdown": [4, 0, 8, 0],
            "walkright": [5, 1, 9, 1],
            "walkup": [6, 2, 10, 2],
            "walkleft": [7, 3, 11, 3],
        }

        self.player_anim_key_prefix = "walk"
        self.player_anim_key_suffix = "down"
        self.player_anim_key = f"{self.player_anim_key_prefix}{self.player_anim_key_suffix}"
        self.player_anim_prev_key = self.player_anim_key

        self.player_facing_dir = Vector2(0, 1)
        self.player_pos = get_player_spawn(self.map_data)
        self.player_hitbox = pygame.FRect(self.player_pos.x, self.player_pos.y, 10, 10)
        self.input_dir = Vector2()

        # Load the music and footstep sound
        pygame.mixer.music.load(os.path.join(self.ASSETS_PATH, "TownTheme.mp3"))
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(loops=-1)

        self.footstep_sounds = [
            pygame.Sound(os.path.join(self.ASSETS_PATH, "footstep1.wav")),
            pygame.Sound(os.path.join(self.ASSETS_PATH, "footstep2.wav")),
            pygame.Sound(os.path.join(self.ASSETS_PATH, "footstep3.wav")),
        ]
        self.max_footstep_timer = 0.3
        self.footstep_timer = self.max_footstep_timer
        self.footstep_active = False

        self.camera_pos = Vector2()

        # Mobile joystick variables
        self.original_joystick_pos = Vector2(30.0, self.controls_canvas.height - 30.0)
        self.max_knob_distance = 15
        self.current_joystick_finger = -1

        # Reposition the UI elements based on safe area insets
        if sys.platform == "ios":
            ios_window = get_ios_window()
            itop, ileft, ibottom, iright = get_safe_area_insets(ios_window)

            self.original_joystick_pos.x += ileft / self.SCALE_FACTOR
            self.original_joystick_pos.y -= ibottom / self.SCALE_FACTOR

            for i in range(self.max_health):
                self.health_pips.append(
                    (
                        self.health_pip_image,
                        (10 + (ileft / self.SCALE_FACTOR), 10 + (12 * i) + (itop / self.SCALE_FACTOR)),
                    )
                )
        else:
            # Ignore the safe area insets on desktop
            for i in range(self.max_health):
                self.health_pips.append((self.health_pip_image, (10, 10 + (12 * i))))

        # Set other joystick positions after safe area adjustments
        self.current_joystick_pos = self.original_joystick_pos.copy()
        self.current_knob_pos = self.current_joystick_pos.copy()


    def tick(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return True

            # Finger events are used to handle joystick movement
            if event.type == pygame.FINGERDOWN:
                # Only allow one finger at a time to control the joystick
                if self.current_joystick_finger == -1:
                    self.current_joystick_finger = event.finger_id

                    # Finger events return x and y as normalised values between 0 and 1
                    # Multiply by the screen size to get the correct pixel values
                    mpos = Vector2(event.x * self.SCREEN_WIDTH, event.y * self.SCREEN_HEIGHT)

                    self.current_joystick_pos = mpos / self.SCALE_FACTOR
                    self.current_knob_pos = self.current_joystick_pos.copy()

            if event.type == pygame.FINGERMOTION:
                if self.current_joystick_finger == event.finger_id:
                    mpos = Vector2(event.x * self.SCREEN_WIDTH, event.y * self.SCREEN_HEIGHT)

                    self.current_knob_pos = mpos / self.SCALE_FACTOR

                    # Constrain the knob's position to a max distance from the base
                    diff = self.current_knob_pos - self.current_joystick_pos
                    diff.clamp_magnitude_ip(self.max_knob_distance)
                    self.current_knob_pos = self.current_joystick_pos + diff

                    # If the joystick has moved, set input_dir to move the player
                    self.input_dir = diff.normalize() if diff.length() > 0 else diff
                    self.player_facing_dir = self.input_dir.copy()

                    self.footstep_active = True

            if event.type == pygame.FINGERUP:
                # Release ownership of the joystick and reset its position
                if self.current_joystick_finger == event.finger_id:
                    self.current_joystick_finger = -1
                    self.current_joystick_pos = self.original_joystick_pos.copy()
                    self.current_knob_pos = self.current_joystick_pos.copy()
                    self.input_dir = Vector2()

                    self.footstep_active = False

        dt = self.clock.tick(60) / 1000

        # Standard WASD/arrow keys movement on desktop
        if sys.platform != "ios":
            pressed = pygame.key.get_pressed()
            moved = False

            up = pressed[pygame.K_w] or pressed[pygame.K_UP]
            left = pressed[pygame.K_a] or pressed[pygame.K_LEFT]
            down = pressed[pygame.K_s] or pressed[pygame.K_DOWN]
            right = pressed[pygame.K_d] or pressed[pygame.K_RIGHT]

            if up and down:
                self.input_dir.y = 0
            elif up:
                self.input_dir.y = -1
                moved = True
            elif down:
                self.input_dir.y = 1
                moved = True
            else:
                self.input_dir.y = 0

            if left and right:
                self.input_dir.x = 0
            elif left:
                self.input_dir.x = -1
                moved = True
            elif right:
                self.input_dir.x = 1
                moved = True
            else:
                self.input_dir.x = 0

            if moved:
                self.input_dir.normalize_ip()
                self.player_facing_dir = self.input_dir.copy()
                self.footstep_active = True
            else:
                self.footstep_active = False

        # Move and collide X
        self.player_pos.x += self.input_dir.x
        self.player_hitbox.x = self.player_pos.x + 3
        for tile in self.map_collisions:
            if tile.colliderect(self.player_hitbox):
                if self.input_dir.x > 0:
                    self.player_hitbox.right = tile.left
                else:
                    self.player_hitbox.left = tile.right
                self.player_pos.x = self.player_hitbox.x - 3

        # Move and collide Y
        self.player_pos.y += self.input_dir.y
        self.player_hitbox.y = self.player_pos.y + 6
        for tile in self.map_collisions:
            if tile.colliderect(self.player_hitbox):
                if self.input_dir.y > 0:
                    self.player_hitbox.bottom = tile.top
                else:
                    self.player_hitbox.top = tile.bottom
                self.player_pos.y = self.player_hitbox.y - 6

        # Footstep timer, activated when the player moves
        self.footstep_timer += dt
        if self.footstep_active and self.footstep_timer > self.max_footstep_timer:
            random.choice(self.footstep_sounds).play()
            self.footstep_timer = 0.0

        # Animation timer, always running
        self.player_anim_timer += dt
        if self.player_anim_timer > self.max_footstep_timer / 2:
            self.player_anim_index = (self.player_anim_index + 1) % len(
                self.player_anim_set[self.player_anim_key]
            )
            self.player_anim_timer = 0.0

        # Set the correct animation key using the direction the player is facing
        if self.player_facing_dir.angle > -135 and self.player_facing_dir.angle < -45:
            self.player_anim_key_suffix = "up"
        elif self.player_facing_dir.angle >= -45 and self.player_facing_dir.angle <= 45:
            self.player_anim_key_suffix = "right"
        elif self.player_facing_dir.angle > 45 and self.player_facing_dir.angle < 135:
            self.player_anim_key_suffix = "down"
        else:
            self.player_anim_key_suffix = "left"

        if self.input_dir.length() > 0.01:
            self.player_anim_key_prefix = "walk"
        else:
            self.player_anim_key_prefix = "idle"

        self.player_anim_key = f"{self.player_anim_key_prefix}{self.player_anim_key_suffix}"
        # If the key has changed, reset the index and timer
        if self.player_anim_key != self.player_anim_prev_key:
            self.player_anim_index = 0
            self.player_anim_timer = 0.0
            self.player_anim_prev_key = self.player_anim_key

        # Move the camera and clamp it to the tilemap bounds
        self.camera_pos = (
            -self.player_pos.copy()
            + Vector2(self.canvas.width / 2, self.canvas.height / 2)
            - Vector2(self.PLAYER_SIZE / 2, self.PLAYER_SIZE / 2)
        )
        self.camera_pos.x = pygame.math.clamp(
            self.camera_pos.x,
            -(self.map_data["mapWidth"] * self.map_data["tileSize"]) + self.canvas.width,
            0,
        )
        self.camera_pos.y = pygame.math.clamp(
            self.camera_pos.y,
            -(self.map_data["mapHeight"] * self.map_data["tileSize"]) + self.canvas.height,
            0,
        )

        # Start drawing
        self.canvas.fill((0, 0, 0))
        draw_tilemap(self.canvas, self.map_image, self.map_data, self.map_image_width, self.camera_pos)

        # Draw the shadow, then the player with the correct animation index
        self.canvas.blit(self.shadow_image, self.player_pos + self.camera_pos + Vector2(3, 14))
        srcrect_index = self.player_anim_set[self.player_anim_key][self.player_anim_index]
        self.canvas.blit(self.player_image, self.player_pos + self.camera_pos, self.player_srcrects[srcrect_index])

        self.canvas.fblits(self.health_pips)

        # Draw the joystick, but only on iOS
        if sys.platform == "ios":
            self.controls_canvas.fill((0, 0, 0, 0))
            pygame.draw.circle(
                self.controls_canvas, (127, 127, 127, 100), self.current_joystick_pos, 20
            )
            pygame.draw.circle(self.controls_canvas, (204, 204, 204, 100), self.current_knob_pos, 10)
            self.canvas.blit(self.controls_canvas)

        # Scale up the canvas to blit it to the window surface
        self.screen.blit(pygame.transform.scale_by(self.canvas, self.SCALE_FACTOR))

        pygame.display.flip()
        
        return False


game = Game()

if sys.platform != "ios":
    should_exit = False
    while not should_exit:
        should_exit = game.tick()
    pygame.quit()
else:
    _ios_tick = game.tick
