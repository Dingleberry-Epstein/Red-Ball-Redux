import pygame
import os
import pytmx
from characters import Sonic
from objects import Tile, Ring, Enemy, GameObject
from constants import *
from utils import Camera

pygame.init()
pygame.mixer.init()

class Level:
    """Base level class"""
    def __init__(self):
        self.background = None
        self.tiles = pygame.sprite.Group()
        self.objects = pygame.sprite.Group()
        self.camera = None
        self.level_width = 0
        self.level_height = 0

    def load_tiles(self):
        """Load tiles - to be implemented by subclasses"""
        pass

    def update(self):
        """Update level objects - to be implemented by subclasses"""
        pass

    def draw(self, screen):
        """Draw level and all objects"""
        if self.background:
            screen.blit(self.background, (0, 0))
        
        for sprite in self.tiles:
            screen.blit(sprite.image, self.camera.apply(sprite))

        for obj in self.objects:
            screen.blit(obj.image, self.camera.apply(obj))


class EggmanLand(Level):
    """Specific level implementation (formerly Windmill Isle)"""
    def __init__(self):
        super().__init__()
        
        self.background = pygame.transform.scale(
            pygame.image.load(os.path.join("assets", "backgrounds", "windmillisle.png")).convert(),
            (SCREEN_WIDTH, SCREEN_HEIGHT)
        )
        pygame.mixer_music.load(os.path.join("assets", "music", "windmillisle.mp3"))

        self.sonic = Sonic(100, 300)
        self.rings = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        
        self.ring_counter = 0
        
        # Load level size from TMX
        self.tmx = pytmx.load_pygame(os.path.join("assets", "world building", "Tiled Worlds", "sonic test world.tmx"))
        self.level_width = self.tmx.width * 96
        self.level_height = self.tmx.height * 96
        self.camera = Camera(self.level_width, self.level_height)
        
        # Load level elements
        self.load_tiles()
        self.load_rings()
        self.load_enemies()

    def load_tiles(self):
        """Loads tiles from TMX file and adds them to tile_group."""
        for layer in self.tmx.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                layer_index = self.tmx.layers.index(layer)
                is_collidable = layer.name != "non-collideable"

                for x, y, tile_gid in layer.tiles():
                    tile_image = self.tmx.get_tile_image(x, y, layer_index)
                    if not tile_image:
                        continue

                    tile_x, tile_y = x * 64, y * 64
                    angle = self.tmx.get_tile_properties(x, y, layer_index).get("angle", 0) if self.tmx.get_tile_properties(x, y, layer_index) else 0

                    # Process tile image
                    scaled_tile = pygame.transform.scale(tile_image, (64, 64))
                    final_tile = pygame.Surface((64, 64), pygame.SRCALPHA)
                    final_tile.blit(scaled_tile, (0, 0))
                    final_tile.set_colorkey((0, 0, 0))

                    # Add tile to group
                    tile = Tile(final_tile, (tile_x, tile_y), angle if is_collidable else None, collideable=is_collidable)
                    self.tiles.add(tile)

    def load_rings(self):
        """Populates rings at evenly spaced intervals."""
        min_x, max_x, num_rings = 100, 900, 5
        gap_width = (max_x - min_x) // (num_rings + 1)

        for i in range(1, num_rings + 1):
            ring = Ring(min_x + i * gap_width, 425)
            self.rings.add(ring)
            self.objects.add(ring)

    def load_enemies(self):
        """Loads enemies (currently a placeholder)."""
        pass

    def handle_tile_collision(self):
        """Handles Sonic's collision with tiles efficiently."""
        self.sonic.grounded = False  # Default assumption

        for tile in self.tiles:
            if not getattr(tile, "collideable", True):
                continue

            if self.sonic.mask.overlap(tile.mask, (tile.rect.x - self.sonic.hitbox.x, tile.rect.y - self.sonic.hitbox.y)):
                if getattr(tile, "loop_left_wall", False) and self.sonic.contact_mode == FLOOR:
                    continue  # Sonic phases through left loop walls while on the floor
                if getattr(tile, "loop_floor", False) and self.sonic.contact_mode in [LEFT_WALL, RIGHT_WALL]:
                    continue  # Sonic phases through loop floors while on the walls

                # Sonic collides with the tile
                self.sonic.Yvel = 0
                self.sonic.grounded = True
                self.sonic.jumped = False
                self.sonic.angle = tile.angle
                break  # Stop checking after the first collision

    def check_ring_collisions(self):
        """Checks if Sonic collects any rings."""
        for ring in self.rings:
            if pygame.sprite.collide_rect(ring, self.sonic):
                ring.collect()
                self.ring_counter += 1
                self.rings.remove(ring)
                self.objects.remove(ring)

    def update(self):
        """Updates game objects and handles collisions."""
        self.sonic.update()
        self.camera.update(self.sonic)
        self.handle_tile_collision()
        
        for ring in self.rings:
            ring.update()
            
        for enemy in self.enemies:
            enemy.update(self.sonic.rect)
            
        self.check_ring_collisions()

    def draw(self, screen):
        """Overrides the base draw method to include Sonic and the ring counter"""
        super().draw(screen)
        
        # Draw Sonic
        screen.blit(self.sonic.image, self.camera.apply(self.sonic))
        
        # Display ring counter
        ring_counter_display = RingFont.render(f"RINGS: {self.ring_counter}", True, (255, 255, 255))
        screen.blit(ring_counter_display, (0, 0))