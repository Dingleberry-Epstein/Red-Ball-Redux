import pygame, pygame_gui, os, random, objects, threading, time
from constants import *
from levels import SpaceLevel, CaveLevel, PymunkLevel, levels, spawn_points, BossArena
from utils import PhysicsManager, SceneManager, MapSystem, GameSave

class Game:
    """Main game using impulse-based ball movement with improved pygame-gui UI"""
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        pygame.mixer_music.load(os.path.join("assets", "music", "theme.mp3"))
        global CURRENT_TRACK
        CURRENT_TRACK = 'menu'
        pygame.mixer_music.set_volume(0.75)  # Set volume to 75%

        self._screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self._clock = pygame.time.Clock()
        self._running = True
        self._state = "intro"  # Start with intro state
        self._credits = None
        
        self._game_save = GameSave()  # Initialize game save system

        self._setup_autosave_warning()

        self._player_has_map = False
        self._setup_loading_tips()

        # Set up physics and level
        self._physics = None
        self._level = None
        self._current_level_index = 0  # To track the current level

        # Load theme file for pygame_gui
        self._theme_path = os.path.join("assets", "theme.json")

        # Set up pygame_gui with theme
        self._ui_manager = pygame_gui.UIManager(
            (SCREEN_WIDTH, SCREEN_HEIGHT),
            self._theme_path
        )
        
        # Add secret code variables
        self._secret_code = "KFC"
        self._current_input = ""
        self._boss_level_unlocked = False

        # Storage for menu UI elements
        self._main_menu_buttons = []
        self._level_buttons = []

        # Load menu background
        self._setup_reactive_background()

        # Add transition variables
        self._setup_transition_variables()
        
        # Variables for level complete handling
        self._show_level_complete = False
        self._level_complete_timer = 0
        self._level_complete_delay = 1.0  # 1 second delay to show completion message
        
        # Level select variables
        self._level_select_open = False

        # Try to load the Daydream font
        self._setup_fonts()

        self._fade_duration = 1.0  # 1 second for fades

        # Load logo
        self._logo_image = pygame.image.load(os.path.join("assets", "Migglesoft.png")).convert_alpha()

        # Load title once to reuse
        self._title_text = pygame.image.load(os.path.join("assets", "title.png")).convert_alpha()

        pygame.display.set_caption("Red Ball: REDUX!")
        pygame.display.set_icon(pygame.image.load(os.path.join("assets", "sprites", "Red Ball portrait.png")).convert_alpha())

        # Add variables for flashing text
        self._flash_timer = 0
        self._flash_rate = 0.5  # Flash every 0.5 seconds
        self._show_flash_text = True
        
        # Initialize map system
        self._map_system = MapSystem(self)
        self._map_key_pressed = False  # Track M key state to avoid repeat toggling

        self._level_images = {}  # Dictionary to store level images
        self._scroll_offset = 0
        self._target_scroll = 0
        self._selected_level = 0
        self._level_positions = []
        self._level_rects = []
        self._mouse_dragging = False
        self._drag_start_pos = None
        self._drag_start_scroll = 0
        self._drag_velocity = 0
        self._last_mouse_pos = None
        self._drag_history = []  # Store recent drag positions for velocity calculation
        self._momentum_decay = 0.95  # How quickly momentum fades
        self._min_drag_distance = 5  # Minimum distance to start dragging
        
        # Configuration for level images (add this to your game initialization)
        self._level_image_paths = {
            0: os.path.join("assets", "sprites", "level thumbnails", "level 1.png"),  # Configure these paths as needed
            1: os.path.join("assets", "sprites", "level thumbnails", "level 2.png"),
            2: os.path.join("assets", "sprites", "level thumbnails", "level 3.png"),
            3: os.path.join("assets", "sprites", "level thumbnails", "level 4.png"),
            4: os.path.join("assets", "sprites", "level thumbnails", "level 5.png"),
            5: os.path.join("assets", "sprites", "level thumbnails", "level 6.png")
        }

        # Setup loading screen
        self._setup_loading_screen()

    def _setup_loading_tips(self):
        """Setup loading tips system"""
        self._loading_tips = [
            "Tip: Holding the jump button makes you feel like you're jumping higher. It doesn't, but it feels like it.",
            "Tip: Red balls are red. This is important. Probably.",
            "Tip: Pressing random keys rapidly may not help, but it sure is exciting!",
            "Tip: Always look both ways before crossing... in a 2D platformer.",
            "Tip: The loading screen always finishes eventually. Hang in there.",
            "Tip: If you're seeing this, you're not in the game.",
            "Tip: You can't win if you don't play. You also can't lose.",
            "Tip: Secrets are hidden where you least expect... or sometimes right in front of you. Who knows?",
            "Tip: Sound effects are 87% more satisfying when wearing headphones. This statistic is made up.",
            "Tip: The pause button should pause the game. Too bad the game doesn't have one.",
            "Tip: Reloading a game does not reload your ammo.",
            "Tip: The cake is... not relevant to this game, but we thought we'd say it anyway.",
            "Tip: Press 'M' to open the map... if you've found one.",
            "Tip: Can't complete a level? Sometimes, speed is key. - JackSepticEye.",
            "Tip: You can respawn with 'R' - useful if you're stuck.",
            "Tip: Some objects can be interacted with by pressing 'E'. Don't worry, it's obvious which ones.",
            "Tip: You can toggle music and audio in the settings screen, once I've added it.",
            "Tip: Don't forget: maps only unlock when collected in-game.",
            "Tip: Pressing 'ESC' does not bring up the main menu — it's how you rage quit in style.",
            "Tip: Game dev is hard. I made this in two weeks.",
            "Tip: If you find a bug, please report it. Not that I can fix it, but still."
        ]
        
        # Pick initial random tip
        self._current_tip = random.choice(self._loading_tips)
        self._tip_change_timer = 0
        self._tip_change_interval = 2.0  # Change tip every 2 seconds
        self._tip_fade_alpha = 255  # Start fully visible
        self._tip_fade_duration = 0.3  # Fade duration for tip transitions
        self._tip_fading = False
        self._tip_fade_timer = 0

    def _setup_loading_screen(self):
        """Setup loading screen animation with 4 frame loading icon"""
        self._loading_frames = []
        self._loading_frame_index = 0
        self._loading_animation_timer = 0
        self._loading_animation_speed = 0.1  # Change frame every 0.1 seconds
        self._show_loading = False
        
        # Try to load the 4 loading frames
        for i in range(1, 5):  # Assuming files are named loading1.png, loading2.png, etc.
            try:
                frame_path = os.path.join("assets", "sprites", "loading screen", f"{i}.png")
                frame = pygame.image.load(frame_path).convert_alpha()
                self._loading_frames.append(frame)
                print(f"Loaded loading frame: {frame_path}")
            except pygame.error as e:
                print(f"Could not load loading frame {frame_path}: {e}")
                # Create a simple fallback loading frame
                fallback_frame = pygame.Surface((32, 32), pygame.SRCALPHA)
                # Create a simple rotating square pattern for each frame
                color_intensity = 64 + (i * 48)  # Different intensity for each frame
                pygame.draw.rect(fallback_frame, (color_intensity, color_intensity, color_intensity), 
                               (8 + i*2, 8 + i*2, 16 - i*2, 16 - i*2))
                self._loading_frames.append(fallback_frame)
        
        # If no frames were loaded, create simple fallback animation
        if not self._loading_frames:
            for i in range(4):
                fallback_frame = pygame.Surface((32, 32), pygame.SRCALPHA)
                color_intensity = 64 + (i * 48)
                pygame.draw.circle(fallback_frame, (color_intensity, color_intensity, color_intensity), 
                                 (16, 16), 12 - i*2)
                self._loading_frames.append(fallback_frame)

    def _update_loading_animation(self, dt):
        """Update the loading animation frame and tips"""
        if not self._show_loading or not self._loading_frames:
            return
            
        # Update loading icon animation
        self._loading_animation_timer += dt
        if self._loading_animation_timer >= self._loading_animation_speed:
            self._loading_animation_timer = 0
            self._loading_frame_index = (self._loading_frame_index + 1) % len(self._loading_frames)
        
        # Update tip cycling
        if hasattr(self, '_loading_tips') and self._loading_tips:
            self._tip_change_timer += dt
            
            # Handle fade transitions
            if self._tip_fading:
                self._tip_fade_timer += dt
                fade_progress = self._tip_fade_timer / self._tip_fade_duration
                
                if fade_progress < 0.5:
                    # Fade out current tip
                    self._tip_fade_alpha = int(255 * (1 - fade_progress * 2))
                else:
                    # Change tip at halfway point and fade in
                    if fade_progress == 0.5 or (fade_progress > 0.5 and self._tip_fade_alpha < 128):
                        # Pick a new random tip (avoid repeating the same tip)
                        new_tip = random.choice(self._loading_tips)
                        while new_tip == self._current_tip and len(self._loading_tips) > 1:
                            new_tip = random.choice(self._loading_tips)
                        self._current_tip = new_tip
                    
                    # Fade in new tip
                    self._tip_fade_alpha = int(255 * ((fade_progress - 0.5) * 2))
                
                # End fade transition
                if fade_progress >= 1.0:
                    self._tip_fading = False
                    self._tip_fade_alpha = 255
                    self._tip_fade_timer = 0
                    self._tip_change_timer = 0
            
            # Start new fade transition when timer expires
            elif self._tip_change_timer >= self._tip_change_interval:
                self._tip_fading = True
                self._tip_fade_timer = 0

    def _draw_loading_tip(self):
        """Draw the current loading tip with fade effects"""
        if not hasattr(self, '_loading_tips') or not self._loading_tips:
            return
        
        # Get current tip
        current_tip = self._current_tip
        
        # Word wrap the tip text for better display
        words = current_tip.split(' ')
        lines = []
        current_line = []
        max_width = SCREEN_WIDTH - 100  # Leave padding on sides
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            text_width = self._small_font.size(test_line)[0]
            
            if text_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # Single word is too long, just add it
                    lines.append(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Calculate total height and starting position
        line_height = self._small_font.get_height() + 5
        total_height = len(lines) * line_height
        start_y = SCREEN_HEIGHT // 2 - total_height // 2
        
        # Draw each line with fade effect
        for i, line in enumerate(lines):
            # Create text surface
            text_surface = self._small_font.render(line, True, (255, 255, 255))
            
            # Apply alpha if fading
            if self._tip_fade_alpha < 255:
                # Create a surface with per-pixel alpha
                faded_surface = pygame.Surface(text_surface.get_size(), pygame.SRCALPHA)
                faded_surface.fill((255, 255, 255, self._tip_fade_alpha))
                faded_surface.blit(text_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                text_surface = faded_surface
            
            # Center the line horizontally
            text_rect = text_surface.get_rect()
            text_rect.centerx = SCREEN_WIDTH // 2
            text_rect.y = start_y + (i * line_height)
            
            # Add subtle glow effect for better visibility
            for offset in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
                glow_surface = self._small_font.render(line, True, (50, 50, 50))
                if self._tip_fade_alpha < 255:
                    glow_faded = pygame.Surface(glow_surface.get_size(), pygame.SRCALPHA)
                    glow_faded.fill((50, 50, 50, self._tip_fade_alpha // 3))
                    glow_faded.blit(glow_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                    glow_surface = glow_faded
                
                glow_rect = text_rect.copy()
                glow_rect.x += offset[0]
                glow_rect.y += offset[1]
                self._screen.blit(glow_surface, glow_rect)
            
            # Draw the main text
            self._screen.blit(text_surface, text_rect)

    def _draw_loading_icon(self):
        """Draw the loading icon and tips prominently on black screen"""
        if not self._show_loading or not self._loading_frames:
            return
            
        # Position in bottom right corner with padding
        padding = 30
        frame = self._loading_frames[self._loading_frame_index]
        
        # Scale the loading icon to be more visible
        scaled_size = (64, 48)  # Even larger for black screen visibility
        scaled_frame = pygame.transform.scale(frame, scaled_size)
        
        x = SCREEN_WIDTH - scaled_frame.get_width() - padding
        y = SCREEN_HEIGHT - scaled_frame.get_height() - padding
        
        # Add a glowing effect for better visibility on black background
        glow_surface = pygame.Surface((scaled_size[0] + 20, scaled_size[1] + 20), pygame.SRCALPHA)
        
        # Create multiple circles for glow effect
        glow_center = (glow_surface.get_width() // 2, glow_surface.get_height() // 2)
        for i in range(5):
            alpha = 30 - (i * 5)  # Decreasing alpha for glow layers  
            radius = (max(scaled_size) // 2) + (i * 3)
            glow_color = (255, 255, 255, alpha)
            pygame.draw.circle(glow_surface, glow_color, glow_center, radius)
        
        # Position glow
        glow_x = x - 10
        glow_y = y - 10
        self._screen.blit(glow_surface, (glow_x, glow_y))
        
        # Draw the actual loading icon
        self._screen.blit(scaled_frame, (x, y))
        
        # Add "Loading..." text with glow effect
        loading_text = self._menu_font.render("Loading...", True, (255, 255, 255))
        text_x = x - loading_text.get_width() - 20
        text_y = y + (scaled_frame.get_height() // 2) - (loading_text.get_height() // 2)
        
        # Text glow effect
        for offset in [(-2, -2), (-2, 0), (-2, 2), (0, -2), (0, 2), (2, -2), (2, 0), (2, 2)]:
            glow_text = self._menu_font.render("Loading...", True, (100, 100, 100))
            self._screen.blit(glow_text, (text_x + offset[0], text_y + offset[1]))
        
        # Main text
        self._screen.blit(loading_text, (text_x, text_y))
        
        # Draw loading tips if available
        self._draw_loading_tip()

    def _setup_reactive_background(self):
        """Load three background layers for a parallax effect based on mouse movement"""
        # Define paths for the three background layers
        bg_paths = [
            os.path.join("assets", "backgrounds", "cloud", "1.png"),  # Far background
            os.path.join("assets", "backgrounds", "cloud", "3.png"),  # Middle ground
            os.path.join("assets", "backgrounds", "cloud", "2.png"),  # Foreground
        ]

        # Define speed factors for each layer (higher value = more movement)
        speed_factors = [0.9, 1.5, 2]  # Background moves slower, foreground faster

        # Initialize list to store layer information
        self._bg_layers = []

        # Try to load each layer
        for i, path in enumerate(bg_paths):
            try:
                # Load the image
                print(f"Loading background layer: {path}")
                image = pygame.image.load(path).convert_alpha()

                # Scale slightly larger to allow movement without showing edges
                scaled_width = int(SCREEN_WIDTH * 1.1)
                scaled_height = int(SCREEN_HEIGHT * 1.1)
                scaled_image = pygame.transform.scale(image, (scaled_width, scaled_height))

                # Store layer information: image, center position, and speed factor
                center_x = (scaled_width - SCREEN_WIDTH) / 2
                center_y = (scaled_height - SCREEN_HEIGHT) / 2

                self._bg_layers.append({
                    'image': scaled_image,
                    'center_x': center_x,
                    'center_y': center_y,
                    'pos_x': 0,
                    'pos_y': 0,
                    'factor': speed_factors[i]
                })

            except Exception as e:
                print(f"Error loading background layer {path}: {e}")
                # Create a simple colored background as fallback
                color = (20, 30, 50)  # Dark blue
                if i == 1:
                    color = (30, 40, 60)  # Slightly lighter blue for middle
                elif i == 2:
                    color = (40, 50, 70)  # Even lighter for foreground

                surface = pygame.Surface((int(SCREEN_WIDTH * 1.1), int(SCREEN_HEIGHT * 1.1)))
                surface.fill(color)

                # Add some simple stars for the farthest background
                if i == 0:
                    for _ in range(200):
                        x = random.randint(0, surface.get_width() - 1)
                        y = random.randint(0, surface.get_height() - 1)
                        size = random.randint(1, 3)
                        pygame.draw.circle(surface, (255, 255, 255), (x, y), size)

                center_x = (surface.get_width() - SCREEN_WIDTH) / 2
                center_y = (surface.get_height() - SCREEN_HEIGHT) / 2

                self._bg_layers.append({
                    'image': surface,
                    'center_x': center_x,
                    'center_y': center_y,
                    'pos_x': 0,
                    'pos_y': 0,
                    'factor': speed_factors[i]
                })

        # Maximum amount the backgrounds can move in each direction
        self._bg_move_amount = 20

    def _setup_transition_variables(self):
        """Set up transition variables for animations between screens"""
        self._is_transitioning = False
        self._transition_phase = 0  # 0=not transitioning, 1=flashing, 2=moving
        self._transition_timer = 0
        self._flash_duration = 1.5  # 1.5 seconds for rapid flashing
        self._move_duration = 0.3  # 0.3 seconds for quick movement
        self._title_y_pos = 0
        self._title_target_y = 0
        self._button_alpha = 0

    def _setup_fonts(self):
        """Load game fonts with fallback to system fonts if needed"""
        try:
            self._pixel_font = pygame.font.Font(os.path.join("assets", "Daydream.ttf"), 32)
            self._small_font = pygame.font.Font(os.path.join("assets", "Daydream.ttf"), 15)
            self._menu_font = pygame.font.Font(os.path.join("assets", "Daydream.ttf"), 24)
        except pygame.error as e:
            print(f"Error loading font: {e}")
            # Fallback to default font
            self._pixel_font = pygame.font.SysFont(None, 36)
            self._small_font = pygame.font.SysFont(None, 18)
            self._menu_font = pygame.font.SysFont(None, 24)

    @property
    def screen(self):
        """Get the game screen surface"""
        return self._screen
    
    @property
    def clock(self):
        """Get the game clock"""
        return self._clock
    
    @property
    def running(self):
        """Check if the game is running"""
        return self._running
    
    @running.setter
    def running(self, value):
        """Set if the game is running"""
        self._running = value
    
    @property
    def state(self):
        """Get the current game state"""
        return self._state
    
    @state.setter
    def state(self, value):
        """Set the current game state"""
        self._state = value
    
    @property
    def player_has_map(self):
        """Check if player has acquired the map"""
        return self._player_has_map
    
    @player_has_map.setter
    def player_has_map(self, value):
        """Set whether player has acquired the map"""
        self._player_has_map = value
    
    @property
    def level(self):
        """Get the current level"""
        return self._level
    
    @property
    def ui_manager(self):
        """Get the UI manager"""
        return self._ui_manager
    
    @property
    def current_level_index(self):
        """Get the current level index"""
        return self._current_level_index
    
    @property
    def boss_level_unlocked(self):
        """Check if the boss level is unlocked"""
        return self._boss_level_unlocked
    
    @boss_level_unlocked.setter
    def boss_level_unlocked(self, value):
        """Set if the boss level is unlocked"""
        self._boss_level_unlocked = value
    
    @property
    def map_system(self):
        """Get the map system"""
        return self._map_system
    
    def _setup_autosave_warning(self):
        """Setup autosave warning splash screen with custom loading animation"""
        # Timer and duration
        self._autosave_timer = 0
        self._autosave_duration = 7.0  # 7 seconds
        
        # Warning text
        self._autosave_warning_text = [
            "This game has an autosave feature",
            "Please do not power off the system or close the game",
            "while this icon is visible"
        ]
        
        # Loading animation setup
        self._autosave_loading_frames = []
        self._autosave_frame_index = 0
        self._autosave_animation_timer = 0
        self._autosave_animation_speed = 0.15  # Change frame every 0.15 seconds
        
        # Load loading animation sprites
        for i in range(1, 5):  # Assuming files are named 1.png, 2.png, 3.png, 4.png
            try:
                frame_path = os.path.join("assets", "sprites", "loading screen", f"{i}.png")
                frame = pygame.image.load(frame_path).convert_alpha()
                self._autosave_loading_frames.append(frame)
                print(f"Loaded autosave loading frame: {frame_path}")
            except pygame.error as e:
                print(f"Could not load autosave loading frame {frame_path}: {e}")
        
        # Create fallback frames if loading failed
        if not self._autosave_loading_frames:
            print("Creating fallback autosave loading animation")
            for i in range(4):
                # Create simple animated circles as fallback
                fallback_frame = pygame.Surface((32, 32), pygame.SRCALPHA)
                color_intensity = 100 + (i * 40)  # Varying brightness
                radius = 12 - (i * 2)  # Varying size
                pygame.draw.circle(fallback_frame, (color_intensity, color_intensity, color_intensity), 
                                (16, 16), max(radius, 4))
                self._autosave_loading_frames.append(fallback_frame)

    def _update_autosave_warning(self, dt):
        """Update autosave warning screen timer and animation"""
        if self._state != 'autosave_warning':
            return
        
        # Update timer
        self._autosave_timer += dt
        
        # Update loading animation
        self._autosave_animation_timer += dt
        if self._autosave_animation_timer >= self._autosave_animation_speed:
            self._autosave_animation_timer = 0
            self._autosave_frame_index = (self._autosave_frame_index + 1) % len(self._autosave_loading_frames)
        
        # Auto-advance after 7 seconds
        if self._autosave_timer >= self._autosave_duration:
            self._finish_autosave_warning()

    def _draw_autosave_warning(self):
        """Draw the complete autosave warning splash screen"""
        # Fill screen with black background
        self._screen.fill((0, 0, 0))
        
        # Prepare text surfaces
        text_surfaces = []
        line_heights = []
        
        for i, line in enumerate(self._autosave_warning_text):
            if i == 0:  # First line - title
                font = self._menu_font if hasattr(self, '_menu_font') else pygame.font.Font(None, 48)
                color = (255, 255, 100)  # Yellow for emphasis
            else:  # Body text
                font = self._small_font if hasattr(self, '_small_font') else pygame.font.Font(None, 32)
                color = (255, 255, 255)  # White
            
            text_surface = font.render(line, True, color)
            text_surfaces.append(text_surface)
            line_heights.append(text_surface.get_height())
        
        # Calculate total text height and starting position
        total_text_height = sum(line_heights) + (len(line_heights) - 1) * 15  # 15px spacing
        text_start_y = (SCREEN_HEIGHT // 2) - (total_text_height // 2) - 60  # Offset for loading icon
        
        # Draw text with glow effects
        current_y = text_start_y
        for i, (text_surface, line_height) in enumerate(zip(text_surfaces, line_heights)):
            # Center text horizontally
            text_x = SCREEN_WIDTH // 2 - text_surface.get_width() // 2
            
            # Draw glow effect
            glow_color = (80, 80, 40) if i == 0 else (60, 60, 60)  # Different glow for title
            font = self._menu_font if (i == 0 and hasattr(self, '_menu_font')) else (self._small_font if hasattr(self, '_small_font') else pygame.font.Font(None, 32))
            
            for offset_x in [-2, -1, 0, 1, 2]:
                for offset_y in [-2, -1, 0, 1, 2]:
                    if offset_x == 0 and offset_y == 0:
                        continue  # Skip center position
                    glow_surface = font.render(self._autosave_warning_text[i], True, glow_color)
                    self._screen.blit(glow_surface, (text_x + offset_x, current_y + offset_y))
            
            # Draw main text
            self._screen.blit(text_surface, (text_x, current_y))
            current_y += line_height + 15
        
        # Draw loading icon
        if self._autosave_loading_frames:
            # Get current frame
            current_frame = self._autosave_loading_frames[self._autosave_frame_index]
            
            # Scale the frame for better visibility
            scaled_size = (96, 72)
            scaled_frame = pygame.transform.scale(current_frame, scaled_size)
            
            # Position below text
            icon_x = SCREEN_WIDTH // 2 - scaled_frame.get_width() // 2
            icon_y = current_y + 30  # 30px below text
            
            # Create glow effect for loading icon
            glow_surface = pygame.Surface((scaled_size[0] + 30, scaled_size[1] + 30), pygame.SRCALPHA)
            glow_center = (glow_surface.get_width() // 2, glow_surface.get_height() // 2)
            
            # Multiple glow layers for smooth effect
            for layer in range(6):
                alpha = max(0, 40 - (layer * 6))  # Decreasing alpha
                radius = (scaled_size[0] // 2) + (layer * 4)  # Increasing radius
                glow_color = (255, 255, 255, alpha)
                # Draw glow circle
                glow_temp = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow_temp, glow_color, (radius, radius), radius)
                glow_rect = glow_temp.get_rect(center=glow_center)
                glow_surface.blit(glow_temp, glow_rect)
            
            # Draw glow
            glow_x = icon_x - 15
            glow_y = icon_y - 15
            self._screen.blit(glow_surface, (glow_x, glow_y))
            
            # Draw the actual loading icon
            self._screen.blit(scaled_frame, (icon_x, icon_y))
        
        # Draw "Press any key to continue" text at bottom
        continue_font = pygame.font.Font(None, 28)
        continue_text = ""
        continue_surface = continue_font.render(continue_text, True, (180, 180, 180))
        continue_x = SCREEN_WIDTH // 2 - continue_surface.get_width() // 2
        continue_y = SCREEN_HEIGHT - 60
        
        # Add subtle glow to continue text
        for offset in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
            glow_continue = continue_font.render(continue_text, True, (50, 50, 50))
            self._screen.blit(glow_continue, (continue_x + offset[0], continue_y + offset[1]))
        
        self._screen.blit(continue_surface, (continue_x, continue_y))

    def _finish_autosave_warning(self):
        """Finish autosave warning and transition to start screen"""
        self._state = 'start_screen'
        
        # Initialize title position for start screen (center)
        self._title_y_pos = SCREEN_HEIGHT // 2 - self._title_text.get_height() // 2
        # Set target position for when we transition (top quarter)  
        self._title_target_y = SCREEN_HEIGHT // 4 - self._title_text.get_height() // 2
        
        # Start playing the music in a loop
        pygame.mixer_music.play(-1)  # -1 means loop indefinitely
        
        def render_start_screen():
            self.update_background()
            self.render_start_screen()
        SceneManager.fade_from_black(self._screen, render_start_screen, self._fade_duration)

    def handle_intro_sequence(self, events):
        """Handle the complete intro sequence: logo -> autosave warning -> start screen"""
        if self._state == 'intro':
            def render_logo():
                self._screen.fill((0, 0, 0))  # Fill with black first

            if SceneManager.fade_in(self._screen, render_logo, self._logo_image, self._fade_duration, (0, 0, 0)):
                pygame.time.delay(1000)  # show the logo for one second
                if SceneManager.fade_out(self._screen, render_logo, self._logo_image, self._fade_duration, (0, 0, 0)):
                    # Transition to autosave warning
                    self._state = 'autosave_warning'
                    self._autosave_timer = 0
                    self._autosave_frame_index = 0
                    self._autosave_animation_timer = 0
                    
        elif self._state == 'autosave_warning':
            # Handle key presses to skip the warning
            for event in events:
                if event.type == pygame.KEYDOWN:
                    self._finish_autosave_warning()
                    return
            
            # Calculate delta time for updates
            current_time = pygame.time.get_ticks() / 1000.0
            if not hasattr(self, '_last_autosave_time'):
                self._last_autosave_time = current_time
            dt = current_time - self._last_autosave_time
            self._last_autosave_time = current_time
            
            # Update and draw the autosave warning
            self._update_autosave_warning(dt)
            self._draw_autosave_warning()

    def handle_start_screen(self, events, dt):
        """Handle the start screen with flashing text"""
        if not self._is_transitioning:
            # Normal flashing for "press anything to start"
            self._flash_timer += dt
            if self._flash_timer >= self._flash_rate:
                self._flash_timer = 0
                self._show_flash_text = not self._show_flash_text

            # Check for any input to start transition
            for event in events:
                if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    self._is_transitioning = True
                    self._transition_phase = 1  # Start with flashing phase
                    self._transition_timer = 0
                    self._flash_rate = 0.08  # Faster flashing during transition
                    self._button_alpha = 0
        else:
            # Transition handling
            self._transition_timer += dt

            # Flash text rapidly during transition phase 1
            self._flash_timer += dt
            if self._flash_timer >= self._flash_rate:
                self._flash_timer = 0
                self._show_flash_text = not self._show_flash_text

            # Phase 1: Just flash the text rapidly
            if self._transition_phase == 1:
                if self._transition_timer >= self._flash_duration:
                    # Move to phase 2 once flashing is complete
                    self._transition_phase = 2
                    self._transition_timer = 0
                    self._show_flash_text = False  # Hide the text during movement

            # Phase 2: Move the title up quickly
            elif self._transition_phase == 2:
                if self._transition_timer <= self._move_duration:
                    # Calculate progress (0 to 1)
                    progress = min(self._transition_timer / self._move_duration, 1.0)

                    # Move title up quickly
                    start_y = SCREEN_HEIGHT // 2 - self._title_text.get_height() // 2
                    end_y = SCREEN_HEIGHT // 4 - self._title_text.get_height() // 2
                    self._title_y_pos = start_y + (end_y - start_y) * progress

                    # Fade in menu buttons
                    self._button_alpha = int(progress * 255)  # 0 to 255
                else:
                    # Transition complete
                    self._is_transitioning = False
                    self._transition_phase = 0
                    self._state = "main_menu"
                    self._title_y_pos = SCREEN_HEIGHT // 4 - self._title_text.get_height() // 2
                    
                    # Setup the main menu
                    self.setup_main_menu()

    def render_outlined_text(self, text, color, outline_color, position):
        """Render text with an outline effect"""
        # Render the outline by drawing the text multiple times with offsets
        outline_offsets = [(-2, -2), (-2, 0), (-2, 2), (0, -2), (0, 2), (2, -2), (2, 0), (2, 2)]

        # First render outline
        for offset in outline_offsets:
            offset_position = (position[0] + offset[0], position[1] + offset[1])
            outline_surface = self._pixel_font.render(text, True, outline_color)
            self._screen.blit(outline_surface, offset_position)

        # Then render the text on top
        text_surface = self._pixel_font.render(text, True, color)
        self._screen.blit(text_surface, position)

        return text_surface.get_rect(topleft=position)

    def run(self):
        """Main game loop"""
        while self._running:
            # Calculate delta time for smooth physics
            global dt
            dt = self._clock.tick(60) / 1000.0  # Convert to seconds

            # Update loading animation
            self._update_loading_animation(dt)

            # Get events
            events = pygame.event.get()
            for event in events:
                # Handle quit
                if event.type == pygame.QUIT:
                    self._running = False

                # If in main menu or level select, handle UI events
                if self._state == "main_menu":
                    # Handle UI events
                    self._ui_manager.process_events(event)
                    self.handle_menu_events(event)

                # Handle keyboard input
                if event.type == pygame.KEYDOWN:
                    self._handle_keydown_events(event)
                elif event.type == pygame.KEYUP:
                    if event.key == pygame.K_m:
                        self._map_key_pressed = False

                # Pass events to map system
                if self._state == "game" and (self._map_system.is_open or self._map_system.fading_in or self._map_system.fading_out):
                    if self._map_system.handle_event(event):
                        continue  # Skip further event processing if map handled it

                # Pass events to level if in game state - just handle events, don't check for completion here
                if self._level and self._state == "game" and not self._show_level_complete and not self._map_system.is_open:
                    self._level.handle_events(event)

            # Update and render based on state
            self._update_game_state(events, dt)

            # Draw loading icon if it should be visible
            self._draw_loading_icon()

            pygame.display.flip()

    def _handle_keydown_events(self, event):
        """Handle keyboard down events"""
        if event.key == pygame.K_m:
            # Toggle map when M is pressed
            if not self._map_key_pressed and self._state == "game" and self._player_has_map:
                self._map_system.toggle()
                self._map_key_pressed = True
            elif not self._map_key_pressed and self._state == "game" and not self._player_has_map:
                self._map_system.show_message = True
        elif event.key == pygame.K_ESCAPE:
            self._handle_escape_key()
        elif event.key == pygame.K_r and self._state == "game" and not self._map_system.is_open:
            self._level.reset_ball()

    def _handle_escape_key(self):
        """Handle behavior when escape key is pressed with loading screen"""
        if self._map_system.is_open:
            self._map_system.toggle()
        elif self._state == "game":
            def render_game():
                self.update(dt)
                self.render()
            
            def render_main_menu():
                self.update_background() 
                self.render_main_menu()

            # 1. Fade to black
            pygame.mixer_music.fadeout(500)
            SceneManager.fade_to_black(self._screen, render_game, self._fade_duration)
            
            # 2. Show loading screen while transitioning
            self._show_loading = True
            
            def loading_task():
                self.handle_state_transition("main_menu")
            
            self._draw_loading_screen_between_transitions(loading_task)
            
            # 3. Fade from black to main menu
            self._show_loading = False
            SceneManager.fade_from_black(self._screen, render_main_menu, self._fade_duration)
            
        elif self._state == "credits":
            self.handle_state_transition("main_menu")
        else:
            def render_main_menu():
                self.update_background()
                self.render_main_menu()
            
            pygame.mixer_music.fadeout(900)
            SceneManager.fade_to_black(self._screen, render_main_menu, self._fade_duration)
            self._running = False

    def _update_game_state(self, events, dt):
        """Update and render based on the current game state"""
        if self._state == "autosave_warning":
            self._update_autosave_warning(dt)
            self._draw_autosave_warning()
            return
        elif self._state == "intro":
            self.handle_intro_sequence(events)
        elif self._state == "start_screen":
            self.update_background()  # Keep parallax working
            self.handle_start_screen(events, dt)
            self.render_start_screen()
        elif self._state == "main_menu":
            # Update UI manager
            self._ui_manager.update(dt)
            self.update_background()
            
            # Setup main menu buttons if not already set up
            if not hasattr(self, '_main_menu_buttons') or not self._main_menu_buttons:
                self.setup_main_menu()
            
            # Update level select if open
            if self._level_select_open:
                self.update_level_select(dt)
                
            self.render_main_menu()
        elif self._state == "credits":
            self._update_credits_state()
        elif self._state == "game":
            self.update(dt)
            self.render()

    def _update_credits_state(self):
        """Handle credits screen update and finishing"""
        self._credits.update()
        self._screen.fill((0, 0, 0))  # Clear the screen
        self._credits.draw()
        
        # Check if music has stopped playing and return to menu if it has
        if not pygame.mixer.music.get_busy():
            print("Credits music ended - returning to main menu")
            def render_main_menu():
                self.update_background()
                self.render_main_menu()
            SceneManager.fade_from_black(self._screen, render_main_menu, self._fade_duration)
            self.handle_state_transition("main_menu")

    def update_background(self):
        """Update background position of all layers based on mouse movement"""
        # Get mouse position
        mouse_x, mouse_y = pygame.mouse.get_pos()

        # Calculate relative position from -1 to 1
        # When mouse is in center, these values are 0
        # When mouse is at edge, these values approach -1 or 1
        relative_x = (mouse_x / SCREEN_WIDTH) * 2 - 1
        relative_y = (mouse_y / SCREEN_HEIGHT) * 2 - 1

        # Update each layer with its own movement speed
        for layer in self._bg_layers:
            # Calculate new background position
            # Move opposite to mouse position for parallax effect
            # Multiple by move amount and layer factor to control sensitivity
            layer['pos_x'] = layer['center_x'] - (relative_x * self._bg_move_amount * layer['factor'])
            layer['pos_y'] = layer['center_y'] - (relative_y * self._bg_move_amount * layer['factor'])

    def setup_game(self, level_index=0):
        """Set up physics and level with impulse-based ball"""
        # Create minimal physics manager
        self._physics = PhysicsManager()

        # Check if the level index is 3 or 4
        if level_index in [2, 3]:
            self._level = CaveLevel(tmx_map=levels[level_index], spawn=spawn_points[level_index], level_index = level_index, gamesave=self._game_save)
        elif level_index == 4:
            self._level = SpaceLevel(tmx_map=levels[level_index], spawn=spawn_points[level_index], level_index = level_index, gamesave=self._game_save)
        elif level_index == 5:
            self._level = BossArena(tmx_map=levels[level_index], spawn=spawn_points[level_index])
        else:
            self._level = PymunkLevel(tmx_map=levels[level_index], spawn=spawn_points[level_index], level_index = level_index, gamesave=self._game_save)

        self._current_level_index = level_index  # Store current index.

        # Reset level completion flags
        self._show_level_complete = False
        self._level_complete_timer = 0
        self._level.game_ref = self
        # Now load the map for this level
        self._map_system.load_map_for_level(level_index)

    def update(self, dt):
        """Update physics simulation and handle level completion"""
        if not self._level:
            return

        # If level is complete, handle the transition
        if self._show_level_complete:
            self._handle_level_complete(dt)
        else:
            # Update map system
            if self._map_system.is_open or self._map_system.fading_in or self._map_system.fading_out or self._map_system.show_message:
                self._map_system.update(dt)
                
                # Don't update level if map is open (pause gameplay)
                if not self._map_system.is_open and not self._map_system.fading_in:
                    self._level.update(dt)
            else:
                # Normal level update when map is not open
                self._level.update(dt)

            # Check for level completion after updating
            if self._level.level_complete:
                self._show_level_complete = True
                self._level_complete_timer = 0

    def _handle_level_complete(self, dt):
        """Handle the level complete transition with loading screen"""
        self._level_complete_timer += dt
        if self._level_complete_timer >= self._level_complete_delay:
            # Unlock boss level if completing level 5
            if self._current_level_index == 4:
                self._boss_level_unlocked = True
                print("BOSS LEVEL UNLOCKED by completing level 5!")
            
            def render_game():
                self.render()
            
            def render_main_menu():
                self.update_background()
                self.render_main_menu()

            # 1. Fade to black
            pygame.mixer_music.fadeout(500)
            SceneManager.fade_to_black(self._screen, render_game, self._fade_duration)
            
            # 2. Show loading screen
            self._show_loading = True
            
            def loading_task():
                self.handle_state_transition("main_menu")
            
            self._draw_loading_screen_between_transitions(loading_task)
            
            # 3. Fade from black to main menu
            self._show_loading = False
            SceneManager.fade_from_black(self._screen, render_main_menu, self._fade_duration)

            # Reset completion flags
            self._show_level_complete = False
            self._level_complete_timer = 0
            self._level.level_complete = False

    def render(self):
        """Render simulation to screen"""
        self._screen.fill("BLACK")

        if self._level:
            self._level.draw(self._screen)

            # Draw "Level Complete" message if needed
            if self._show_level_complete:
                self._draw_level_complete_overlay()

        # Draw map system if open (with level dimensions)
        if self._state == "game" and self._level and (self._map_system.is_open or self._map_system.fading_in or self._map_system.fading_out or self._map_system.show_message):
            # Get player position
            player_x = self._level.ball.rect.centerx
            player_y = self._level.ball.rect.centery
            
            # Get level dimensions
            level_width = self._level.width
            level_height = self._level.height
            
            # Draw map with all the necessary information
            self._map_system.draw(self._screen, player_x, player_y, level_width, level_height)

        # FPS Display
        fps_counter = self.clock.get_fps()
        fps_display = pygame.font.Font(daFont, 12).render(f"FPS: {int(fps_counter)}", True, (255, 255, 255))
        self.screen.blit(fps_display, (SCREEN_WIDTH - 100, 580))

    def _draw_level_complete_overlay(self):
        """Draw the level complete overlay with message"""
        # Create a semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))  # Semi-transparent black
        self._screen.blit(overlay, (0, 0))

        # Draw completion message with Daydream font
        completion_text = "Returning to menu..."
        text_surface = self._pixel_font.render(completion_text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self._screen.blit(text_surface, text_rect)

    def render_start_screen(self):
        """Render the start screen with centered title and flashing text"""
        # Draw background layers with parallax effect (from back to front)
        self._screen.fill((0, 0, 0))  # Fill with black first

        for layer in self._bg_layers:
            self._screen.blit(layer['image'], (-layer['pos_x'], -layer['pos_y']))

        # Draw title text at current position (will be animated during transition)
        title_x = SCREEN_WIDTH // 2 - self._title_text.get_width() // 2
        self._screen.blit(self._title_text, (title_x, self._title_y_pos))

        # Draw flashing "Press anything to start" text with outline
        if self._show_flash_text and (not self._is_transitioning or self._transition_phase == 1):
            text = "Press anything to start!"
            # Calculate position to center the text
            text_width = self._pixel_font.size(text)[0]
            text_x = SCREEN_WIDTH // 2 - text_width // 2
            text_y = SCREEN_HEIGHT // 2 + 200  # Below the title
            
            # Draw the text with outline
            self.render_outlined_text(text, (255, 255, 255), (0, 0, 0), (text_x, text_y))
            
    def setup_main_menu(self):
        """Set up the main menu UI elements with pygame-gui"""
        # Clear any existing buttons
        if hasattr(self, '_main_menu_buttons'):
            for button in self._main_menu_buttons:
                if hasattr(button, 'kill'):
                    button.kill()
        self._main_menu_buttons = []
        
        # Calculate button dimensions and positioning
        button_width = 200
        button_height = 50
        button_margin = 20
        start_y = SCREEN_HEIGHT // 2 - button_height
        
        # Create START button using the play_button style from theme
        start_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                (SCREEN_WIDTH // 2 - button_width // 2, start_y+100),
                (button_width, button_height)
            ),
            text="START",
            manager=self._ui_manager,
            object_id="#play_button"
        )
        self._main_menu_buttons.append(start_button)
        
        # Create CREDITS button using the credits_button style from theme
        credits_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                (SCREEN_WIDTH // 2 - button_width // 2, start_y + button_height + button_margin+100),
                (button_width, button_height)
            ),
            text="CREDITS",
            manager=self._ui_manager,
            object_id="#credits_button"
        )
        self._main_menu_buttons.append(credits_button)
        
        # Create EXIT button using the exit_button style from theme
        exit_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                (SCREEN_WIDTH // 2 - button_width // 2, start_y + 2 * (button_height + button_margin)+100),
                (button_width, button_height)
            ),
            text="EXIT",
            manager=self._ui_manager,
            object_id="#exit_button"
        )
        self._main_menu_buttons.append(exit_button)

    def load_level_images(self):
        """Load level preview images"""
        for level_id, path in self._level_image_paths.items():
            try:
                # Load and scale the image to fit the level squares
                image = pygame.image.load(path)
                scaled_image = pygame.transform.scale(image, (100, 100))
                self._level_images[level_id] = scaled_image
            except pygame.error:
                # Create a placeholder colored surface if image doesn't exist
                placeholder = pygame.Surface((100, 100))
                if level_id == 5:  # Secret level
                    placeholder.fill((128, 0, 128))  # Purple for secret
                else:
                    placeholder.fill((64 + level_id * 30, 100, 150))  # Different colors per level
                self._level_images[level_id] = placeholder

    def open_level_select(self):
        """Opens the level selection menu with a horizontal scrollable grid"""
        self._level_select_open = True
        
        # Hide main menu buttons
        if hasattr(self, '_main_menu_buttons'):
            for button in self._main_menu_buttons:
                button.hide()
        
        # Clean up any existing level select UI elements first
        self._cleanup_level_select_ui()
        
        # Load level images if not already loaded
        if not self._level_images:
            self.load_level_images()
        
        # Initialize scroll and selection
        self._selected_level = 0
        
        # Calculate level positions first
        self._setup_level_grid()
        
        # Then properly center the first level
        spacing = 180
        self._target_scroll = -self._selected_level * spacing + SCREEN_WIDTH // 2
        self._scroll_offset = self._target_scroll  # Set initial scroll immediately
        
        # Reset mouse interaction state
        self._mouse_dragging = False
        self._drag_start_pos = None
        self._drag_velocity = 0
        self._drag_history = []
        
        # Calculate level positions
        self._setup_level_grid()
        
        # Create navigation buttons with consistent styling
        button_y = SCREEN_HEIGHT // 2 + 150
        
        self._left_arrow = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((50, button_y), (60, 60)),
            text="<",
            manager=self._ui_manager,
            object_id="#nav_button"
        )
        
        self._right_arrow = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((SCREEN_WIDTH - 110, button_y), (60, 60)),
            text=">",
            manager=self._ui_manager,
            object_id="#nav_button"
        )
        
        self._select_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                (SCREEN_WIDTH // 2 - 75, SCREEN_HEIGHT // 2 + 220),
                (150, 50)
            ),
            text="SELECT",
            manager=self._ui_manager,
            object_id="#play_button"
        )
        
        # Add back button
        self._back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                (SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT - 80),
                (200, 50)
            ),
            text="BACK",
            manager=self._ui_manager,
            object_id="#exit_button"
        )
        
        # Add secret code hint
        hint_text = "Secret level unlocked!" if self._boss_level_unlocked else "Type the password to unlock the secret level!"
        self._secret_hint = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(
                (SCREEN_WIDTH // 2 - 300, SCREEN_HEIGHT - 30),
                (600, 20)
            ),
            text=hint_text,
            manager=self._ui_manager,
            object_id="#hint_label"
        )

    def _cleanup_level_select_ui(self):
        """Clean up all level select UI elements"""
        # Clean up navigation and control buttons
        ui_elements = ['_left_arrow', '_right_arrow', '_select_button', '_back_button', '_secret_hint']
        for element_name in ui_elements:
            if hasattr(self, element_name):
                element = getattr(self, element_name)
                if element and hasattr(element, 'kill'):
                    element.kill()
                    setattr(self, element_name, None)
        
        # Clean up any level buttons that might exist from old implementation
        if hasattr(self, '_level_buttons'):
            for button in self._level_buttons:
                if hasattr(button, 'kill'):
                    button.kill()
            self._level_buttons = []

    def _setup_level_grid(self):
        """Setup the positions and rectangles for level squares"""
        self._level_positions = []
        self._level_rects = []
        
        # Grid configuration
        base_size = 120
        spacing = 180
        center_y = SCREEN_HEIGHT // 2 - 20
        start_x = SCREEN_WIDTH // 2 - (spacing * 2.2)  # Center the grid
        
        for i in range(6):  # 6 levels total (5 + secret)
            x = start_x + (i * spacing)
            y = center_y
            
            self._level_positions.append((x, y))
            self._level_rects.append(pygame.Rect(x - base_size//2, y - base_size//2, base_size, base_size))

    def _get_level_at_mouse_pos(self, mouse_pos):
        """Get which level the mouse is hovering over, accounting for scroll offset"""
        mouse_x, mouse_y = mouse_pos
        
        for i in range(6):
            if i >= len(self._level_positions):
                continue
                
            base_x, base_y = self._level_positions[i]
            x = base_x + self._scroll_offset
            
            # Calculate size based on selection state
            base_size = 140 if i == self._selected_level else 120
            
            # Create rect for this level
            level_rect = pygame.Rect(x - base_size//2, base_y - base_size//2, base_size, base_size)
            
            if level_rect.collidepoint(mouse_x, mouse_y):
                return i
        
        return None

    def _update_drag_velocity(self, current_pos):
        """Update drag velocity based on recent mouse movement"""
        current_time = pygame.time.get_ticks()
        
        # Add current position to history
        self._drag_history.append((current_pos[0], current_time))
        
        # Remove old history (keep only last 100ms)
        self._drag_history = [(pos, time) for pos, time in self._drag_history 
                             if current_time - time <= 100]
        
        # Calculate velocity based on recent movement
        if len(self._drag_history) >= 2:
            recent_pos, recent_time = self._drag_history[-1]
            old_pos, old_time = self._drag_history[0]
            
            time_diff = recent_time - old_time
            if time_diff > 0:
                self._drag_velocity = (recent_pos - old_pos) / time_diff * 16  # Scale for 60fps

    def update_level_select(self, time_delta):
        """Update the level select screen"""
        if not self._level_select_open:
            return
        
        # Apply momentum/inertia when not actively dragging
        if not self._mouse_dragging and abs(self._drag_velocity) > 0.1:
            self._target_scroll += self._drag_velocity * time_delta * 60  # Scale for frame rate
            self._drag_velocity *= self._momentum_decay
            
            # Clamp scroll bounds
            self._clamp_scroll_bounds()
            
            # If momentum is very low, snap to nearest level
            if abs(self._drag_velocity) < 0.5:
                self._snap_to_nearest_level()
                self._drag_velocity = 0
        
        # Smooth scrolling animation
        if abs(self._target_scroll - self._scroll_offset) > 1:
            self._scroll_offset += (self._target_scroll - self._scroll_offset) * 0.1
        else:
            self._scroll_offset = self._target_scroll
        
        # Update selected level based on what's closest to center
        self._update_selected_level_from_scroll()

    def _clamp_scroll_bounds(self):
        """Ensure scroll doesn't go beyond reasonable bounds"""
        # Calculate bounds based on level positions
        spacing = 180
        max_scroll = spacing * 2  # Allow scrolling a bit past first level
        min_scroll = -spacing * 6  # Allow scrolling a bit past last level
        
        if self._target_scroll > max_scroll:
            self._target_scroll = max_scroll
            self._drag_velocity = 0
        elif self._target_scroll < min_scroll:
            self._target_scroll = min_scroll
            self._drag_velocity = 0

    def _update_selected_level_from_scroll(self):
        """Update selected level based on current scroll position"""
        # Find which level is closest to screen center
        center_x = SCREEN_WIDTH // 2
        closest_level = 0
        closest_distance = float('inf')
        
        for i in range(6):
            if i >= len(self._level_positions):
                continue
                
            base_x, _ = self._level_positions[i]
            level_x = base_x + self._scroll_offset
            distance = abs(level_x - center_x)
            
            if distance < closest_distance:
                closest_distance = distance
                closest_level = i
        
        self._selected_level = closest_level

    def _snap_to_nearest_level(self):
        """Snap to the nearest level after dragging ends"""
        spacing = 180
        # Calculate which level should be centered
        target_level = self._selected_level
        self._target_scroll = -target_level * spacing + SCREEN_WIDTH // 2

    def handle_level_select_input(self, event):
        """Handle input for level select"""
        if not self._level_select_open:
            return False
        
        # Handle mouse events
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                mouse_pos = pygame.mouse.get_pos()
                
                # Check if clicking on a level - but don't select immediately
                clicked_level = self._get_level_at_mouse_pos(mouse_pos)
                if clicked_level is not None:
                    # Start potential drag
                    self._drag_start_pos = mouse_pos
                    self._drag_start_scroll = self._scroll_offset
                    self._last_mouse_pos = mouse_pos
                    self._drag_history = [(mouse_pos[0], pygame.time.get_ticks())]
                    return True
                        
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:  # Left click release
                mouse_pos = pygame.mouse.get_pos()
                
                if self._mouse_dragging:
                    # End dragging
                    self._mouse_dragging = False
                    self._drag_start_pos = None
                    
                    # If we were dragging with low velocity, snap to nearest level
                    if abs(self._drag_velocity) < 2:
                        self._snap_to_nearest_level()
                        self._drag_velocity = 0
                    return True
                    
                elif self._drag_start_pos is not None:
                    # This was a click (not a drag) - check if we're still on the same level
                    clicked_level = self._get_level_at_mouse_pos(mouse_pos)
                    if clicked_level is not None:
                        # If clicking on the currently selected level, select it
                        if clicked_level == self._selected_level:
                            self._select_current_level()
                        else:
                            # Move to clicked level
                            self._selected_level = clicked_level
                            spacing = 180
                            self._target_scroll = -self._selected_level * spacing + SCREEN_WIDTH // 2
                            self._drag_velocity = 0
                    
                    # Clean up drag state
                    self._drag_start_pos = None
                    return True
                
        elif event.type == pygame.MOUSEMOTION:
            if self._drag_start_pos is not None:
                mouse_pos = pygame.mouse.get_pos()
                
                # Check if we've moved enough to start dragging
                drag_distance = abs(mouse_pos[0] - self._drag_start_pos[0])
                
                if not self._mouse_dragging and drag_distance > self._min_drag_distance:
                    self._mouse_dragging = True
                
                if self._mouse_dragging:
                    # Update scroll based on drag
                    drag_offset = mouse_pos[0] - self._drag_start_pos[0]
                    self._target_scroll = self._drag_start_scroll + drag_offset
                    self._scroll_offset = self._target_scroll  # Immediate response while dragging
                    
                    # Update velocity for momentum
                    self._update_drag_velocity(mouse_pos)
                    
                    # Clamp bounds
                    self._clamp_scroll_bounds()
                    return True
            
        # Handle keyboard events
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT or event.key == pygame.K_a:
                self._move_selection(-1)
                return True
            elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                self._move_selection(1)
                return True
            elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                self._select_current_level()
                return True
            elif event.key == pygame.K_ESCAPE:
                self.close_level_select()
                return True
        
        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if hasattr(self, '_left_arrow') and event.ui_element == self._left_arrow:
                self._move_selection(-1)
                return True
            elif hasattr(self, '_right_arrow') and event.ui_element == self._right_arrow:
                self._move_selection(1)
                return True
            elif hasattr(self, '_select_button') and event.ui_element == self._select_button:
                self._select_current_level()
                return True
            elif hasattr(self, '_back_button') and event.ui_element == self._back_button:
                self.close_level_select()
                return True
        
        return False

    def _move_selection(self, direction):
        """Move the selection left or right"""
        new_selection = self._selected_level + direction
        
        # Clamp to valid range
        if new_selection < 0:
            new_selection = 0
        elif new_selection >= 6:
            new_selection = 5
            
        if new_selection != self._selected_level:
            self._selected_level = new_selection
            # Update target scroll to center the selected level
            spacing = 180
            self._target_scroll = -self._selected_level * spacing + SCREEN_WIDTH // 2
            # Stop any existing momentum
            self._drag_velocity = 0

    def _select_current_level(self):
        """Select the currently highlighted level"""
        # Check if secret level is locked
        if self._selected_level == 5 and not self._boss_level_unlocked:
            # You can add a sound effect or visual feedback here
            print("Secret level is locked!")
            return
            
        # Close level select and start the selected level
        self.close_level_select()
        self.start_level(self._selected_level)

    def close_level_select(self):
        """Close the level select screen"""
        self._level_select_open = False
        self._mouse_dragging = False
        self._drag_start_pos = None
        self._drag_velocity = 0
        
        # Clean up UI
        self._cleanup_level_select_ui()
        
        # Show main menu buttons again
        if hasattr(self, '_main_menu_buttons'):
            for button in self._main_menu_buttons:
                button.show()

    def draw_level_select(self, screen):
        """Draw the level select grid as a full screen replacement"""
        if not self._level_select_open:
            return
        
        # Draw the same background as main menu (no overlay, full replacement)
        # Background is already drawn in render_main_menu, so we just need to add the new content
        
        # Draw level select title with the same style as main menu title
        if hasattr(self, '_title_text'):
            title_text = "SELECT LEVEL"
            title_color = (255, 255, 255)
            outline_color = (0, 0, 0)
            title_center = (SCREEN_WIDTH // 2, 120)
            outline_width = 3

            # Draw outline for title
            outline_surface = self._pixel_font.render(title_text, True, outline_color)
            for dx in range(-outline_width, outline_width + 1):
                for dy in range(-outline_width, outline_width + 1):
                    if dx != 0 or dy != 0:
                        screen.blit(outline_surface, (title_center[0] + dx - outline_surface.get_width() // 2,
                                                     title_center[1] + dy - outline_surface.get_height() // 2))
            
            # Draw main title text
            title_surface = self._pixel_font.render(title_text, True, title_color)
            title_rect = title_surface.get_rect(center=title_center)
            screen.blit(title_surface, title_rect)
        
        # Draw level squares
        for i in range(6):
            if i >= len(self._level_positions):
                continue
                
            base_x, base_y = self._level_positions[i]
            
            # Apply scroll offset
            x = base_x + self._scroll_offset
            
            # Skip if off screen
            if x < -200 or x > SCREEN_WIDTH + 200:
                continue
            
            # Calculate size based on distance from center and selection
            distance_from_center = abs(x - SCREEN_WIDTH // 2)
            max_distance = SCREEN_WIDTH // 2
            
            # Base size with selection boost
            if i == self._selected_level:
                base_size = 140  # Selected level is bigger
                alpha = 255
            else:
                base_size = 100 + max(0, 40 - distance_from_center // 10)  # Size based on distance
                alpha = max(180, 255 - distance_from_center // 5)  # Fade based on distance
            
            # Create rect for this level
            level_rect = pygame.Rect(x - base_size//2, base_y - base_size//2, base_size, base_size)
            
            # Check if mouse is hovering over this level
            mouse_pos = pygame.mouse.get_pos()
            is_hovering = level_rect.collidepoint(mouse_pos) and not self._mouse_dragging
            
            # Draw level background with border
            pygame.draw.rect(screen, (40, 40, 40), level_rect)  # Dark background
            
            # Draw level border - selected gets special treatment, hovered gets intermediate
            if i == self._selected_level:
                border_color = (255, 255, 0)
                border_width = 4
            elif is_hovering:
                border_color = (200, 200, 0)
                border_width = 3
            else:
                border_color = (100, 100, 100)
                border_width = 2
            pygame.draw.rect(screen, border_color, level_rect, border_width)
            
            # Check if level is locked (only secret level can be locked)
            is_locked = (i == 5 and not self._boss_level_unlocked)
            
            # Draw level image if available
            if i in self._level_images:
                # Scale image to current size
                image_size = base_size - 20  # Leave space for border
                scaled_image = pygame.transform.scale(self._level_images[i], (image_size, image_size))
                
                # Apply lock overlay if locked
                if is_locked:
                    # Create a darker version of the image
                    scaled_image = scaled_image.copy()
                    dark_overlay = pygame.Surface((image_size, image_size))
                    dark_overlay.fill((0, 0, 0))
                    dark_overlay.set_alpha(180)
                    scaled_image.blit(dark_overlay, (0, 0))
                elif alpha < 255:
                    scaled_image = scaled_image.copy()
                    scaled_image.set_alpha(alpha)
                
                image_rect = scaled_image.get_rect(center=(x, base_y))
                screen.blit(scaled_image, image_rect)
            else:
                # Fallback colored rectangle
                inner_rect = pygame.Rect(x - (base_size-20)//2, base_y - (base_size-20)//2, base_size-20, base_size-20)
                if is_locked:
                    color = (64, 64, 64)  # Gray for locked
                else:
                    color = (64 + i * 30, 100, 150) if i < 5 else (128, 0, 128)
                    
                if alpha < 255 and not is_locked:
                    color = tuple(int(c * alpha / 255) for c in color)
                pygame.draw.rect(screen, color, inner_rect)
            
            # Draw lock icon if locked
            if is_locked:
                lock_font = pygame.font.Font(daFont, 18)
                lock_text = "LOCKED"
                lock_color = (255, 255, 255)
                outline_color = (0, 0, 0)
                lock_center = (x, base_y)
                outline_width = 2
                
                try:
                    # Draw outline for LOCKED text
                    outline_surface = lock_font.render(lock_text, True, outline_color)
                    for dx in range(-outline_width, outline_width + 1):
                        for dy in range(-outline_width, outline_width + 1):
                            if dx != 0 or dy != 0:
                                screen.blit(outline_surface, (lock_center[0] + dx - outline_surface.get_width() // 2,
                                                             lock_center[1] + dy - outline_surface.get_height() // 2))
                    
                    # Draw main LOCKED text
                    lock_surface = lock_font.render(lock_text, True, lock_color)
                    lock_rect = lock_surface.get_rect(center=lock_center)
                    screen.blit(lock_surface, lock_rect)
                except:
                    # Fallback if emoji doesn't render
                    fallback_text = "LOCK"
                    # Draw outline for fallback LOCK text
                    outline_surface = lock_font.render(fallback_text, True, outline_color)
                    for dx in range(-outline_width, outline_width + 1):
                        for dy in range(-outline_width, outline_width + 1):
                            if dx != 0 or dy != 0:
                                screen.blit(outline_surface, (lock_center[0] + dx - outline_surface.get_width() // 2,
                                                             lock_center[1] + dy - outline_surface.get_height() // 2))
                    
                    # Draw main fallback LOCK text
                    lock_surface = lock_font.render(fallback_text, True, lock_color)
                    lock_rect = lock_surface.get_rect(center=lock_center)
                    screen.blit(lock_surface, lock_rect)
            
            # Draw level number/text
            font = pygame.font.Font(daFont, 18)
            if i == 5:
                text = "???" if not self._boss_level_unlocked else "BOSS"
            else:
                text = "Level "  + str( i + 1)
            
            text_color = (255, 255, 255) if alpha > 200 else (alpha, alpha, alpha)
            if is_locked:
                text_color = (128, 128, 128)
            
            text_center = (x, base_y + base_size//2 + 25)
            outline_color = (0, 0, 0) # Black outline for level numbers/text
            outline_width = 2

            # Draw outline for level number/text
            outline_surface = font.render(text, True, outline_color)
            for dx in range(-outline_width, outline_width + 1):
                for dy in range(-outline_width, outline_width + 1):
                    if dx != 0 or dy != 0:
                        screen.blit(outline_surface, (text_center[0] + dx - outline_surface.get_width() // 2,
                                                     text_center[1] + dy - outline_surface.get_height() // 2))
            
            # Draw main level number/text
            text_surface = font.render(text, True, text_color)
            text_rect = text_surface.get_rect(center=text_center)
            screen.blit(text_surface, text_rect)
        
        # Draw selection indicator
        center_x = SCREEN_WIDTH // 2
        # Draw a pulsing circle
        import math
        pulse = abs(math.sin(pygame.time.get_ticks() / 200.0))
        radius = int(5 + pulse * 3)
        pygame.draw.circle(screen, (255, 255, 0), (center_x, SCREEN_HEIGHT // 2 + 100), radius)
        
        # Draw navigation instructions with better styling
        if hasattr(self, '_small_font'):
            instructions = [
                f"Best Time: {self._game_save.display_best_time(self._selected_level)}",
                f"Rank: {self._game_save.display_best_rank(self._selected_level)}",
                f"High Score: {self._game_save.display_best_score(self._selected_level)}",
            ]
            
            y_offset = SCREEN_HEIGHT - 180
            instruction_outline_color = (0, 0, 0)
            instruction_text_color = "WHITE"
            outline_width = 1

            for i, instruction in enumerate(instructions):
                inst_center = (SCREEN_WIDTH // 2, y_offset + i * 40)
                
                # Draw outline for instructions
                outline_surface = self._small_font.render(instruction, True, instruction_outline_color)
                for dx in range(-outline_width, outline_width + 1):
                    for dy in range(-outline_width, outline_width + 1):
                        if dx != 0 or dy != 0:
                            screen.blit(outline_surface, (inst_center[0] + dx - outline_surface.get_width() // 2,
                                                         inst_center[1] + dy - outline_surface.get_height() // 2))
                
                # Draw main instruction text
                inst_surface = self._small_font.render(instruction, True, instruction_text_color)
                inst_rect = inst_surface.get_rect(center=inst_center)
                screen.blit(inst_surface, inst_rect)

    def _handle_ui_button_press(self, event):
        """Handle UI button presses in the menu"""
        # Main menu buttons (only if level select is not open)
        if not self._level_select_open and hasattr(self, '_main_menu_buttons') and self._main_menu_buttons:
            if event.ui_element == self._main_menu_buttons[0]:  # START
                self.open_level_select()
            elif len(self._main_menu_buttons) > 1 and event.ui_element == self._main_menu_buttons[1]:  # CREDITS
                self._handle_credits_button()
            elif len(self._main_menu_buttons) > 2 and event.ui_element == self._main_menu_buttons[2]:  # EXIT
                self._handle_exit_button()

    def _handle_secret_code_input(self, event):
        """Handle keyboard input for the secret code"""
        # Add key to current input
        if event.unicode.isalpha():
            self._current_input += event.unicode.upper()
            
            # Keep only the last N characters where N is the length of the secret code
            if len(self._current_input) > len(self._secret_code):
                self._current_input = self._current_input[-len(self._secret_code):]
            
            # Check if secret code entered
            if self._current_input == self._secret_code:
                self._boss_level_unlocked = True
                print("BOSS LEVEL UNLOCKED!")
                
                # Update the secret hint text if in level select
                if self._level_select_open and hasattr(self, '_secret_hint') and self._secret_hint:
                    self._secret_hint.set_text("Secret level unlocked!")
                
                # Play a special sound effect (if available)
                try:
                    secret_sound = pygame.mixer.Sound(os.path.join("assets", "sounds", "secret.mp3"))
                    secret_sound.play()
                except:
                    print("Secret sound effect not found")

    def handle_state_transition(self, new_state):
        """Handle UI transitions between game states"""
        old_state = self._state
        self._state = new_state
        
        # Hide/show UI elements based on state
        if new_state == "main_menu":
            # Show main menu buttons
            if hasattr(self, '_main_menu_buttons'):
                for button in self._main_menu_buttons:
                    button.show()
                    
            # Ensure main menu is set up
            if not hasattr(self, '_main_menu_buttons') or not self._main_menu_buttons:
                self.setup_main_menu()
                
            # Reset level select state
            if self._level_select_open:
                self.close_level_select()
                    
        elif new_state == "game":
            # Hide all UI elements during game
            if hasattr(self, '_main_menu_buttons'):
                for button in self._main_menu_buttons:
                    button.hide()
                    
            # Close level select if open
            if self._level_select_open:
                self.close_level_select()
                    
        elif new_state == "credits":
            # Hide all UI elements during credits
            if hasattr(self, '_main_menu_buttons'):
                for button in self._main_menu_buttons:
                    button.hide()
                    
            # Close level select if open
            if self._level_select_open:
                self.close_level_select()
        
        # Handle music transitions
        if new_state == "main_menu" and old_state != "main_menu":
            pygame.mixer_music.load(os.path.join("assets", "music", "theme.mp3"))
            global CURRENT_TRACK
            CURRENT_TRACK = 'menu'
            pygame.mixer_music.play(-1)

    def close_level_select(self):
        """Closes the level selection menu"""
        self._level_select_open = False
        
        # Show main menu buttons
        if hasattr(self, '_main_menu_buttons'):
            for button in self._main_menu_buttons:
                button.show()
        
        # Clean up all level select UI elements
        self._cleanup_level_select_ui()

    def render_main_menu(self):
        """Render main menu screen with pygame-gui buttons"""
        # Draw background layers with parallax effect
        self._screen.fill((0, 0, 0))  # Fill with black first

        for layer in self._bg_layers:
            self._screen.blit(layer['image'], (-layer['pos_x'], -layer['pos_y']))

        # If level select is open, draw it as a full screen replacement
        if self._level_select_open:
            self.draw_level_select(self._screen)
        else:
            # Draw normal main menu
            # Draw title text
            title_x = SCREEN_WIDTH // 2 - self._title_text.get_width() // 2
            self._screen.blit(self._title_text, (title_x, SCREEN_HEIGHT // 4 - self._title_text.get_height() // 2))
            
            # If we've unlocked the boss level, show a small indicator
            if self._boss_level_unlocked:
                boss_unlocked_text = "BOSS LEVEL UNLOCKED!"
                boss_text_surface = self._small_font.render(boss_unlocked_text, True, (255, 215, 0))  # Gold color
                boss_text_rect = boss_text_surface.get_rect(topleft=(10, 10))
                self._screen.blit(boss_text_surface, boss_text_rect)
        
        # Draw UI elements (buttons will be shown/hidden based on state)
        self._ui_manager.draw_ui(self._screen)

    def handle_menu_events(self, event):
        """Handles menu events for UI buttons"""
        # Handle level select input first if it's open
        if self._level_select_open and self.handle_level_select_input(event):
            return
        
        # Handle secret code input when level select is open
        if event.type == pygame.KEYDOWN and self._level_select_open:
            self._handle_secret_code_input(event)
        
        # Handle main UI button presses
        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            self._handle_ui_button_press(event)

    def _handle_credits_button(self):
        """Handle when the credits button is pressed"""
        def render_main_menu():
            self.update_background()
            self.render_main_menu()
        
        SceneManager.fade_to_black(self._screen, render_main_menu, self._fade_duration)
        pygame.mixer_music.fadeout(500)
        self._credits = objects.Credits(self._screen, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.handle_state_transition("credits")

    def _handle_exit_button(self):
        """Handle when the exit button is pressed"""
        def render_main_menu():
            self.update_background()
            self.render_main_menu()
        
        pygame.mixer_music.fadeout(900)
        SceneManager.fade_to_black(self._screen, render_main_menu, self._fade_duration)
        self._running = False

    def start_level(self, level_index):
        """Start the specified level with loading screen between transitions"""
        def render_main_menu():
            self.update_background()
            self.render_main_menu()

        def render_game():
            self.update(dt)
            self.render()
    
        # 1. Fade to black from current state
        pygame.mixer_music.fadeout(500)
        SceneManager.fade_to_black(self._screen, render_main_menu, self._fade_duration)
        
        # 2. Show loading screen on black background while setting up game
        self._show_loading = True
        
        def loading_task():
            """The actual loading work"""
            self.setup_game(level_index)
            self.handle_state_transition("game")
        
        self._draw_loading_screen_between_transitions(loading_task)
        
        # 3. Fade from black to new game state
        self._show_loading = False
        SceneManager.fade_from_black(self._screen, render_game, self._fade_duration)
        self.close_level_select()

    def _draw_loading_screen_between_transitions(self, loading_task=None):
        """Draw loading screen and run loading in background thread"""
        min_display_time = 1.0  # Minimum display duration for loading screen
        loading_complete = False
        start_time = time.time()
        self._shuffled_tips = random.sample(self._loading_tips, len(self._loading_tips))
        self._current_tip_index = random.randint(0, len(self._shuffled_tips) - 1)
        self._tip_change_timer = 0
        self._tip_fade_timer = 0
        self._tip_fading = False
        # Run loading task in separate thread
        if loading_task:
            def thread_target():
                loading_task()
                nonlocal loading_complete
                loading_complete = True

            loading_thread = threading.Thread(target=thread_target)
            loading_thread.start()
        else:
            loading_complete = True

        # Main loop to keep animating while loading
        while True:
            current_time = time.time()
            elapsed = current_time - start_time

            # Handle window close event
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                    return

            # Update loading animation
            dt = self._clock.tick(60) / 1000.0
            self._update_loading_animation(dt)

            # Draw loading screen
            self._screen.fill((0, 0, 0))
            self._draw_loading_icon()
            pygame.display.flip()

            # Exit loop once both loading is done and min time has passed
            if loading_complete and elapsed >= min_display_time:
                break

        # Ensure thread is done
        if loading_task:
            loading_thread.join()

    def _show_loading_screen_with_minimum_time(self, min_time=0.5):
        """Show loading screen on black background for minimum time while loading occurs"""
        import time
        
        loading_start_time = time.time()
        
        # Keep showing loading screen until minimum time has passed
        while time.time() - loading_start_time < min_time:
            # Handle events to prevent freezing
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                    return
            
            # Update loading animation
            dt = self._clock.tick(60) / 1000.0
            self._update_loading_animation(dt)
            
            # Draw pure black screen with loading icon
            self._screen.fill((0, 0, 0))
            self._draw_loading_icon()
            pygame.display.flip()

if __name__ == "__main__":
    Game().run()