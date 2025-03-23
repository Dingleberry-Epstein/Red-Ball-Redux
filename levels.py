# levels.py - Level class that inherits from a more general Level base class
import pygame, os, random, math, pytmx, json
from characters import Sonic, Tails
from objects import *
from constants import *
from utils import Camera

pygame.init()
pygame.mixer.init()

class Level:
    """Base class for all game levels"""
    def __init__(self):
        self.background = None
        self.character = None
        self.camera = None
        self.tile_group = pygame.sprite.Group()
        self.ring_sound_queue = []
        self.ring_sound_delay = 50
        self.last_ring_sound_time = 0
        
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
    def __init__(self, character):
        super().__init__()
        self.background_img = pygame.image.load(os.path.join("assets", "backgrounds", "windmillisle.png")).convert()
        self.background = pygame.transform.scale(self.background_img, (SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.mixer_music.load(os.path.join("assets", "music", "windmillisle.mp3"))
        if character == "Sonic":
            self.character = Sonic(100, 1500)
        elif character == "Tails":
            self.character = Tails(100, 1500)
        self.rings = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.monkey_bars = pygame.sprite.Group()  # New group for monkey bars
        self.springs = pygame.sprite.Group()
        self.load_enemies()
        self.ring_counter = 0
        self.show_target = False
        self.tile_group = self.load_tiles()

        # Determine level size based on tiles
        level_width = Windmill_Isle_TMX.width * 96  # Tile width * tile size
        level_height = Windmill_Isle_TMX.height * 96
        self.camera = Camera(level_width, level_height)

    def load_tiles(self):
        """Load level tiles while ignoring the 'masks' layer."""
        tile_group = pygame.sprite.Group()

        for layer in Windmill_Isle_TMX.visible_layers:
            # Ignore the "masks" layer entirely
            if isinstance(layer, pytmx.TiledTileLayer) and layer.name not in ["masks", "objects"]:
                layer_index = Windmill_Isle_TMX.layers.index(layer)

                for x, y, tile_gid in layer.tiles():
                    tile_x = x * 64
                    tile_y = y * 64

                    tile_properties = Windmill_Isle_TMX.get_tile_properties(x, y, layer_index)
                    angle = tile_properties.get("angle", 0) if tile_properties else 0

                    tile_image = Windmill_Isle_TMX.get_tile_image(x, y, layer_index)

                    # Determine if the tile should be collideable
                    collideable = layer.name not in ["non-collideable", "background"]

                    if tile_image:
                        # Create a 64x64 surface with transparency
                        scaled_tile_image = pygame.Surface((64, 64), pygame.SRCALPHA)
                        scaled_tile_image.blit(pygame.transform.scale(tile_image, (64, 64)), (0, 0))

                        # Remove black background by setting the color key
                        scaled_tile_image.set_colorkey((0, 0, 0))

                        tile_group.add(Tile(scaled_tile_image, (tile_x, tile_y), angle, collideable=collideable))

        # Process objects separately
        objects_layer = next((layer for layer in Windmill_Isle_TMX.layers if isinstance(layer, pytmx.TiledTileLayer) and layer.name == "objects"), None)

        if objects_layer:
            layer_index = Windmill_Isle_TMX.layers.index(objects_layer)

            for x, y, tile_gid in objects_layer.tiles():
                tile_properties = Windmill_Isle_TMX.get_tile_properties(x, y, layer_index)

                if tile_properties:
                    tile_x = x * 64
                    tile_y = y * 64

                    # Handle rings
                    if tile_properties.get("ring", False):
                        self.rings.add(Ring(tile_x, tile_y))

                    # Handle springs
                    if tile_properties.get("spring", False):
                        angle = int(tile_properties.get("angle", 90))  # Default to 90° (up)
                        self.springs.add(Spring(tile_x, tile_y, angle))

                    # Handle monkey bars
                    if tile_properties.get("monkey_bar", False):
                        tile_image = Windmill_Isle_TMX.get_tile_image(x, y, layer_index)
                        if tile_image:
                            scaled_tile_image = pygame.Surface((64, 64), pygame.SRCALPHA)
                            scaled_tile_image.blit(pygame.transform.scale(tile_image, (64, 64)), (0, 0))
                            scaled_tile_image.set_colorkey((0, 0, 0))

                            # Create a monkey bar tile
                            monkey_bar = Tile(scaled_tile_image, (tile_x, tile_y), 0, collideable=True)
                            monkey_bar.is_monkey_bar = True

                            # Add to both groups for easier management
                            tile_group.add(monkey_bar)
                            self.monkey_bars.add(monkey_bar)

        return tile_group

    def handle_tile_collision(self):
        """Handles Sonic's collision with tiles efficiently."""
        
        # If Sonic is already on monkey bars, we handle them differently
        if self.character.swinging:
            # Check if Sonic has moved off the monkey bar
            still_on_bar = False
            for bar in self.monkey_bars:
                if pygame.Rect.colliderect(self.character.hitbox, bar.rect):
                    still_on_bar = True
                    break
            
            if not still_on_bar:
                # Sonic has moved off the monkey bar - release
                self.character.release_monkey_bar(jump=False)
            
            # Skip regular collision detection while swinging
            return
        
        # First check for monkey bars if not swinging
        # Only check if Sonic is in the air (jumping or falling)
        if not self.character.grounded:  # Allow grabbing when in air (falling or jumping)
            for bar in self.monkey_bars:
                if pygame.Rect.colliderect(self.character.sensor_top, bar.rect):
                    self.character.grab_monkey_bar(bar)
                    return  # Exit after grabbing
        
        for spring in self.springs:
            # Use rect collision first as a quick check
            if pygame.Rect.colliderect(self.character.hitbox, spring.rect):
                # Then do a more precise mask collision check
                offset_x = spring.rect.x - self.character.hitbox.x
                offset_y = spring.rect.y - self.character.hitbox.y
                
                # Make sure spring has a mask
                if not hasattr(spring, 'mask') or spring.mask is None:
                    spring.mask = pygame.mask.from_surface(spring.image)
                    
                # Make sure sonic has a mask
                if not hasattr(self.character, 'mask') or self.character.mask is None:
                    self.character.mask = pygame.mask.from_surface(self.character.image)
                    
                # Check for mask collision
                if self.character.mask.overlap(spring.mask, (offset_x, offset_y)):
                    print("Spring activated!") # Debug message
                    self.character.activate_spring(spring.angle, spring.force)
                    # **Ensure every spring always plays its sound**
                    if not spring.sound_played:
                        if spring.sound_channel:  # If a free channel is found, use it
                            spring.sound_channel.play(spring.sound)
                        else:  # If no free channel, fall back to normal play
                            spring.sound.play()
                        
                        spring.sound_played = True  # Prevent repeated triggers
                    
                spring.sound_played = False  # Reset sound flag after collision check

        # Default assumption - not on ground
        self.character.grounded = False  

        for tile in self.tile_group:
            # Skip non-collideable tiles and monkey bars for regular collision
            if not getattr(tile, "collideable", True) or getattr(tile, "is_monkey_bar", False):
                continue

            if self.character.mask.overlap(tile.mask, (tile.rect.x - self.character.hitbox.x, tile.rect.y - self.character.hitbox.y)):

                if self.character.launched:
                    self.character.launched = False
                    self.character.launch_timer = 0
                    print("Launch ended early due to tile collision")

                # Sonic collides with the tile
                self.character.Yvel = 0
                self.character.grounded = True
                self.character.jumped = False
                # Interpolate angle for smooth transition
                angle_difference = (tile.angle - self.character.angle) % 360
                if angle_difference > 180:
                    angle_difference -= 360  # Take the shortest rotation direction

                # Adjust speed of rotation based on Sonic's speed
                rotation_speed = max(5, abs(self.character.groundSpeed) * 0.3)  # Faster when moving fast
                self.character.angle += angle_difference * 0.2 * rotation_speed
                break  # Stop checking after the first collision
        if not self.character.grounded:
            # Reset angle smoothly back to 0 when in air
            self.character.angle += (0 - self.character.angle) * 0.15

    def check_ring_collisions(self):
        current_time = pygame.time.get_ticks()
        """Checks if Sonic collects any rings."""

        for ring in list(self.rings):  # Convert to list to avoid modifying during iteration
            if pygame.sprite.collide_rect(ring, self.character):
                self.ring_counter += 1
                self.rings.remove(ring)  # Remove the ring from the group
                self.ring_sound_queue.append(ring.sound)  # Add sound to queue

        # Play ring sounds sequentially to avoid overlap
        if self.ring_sound_queue and current_time - self.last_ring_sound_time > self.ring_sound_delay:
            sound = self.ring_sound_queue.pop(0)  # Get first queued sound
            sound.play()
            self.last_ring_sound_time = current_time  # Reset sound timer

    def draw(self, screen):
        screen.blit(self.background, (0, 0))

        # Draw tiles using camera offsets
        for tile in self.tile_group:
            screen.blit(tile.image, self.camera.apply(tile))
        
        for spring in self.springs:
            screen.blit(spring.image, self.camera.apply(spring))

        # Draw Sonic
        screen.blit(self.character.image, self.camera.apply(self.character))

                # Convert mask to surface for debugging
        mask_surface = self.character.mask.to_surface(setcolor=(255, 0, 0, 100), unsetcolor=(0, 0, 0, 0))  # Red overlay, transparent background
        mask_surface.set_colorkey((0, 0, 0))  # Make black transparent

        # Blit mask over character
        screen.blit(mask_surface, self.camera.apply(self.character))

        # Draw rings
        for ring in self.rings:
            screen.blit(ring.image, self.camera.apply(ring))

        # Draw enemies
        for enemy in self.enemies:
            screen.blit(enemy.image, self.camera.apply(enemy))

        # Display ring counter
        ring_counter_display = RingFont.render("RINGS: " + str(self.ring_counter), True, (255, 255, 255))
        screen.blit(ring_counter_display, (0, 0))

        # **Draw homing target indicator (scaled and centered)**
        if self.character.homing_target and not self.character.homing_attack_active:
            target_rect = self.character.homing_target.rect
            homing_scaled = pygame.transform.smoothscale(homing_image, (target_rect.width, target_rect.height))
            homing_x = target_rect.centerx - self.camera.viewport.x - (homing_scaled.get_width() // 2)
            homing_y = target_rect.centery - self.camera.viewport.y - (homing_scaled.get_height() // 2)
            screen.blit(homing_scaled, (homing_x, homing_y))

        # Apply camera to Sonic's position, then draw the debug dot
        center_x, center_y = self.character.rect.center
        offset_x, offset_y = self.camera.apply(self.character).topleft  # Get camera offset
        pygame.draw.circle(screen, (0, 255, 0), (center_x - offset_x, center_y - offset_y), 3)

    def load_enemies(self):
        pass

    def update(self):
        # Update Sonic first
        self.character.update()
        
        # Update camera to follow Sonic
        self.camera.update(self.character)

        # Reset grounded state if not swinging
        if not self.character.swinging:
            self.character.grounded = False
        
        # Optimize collision detection with spatial partitioning
        # Only check tiles that are close to Sonic
        camera_rect = pygame.Rect(self.camera.viewport.x, self.camera.viewport.y, SCREEN_WIDTH, SCREEN_HEIGHT)
        
        # Expand the check area slightly to catch tiles just outside view
        check_rect = camera_rect.inflate(128, 128)
        
        # Only check tiles within view range
        visible_tiles = [tile for tile in self.tile_group if check_rect.colliderect(tile.rect)]
        
        # Only update rings that are visible on screen
        for ring in self.rings:
            ring.update()
        
        # Update enemies only if they're visible
        visible_enemies = [enemy for enemy in self.enemies if camera_rect.colliderect(enemy.rect)]
        for enemy in visible_enemies:
            enemy.update(self.character.rect)

        self.handle_tile_collision()
        self.check_ring_collisions()
        if self.character.jumped and not self.character.homing_attack_active and not self.character.homing_target:
            # Pass the enemy and spring groups to Sonic's find_homing_target method
            self.character.find_homing_target(self.enemies, self.springs)
