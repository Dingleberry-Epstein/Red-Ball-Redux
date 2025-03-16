import pygame
from levels import Windmill_Isle
from constants import SCREEN_WIDTH, SCREEN_HEIGHT, RingFont

class Game:
    """Main game loop manager"""
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.level = Windmill_Isle()
        self.running = True
        pygame.display.set_caption("Sonic In Pygame: The Quest to Make a Sonic Game with Python")

    def run(self):
        """Main game loop"""
        while self.running:
            self.handle_events()
            self.update()
            self.render()

    def handle_events(self):
        """Process input events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                self.running = False

    def update(self):
        """Update game objects"""
        self.level.update()

    def render(self):
        """Render everything on the screen"""
        self.screen.fill("BLACK")
        self.level.draw(self.screen)
        
        # FPS Display
        fps_counter = self.clock.get_fps()
        fps_display = RingFont.render(f"FPS: {int(fps_counter)}", True, (255, 255, 255))
        self.screen.blit(fps_display, (1160, 0))

        pygame.display.flip()
        self.clock.tick(60)

if __name__ == "__main__":
    Game().run()