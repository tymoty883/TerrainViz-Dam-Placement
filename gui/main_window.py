from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QComboBox, 
                           QSlider, QLabel, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor, QPainter, QLinearGradient, QPen, QPolygonF
from PyQt6.QtCore import QPointF
from .file_dialog import FileDialog
from rendering.terrain_renderer import TerrainRenderer
import numpy as np

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Terrain Visualizer")
        self.setMinimumSize(1000, 600)
        
        # Initialize all widgets
        # File selection
        self.load_button = QPushButton("Load Terrain")
        self.load_button.clicked.connect(self.load_terrain)
        
        # Rendering scheme
        self.scheme_combo = QComboBox()
        self.scheme_combo.addItems(["Green-Gray", "Yellow-Red", "Green-Gray + Isolines", "Yellow-Red + Isolines"])
        self.scheme_combo.currentTextChanged.connect(self.change_scheme)
        
        # Detail level slider
        self.detail_slider = QSlider(Qt.Orientation.Horizontal)
        self.detail_slider.setMinimum(1)
        self.detail_slider.setMaximum(100)
        self.detail_slider.setValue(50)
        self.detail_slider.valueChanged.connect(self.change_detail)
        
        # Reset camera button
        self.reset_button = QPushButton("Reset View")
        self.reset_button.clicked.connect(self.reset_camera)
        
        # Dam controls
        self.dam_button = QPushButton("Create Dam")
        self.dam_button.setCheckable(True)
        self.dam_button.clicked.connect(self.toggle_dam_mode)
        
        self.finish_dam_button = QPushButton("Finish Dam")
        self.finish_dam_button.setEnabled(False)
        self.finish_dam_button.clicked.connect(self.finish_dam)
        
        self.clear_dams_button = QPushButton("Clear Dams")
        self.clear_dams_button.clicked.connect(self.clear_dams)
        self.clear_dams_button.setEnabled(False)
        
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # Left side (OpenGL and controls)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Create OpenGL widget
        self.gl_widget = TerrainRenderer()
        left_layout.addWidget(self.gl_widget)
        
        # Controls panel - change to VBoxLayout for vertical arrangement
        controls_layout = QVBoxLayout()
        
        # Top controls (file and render scheme) in horizontal layout
        top_controls = QHBoxLayout()
        top_controls.addWidget(self.load_button)
        top_controls.addWidget(QLabel("Render Scheme:"))
        top_controls.addWidget(self.scheme_combo)
        controls_layout.addLayout(top_controls)
        
        # Detail level slider in its own horizontal layout
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("Detail Level:"))
        slider_layout.addWidget(self.detail_slider)
        controls_layout.addLayout(slider_layout)
        
        # Buttons in horizontal layout
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.reset_button)
        buttons_layout.addWidget(self.dam_button)
        buttons_layout.addWidget(self.finish_dam_button)
        buttons_layout.addWidget(self.clear_dams_button)
        controls_layout.addLayout(buttons_layout)
        
        left_layout.addLayout(controls_layout)
        
        # Add left panel to main layout
        main_layout.addWidget(left_panel, stretch=4)  # Give more space to left panel
        
        # Right side (Statistics)
        right_panel = QFrame()
        right_panel.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
        right_panel.setMaximumWidth(200)  # Limit width of statistics panel
        right_layout = QVBoxLayout(right_panel)
        
        # Statistics header
        stats_header = QLabel("Terrain Statistics")
        stats_header.setStyleSheet("font-weight: bold; font-size: 12px;")
        right_layout.addWidget(stats_header)
        
        # Add color legend
        self.color_legend = ColorLegend()
        right_layout.addWidget(self.color_legend)
        
        # Statistics content (move this after the legend)
        self.stats_label = QLabel("No terrain loaded")
        self.stats_label.setWordWrap(True)
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        right_layout.addWidget(self.stats_label)
        right_layout.addStretch()
        
        # Add right panel to main layout
        main_layout.addWidget(right_panel, stretch=1)  # Give less space to right panel
        
    def load_terrain(self):
        file_dialog = FileDialog()
        if file_path := file_dialog.get_terrain_file():
            self.gl_widget.load_terrain(file_path)
            
    def change_scheme(self, scheme):
        self.gl_widget.set_render_scheme(scheme)
        
        # Update color legend with new scheme
        if self.gl_widget.terrain_data is not None:
            show_isolines = "Isolines" in scheme
            use_yellow_red = scheme.startswith("Yellow-Red")
            min_height = np.min(self.gl_widget.terrain_data)
            max_height = np.max(self.gl_widget.terrain_data)
            self.color_legend.set_height_range(min_height, max_height, show_isolines, use_yellow_red)
        
    def change_detail(self, value):
        self.gl_widget.set_detail_level(value)
        
    def reset_camera(self):
        self.gl_widget.reset_camera() 
        
    def update_statistics(self, terrain_data):
        """Update the statistics display"""
        if terrain_data is None:
            self.stats_label.setText("No terrain loaded")
            self.color_legend.set_height_range(0, 1, False, False)
            return
        
        min_height = np.min(terrain_data)
        max_height = np.max(terrain_data)
        rows, cols = terrain_data.shape
        
        # Update color legend with scheme and isoline state
        current_scheme = self.scheme_combo.currentText()
        show_isolines = "Isolines" in current_scheme
        use_yellow_red = current_scheme.startswith("Yellow-Red")
        self.color_legend.set_height_range(min_height, max_height, show_isolines, use_yellow_red)
        
        stats = (
            f"Resolution:\n{cols} × {rows}\n\n"
            f"Height Range:\n"
            f"Min: {min_height:.1f}\n"
            f"Max: {max_height:.1f}\n\n"
            f"Detail Level:\n{self.gl_widget.detail_level}%"
        )
        self.stats_label.setText(stats) 
        
    def toggle_dam_mode(self, checked):
        self.gl_widget.set_dam_mode(checked)
        self.finish_dam_button.setEnabled(checked)
        
        if checked:
            # Update stats to show dam creation instructions
            current_stats = self.stats_label.text()
            self.stats_label.setText(
                "Dam Creation Mode\n\n"
                "Click on the terrain to add dam points.\n"
                "Click 'Finish Dam' when done.\n\n"
                "-------------------\n" + current_stats
            )
        else:
            # Restore normal stats display
            if self.gl_widget.terrain_data is not None:
                self.update_statistics(self.gl_widget.terrain_data)
        
    def finish_dam(self):
        """Complete the dam creation process"""
        self.dam_button.setChecked(False)
        self.finish_dam_button.setEnabled(False)
        self.gl_widget.set_dam_mode(False)
        self.clear_dams_button.setEnabled(True)
        
        # Restore normal stats display
        if self.gl_widget.terrain_data is not None:
            self.update_statistics(self.gl_widget.terrain_data)
            
    def clear_dams(self):
        """Clear all dams and points"""
        self.gl_widget.clear_dams()
        self.clear_dams_button.setEnabled(False)

class ColorLegend(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(200)
        self.setMaximumHeight(200)
        self.min_height = 0
        self.max_height = 1
        self.show_isolines = False  # Keep this for interface consistency
        self.use_yellow_red = False
        
        # Define color schemes
        self.green_gray_colors = {
            'low': QColor(51, 128, 26),    # Dark green (0.2, 0.5, 0.1)
            'high': QColor(204, 204, 204)  # Light gray (0.8, 0.8, 0.8)
        }
        self.yellow_red_colors = {
            'low': QColor(255, 204, 0),    # Yellow (1.0, 0.8, 0.0)
            'high': QColor(204, 0, 0)      # Red (0.8, 0.0, 0.0)
        }
        
    def set_height_range(self, min_height, max_height, show_isolines=False, use_yellow_red=False):
        self.min_height = min_height
        self.max_height = max_height
        self.show_isolines = show_isolines
        self.use_yellow_red = use_yellow_red
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Create gradient based on color scheme
        gradient = QLinearGradient(0, self.height() - 20, 0, 20)
        if self.use_yellow_red:
            gradient.setColorAt(0.0, self.yellow_red_colors['low'])
            gradient.setColorAt(1.0, self.yellow_red_colors['high'])
        else:
            gradient.setColorAt(0.0, self.green_gray_colors['low'])
            gradient.setColorAt(1.0, self.green_gray_colors['high'])
        
        # Draw gradient bar
        bar_width = 30
        x = 10
        y = 20
        height = self.height() - 40
        painter.fillRect(x, y, bar_width, height, gradient)
        
        # Draw height labels in white
        painter.setPen(QColor(255, 255, 255))  # Set text color to white
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)
        
        # Max height label
        painter.drawText(bar_width + 15, y + 5, 
                        f"{self.max_height:.1f}")
        
        # Middle height label
        mid_height = (self.max_height + self.min_height) / 2
        painter.drawText(bar_width + 15, y + height/2 + 5, 
                        f"{mid_height:.1f}")
        
        # Min height label
        painter.drawText(bar_width + 15, y + height + 5, 
                        f"{self.min_height:.1f}") 