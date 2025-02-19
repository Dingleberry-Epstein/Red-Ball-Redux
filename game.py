import pygame, os, math, random
from levels import Eggman_Land
from constants import RingFont

pygame.init()

screen = pygame.display.set_mode((1280, 720))
clock = pygame.time.Clock()
level = Eggman_Land()
running = True

while running:
    screen.fill("BLACK")
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

    level.update()  # Updates camera
    level.draw(screen)  # Draws everything with camera offsets

    # FPS Display
    FPScounter = clock.get_fps()
    FPScounter_display = RingFont.render(f"FPS: {int(FPScounter)}", True, (255, 255, 255))
    screen.blit(FPScounter_display, (1160, 0))

    pygame.display.flip()
    clock.tick(60)  # Limits FPS