import pygame, os

pygame.mixer.init()
pygame.font.init()
pygame.display.init()

PLAYER_WIDTH = 64
PLAYER_HEIGHT = 64
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (150, 150, 150)
LIGHT_GRAY = (200, 200, 200)



CURRENT_TRACK = None

# Default values that can be overridden
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
TARGET_FPS = 60
FULLSCREEN = False
VSYNC = True

daFont = os.path.join("assets", "Daydream.ttf")