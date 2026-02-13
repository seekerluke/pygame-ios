import json
import os
import random
import sys

import pygame
from pygame.math import Vector2

# Get assets relative to the script location
ASSETS_PATH = os.path.join(os.path.dirname(__file__), "assets")


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
    surf: pygame.Surface, map_data: dict, image_cell_width: int, pos: Vector2
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


# Game initialisation
pygame.init()
screen = pygame.display.set_mode((874, 402))
pygame.display.set_caption("Mobile Pixel Art Example")

# Get the window size after set_mode, because SDL automatically changes this to the full screen size on iOS
SCREEN_WIDTH, SCREEN_HEIGHT = pygame.display.get_window_size()

# Define a scale factor based on the width of the game's visible contents (usually called logical size)
# The scale factor scales the canvas, but some positions also need to be divided by this scale factor to be converted to canvas coordinates
# It is also rounded for integer scaling, important for pixel art
LOGICAL_WIDTH = 300
SCALE_FACTOR = round(SCREEN_WIDTH / LOGICAL_WIDTH)

clock = pygame.Clock()

# Create a tiny canvas to draw the tiny pixel art to, scale it up and blit to the window surface later
canvas = pygame.Surface((SCREEN_WIDTH / SCALE_FACTOR, SCREEN_HEIGHT / SCALE_FACTOR))

# Separate canvas for mobile joystick that supports transparency
controls_canvas = pygame.Surface(canvas.size, pygame.SRCALPHA)

# Load the tilemap and its spritesheet, and generate collision rects
with open(os.path.join(ASSETS_PATH, "map.json")) as f:
    map_data = json.load(f)

map_collisions = create_tilemap_collision(map_data)
map_image = pygame.image.load(
    os.path.join(ASSETS_PATH, "spritesheet.png")
).convert_alpha()
map_image_width = map_image.width // map_data["tileSize"]

# Load health pips for the UI
health_pip_image = pygame.image.load(
    os.path.join(ASSETS_PATH, "health_pip.png")
).convert_alpha()
health_pips = []
max_health = 4

# Load the player sprite sheet
player_image = pygame.image.load(os.path.join(ASSETS_PATH, "player.png")).convert()
player_image.set_colorkey((255, 0, 255))
PLAYER_SIZE = 16

# Load a shadow to display under the player
shadow_image = pygame.image.load(
    os.path.join(ASSETS_PATH, "shadow.png")
).convert_alpha()

# Animation variables, including source rectangles for blitting the player
player_anim_timer = 0.0
player_anim_index = 0

player_srcrects = [
    # first row
    (0, 0, PLAYER_SIZE, PLAYER_SIZE),
    (16, 0, PLAYER_SIZE, PLAYER_SIZE),
    (32, 0, PLAYER_SIZE, PLAYER_SIZE),
    (48, 0, PLAYER_SIZE, PLAYER_SIZE),
    # second row
    (0, 16, PLAYER_SIZE, PLAYER_SIZE),
    (16, 16, PLAYER_SIZE, PLAYER_SIZE),
    (32, 16, PLAYER_SIZE, PLAYER_SIZE),
    (48, 16, PLAYER_SIZE, PLAYER_SIZE),
    # third row
    (0, 32, PLAYER_SIZE, PLAYER_SIZE),
    (16, 32, PLAYER_SIZE, PLAYER_SIZE),
    (32, 32, PLAYER_SIZE, PLAYER_SIZE),
    (48, 32, PLAYER_SIZE, PLAYER_SIZE),
]

# Each animation contains a list of indices, used to index into player_srcrects
player_anim_set = {
    "idledown": [0],
    "idleright": [1],
    "idleup": [2],
    "idleleft": [3],
    "walkdown": [4, 0, 8, 0],
    "walkright": [5, 1, 9, 1],
    "walkup": [6, 2, 10, 2],
    "walkleft": [7, 3, 11, 3],
}

player_anim_key_prefix = "walk"
player_anim_key_suffix = "down"
player_anim_key = f"{player_anim_key_prefix}{player_anim_key_suffix}"
player_anim_prev_key = player_anim_key

player_facing_dir = Vector2(0, 1)
player_pos = get_player_spawn(map_data)
player_hitbox = pygame.FRect(player_pos.x, player_pos.y, 10, 10)
input_dir = Vector2()

# Load the music and footstep sound
pygame.mixer.music.load(os.path.join(ASSETS_PATH, "TownTheme.mp3"))
pygame.mixer.music.set_volume(0.5)
pygame.mixer.music.play(loops=-1)

footstep_sounds = [
    pygame.Sound(os.path.join(ASSETS_PATH, "footstep1.wav")),
    pygame.Sound(os.path.join(ASSETS_PATH, "footstep2.wav")),
    pygame.Sound(os.path.join(ASSETS_PATH, "footstep3.wav")),
]
max_footstep_timer = 0.3
footstep_timer = max_footstep_timer
footstep_active = False

camera_pos = Vector2()

# Mobile joystick variables
original_joystick_pos = Vector2(30.0, controls_canvas.height - 30.0)
max_knob_distance = 15
current_joystick_finger = -1

# Reposition the UI elements based on safe area insets
if sys.platform == "ios":
    ios_window = get_ios_window()
    itop, ileft, ibottom, iright = get_safe_area_insets(ios_window)

    original_joystick_pos.x += ileft / SCALE_FACTOR
    original_joystick_pos.y -= ibottom / SCALE_FACTOR

    for i in range(max_health):
        health_pips.append(
            (
                health_pip_image,
                (10 + (ileft / SCALE_FACTOR), 10 + (12 * i) + (itop / SCALE_FACTOR)),
            )
        )
else:
    # Ignore the safe area insets on desktop
    for i in range(max_health):
        health_pips.append((health_pip_image, (10, 10 + (12 * i))))

# Set other joystick positions after safe area adjustments
current_joystick_pos = original_joystick_pos.copy()
current_knob_pos = current_joystick_pos.copy()


running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # Finger events are used to handle joystick movement
        if event.type == pygame.FINGERDOWN:
            # Only allow one finger at a time to control the joystick
            if current_joystick_finger == -1:
                current_joystick_finger = event.finger_id

                # Finger events return x and y as normalised values between 0 and 1
                # Multiply by the screen size to get the correct pixel values
                mpos = Vector2(event.x * SCREEN_WIDTH, event.y * SCREEN_HEIGHT)

                current_joystick_pos = mpos / SCALE_FACTOR
                current_knob_pos = current_joystick_pos.copy()

        if event.type == pygame.FINGERMOTION:
            if current_joystick_finger == event.finger_id:
                mpos = Vector2(event.x * SCREEN_WIDTH, event.y * SCREEN_HEIGHT)

                current_knob_pos = mpos / SCALE_FACTOR

                # Constrain the knob's position to a max distance from the base
                diff = current_knob_pos - current_joystick_pos
                diff.clamp_magnitude_ip(max_knob_distance)
                current_knob_pos = current_joystick_pos + diff

                # If the joystick has moved, set input_dir to move the player
                input_dir = diff.normalize() if diff.length() > 0 else diff
                player_facing_dir = input_dir.copy()

                footstep_active = True

        if event.type == pygame.FINGERUP:
            # Release ownership of the joystick and reset its position
            if current_joystick_finger == event.finger_id:
                current_joystick_finger = -1
                current_joystick_pos = original_joystick_pos.copy()
                current_knob_pos = current_joystick_pos.copy()
                input_dir = Vector2()

                footstep_active = False

    dt = clock.tick(60) / 1000

    # Standard WASD/arrow keys movement on desktop
    if sys.platform != "ios":
        pressed = pygame.key.get_pressed()
        moved = False

        up = pressed[pygame.K_w] or pressed[pygame.K_UP]
        left = pressed[pygame.K_a] or pressed[pygame.K_LEFT]
        down = pressed[pygame.K_s] or pressed[pygame.K_DOWN]
        right = pressed[pygame.K_d] or pressed[pygame.K_RIGHT]

        if up and down:
            input_dir.y = 0
        elif up:
            input_dir.y = -1
            moved = True
        elif down:
            input_dir.y = 1
            moved = True
        else:
            input_dir.y = 0

        if left and right:
            input_dir.x = 0
        elif left:
            input_dir.x = -1
            moved = True
        elif right:
            input_dir.x = 1
            moved = True
        else:
            input_dir.x = 0

        if moved:
            input_dir.normalize_ip()
            player_facing_dir = input_dir.copy()
            footstep_active = True
        else:
            footstep_active = False

    # Move and collide X
    player_pos.x += input_dir.x
    player_hitbox.x = player_pos.x + 3
    for tile in map_collisions:
        if tile.colliderect(player_hitbox):
            if input_dir.x > 0:
                player_hitbox.right = tile.left
            else:
                player_hitbox.left = tile.right
            player_pos.x = player_hitbox.x - 3

    # Move and collide Y
    player_pos.y += input_dir.y
    player_hitbox.y = player_pos.y + 6
    for tile in map_collisions:
        if tile.colliderect(player_hitbox):
            if input_dir.y > 0:
                player_hitbox.bottom = tile.top
            else:
                player_hitbox.top = tile.bottom
            player_pos.y = player_hitbox.y - 6

    # Footstep timer, activated when the player moves
    footstep_timer += dt
    if footstep_active and footstep_timer > max_footstep_timer:
        random.choice(footstep_sounds).play()
        footstep_timer = 0.0

    # Animation timer, always running
    player_anim_timer += dt
    if player_anim_timer > max_footstep_timer / 2:
        player_anim_index = (player_anim_index + 1) % len(
            player_anim_set[player_anim_key]
        )
        player_anim_timer = 0.0

    # Set the correct animation key using the direction the player is facing
    if player_facing_dir.angle > -135 and player_facing_dir.angle < -45:
        player_anim_key_suffix = "up"
    elif player_facing_dir.angle >= -45 and player_facing_dir.angle <= 45:
        player_anim_key_suffix = "right"
    elif player_facing_dir.angle > 45 and player_facing_dir.angle < 135:
        player_anim_key_suffix = "down"
    else:
        player_anim_key_suffix = "left"

    if input_dir.length() > 0.01:
        player_anim_key_prefix = "walk"
    else:
        player_anim_key_prefix = "idle"

    player_anim_key = f"{player_anim_key_prefix}{player_anim_key_suffix}"
    # If the key has changed, reset the index and timer
    if player_anim_key != player_anim_prev_key:
        player_anim_index = 0
        player_anim_timer = 0.0
        player_anim_prev_key = player_anim_key

    # Move the camera and clamp it to the tilemap bounds
    camera_pos = (
        -player_pos.copy()
        + Vector2(canvas.width / 2, canvas.height / 2)
        - Vector2(PLAYER_SIZE / 2, PLAYER_SIZE / 2)
    )
    camera_pos.x = pygame.math.clamp(
        camera_pos.x,
        -(map_data["mapWidth"] * map_data["tileSize"]) + canvas.width,
        0,
    )
    camera_pos.y = pygame.math.clamp(
        camera_pos.y,
        -(map_data["mapHeight"] * map_data["tileSize"]) + canvas.height,
        0,
    )

    # Start drawing
    canvas.fill((0, 0, 0))
    draw_tilemap(canvas, map_data, map_image_width, camera_pos)

    # Draw the shadow, then the player with the correct animation index
    canvas.blit(shadow_image, player_pos + camera_pos + Vector2(3, 14))
    srcrect_index = player_anim_set[player_anim_key][player_anim_index]
    canvas.blit(player_image, player_pos + camera_pos, player_srcrects[srcrect_index])

    canvas.fblits(health_pips)

    # Draw the joystick, but only on iOS
    if sys.platform == "ios":
        controls_canvas.fill((0, 0, 0, 0))
        pygame.draw.circle(
            controls_canvas, (127, 127, 127, 100), current_joystick_pos, 20
        )
        pygame.draw.circle(controls_canvas, (204, 204, 204, 100), current_knob_pos, 10)
        canvas.blit(controls_canvas)

    # Scale up the canvas to blit it to the window surface
    screen.blit(pygame.transform.scale_by(canvas, SCALE_FACTOR))

    pygame.display.flip()


pygame.quit()
