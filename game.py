import pygame
from levels import Windmill_Isle
from constants import *

class Game:
    """Main game loop manager"""
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = "main_menu"
        self.level = None  # Prevent crash when `game` state is entered
        pygame.display.set_caption("Sonic In Pygame: The Quest to Make a Sonic Game with Python")

    def run(self):
        """Main game loop"""
        while self.running:
            self.handle_events()

            if self.state == "main_menu":
                self.render_main_menu()
            elif self.state == "game":
                self.update()
                self.render()

    def handle_events(self):
        """Process input events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_2:
                self.level = Windmill_Isle('Tails')
                self.state = "game"
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_1:
                self.level = Windmill_Isle('Sonic')
                self.state = "game"

    def update(self):
        """Update game objects"""
        if self.level:
            self.level.update()

    def render(self):
        """Render everything on the screen"""
        self.screen.fill("BLACK")
        if self.level:
            self.level.draw(self.screen)

        # FPS Display
        fps_counter = self.clock.get_fps()
        fps_display = RingFont.render(f"FPS: {int(fps_counter)}", True, (255, 255, 255))
        self.screen.blit(fps_display, (1160, 0))

        pygame.display.flip()
        self.clock.tick(60)

    def render_main_menu(self):
        """Render main menu screen"""
        self.screen.fill("BLACK")  # Clear the screen
        charSelectText = gameover_font.render("Press 1 to play as Sonic, press 2 to play as Tails!", True, (255, 255, 255))
        text_rect = charSelectText.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
        self.screen.blit(charSelectText, text_rect)

        pygame.display.flip()  # Refresh screen

if __name__ == "__main__":
    Game().run()