from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QComboBox, 
                            QLabel, QFrame, QGroupBox, QDoubleSpinBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import  QColor, QLinearGradient
from .file_dialog import FileDialog
from rendering.terrain_renderer import TerrainRenderer
import numpy as np
from .dam_selection_dialog import DamSelectionDialog

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
        
        # Reset camera button
        self.reset_button = QPushButton("Reset View")
        self.reset_button.clicked.connect(self.reset_camera)
        
        # Dam creation button
        self.dam_button = QPushButton("Create Dam")
        self.dam_button.clicked.connect(self.create_dam)
        
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
        
        # Reset view button
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.reset_button)
        buttons_layout.addWidget(self.dam_button)
        controls_layout.addLayout(buttons_layout)
        
        left_layout.addLayout(controls_layout)
        
        # Add left panel to main layout
        main_layout.addWidget(left_panel, stretch=4)  # Give more space to left panel
        
        # Right side (Statistics)
        right_panel = QFrame()
        right_panel.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
        right_panel.setMaximumWidth(200)
        right_layout = QVBoxLayout(right_panel)
        
        # Statistics header
        stats_header = QLabel("Terrain Statistics")
        stats_header.setStyleSheet("font-weight: bold; font-size: 12px;")
        right_layout.addWidget(stats_header)
        
        # Add color legend
        self.color_legend = ColorLegend()
        right_layout.addWidget(self.color_legend)
        
        # Add isoline controls
        self.isoline_group = QGroupBox("Isoline Settings")
        self.isoline_group.setVisible(False)  # Initially hidden
        isoline_layout = QVBoxLayout()
        
        # Isoline spacing control
        spacing_layout = QHBoxLayout()
        spacing_layout.addWidget(QLabel("Spacing:"))
        self.isoline_spacing = QDoubleSpinBox()
        self.isoline_spacing.setRange(1, 1000)
        self.isoline_spacing.setValue(500)
        self.isoline_spacing.valueChanged.connect(self.update_isoline_spacing)
        spacing_layout.addWidget(self.isoline_spacing)
        isoline_layout.addLayout(spacing_layout)
        
        self.isoline_group.setLayout(isoline_layout)
        right_layout.addWidget(self.isoline_group)
        
        # Statistics content
        self.stats_label = QLabel("No terrain loaded")
        self.stats_label.setWordWrap(True)
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        right_layout.addWidget(self.stats_label)
        right_layout.addStretch()
        
        # Add dam statistics to right panel
        self.dam_stats_group = QGroupBox("Dam Statistics")
        self.dam_stats_group.setVisible(False)  # Initially hidden
        dam_stats_layout = QVBoxLayout()
        
        # Dam height label
        self.dam_height_label = QLabel("Dam Height: N/A")
        dam_stats_layout.addWidget(self.dam_height_label)
        
        self.dam_stats_group.setLayout(dam_stats_layout)
        right_layout.addWidget(self.dam_stats_group)
        
        # Add right panel to main layout
        main_layout.addWidget(right_panel, stretch=1)
        
    def load_terrain(self):
        file_dialog = FileDialog()
        file_path, region = file_dialog.get_terrain_file()
        if file_path:
            self.gl_widget.load_terrain(file_path, region)
            
    def change_scheme(self, scheme):
        self.gl_widget.set_render_scheme(scheme)
        
        # Show/hide isoline controls based on scheme
        self.isoline_group.setVisible("Isolines" in scheme)
        
        # Update color legend with new scheme
        if self.gl_widget.terrain_data is not None:
            show_isolines = "Isolines" in scheme
            use_yellow_red = scheme.startswith("Yellow-Red")
            min_height = np.min(self.gl_widget.terrain_data)
            max_height = np.max(self.gl_widget.terrain_data)
            self.color_legend.set_height_range(min_height, max_height, show_isolines, use_yellow_red)
            
        
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
        )
        self.stats_label.setText(stats) 
        
    def update_isoline_spacing(self, value):
        """Update the isoline spacing in the renderer"""
        self.gl_widget.set_isoline_spacing(value)
        
    def create_dam(self):
        """Open dam selection dialog and create dam"""
        if self.gl_widget.terrain_data is None:
            return
            
        dialog = DamSelectionDialog(self.gl_widget.terrain_data, self)
        if dialog.exec():
            points = dialog.get_dam_points()
            if points and len(points) == 3:
                # First two points are dam ends, third point indicates flood direction
                dam_points = points[:2]
                flood_point = points[2]
                self.gl_widget.create_dam(dam_points, flood_point)
                self.update_dam_statistics()
                
    def update_dam_statistics(self):
        """Update dam statistics display"""
        stats = self.gl_widget.dam_builder.get_dam_stats()
        if stats:
            self.dam_stats_group.setVisible(True)
            self.dam_height_label.setText(f"Dam Height: {stats['height']:.1f} m")
        else:
            self.dam_stats_group.setVisible(False)
            self.dam_height_label.setText("Dam Height: N/A")
        
class ColorLegend(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(250)
        self.setMaximumHeight(250)
        self.min_height = 0
        self.max_height = 1
        self.show_isolines = False
        self.use_yellow_red = False
        
        # Define color schemes
        self.green_gray_colors = {
            'low': QColor(51, 128, 26),
            'high': QColor(204, 204, 204)
        }
        self.yellow_red_colors = {
            'low': QColor(255, 204, 0),
            'high': QColor(204, 0, 0)
        }
        
        
    def set_height_range(self, min_height, max_height, show_isolines=False, use_yellow_red=False):
        self.min_height = min_height
        self.max_height = max_height
        self.show_isolines = show_isolines
        self.use_yellow_red = use_yellow_red
        self.update()
        

            
    def _draw_height_legend(self, painter):
        # Original height legend code
        gradient = QLinearGradient(0, self.height() - 20, 0, 20)
        if self.use_yellow_red:
            gradient.setColorAt(0.0, self.yellow_red_colors['low'])
            gradient.setColorAt(1.0, self.yellow_red_colors['high'])
        else:
            gradient.setColorAt(0.0, self.green_gray_colors['low'])
            gradient.setColorAt(1.0, self.green_gray_colors['high'])
        
        # Draw gradient bar and labels
        bar_width = 30
        x = 10
        y = 20
        height = self.height() - 40
        painter.fillRect(x, y, bar_width, height, gradient)
        
        # Draw labels in white
        painter.setPen(QColor(255, 255, 255))
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)
        
        painter.drawText(bar_width + 15, y + 5, f"{self.max_height:.1f}")
        mid_height = (self.max_height + self.min_height) / 2
        painter.drawText(bar_width + 15, y + height/2 + 5, f"{mid_height:.1f}")
        painter.drawText(bar_width + 15, y + height + 5, f"{self.min_height:.1f}")
        