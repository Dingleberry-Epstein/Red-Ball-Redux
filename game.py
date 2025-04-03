import pygame
import os
from constants import *
from levels import PymunkLevel
from utils import PhysicsManager
from characters import PurePymunkBall
from objects import Windmill_Isle_TMX

class Game:
    """Main game using impulse-based ball movement"""
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = "main_menu"
        
        # Set up physics and level
        self.physics = None
        self.level = None
        
        pygame.display.set_caption("Impulse-Based Pymunk Physics")

    def run(self):
        """Main game loop"""
        while self.running:
            # Calculate delta time for smooth physics
            dt = self.clock.tick(60) / 1000.0  # Convert to seconds
            
            self.handle_events()

            if self.state == "main_menu":
                self.render_main_menu()
            elif self.state == "game":
                self.update(dt)
                self.render()

    def handle_events(self):
        """Process input events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    # Start game with test level
                    self.setup_game()
                    self.state = "game"
                elif event.key == pygame.K_r and self.level:
                    # Reset level
                    self.setup_game()
            
            # Pass events to level for layer switching if we're in the game
            if self.level and self.state == "game":
                self.level.handle_events(event)

    def setup_game(self):
        """Set up physics and level with impulse-based ball"""
        # Create minimal physics manager
        self.physics = PhysicsManager()
        
        # Create level with impulse-based ball
        self.level = PymunkLevel(tmx_map=Windmill_Isle_TMX)

    def update(self, dt):
        """Update physics simulation"""
        if self.level:
            self.level.update(dt)

    def render(self):
        """Render simulation to screen"""
        self.screen.fill("BLACK")
        
        if self.level:
            self.level.draw(self.screen)

        # FPS Display
        fps_counter = self.clock.get_fps()
        fps_display = pygame.font.SysFont(None, 24).render(f"FPS: {int(fps_counter)}", True, (255, 255, 255))
        self.screen.blit(fps_display, (SCREEN_WIDTH - 100, 10))

        pygame.display.flip()

    def render_main_menu(self):
        """Render main menu screen"""
        self.screen.fill("BLACK")
        font = pygame.font.SysFont(None, 36)
        
        menu_text = [
            "Impulse-Based Pymunk Physics",
            "",
            "Press ENTER to start test level",
            "Press R to reset the level",
            "Press L to switch mask layers",
            "Press ESC to quit"
        ]
        
        for i, text in enumerate(menu_text):
            text_surf = font.render(text, True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=(SCREEN_WIDTH//2, 200 + i*40))
            self.screen.blit(text_surf, text_rect)
            
        pygame.display.flip()

if __name__ == "__main__":
    Game().run()