# levels.py - Level class that inherits from a more general Level base class
import pygame, os, random, math, pytmx, json
from characters import Sonic, Tails
from objects import *
from constants import *
from utils import Camera, Mask

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
        # Load and scale background
        self.background_img = pygame.image.load(os.path.join("assets", "backgrounds", "windmillisle.png")).convert()
        self.background = pygame.transform.scale(self.background_img, (SCREEN_WIDTH, SCREEN_HEIGHT))
        
        # Load music for the level
        pygame.mixer_music.load(os.path.join("assets", "music", "windmillisle.mp3"))
        
        # Instantiate the character based on name
        if character == "Sonic":
            self.character = Sonic(100, 100)
        elif character == "Tails":
            self.character = Tails(100, 100)
            
        self.rings = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.monkey_bars = pygame.sprite.Group()   # Group for monkey bars/triggers
        self.springs = pygame.sprite.Group()
        self.load_enemies()
        self.ring_counter = 0
        self.show_target = False
        
        self.collidable_tiles = []
        self.load_tiles()

        # Determine level size based on Tiled map dimensions
        level_width = Windmill_Isle_TMX.width * 96  # For instance: tile width * tile size
        level_height = Windmill_Isle_TMX.height * 96
        self.camera = Camera(level_width, level_height)

    def load_tiles(self):
        """
        Load tiles directly from all layers, identifying 'Masks F' and 'Surface F' layers.
        Tiles from 'Masks F' are processed for collision and made renderable,
        while tiles from 'Surface F' are prepared for visual rendering.
        """
        # Debug: Print all layer names
        print("Available layers:", [layer.name for layer in Windmill_Isle_TMX.layers])
        
        # Find Masks F and Surface F layers by name
        masks_layer = next(
            (layer for layer in Windmill_Isle_TMX.layers 
            if isinstance(layer, pytmx.TiledTileLayer) and layer.name == "Masks F"), 
            None
        )
        
        surface_layer = next(
            (layer for layer in Windmill_Isle_TMX.layers 
            if isinstance(layer, pytmx.TiledTileLayer) and layer.name == "Surface F"), 
            None
        )
        
        if not masks_layer or not surface_layer:
            print("Error: Masks F or Surface F layer not found!")
            # Print out all layer names and types for debugging
            for layer in Windmill_Isle_TMX.layers:
                print(f"Layer Name: {layer.name}, Type: {type(layer)}")
            return
        
                # Process Masks F layer
        for x, y, tile_gid in masks_layer.tiles():
            if not tile_gid:  # Skip empty or invalid tiles
                continue
            
            tile_x = x * 64
            tile_y = y * 64
            
            # If tile_gid is already the image, use it directly
            if isinstance(tile_gid, pygame.Surface):
                mask_tile_image = tile_gid
            else:
                # Retrieve the tile image by GID if it's not already a surface
                mask_tile_image = Windmill_Isle_TMX.get_tile_image_by_gid(tile_gid)
            
            if mask_tile_image:
                # Scale the tile image
                scaled_mask_image = pygame.transform.scale(mask_tile_image, (64, 64))
                tile_rect = pygame.Rect(tile_x, tile_y, 64, 64)
                
                # Create a mask for collision detection
                mask_sensor = Mask.surface_to_mask(scaled_mask_image, tile_rect)
                
                # Create a renderable mask tile
                mask_tile = Tile(
                    scaled_mask_image, 
                    (tile_x, tile_y), 
                    collideable=True
                )
                
                # Add mask tile and sensor to collidable tiles
                self.collidable_tiles.append({
                    'tile': mask_tile,
                    'mask': mask_sensor
                })
                
                # Add to tile group to enable rendering if needed
                self.tile_group.add(mask_tile)
        
        # Process Surface F layer
        for x, y, tile_gid in surface_layer.tiles():
            if tile_gid == 0:  # Skip empty tiles
                continue
            
            tile_x = x * 64
            tile_y = y * 64
            
            # Get surface tile image
            surface_tile_image = Windmill_Isle_TMX.get_tile_image_by_gid(tile_gid)
            
            if surface_tile_image:
                # Scale surface tile image
                scaled_surface_image = pygame.transform.scale(surface_tile_image, (64, 64))
                tile_rect = pygame.Rect(tile_x, tile_y, 64, 64)
                
                # Create surface tile (non-collideable visual tile)
                surface_tile = Tile(
                    scaled_surface_image, 
                    (tile_x, tile_y), 
                    collideable=False  # Visual tiles do not collide
                )
                
                # Add to tile group for rendering
                self.tile_group.add(surface_tile)
        
    def handle_tile_collision(self):
        """Stable ground detection with smooth correction for Y-axis only"""
        # Store previous grounded state
        was_grounded = self.character.grounded
        
        # Reset collision states
        self.character.grounded = False
        
        # Correction settings - configurable based on game feel
        ground_correction_factor = 0.3  # Lower value = smoother but less responsive
        max_ground_correction = 5.0     # Maximum pixels to move in a single frame
        
        # Track ground contact info
        ground_corrections = []
        ground_angles = []
        
        # Detect ground collisions - Y axis only
        for tile_data in self.collidable_tiles:
            tile = tile_data['tile']
            tile_mask = tile_data['mask']
            
            # Only check tiles that are near the character (optimization)
            if abs(tile.rect.x - self.character.rect.x) < 300 and abs(tile.rect.y - self.character.rect.y) < 300:
                # Check both sensors for ground contact
                for sensor in [self.character.left_sensor, self.character.right_sensor]:
                    # First check if sensor is in contact with tile at all
                    if Mask.collide(sensor, tile_mask):
                        # Then get the precise overlap amount
                        y_correction = Mask.collide_inside_y_minus(sensor, tile_mask)
                        
                        # If there's vertical overlap, record ground contact
                        if y_correction < 0:
                            ground_corrections.append(-y_correction)  # Convert to positive (amount to move up)
                            
                            # Store angle data for slopes
                            if hasattr(tile, 'angle'):
                                ground_angles.append(tile.angle)
        
        # Apply ground positioning with smoothing
        if ground_corrections:
            # Set grounded state
            self.character.grounded = True
            
            # Calculate average ground level from all contacts
            avg_correction = sum(ground_corrections) / len(ground_corrections)
            
            # Apply smoothed correction - prevents jitter
            smooth_correction = min(avg_correction * ground_correction_factor, max_ground_correction)
            
            # Apply correction as floating-point movement - Y AXIS ONLY
            self.character.y -= smooth_correction
            # Only update rect after the correction
            self.character.rect.y = int(self.character.y)
            
            # Only zero Y velocity when first landing
            if not was_grounded:
                self.character.Yvel = 0
            
            # Update slope angle with smooth interpolation
            if ground_angles:
                target_angle = sum(ground_angles) / len(ground_angles)
                angle_factor = 0.2  # Lower = smoother angle transition
                self.character.angle += (target_angle - self.character.angle) * angle_factor
        else:
            # When not on ground, gradually return to 0 angle
            self.character.angle += (0 - self.character.angle) * 0.1
        
        # Update rect position from floating point after all corrections
        # Note: Only updating Y because we're not doing X-axis corrections
        self.character.rect.y = int(self.character.y)
        
        # Update hitbox position
        self.character.hitbox.x = ((self.character.rect.x//2) + 100)
        self.character.hitbox.y = (self.character.rect.y + 50)
        self.character.hitbox.center = self.character.rect.center
        self.character.hitbox.bottom = self.character.rect.bottom
        
        # Update sensors after all position corrections
        self.character.update_sensors()
        
        # Check if character just landed
        if not was_grounded and self.character.grounded:
            # Reset jumping state when landing
            self.character.jumped = False
        
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

    def visualize_debug_info(self, screen, camera, character):
        """
        Visualizes the character's sensors, chunk hitboxes, and tile hitboxes on the screen.

        Parameters:
            screen: The Pygame surface to draw on (e.g., the game screen).
            camera: An instance of the Camera class to handle offset adjustments.
            character: The character entity whose sensors are being drawn.
            chunks: A dictionary representing the chunks (e.g., CHUNKSLIST).
            tile_size: Size of each tile (e.g., 64x64).
        """
        debug_sensor_color = (255, 255, 255)  # Red for sensors
        debug_chunk_color = (0, 255, 0)  # Green for chunk hitboxes
        debug_tile_color = (0, 0, 255)  # Blue for individual tile hitboxes

        # --- Draw Character Sensors ---
        sensors = [character.left_sensor, character.right_sensor]
        for sensor in sensors:
            # The second element in the sensor list is the shifted rectangle.
            sensor_rect = sensor[1]

            # Apply camera offset
            adjusted_sensor_rect = camera.apply_rect(sensor_rect)

            # Draw the sensor rectangle on the screen
            pygame.draw.rect(screen, debug_sensor_color, adjusted_sensor_rect, 2)  # Width of 2 for debugging

    def draw(self, screen):
        screen.blit(self.background, (0, 0))

        # Draw tiles using camera offsets
        for tile_data in self.collidable_tiles:
            # Access the tile object from the dictionary
            tile = tile_data['tile']

            # Check if the tile exists (some entries may not include visual tiles)
            if tile:
                # Apply the camera offset to the tile's rect and render it
                screen.blit(tile.image, self.camera.apply(tile.rect))

        for spring in self.springs:
            screen.blit(spring.image, self.camera.apply(spring))

        # Draw Sonic
        screen.blit(self.character.image, self.camera.apply(self.character))
        
        # Draw hitboxes for debugging
        offset_hitbox = self.camera.apply_rect(self.character.hitbox)
        offset_rect = self.camera.apply_rect(self.character.rect)

        # Draw Sonic's bounding box (green)
        pygame.draw.rect(screen, (0, 255, 0), offset_rect, 1)

        # Draw Sonic's hitbox (red)
        pygame.draw.rect(screen, (255, 0, 0), offset_hitbox, 1)

        # Visualize debug information
        self.visualize_debug_info(screen, self.camera, self.character)
        
        # Draw rings
        for ring in self.rings:
            screen.blit(ring.image, self.camera.apply(ring))

        # Draw enemies
        for enemy in self.enemies:
            screen.blit(enemy.image, self.camera.apply(enemy))

        # Display ring counter
        ring_counter_display = RingFont.render("RINGS: " + str(self.ring_counter), True, (255, 255, 255))
        screen.blit(ring_counter_display, (0, 0))

        # Draw homing target indicator
        if self.character.homing_target and not self.character.homing_attack_active:
            target_rect = self.character.homing_target.rect
            homing_scaled = pygame.transform.smoothscale(homing_image, (target_rect.width, target_rect.height))
            homing_x = target_rect.centerx - self.camera.viewport.x - (homing_scaled.get_width() // 2)
            homing_y = target_rect.centery - self.camera.viewport.y - (homing_scaled.get_height() // 2)
            screen.blit(homing_scaled, (homing_x, homing_y))

    def load_enemies(self):
        pass

    def update(self):
        """Master update method with improved gravity control"""
        # Calculate velocity but don't apply position changes yet
        self.character.update()
        
        # CRITICAL FIX: Completely prevent gravity application when grounded
        # This check happens BEFORE applying position changes
        if self.character.grounded:
            # Force vertical velocity to zero while on ground
            self.character.Yvel = 0
        
        # Apply velocity to position
        self.character.x += self.character.Xvel
        self.character.rect.x = self.character.x
        self.character.y += self.character.Yvel
        self.character.rect.y = self.character.y
        
        # Update hitbox and sensors
        self.character.hitbox.x = ((self.character.rect.x//2) + 100)
        self.character.hitbox.y = (self.character.rect.y + 50)
        self.character.hitbox.center = self.character.rect.center
        self.character.hitbox.bottom = self.character.rect.bottom
        
        # Handle tile collisions
        self.handle_tile_collision()
        
        # Update camera
        self.camera.update(self.character)
        
        # Update other game elements
        for ring in self.rings:
            ring.update()
        
        visible_enemies = [enemy for enemy in self.enemies if 
                        pygame.Rect(self.camera.viewport.x, self.camera.viewport.y, 
                                    SCREEN_WIDTH, SCREEN_HEIGHT).colliderect(enemy.rect)]
        for enemy in visible_enemies:
            enemy.update(self.character.rect)
        
        # Check for ring collisions
        self.check_ring_collisions()
        
        # Check for homing target when jumping
        if self.character.jumped and not self.character.homing_attack_active and not self.character.homing_target:
            self.character.find_homing_target(self.enemies, self.springs)