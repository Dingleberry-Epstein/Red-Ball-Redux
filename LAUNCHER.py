import pygame
import pygame_gui
import json
import os
from typing import Dict, Any

class GameLauncher:
    """Game launcher with resolution, fullscreen, and framerate settings"""
    
    def __init__(self):
        pygame.init()
        
        # Launcher window settings - increased size to accommodate larger font
        self.launcher_width = 800
        self.launcher_height = 600
        self.screen = pygame.display.set_mode((self.launcher_width, self.launcher_height))
        pygame.display.set_caption("Red Ball: REDUX - Game Settings")
        
        # Set launcher icon (reuse game icon if available)
        try:
            icon = pygame.image.load(os.path.join("assets", "sprites", "Red Ball portrait.png")).convert_alpha()
            pygame.display.set_icon(icon)
        except:
            pass  # Icon not found, continue without it
        
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Game settings with defaults
        self.settings = {
            'width': 800,
            'height': 600,
            'fullscreen': False,
            'framerate': 60,
            'vsync': True
        }
        
        # Load existing settings if they exist
        self.load_settings()
        
        # Expanded resolutions including minimum 800x600
        self.resolutions = [
            (800, 600),    # SVGA (4:3) - minimum
            (1024, 768),   # XGA (4:3)
            (1152, 864),   # XGA+ (4:3)
            (1280, 720),   # 720p (16:9)
            (1280, 800),   # WXGA (16:10)
            (1280, 960),   # SXGA- (4:3)
            (1280, 1024),  # SXGA (5:4)
            (1366, 768),   # WXGA (16:9)
            (1440, 900),   # WXGA+ (16:10)
            (1600, 900),   # HD+ (16:9)
            (1600, 1200),  # UXGA (4:3)
            (1680, 1050),  # WSXGA+ (16:10)
            (1920, 1080),  # 1080p (16:9)
            (1920, 1200),  # WUXGA (16:10)
            (2048, 1152),  # QWXGA (16:9)
            (2560, 1440),  # 1440p (16:9)
            (2560, 1600),  # WQXGA (16:10)
            (3440, 1440),  # UWQHD (21:9) ultrawide
            (3840, 2160),  # 4K (16:9)
            (5120, 2880),  # 5K (16:9)
        ]
        
        # Sort resolutions by total pixels for better organization
        self.resolutions.sort(key=lambda x: x[0] * x[1])
        
        # Copy the provided theme file for use
        self.theme_path = os.path.join("assets", "theme.json")
        
        # Initialize pygame_gui manager with the provided theme
        self.ui_manager = pygame_gui.UIManager((self.launcher_width, self.launcher_height), self.theme_path)
        
        # Create UI elements
        self.setup_ui_elements()
        
        # Background
        self.background = pygame.Surface((self.launcher_width, self.launcher_height))
        self.background.fill((20, 25, 40))  # Dark blue background
        
        # Create some visual elements for the background
        self.create_background_pattern()
    
    def create_background_pattern(self):
        """Create a subtle background pattern"""
        # Draw some subtle grid lines
        for x in range(0, self.launcher_width, 40):
            pygame.draw.line(self.background, (25, 30, 45), (x, 0), (x, self.launcher_height), 1)
        for y in range(0, self.launcher_height, 40):
            pygame.draw.line(self.background, (25, 30, 45), (0, y), (self.launcher_width, y), 1)
        
        # Add some decorative elements
        pygame.draw.circle(self.background, (30, 35, 50), (120, 120), 60, 2)
        pygame.draw.circle(self.background, (30, 35, 50), (650, 480), 90, 2)
        pygame.draw.circle(self.background, (30, 35, 50), (600, 180), 40, 2)
    
    def setup_ui_elements(self):
        """Create all UI elements with proper sizing for larger font"""
        # Title - using the title_label style from theme
        self.title_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(0, 20, self.launcher_width, 50),
            text="Red Ball: REDUX - Game Settings",
            manager=self.ui_manager,
            object_id="#title_label"
        )
        
        # Resolution section
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(50, 90, 250, 35),
            text="Resolution:",
            manager=self.ui_manager
        )
        
        # Create resolution dropdown options
        resolution_options = []
        current_resolution_index = 0
        for i, (w, h) in enumerate(self.resolutions):
            aspect_ratio = self.get_aspect_ratio(w, h)
            res_text = f"{w} x {h} ({aspect_ratio})"
            if w == self.settings['width'] and h == self.settings['height']:
                current_resolution_index = i
            resolution_options.append(res_text)
        
        self.resolution_dropdown = pygame_gui.elements.UIDropDownMenu(
            options_list=resolution_options,
            starting_option=resolution_options[current_resolution_index],
            relative_rect=pygame.Rect(320, 90, 350, 35),
            manager=self.ui_manager
        )
        
        # Fullscreen toggle
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(50, 145, 250, 35),
            text="Fullscreen:",
            manager=self.ui_manager
        )
        
        self.fullscreen_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(320, 145, 120, 35),
            text="ON" if self.settings['fullscreen'] else "OFF",
            manager=self.ui_manager
        )
        
        # Framerate section
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(50, 200, 250, 35),
            text="Target Framerate:",
            manager=self.ui_manager
        )
        
        self.framerate_slider = pygame_gui.elements.UIHorizontalSlider(
            relative_rect=pygame.Rect(320, 205, 200, 25),
            start_value=self.settings['framerate'],
            value_range=(30, 144),
            manager=self.ui_manager
        )
        
        # Framerate text input for precise values
        self.framerate_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(530, 200, 80, 35),
            manager=self.ui_manager,
            initial_text=str(self.settings['framerate'])
        )
        
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(620, 200, 50, 35),
            text="FPS",
            manager=self.ui_manager
        )
        
        # VSync toggle
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(50, 255, 250, 35),
            text="VSync (Limit to Display):",
            manager=self.ui_manager
        )
        
        self.vsync_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(320, 255, 120, 35),
            text="ON" if self.settings['vsync'] else "OFF",
            manager=self.ui_manager
        )
        
        # Note about VSync
        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(50, 310, 650, 50),
            text="Note: VSync will override framerate setting and sync to your display's refresh rate.",
            manager=self.ui_manager
        )
        
        # Control buttons - increased size and spacing
        self.launch_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(self.launcher_width//2 - 220, 420, 140, 60),
            text="START",
            manager=self.ui_manager,
            object_id="#main_menu_button"
        )
        
        self.save_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(self.launcher_width//2 - 70, 420, 140, 60),
            text="SAVE",
            manager=self.ui_manager,
            object_id="#main_menu_button"
        )
        
        self.exit_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(self.launcher_width//2 + 80, 420, 140, 60),
            text="EXIT",
            manager=self.ui_manager,
            object_id="#main_menu_button"
        )
        
        # Display current settings info
        settings_text = self.get_settings_summary()
        self.settings_info = pygame_gui.elements.UITextBox(
            html_text=settings_text,
            relative_rect=pygame.Rect(50, 510, 700, 70),
            manager=self.ui_manager
        )
    
    def get_aspect_ratio(self, width: int, height: int) -> str:
        """Calculate and return the aspect ratio as a string"""
        def gcd(a, b):
            while b:
                a, b = b, a % b
            return a
        
        ratio_gcd = gcd(width, height)
        ratio_w = width // ratio_gcd
        ratio_h = height // ratio_gcd
        
        # Common aspect ratio names
        aspect_ratios = {
            (4, 3): "4:3",
            (5, 4): "5:4",
            (16, 9): "16:9",
            (16, 10): "16:10",
            (21, 9): "21:9",
            (32, 9): "32:9"
        }
        
        return aspect_ratios.get((ratio_w, ratio_h), f"{ratio_w}:{ratio_h}")
    
    def get_settings_summary(self) -> str:
        """Get a formatted summary of current settings"""
        vsync_note = " (VSync Enabled - will override framerate)" if self.settings['vsync'] else ""
        fullscreen_text = "Fullscreen" if self.settings['fullscreen'] else "Windowed"
        aspect_ratio = self.get_aspect_ratio(self.settings['width'], self.settings['height'])
        
        return f"""<b>Current Settings:</b><br>
Resolution: {self.settings['width']}x{self.settings['height']} ({aspect_ratio}) - {fullscreen_text}<br>
Framerate: {self.settings['framerate']} FPS{vsync_note}"""
    
    def load_settings(self):
        """Load settings from file if it exists"""
        settings_file = "game_settings.json"
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r') as f:
                    saved_settings = json.load(f)
                    # Update settings with saved values, keeping defaults for missing keys
                    for key, value in saved_settings.items():
                        if key in self.settings:
                            self.settings[key] = value
                print(f"Loaded settings: {self.settings}")
            except Exception as e:
                print(f"Error loading settings: {e}")
    
    def save_settings(self):
        """Save current settings to file"""
        settings_file = "game_settings.json"
        try:
            with open(settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            print(f"Settings saved: {self.settings}")
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False
    
    def handle_resolution_change(self, selected_text: str):
        """Handle resolution dropdown change"""
        # Parse the resolution text (e.g., "1920 x 1080 (16:9)")
        try:
            parts = selected_text.split()
            width_str = parts[0]
            height_str = parts[2]  # Skip 'x'
            self.settings['width'] = int(width_str)
            self.settings['height'] = int(height_str)
            self.update_settings_display()
        except (ValueError, IndexError):
            print(f"Error parsing resolution: {selected_text}")
    
    def toggle_fullscreen(self):
        """Toggle fullscreen setting"""
        self.settings['fullscreen'] = not self.settings['fullscreen']
        self.fullscreen_button.set_text("ON" if self.settings['fullscreen'] else "OFF")
        self.update_settings_display()
    
    def toggle_vsync(self):
        """Toggle VSync setting"""
        self.settings['vsync'] = not self.settings['vsync']
        self.vsync_button.set_text("ON" if self.settings['vsync'] else "OFF")
        self.update_settings_display()
    
    def update_framerate(self, value: float):
        """Update framerate from slider"""
        framerate = int(value)
        self.settings['framerate'] = framerate
        self.framerate_entry.set_text(str(framerate))
        self.update_settings_display()
    
    def update_framerate_from_text(self, text: str):
        """Update framerate from text input"""
        try:
            framerate = int(text)
            if 1 <= framerate <= 1000:  # Reasonable bounds
                self.settings['framerate'] = framerate
                self.framerate_slider.set_current_value(framerate)
                self.update_settings_display()
        except ValueError:
            # Invalid input, revert to current setting
            self.framerate_entry.set_text(str(self.settings['framerate']))
    
    def update_settings_display(self):
        """Update the settings summary display"""
        settings_text = self.get_settings_summary()
        self.settings_info.html_text = settings_text
        self.settings_info.rebuild()
    
    def launch_game(self):
        """Launch the game with current settings"""
        # Save settings before launching
        self.save_settings()
        
        print(f"Launching game with settings: {self.settings}")
        
        # Close the launcher without calling pygame.quit()
        self.running = False
        
        # Import and launch the game with the settings
        self.start_game_with_settings()
    
    def start_game_with_settings(self):
        """Start the actual game with the configured settings"""
        # Close the launcher display
        pygame.display.quit()
        
        # Modify the constants file or pass settings to the game
        try:
            import constants
            
            # Update constants with our settings
            constants.SCREEN_WIDTH = self.settings['width']
            constants.SCREEN_HEIGHT = self.settings['height']
            constants.TARGET_FPS = self.settings['framerate']
            constants.FULLSCREEN = self.settings['fullscreen']
            constants.VSYNC = self.settings['vsync']
        except ImportError:
            pass  # Constants file not found, continue anyway
        
        # Now import and start the game
        try:
            from game import Game  # Replace with your actual game file name
            
            # Create and run the game with settings
            game = Game(self.settings)
            game.run()
        except ImportError:
            print("Game module not found. Settings have been saved.")
    
    def run(self):
        """Main launcher loop"""
        while self.running:
            time_delta = self.clock.tick(60) / 1000.0
            
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                
                # Handle UI events
                if event.type == pygame.USEREVENT:
                    if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                        if event.ui_element == self.fullscreen_button:
                            self.toggle_fullscreen()
                        elif event.ui_element == self.vsync_button:
                            self.toggle_vsync()
                        elif event.ui_element == self.launch_button:
                            self.launch_game()
                            return  # Exit launcher after launching game
                        elif event.ui_element == self.save_button:
                            if self.save_settings():
                                # Could add a brief "Settings Saved!" message here
                                pass
                        elif event.ui_element == self.exit_button:
                            self.running = False
                    
                    elif event.user_type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
                        if event.ui_element == self.resolution_dropdown:
                            self.handle_resolution_change(event.text)
                    
                    elif event.user_type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
                        if event.ui_element == self.framerate_slider:
                            self.update_framerate(event.value)
                    
                    elif event.user_type == pygame_gui.UI_TEXT_ENTRY_FINISHED:
                        if event.ui_element == self.framerate_entry:
                            self.update_framerate_from_text(event.text)
                
                # Pass events to UI manager
                self.ui_manager.process_events(event)
            
            # Update UI
            self.ui_manager.update(time_delta)
            
            # Draw everything
            self.screen.blit(self.background, (0, 0))
            self.ui_manager.draw_ui(self.screen)
            
            pygame.display.flip()
        
        # Cleanup
        pygame.quit()

# Main entry point
if __name__ == "__main__":
    # Launch the settings launcher first
    launcher = GameLauncher()
    launcher.run()
    
    # If we get here, either the launcher was closed without launching
    # or the game has finished running