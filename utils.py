import pygame, os, math
from constants import *
from random import randint
from pytmx.util_pygame import *

pygame.init()
pygame.display.set_mode((1280, 720))

clock = pygame.time.Clock()

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720

GRAY = (150, 150, 150)
LIGHT_GRAY = (200, 200, 200)
hover_sound = pygame.mixer.Sound(os.path.join("assets", "sounds" , "HoverSound.mp3"))
select_sound = pygame.mixer.Sound(os.path.join("assets", "sounds" , "SelectSound.mp3"))

def fade_in_out(image, duration):
    alpha = 0
    scaled_image = pygame.transform.scale(image, (int(image.get_width() * 0.33), int(image.get_height() * 0.33)))
    image_rect = scaled_image.get_rect(center=screen.get_rect().center)

    # Set the background color
    background_color = (255, 255, 255)
    screen.fill(background_color)
    pygame.display.flip()
    clock.tick(60)  # Adjust the frame rate as needed 

    # Fade in
    while alpha < 255:
        alpha += 5  # Adjust the speed of the fade-in
        scaled_image.set_alpha(alpha)
        screen.fill(background_color)  # Clear the screen with the background color
        screen.blit(scaled_image, image_rect)
        pygame.display.flip()
        clock.tick(60)  # Adjust the frame rate as needed

    # Hold the image for the specified duration
    pygame.time.wait(duration * 1000)  # Convert seconds to milliseconds

    # Fade out
    while alpha > 0:
        alpha -= 5  # Adjust the speed of the fade-out
        scaled_image.set_alpha(alpha)
        screen.fill(background_color)  # Clear the screen with the background color
        screen.blit(scaled_image, image_rect)
        pygame.display.flip()
        clock.tick(60)  # Adjust the frame rate as needed

def scene_fade_in(screen, clock, image, duration, background_color=(255, 255, 255)):
    """
    Fade in a scene on the screen.

    Args:
    - screen: The Pygame screen surface.
    - clock: Pygame clock object.
    - image: The image to be faded in.
    - duration: The duration of the fade-in effect in seconds.
    - background_color: The background color of the screen. Default is white (255, 255, 255).
    """
    alpha = 0
    image_rect = image.get_rect(center=screen.get_rect().center)

    # Fill the screen with the background color
    screen.fill(background_color)
    pygame.display.flip()
    clock.tick(60)  # Adjust the frame rate as needed

    # Scale the image to fit the screen while preserving its aspect ratio
    scaled_image = pygame.transform.smoothscale(image, (screen.get_width(), screen.get_height()))

    # Calculate the alpha increment per frame
    alpha_increment = 255 / (duration * 60)  # 60 FPS

    # Fade in
    while alpha < 255:
        alpha += alpha_increment
        scaled_image.set_alpha(int(alpha))
        screen.fill(background_color)  # Clear the screen with the background color
        screen.blit(scaled_image, (0, 0))
        pygame.display.flip()
        clock.tick(60)  # Adjust the frame rate as needed

def scene_fade_out(screen, clock, image, duration, background_color=(1, 1, 1)):
    """
    Fade out a scene on the screen.

    Args:
    - screen: The Pygame screen surface.
    - clock: Pygame clock object.
    - image: The image to be faded out.
    - duration: The duration of the fade-out effect in seconds.
    - background_color: The background color of the screen during the fade-out. Default is (1, 1, 1).
    """
    start_time = pygame.time.get_ticks()  # Get the start time in milliseconds
    scaled_image = pygame.transform.smoothscale(image, (screen.get_width(), screen.get_height()))

    # Calculate the alpha increment per frame
    alpha_increment = 255 / (duration * 60)  # 60 FPS

    # Fade out
    while pygame.time.get_ticks() - start_time < duration * 1000:  # Convert duration to milliseconds
        alpha = int((pygame.time.get_ticks() - start_time) / (duration * 2.5))  # Adjust the speed of the fade-out
        alpha = max(0, min(255, alpha))  # Ensure alpha stays within the valid range [0, 255]
        scaled_image.set_alpha(255 - alpha)
        screen.fill(background_color)  # Clear the screen with the background color
        screen.blit(scaled_image, (0, 0))
        pygame.display.flip()
        clock.tick(60)  # Adjust the frame rate as needed

class Button:
    def __init__(self, x, y, width, height, text):
        self.rect = pygame.Rect(x, y, width, height)
        self.default_color = GRAY
        self.hover_color = LIGHT_GRAY
        self.clicked = False
        self.hovered = False
        self.text = text
        self.hoverSoundPlayed = False
        self.clickSoundPlayed = False

    def draw(self, surface, font, text, text_color):
        if self.hovered:
            color = self.hover_color
        else:
            color = self.default_color
        pygame.draw.rect(surface, color, self.rect)
        text_surface = font.render(text, True, text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            pos = pygame.mouse.get_pos()
            self.hovered = self.rect.collidepoint(pos)
            if self.hovered and not self.hoverSoundPlayed:
                hover_sound.play()
                self.hoverSoundPlayed = True
            elif not self.hovered:
                self.hoverSoundPlayed = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = pygame.mouse.get_pos()
            is_clicked = self.rect.collidepoint(pos)
            if is_clicked and not self.clickSoundPlayed:
                select_sound.play()
                self.clickSoundPlayed = True
            elif not is_clicked:
                self.clickSoundPlayed = False
            self.clicked = is_clicked
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.clicked = False
        else:
            self.hovered = False

class Camera:
    def __init__(self, width, height):
        self.camera = pygame.Rect(0, 0, width, height)  # Viewport
        self.width = width
        self.height = height

    def apply(self, entity):
        """Offset an entity’s position relative to the camera"""
        return entity.rect.move(self.camera.topleft)

    def update(self, target):
        """Move the camera to follow Sonic"""
        x = -target.rect.centerx + SCREEN_WIDTH // 2  # Keep Sonic in the center
        y = -target.rect.centery + SCREEN_HEIGHT // 2

        # Clamp camera to level boundaries
        x = max(-(self.width - SCREEN_WIDTH), min(0, x))
        y = max(-(self.height - SCREEN_HEIGHT), min(0, y))

        self.camera = pygame.Rect(x, y, self.width, self.height)