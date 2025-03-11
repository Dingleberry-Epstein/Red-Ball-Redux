import pygame
import os
from constants import *

pygame.init()

class Camera:
    # Camera class that follows a target entity and handles viewport calculations
    def __init__(self, width, height):
        # Initialize the camera with level dimensions
        """
        Args:
            width (int): The width of the level
            height (int): The height of the level
        """
        self.viewport = pygame.Rect(0, 0, width, height)
        self.width = width
        self.height = height
        self.locked = False  # Add a lock state for the camera

    def apply(self, entity):
        # Offset an entity's position relative to the camera
        """
        Args:
            entity (GameObject): The entity to apply camera offset to
            
        Returns:
            pygame.Rect: Offset rect for rendering
        """
        return entity.rect.move(self.viewport.topleft)

    def update(self, target):
        # Move the camera to follow a target entity
        """
        Args:
            target (GameObject): The entity to follow (usually Sonic)
        """
        # If camera is locked (during death sequence), don't update position
        if self.locked:
            return
            
        # Center the target in the screen
        x = -target.rect.centerx + SCREEN_WIDTH // 2
        y = -target.rect.centery + SCREEN_HEIGHT // 2

        # Clamp camera to level boundaries
        x = max(-(self.width - SCREEN_WIDTH), min(0, x))
        y = max(-(self.height - SCREEN_HEIGHT), min(0, y))

        self.viewport = pygame.Rect(x, y, self.width, self.height)

class Button:
    # Interactive button class for UI elements
    def __init__(self, x, y, width, height, text):
        # Initialize a button with position and text
        """
        Args:
            x (int): X position
            y (int): Y position
            width (int): Button width
            height (int): Button height
            text (str): Button text
        """
        self.rect = pygame.Rect(x, y, width, height)
        self.default_color = GRAY
        self.hover_color = LIGHT_GRAY
        self.clicked = False
        self.hovered = False
        self.text = text
        self.hover_sound = pygame.mixer.Sound(os.path.join("assets", "sounds", "HoverSound.mp3"))
        self.select_sound = pygame.mixer.Sound(os.path.join("assets", "sounds", "SelectSound.mp3"))
        self.hover_sound_played = False
        self.click_sound_played = False

    def draw(self, surface, font, text_color=(0, 0, 0)):
        # Draw the button on a surface
        """
        Args:
            surface (pygame.Surface): Surface to draw on
            font (pygame.font.Font): Font for text rendering
            text_color (tuple): RGB color for text
        """
        # Use hover color if hovered, otherwise default color
        color = self.hover_color if self.hovered else self.default_color
        
        # Draw button rectangle
        pygame.draw.rect(surface, color, self.rect)
        
        # Render and center text
        text_surface = font.render(self.text, True, text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def handle_event(self, event):
        # Handle mouse events for the button
        """
        Args:
            event (pygame.event.Event): Pygame event to process
            
        Returns:
            bool: True if button was clicked, False otherwise
        """
        if event.type == pygame.MOUSEMOTION:
            # Check for hover state
            pos = pygame.mouse.get_pos()
            self.hovered = self.rect.collidepoint(pos)
            
            # Play hover sound once when first hovering
            if self.hovered and not self.hover_sound_played:
                self.hover_sound.play()
                self.hover_sound_played = True
            elif not self.hovered:
                self.hover_sound_played = False
                
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Check for click state
            pos = pygame.mouse.get_pos()
            is_clicked = self.rect.collidepoint(pos)
            
            # Play select sound once when clicked
            if is_clicked and not self.click_sound_played:
                self.select_sound.play()
                self.click_sound_played = True
                self.clicked = True
            elif not is_clicked:
                self.click_sound_played = False
                
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_clicked = self.clicked
            self.clicked = False
            return was_clicked and self.rect.collidepoint(pygame.mouse.get_pos())
            
        return False


class SceneManager:
    # Handles scene transitions and effects
    @staticmethod
    def fade_in(screen, image, duration, background_color=(255, 255, 255)):
        # Fade in a scene on the screen
        """
        Args:
            screen (pygame.Surface): The screen surface
            image (pygame.Surface): Image to fade in
            duration (float): Duration in seconds
            background_color (tuple): RGB background color
        """
        clock = pygame.time.Clock()
        alpha = 0
        
        # Scale image to fit screen
        scaled_image = pygame.transform.smoothscale(image, (screen.get_width(), screen.get_height()))
        
        # Calculate alpha increment per frame (60 FPS)
        alpha_increment = 255 / (duration * 60)
        
        # Fill background
        screen.fill(background_color)
        pygame.display.flip()
        
        # Fade in loop
        while alpha < 255:
            alpha += alpha_increment
            scaled_image.set_alpha(int(alpha))
            screen.fill(background_color)
            screen.blit(scaled_image, (0, 0))
            pygame.display.flip()
            clock.tick(60)

    @staticmethod
    def fade_out(screen, image, duration, background_color=(1, 1, 1)):
        # Fade out a scene from the screen
        """
        Args:
            screen (pygame.Surface): The screen surface
            image (pygame.Surface): Image to fade out
            duration (float): Duration in seconds
            background_color (tuple): RGB background color
        """
        clock = pygame.time.Clock()
        start_time = pygame.time.get_ticks()
        
        # Scale image to fit screen
        scaled_image = pygame.transform.smoothscale(image, (screen.get_width(), screen.get_height()))
        
        # Fade out loop
        while pygame.time.get_ticks() - start_time < duration * 1000:
            # Calculate alpha based on elapsed time
            elapsed = pygame.time.get_ticks() - start_time
            alpha = int(elapsed / (duration * 2.5))
            alpha = max(0, min(255, alpha))
            
            # Apply alpha and draw
            scaled_image.set_alpha(255 - alpha)
            screen.fill(background_color)
            screen.blit(scaled_image, (0, 0))
            pygame.display.flip()
            clock.tick(60)