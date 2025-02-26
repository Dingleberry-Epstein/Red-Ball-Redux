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

class Windmill_Isle:
    def __init__(self):
        self.background_img = pygame.image.load(os.path.join("assets", "backgrounds", "windmillisle.png")).convert()
        self.background = pygame.transform.scale(self.background_img, (SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.mixer_music.load(os.path.join("assets", "music", "windmillisle.mp3"))
        self.sonic = Sonic(100, 300)
        self.rings = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.load_rings()
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

        for layer in Windmill_Isle_TMX.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
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

        return tile_group # Return both normal and pass-through tiles

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

    def load_rings(self):
        num_rings = 5
        min_x, max_x = 100, 900
        gap_width = (max_x - min_x) // (num_rings + 1)
        y = 425

        for i in range(1, num_rings + 1):
            x = min_x + i * gap_width
            ring = Ring(x, y)
            self.rings.add(ring)

    def load_enemies(self):
        pass

    def update(self):
        self.sonic.update()
        self.camera.update(self.sonic)  # Follow Sonic
        print(self.sonic.contact_mode)
        # Keep Sonic grounded
        self.sonic.grounded = False  
        for tile in self.tile_group:  # Loop through each tile object
            if hasattr(tile, "collideable") and tile.collideable:
                # Check if Sonic's mask overlaps with the tile's mask
                if self.sonic.mask.overlap(tile.mask, (tile.rect.x - self.sonic.hitbox.x, tile.rect.y - self.sonic.hitbox.y)):
                    # Handle collision based on tile attributes and Sonic's contact mode
                    if hasattr(tile, "loop_left_wall") and tile.loop_left_wall:
                        # Sonic can phase through loop left walls if he is in floor mode
                        if self.sonic.contact_mode == FLOOR:
                            continue  # Skip collision for this tile
                        else:
                            # Handle collision with loop left wall
                            self.sonic.Yvel = 0
                            self.sonic.grounded = True
                            self.sonic.jumped = False
                            self.sonic.angle = tile.angle
                            break  # Stop checking after first collision

                    elif hasattr(tile, "loop_floor") and tile.loop_floor:
                        # Sonic can phase through loop floors if he is in left wall or right wall mode
                        if self.sonic.contact_mode in [LEFT_WALL, RIGHT_WALL]:
                            continue  # Skip collision for this tile
                        else:
                            # Handle collision with loop floor
                            self.sonic.Yvel = 0
                            self.sonic.grounded = True
                            self.sonic.jumped = False
                            self.sonic.angle = tile.angle
                            break  # Stop checking after first collision

                    else:
                        # Handle collision with regular tiles
                        self.sonic.Yvel = 0
                        self.sonic.grounded = True
                        self.sonic.jumped = False
                        self.sonic.angle = tile.angle
                        break  # Stop checking after first collision
                

            # Update rings & enemies
            self.rings.update()
            self.enemies.update(self.sonic.rect)

            for ring in self.rings:
                if pygame.sprite.collide_rect(ring, self.sonic):
                    ring.collectSound.play()
                    ring.kill()
                    self.ring_counter += 1

            self.rings.update()
            self.enemies.update(self.sonic.rect)