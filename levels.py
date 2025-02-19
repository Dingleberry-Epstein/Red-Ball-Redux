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

EggmanLandTMX = pytmx.load_pygame(os.path.join("assets", "world building", "Tiled Worlds", "sonic test world.tmx"))

class Eggman_Land:
    def __init__(self):
        self.background_img = pygame.image.load(os.path.join("assets", "backgrounds", "EggmanLandBG.png")).convert()
        self.background = pygame.transform.scale(self.background_img, (SCREEN_WIDTH, SCREEN_HEIGHT))
        self.sonic = Sonic(100, 300)
        self.rings = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.load_rings()
        self.load_enemies()
        self.ring_counter = 0
        self.show_target = False
        self.tile_group = self.load_tiles()

        # Determine level size based on tiles
        level_width = EggmanLandTMX.width * 96  # Tile width * tile size
        level_height = EggmanLandTMX.height * 96
        self.camera = Camera(level_width, level_height)

    def load_tiles(self):
        tile_group = pygame.sprite.Group()
        for layer in EggmanLandTMX.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):  # Ensure it's a tile layer
                for x, y, tile_gid in layer.tiles():  # Get tile GID
                    tile_x = x * 96
                    tile_y = y * 96

                    # Get properties from the TMX file using map coordinates
                    properties = EggmanLandTMX.get_tile_properties(x, y, EggmanLandTMX.layers.index(layer))

                    # Extract the angle, defaulting to 0 if missing
                    angle = properties.get("angle", 0) if properties else 0

                    tile_group.add(Tile(tile_gid, (tile_x, tile_y), angle))

        return tile_group

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

        # Keep Sonic grounded
        self.sonic.grounded = False  
        for tile in self.tile_group:
            if self.sonic.mask.overlap(tile.mask, (tile.rect.x - self.sonic.hitbox.x, tile.rect.y - self.sonic.hitbox.y)):  
                self.sonic.Yvel = 0
                self.sonic.grounded = True  
                self.sonic.jumped = False
                self.sonic.angle = tile.angle
                break 

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