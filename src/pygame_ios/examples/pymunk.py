import pygame
import pymunk
import pymunk.pygame_util
import random

def create_ball(space, pos):
    body = pymunk.Body()
    body.position = pos

    size = random.randint(20, 50)
    ball = pymunk.Circle(body, size)
    ball.mass = size
    ball.elasticity = 0.95

    space.add(body, ball)
    return body

def create_line(space, p1, p2):
    line = pymunk.Segment(space.static_body, p1, p2, 0)
    line.elasticity = 0.95
    return line 

def create_edges(space, w, h):
    edges = [
        create_line(space, (1, h), (w, h)), # bottom
        create_line(space, (w, h), (w, 0)), # right
        create_line(space, (1, -1), (w, -1)), # top
        create_line(space, (-1, 0), (-1, h)), # left
    ]
    space.add(*edges)
    return edges

pygame.init()
screen = pygame.display.set_mode((400, 600))
clock = pygame.Clock()
timestep = 1.0 / 60.0

w, h = pygame.display.get_window_size()
draw_options = pymunk.pygame_util.DrawOptions(screen)

space = pymunk.Space()
space.gravity = 0, 981

spawn_timer = pygame.time.get_ticks()

create_edges(space, w, h)

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    space.step(timestep)
    clock.tick(60)

    # spawn ball every 2 seconds
    if pygame.time.get_ticks() - spawn_timer > 2000:
        create_ball(space, (w / 2 + random.randint(-5, 5), 50))
        spawn_timer = pygame.time.get_ticks()

    screen.fill("black")
    space.debug_draw(draw_options)
    pygame.display.flip()

pygame.quit()
