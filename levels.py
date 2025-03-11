# levels.py - Level class that inherits from a more general Level base class
import pygame
import os
import random
import math
import pytmx
from characters import Sonic
from objects import *
from constants import *
from utils import Camera

pygame.init()
pygame.mixer.init()

class Level:
    """Base class for all game levels"""
    def __init__(self):
        self.background = None
        self.sonic = None
        self.camera = None
        self.tile_group = pygame.sprite.Group()
        
    def load_tiles(self):
        """Load level tiles"""
        pass
        
    def draw(self, screen):
        """Draw level elements"""
        pass
        
    def update(self):
        """Update level state"""
        pass

class Windmill_Isle(Level):
    def __init__(self):
        super().__init__()
        self.background_img = pygame.image.load(os.path.join("assets", "backgrounds", "windmillisle.png")).convert()
        self.background = pygame.transform.scale(self.background_img, (SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.mixer_music.load(os.path.join("assets", "music", "windmillisle.mp3"))
        self.sonic = Sonic(100, 300)
        self.rings = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.load_enemies()
        self.ring_counter = 0
        self.show_target = False
        self.tile_group = self.load_tiles()

        # Determine level size based on tiles
        level_width = Windmill_Isle_TMX.width * 96  # Tile width * tile size
        level_height = Windmill_Isle_TMX.height * 96
        self.camera = Camera(level_width, level_height)

    def load_tiles(self):
        tile_group = pygame.sprite.Group()
        
        # First, process all regular visible tiles
        for layer in Windmill_Isle_TMX.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer) and layer.name != "objects":
                layer_index = Windmill_Isle_TMX.layers.index(layer)

                for x, y, tile_gid in layer.tiles():
                    tile_x = x * 64
                    tile_y = y * 64

                    tile_properties = Windmill_Isle_TMX.get_tile_properties(x, y, layer_index)
                    angle = tile_properties.get("angle", 0) if tile_properties else 0

                    tile_image = Windmill_Isle_TMX.get_tile_image(x, y, layer_index)

                    if tile_image:
                        # Create a 64x64 surface with transparency
                        scaled_tile_image = pygame.Surface((64, 64), pygame.SRCALPHA)
                        scaled_tile_image.blit(pygame.transform.scale(tile_image, (64, 64)), (0, 0))

                        # Remove black background by setting the color key
                        scaled_tile_image.set_colorkey((0, 0, 0))

                        # Check if the tile belongs to the pass-through loop layer
                        if layer.name == "non-collideable":
                            tile_group.add(Tile(scaled_tile_image, (tile_x, tile_y), angle=None, collideable=False))
                        else:
                            tile_group.add(Tile(scaled_tile_image, (tile_x, tile_y), angle))
        
        # Separately process the objects layer, including invisible tiles
        objects_layer = None
        for layer in Windmill_Isle_TMX.layers:
            if isinstance(layer, pytmx.TiledTileLayer) and layer.name == "objects":
                objects_layer = layer
                break
        
        if objects_layer:
            layer_index = Windmill_Isle_TMX.layers.index(objects_layer)
            
            for x, y, tile_gid in objects_layer.tiles():
                tile_properties = Windmill_Isle_TMX.get_tile_properties(x, y, layer_index)
                
                if tile_properties and tile_properties.get("ring", False):
                    tile_x = x * 64
                    tile_y = y * 64
                    ring = Ring(tile_x, tile_y)
                    self.rings.add(ring)

        return tile_group

    def handle_tile_collision(self):
        """Handles Sonic's collision with tiles efficiently."""
        self.sonic.grounded = False  # Default assumption

        for tile in self.tile_group:
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
                self.ring_counter += 1
                self.rings.remove(ring)

    def draw(self, screen):
        screen.blit(self.background, (0, 0))

        # Draw tiles using camera offsets
        for tile in self.tile_group:
            screen.blit(tile.image, self.camera.apply(tile))


        # Draw Sonic
        screen.blit(self.sonic.image, self.camera.apply(self.sonic))

        # Draw rings
        for ring in self.rings:
            screen.blit(ring.image, self.camera.apply(ring))

        # Draw enemies
        for enemy in self.enemies:
            screen.blit(enemy.image, self.camera.apply(enemy))

        # Display ring counter
        ring_counter_display = RingFont.render("RINGS: " + str(self.ring_counter), True, (255, 255, 255))
        screen.blit(ring_counter_display, (0, 0))

    def load_enemies(self):
        pass

    def update(self):
        # Update Sonic first
        self.sonic.update()
        
        # Update camera to follow Sonic
        self.camera.update(self.sonic)
        
        # Reset grounded state
        self.sonic.grounded = False
        
        # Optimize collision detection with spatial partitioning
        # Only check tiles that are close to Sonic
        camera_rect = pygame.Rect(self.camera.viewport.x, self.camera.viewport.y, SCREEN_WIDTH, SCREEN_HEIGHT)
        
        # Expand the check area slightly to catch tiles just outside view
        check_rect = camera_rect.inflate(128, 128)
        
        # Only check tiles within view range
        visible_tiles = [tile for tile in self.tile_group if check_rect.colliderect(tile.rect)]
        
        # Only update rings that are visible on screen
        visible_rings = [ring for ring in self.rings if camera_rect.colliderect(ring.rect)]
        for ring in visible_rings:
            ring.update()
        
        # Update enemies only if they're visible
        visible_enemies = [enemy for enemy in self.enemies if camera_rect.colliderect(enemy.rect)]
        for enemy in visible_enemies:
            enemy.update(self.sonic.rect)

        self.handle_tile_collision()
        self.check_ring_collisions()