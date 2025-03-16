# levels.py - Level class that inherits from a more general Level base class
import pygame, os, random, math, pytmx, json
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
    def __init__(self):
        super().__init__()
        self.background_img = pygame.image.load(os.path.join("assets", "backgrounds", "windmillisle.png")).convert()
        self.background = pygame.transform.scale(self.background_img, (SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.mixer_music.load(os.path.join("assets", "music", "windmillisle.mp3"))
        self.sonic = Sonic(100, 1500)
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
        tile_group = pygame.sprite.Group()

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

                        # **Fixing Collision Handling Here**
                        if layer.name in ["non-collideable", "background"]:
                            collideable = False  # ✅ Explicitly setting non-collideable
                        else:
                            collideable = True   # ✅ Default for everything else

                        tile_group.add(Tile(scaled_tile_image, (tile_x, tile_y), angle, collideable=collideable))
        
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
                
                if tile_properties:
                    tile_x = x * 64
                    tile_y = y * 64
                    
                    # Handle rings
                    if tile_properties.get("ring", False):
                        ring = Ring(tile_x, tile_y)
                        self.rings.add(ring)

                    if tile_properties.get("spring", False):
                        angle = int(tile_properties.get("angle", 90))  # Default to 90° (up)
                        spring = Spring(tile_x, tile_y, angle)
                        self.springs.add(spring)

                    # Handle monkey bars - new feature
                    if tile_properties.get("monkey_bar", False):
                        # Create a special monkey bar tile
                        tile_image = Windmill_Isle_TMX.get_tile_image(x, y, layer_index)
                        if tile_image:
                            scaled_tile_image = pygame.Surface((64, 64), pygame.SRCALPHA)
                            scaled_tile_image.blit(pygame.transform.scale(tile_image, (64, 64)), (0, 0))
                            scaled_tile_image.set_colorkey((0, 0, 0))
                            
                            # Create a monkey bar tile with special properties
                            monkey_bar = Tile(scaled_tile_image, (tile_x, tile_y), 0, collideable=True)
                            monkey_bar.is_monkey_bar = True
                            
                            # Add to both groups for easier management
                            tile_group.add(monkey_bar)
                            self.monkey_bars.add(monkey_bar)

        return tile_group

    def handle_tile_collision(self):
        """Handles Sonic's collision with tiles efficiently."""
        
        # If Sonic is already on monkey bars, we handle them differently
        if self.sonic.swinging:
            # Check if Sonic has moved off the monkey bar
            still_on_bar = False
            for bar in self.monkey_bars:
                if pygame.Rect.colliderect(self.sonic.hitbox, bar.rect):
                    still_on_bar = True
                    break
            
            if not still_on_bar:
                # Sonic has moved off the monkey bar - release
                self.sonic.release_monkey_bar(jump=False)
            
            # Skip regular collision detection while swinging
            return
        
        # First check for monkey bars if not swinging
        # Only check if Sonic is in the air (jumping or falling)
        if not self.sonic.grounded:  # Allow grabbing when in air (falling or jumping)
            for bar in self.monkey_bars:
                if pygame.Rect.colliderect(self.sonic.sensor_top, bar.rect):
                    self.sonic.grab_monkey_bar(bar)
                    return  # Exit after grabbing
        
        for spring in self.springs:
            # Use rect collision first as a quick check
            if pygame.Rect.colliderect(self.sonic.hitbox, spring.rect):
                # Then do a more precise mask collision check
                offset_x = spring.rect.x - self.sonic.hitbox.x
                offset_y = spring.rect.y - self.sonic.hitbox.y
                
                # Make sure spring has a mask
                if not hasattr(spring, 'mask') or spring.mask is None:
                    spring.mask = pygame.mask.from_surface(spring.image)
                    
                # Make sure sonic has a mask
                if not hasattr(self.sonic, 'mask') or self.sonic.mask is None:
                    self.sonic.mask = pygame.mask.from_surface(self.sonic.image)
                    
                # Check for mask collision
                if self.sonic.mask.overlap(spring.mask, (offset_x, offset_y)):
                    print("Spring activated!") # Debug message
                    self.sonic.activate_spring(spring.angle, spring.force)
                    # **Ensure every spring always plays its sound**
                    if not spring.sound_played:
                        if spring.sound_channel:  # If a free channel is found, use it
                            spring.sound_channel.play(spring.sound)
                        else:  # If no free channel, fall back to normal play
                            spring.sound.play()
                        
                        spring.sound_played = True  # Prevent repeated triggers
                    
                spring.sound_played = False  # Reset sound flag after collision check

        # Default assumption - not on ground
        self.sonic.grounded = False  

        for tile in self.tile_group:
            # Skip non-collideable tiles and monkey bars for regular collision
            if not getattr(tile, "collideable", True) or getattr(tile, "is_monkey_bar", False):
                continue

            if self.sonic.mask.overlap(tile.mask, (tile.rect.x - self.sonic.hitbox.x, tile.rect.y - self.sonic.hitbox.y)):
                if getattr(tile, "loop_left_wall", False) and self.sonic.contact_mode == FLOOR:
                    self.sonic.angle = 0  # Sonic phases through left loop walls while on the floor
                if getattr(tile, "loop_floor", False) and self.sonic.contact_mode in [LEFT_WALL, RIGHT_WALL]:
                    continue  # Sonic phases through loop floors while on the walls

                if self.sonic.launched:
                    self.sonic.launched = False
                    self.sonic.launch_timer = 0
                    print("Launch ended early due to tile collision")

                # Sonic collides with the tile
                self.sonic.Yvel = 0
                self.sonic.grounded = True
                self.sonic.jumped = False
                self.sonic.angle = tile.angle
                break  # Stop checking after the first collision

    def check_ring_collisions(self):
        current_time = pygame.time.get_ticks()
        """Checks if Sonic collects any rings."""

        for ring in list(self.rings):  # Convert to list to avoid modifying during iteration
            if pygame.sprite.collide_rect(ring, self.sonic):
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

        # **Draw homing target indicator (scaled and centered)**
        if self.sonic.homing_target and not self.sonic.homing_attack_active:
            target_rect = self.sonic.homing_target.rect
            homing_scaled = pygame.transform.smoothscale(homing_image, (target_rect.width, target_rect.height))
            homing_x = target_rect.centerx - self.camera.viewport.x - (homing_scaled.get_width() // 2)
            homing_y = target_rect.centery - self.camera.viewport.y - (homing_scaled.get_height() // 2)
            screen.blit(homing_scaled, (homing_x, homing_y))

    def load_enemies(self):
        pass

    def update(self):
        # Update Sonic first
        self.sonic.update()
        
        # Update camera to follow Sonic
        self.camera.update(self.sonic)
        
        # Reset grounded state if not swinging
        if not self.sonic.swinging:
            self.sonic.grounded = False
        
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
            enemy.update(self.sonic.rect)

        self.handle_tile_collision()
        self.check_ring_collisions()
        if self.sonic.jumped and not self.sonic.homing_attack_active and not self.sonic.homing_target:
            # Pass the enemy and spring groups to Sonic's find_homing_target method
            self.sonic.find_homing_target(self.enemies, self.springs)