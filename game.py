import pygame, pygame_gui, os, random, objects
from constants import *
from levels import SpaceLevel, CaveLevel, PymunkLevel, levels, spawn_points, BossArena
from utils import PhysicsManager, SceneManager, MapSystem

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
        
        self._player_has_map = False

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
        self._secret_code = "CUBODEEZ"
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
        self._logo_image = pygame.image.load(os.path.join("assets", "migglesoft.png")).convert_alpha()

        # Load title once to reuse
        self._title_text = pygame.image.load(os.path.join("assets", "title.png")).convert_alpha()

        pygame.display.set_caption("Red Ball: REDUX!")

        # Add variables for flashing text
        self._flash_timer = 0
        self._flash_rate = 0.5  # Flash every 0.5 seconds
        self._show_flash_text = True
        
        # Initialize map system
        self._map_system = MapSystem(self)
        self._map_key_pressed = False  # Track M key state to avoid repeat toggling

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
            self._small_font = pygame.font.Font(os.path.join("assets", "Daydream.ttf"), 18)
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

    def handle_intro_sequence(self, events):
        """Handle the intro logo sequence"""
        if self._state == 'intro':
            def render_logo():
                self._screen.fill((0, 0, 0)) # Fill with black first

            if SceneManager.fade_in(self._screen, render_logo, self._logo_image, self._fade_duration, (0, 0, 0)):
                pygame.time.delay(1000)  # show the logo for one second.
                if SceneManager.fade_out(self._screen, render_logo, self._logo_image, self._fade_duration, (0, 0, 0)):
                    self._state = 'start_screen'  # Go to start screen instead of main menu

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
        """Handle behavior when escape key is pressed"""
        if self._map_system.is_open:
            # Close map with escape key too
            self._map_system.toggle()
        elif self._state == "game":
            def render_game():
                self.update(dt)
                self.render()
            def render_main_menu():
                self.update_background()
                self.render_main_menu()

            SceneManager.fade_to_black(self._screen, render_game, self._fade_duration)
            pygame.mixer_music.fadeout(500)
            self.handle_state_transition("main_menu")
            SceneManager.fade_from_black(self._screen, render_main_menu, self._fade_duration)
        elif self._state == "credits":
            self.handle_state_transition("main_menu")
        else:
            self.update_background()
            self.render_main_menu()
            pygame.mixer_music.fadeout(900)
            SceneManager.fade_to_black(self._screen, render_main_menu, self._fade_duration)
            self._running = False

    def _update_game_state(self, events, dt):
        """Update and render based on the current game state"""
        if self._state == "intro":
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
            # Use CaveLevel if it is level 3 or 4
            self._level = CaveLevel(tmx_map=levels[level_index], spawn=spawn_points[level_index])
        elif level_index == 4:
            # Use SpaceLevel for level 5
            self._level = SpaceLevel(tmx_map=levels[level_index], spawn=spawn_points[level_index])
        elif level_index == 5:
            # Use Boss Arena for level 5
            self._level = BossArena(tmx_map=levels[level_index], spawn=spawn_points[level_index])
        else:
            # Use PymunkLevel for all other levels
            self._level = PymunkLevel(tmx_map=levels[level_index], spawn=spawn_points[level_index])

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
        """Handle the level complete transition"""
        self._level_complete_timer += dt
        if self._level_complete_timer >= self._level_complete_delay:
            # Unlock boss level if completing level 5
            if self._current_level_index == 4:  # Level indices are 0-based, so level 5 is index 4
                self._boss_level_unlocked = True
                print("BOSS LEVEL UNLOCKED by completing level 5!")
                
            # Transition back to main menu after the delay
            def render_game():
                self.render()
            def render_main_menu():
                self.update_background()
                self.render_main_menu()

            pygame.mixer_music.fadeout(500)
            SceneManager.fade_to_black(self._screen, render_game, self._fade_duration)
            self.handle_state_transition("main_menu")
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

        # FPS Display
        fps_counter = self._clock.get_fps()
        fps_display = self._small_font.render(f"FPS: {int(fps_counter)}", True, (255, 255, 255))
        self._screen.blit(fps_display, (SCREEN_WIDTH - 120, 10))
        
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

    def _draw_level_complete_overlay(self):
        """Draw the level complete overlay with message"""
        # Create a semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))  # Semi-transparent black
        self._screen.blit(overlay, (0, 0))

        # Draw completion message with Daydream font
        completion_text = "Level Complete!"
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
            text_y = self._title_y_pos + self._title_text.get_height() + 30

            # Render with outline
            self.render_outlined_text(text, (255, 255, 255), (0, 0, 0), (text_x, text_y))

    # PYGAME-GUI IMPROVED METHODS
    
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

    def open_level_select(self):
        """Opens the level selection menu with a scrollable container"""
        self._level_select_open = True
        
        # Hide main menu buttons
        if hasattr(self, '_main_menu_buttons'):
            for button in self._main_menu_buttons:
                button.hide()
        
        # Clear any existing level buttons
        if hasattr(self, '_level_buttons'):
            for button in self._level_buttons:
                if hasattr(button, 'kill'):
                    button.kill()
        self._level_buttons = []
        
        # Create a scrollable container
        container_width = 300
        container_height = 400
        
        # Create a container at the center of the screen
        self._level_container = pygame_gui.elements.UIScrollingContainer(
            relative_rect=pygame.Rect(
                (SCREEN_WIDTH // 2 - container_width // 2, SCREEN_HEIGHT // 2 - container_height // 2),
                (container_width, container_height)
            ),
            manager=self._ui_manager
        )
        
        # Create level selection buttons within the container
        button_width = 250
        button_height = 50
        button_margin = 20
        total_height = 0
        
        # Level buttons (5 levels + secret)
        for i in range(6):
            if i == 5:
                button_text = "???"  # Secret level initially shows as ???
            else:
                button_text = f"Level {i + 1}"
            
            level_button = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(
                    (container_width // 2 - button_width // 2, total_height),
                    (button_width, button_height)
                ),
                text=button_text,
                manager=self._ui_manager,
                container=self._level_container
            )
            
            # Disable boss level button if not unlocked
            if i == 5 and not self._boss_level_unlocked:
                level_button.disable()  # Disable instead of hide for better UX
            
            self._level_buttons.append(level_button)
            total_height += button_height + button_margin
        
        # Make sure the container is tall enough
        self._level_container.set_scrollable_area_dimensions((container_width - 20, total_height))
        
        # Add back button outside the container using the return_button style from theme
        self._back_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(
                (SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT - 80),
                (200, 50)
            ),
            text="BACK",
            manager=self._ui_manager,
            object_id="#return_button"
        )
        
        # Add a secret code hint
        self._secret_hint = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(
                (SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT - 30),
                (300, 20)
            ),
            text="Type the secret code to unlock...",
            manager=self._ui_manager
        )

    def close_level_select(self):
        """Closes the level selection menu"""
        self._level_select_open = False
        
        # Show main menu buttons
        if hasattr(self, '_main_menu_buttons'):
            for button in self._main_menu_buttons:
                button.show()
        
        # Remove level buttons and container
        if hasattr(self, '_level_buttons'):
            for button in self._level_buttons:
                if hasattr(button, 'kill'):
                    button.kill()
            self._level_buttons = []
        
        if hasattr(self, '_level_container') and self._level_container:
            self._level_container.kill()
        
        if hasattr(self, '_back_button') and self._back_button:
            self._back_button.kill()
            
        if hasattr(self, '_secret_hint') and self._secret_hint:
            self._secret_hint.kill()

    def render_main_menu(self):
        """Render main menu screen with pygame-gui buttons"""
        # Draw background layers with parallax effect
        self._screen.fill((0, 0, 0))  # Fill with black first

        for layer in self._bg_layers:
            self._screen.blit(layer['image'], (-layer['pos_x'], -layer['pos_y']))

        # Draw title text
        title_x = SCREEN_WIDTH // 2 - self._title_text.get_width() // 2
        self._screen.blit(self._title_text, (title_x, SCREEN_HEIGHT // 4 - self._title_text.get_height() // 2))
        
        # Draw UI elements
        self._ui_manager.draw_ui(self._screen)
        
        # If we've unlocked the boss level, show a small indicator
        if self._boss_level_unlocked:
            boss_unlocked_text = "BOSS LEVEL UNLOCKED!"
            boss_text_surface = self._small_font.render(boss_unlocked_text, True, (255, 215, 0))  # Gold color
            boss_text_rect = boss_text_surface.get_rect(topleft=(10, 10))
            self._screen.blit(boss_text_surface, boss_text_rect)

    def handle_menu_events(self, event):
        """Handles menu events for UI buttons"""
        if event.type == pygame.USEREVENT:
            if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                self._handle_ui_button_press(event)
        
        # Handle keyboard input for secret code
        elif event.type == pygame.KEYDOWN:
            self._handle_secret_code_input(event)

    def _handle_ui_button_press(self, event):
        """Handle UI button presses in the menu"""
        # Main menu buttons
        if hasattr(self, '_main_menu_buttons') and self._main_menu_buttons:
            if event.ui_element == self._main_menu_buttons[0]:  # START
                self.open_level_select()
            elif len(self._main_menu_buttons) > 1 and event.ui_element == self._main_menu_buttons[1]:  # CREDITS
                self._handle_credits_button()
            elif len(self._main_menu_buttons) > 2 and event.ui_element == self._main_menu_buttons[2]:  # EXIT
                self._handle_exit_button()
        
        # Handle level selection back button
        if hasattr(self, '_back_button') and event.ui_element == self._back_button:
            self.close_level_select()
        
        # Handle level selection
        elif self._level_select_open and hasattr(self, '_level_buttons'):
            for i, button in enumerate(self._level_buttons):
                if event.ui_element == button:
                    self.start_level(i)
                    break

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
                
                # Update the BOSS level button if we're in level select
                if self._level_select_open and hasattr(self, '_level_buttons') and len(self._level_buttons) >= 6:
                    # Update the label and enable the boss level button
                    self._level_buttons[5].set_text("BOSS")
                    self._level_buttons[5].enable()
                
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
            self._level_select_open = False
                    
        elif new_state == "game":
            # Hide all UI elements during game
            if hasattr(self, '_main_menu_buttons'):
                for button in self._main_menu_buttons:
                    button.hide()
                    
        elif new_state == "credits":
            # Hide all UI elements during credits
            if hasattr(self, '_main_menu_buttons'):
                for button in self._main_menu_buttons:
                    button.hide()
        
        # Handle music transitions
        if new_state == "main_menu" and old_state != "main_menu":
            pygame.mixer_music.load(os.path.join("assets", "music", "theme.mp3"))
            global CURRENT_TRACK
            CURRENT_TRACK = 'menu'
            pygame.mixer_music.play(-1)

    def start_level(self, level_index):
        """Start the specified level with proper transitions"""
        def render_game():
            self.update(dt)
            self.render()
        def render_main_menu():
            self.update_background()
            self.render_main_menu()

        pygame.mixer_music.fadeout(500)

        SceneManager.fade_to_black(self._screen, render_main_menu, self._fade_duration)
        self.setup_game(level_index)
        self.handle_state_transition("game")
        SceneManager.fade_from_black(self._screen, render_game, self._fade_duration)
        self.close_level_select()

if __name__ == "__main__":
    Game().run()