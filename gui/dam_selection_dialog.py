from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QPushButton, 
                           QLabel, QHBoxLayout, QWidget, QScrollArea)
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QImage
import numpy as np
from scipy.ndimage import zoom

class DamPreviewWidget(QWidget):
    def __init__(self, terrain_data, parent=None):
        super().__init__(parent)
        self.terrain_data = terrain_data
        self.points = []  # 3 points: 2 dam points and flood direction point
        self.background_image = None
        self.setMinimumSize(500, 500)
        
        # Zoom and pan variables
        self.zoom_factor = 1.0
        self.pan_offset = QPointF(0, 0)
        self.last_mouse_pos = None
        self.panning = False
        
    def wheelEvent(self, event):
        """Handle mouse wheel for zooming"""
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        
        # Calculate center of view
        view_center = QPointF(self.width() / 2, self.height() / 2)
        old_scene_center = self.mapToScene(view_center)
        
        # Adjust zoom based on wheel direction
        if event.angleDelta().y() > 0:
            self.zoom_factor *= zoom_in_factor
        else:
            self.zoom_factor *= zoom_out_factor
            
        self.zoom_factor = max(1.0, min(10.0, self.zoom_factor))
        
        # Adjust pan to keep center point
        new_scene_center = QPointF(
            old_scene_center.x() * (self.zoom_factor / (self.zoom_factor / zoom_in_factor)),
            old_scene_center.y() * (self.zoom_factor / (self.zoom_factor / zoom_in_factor))
        )
        
        self.pan_offset -= (new_scene_center - old_scene_center) * self.zoom_factor
        self.update()
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self.panning = True
            self.last_mouse_pos = event.position()
        elif event.button() == Qt.MouseButton.LeftButton:
            if len(self.points) >= 3:
                return
                
            pos = self.mapToScene(event.position())
            point = [pos.x() / self.width(), pos.y() / self.height()]
            self.points.append(point)
            
            # Update status based on points count
            parent = self.parent()
            while parent and not isinstance(parent, DamSelectionDialog):
                parent = parent.parent()
                
            if parent:
                if len(self.points) == 2:
                    parent.status_label.setText("Click to set flood direction")
                elif len(self.points) == 3:
                    parent.accept_button.setEnabled(True)
                    parent.status_label.setText("Ready to create dam")
                else:
                    parent.status_label.setText("Click to set second dam point")
                    
            self.update()
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self.panning = False
            
    def mouseMoveEvent(self, event):
        if self.panning and self.last_mouse_pos:
            delta = event.position() - self.last_mouse_pos
            self.pan_offset += delta
            self.last_mouse_pos = event.position()
            self.update()
            
    def mapToScene(self, pos):
        """Convert screen coordinates to scene coordinates"""
        return QPointF(
            (pos.x() - self.pan_offset.x()) / self.zoom_factor,
            (pos.y() - self.pan_offset.y()) / self.zoom_factor
        )
        
    def paintEvent(self, event):
        painter = QPainter(self)
        
        # Create terrain visualization if not exists
        if self.background_image is None:
            self.create_background_image()
            
        # Apply zoom and pan transformation
        painter.translate(self.pan_offset)
        painter.scale(self.zoom_factor, self.zoom_factor)
        
        # Draw terrain
        if self.background_image:
            painter.drawImage(0, 0, self.background_image)
            
        # Draw points and lines
        if self.points:
            # Draw dam line (first two points)
            painter.setPen(QPen(QColor(255, 0, 0), 2 / self.zoom_factor))
            for i, point in enumerate(self.points[:2]):
                screen_x = point[0] * self.width()
                screen_y = point[1] * self.height()
                painter.drawEllipse(QPointF(screen_x, screen_y), 
                                  5 / self.zoom_factor, 
                                  5 / self.zoom_factor)
                
            if len(self.points) >= 2:
                p1, p2 = self.points[:2]
                painter.drawLine(
                    p1[0] * self.width(),
                    p1[1] * self.height(),
                    p2[0] * self.width(),
                    p2[1] * self.height()
                )
                
            # Draw flood direction point and line
            if len(self.points) == 3:
                painter.setPen(QPen(QColor(0, 0, 255), 2 / self.zoom_factor))
                p3 = self.points[2]
                painter.drawEllipse(QPointF(p3[0] * self.width(), p3[1] * self.height()),
                                  5 / self.zoom_factor,
                                  5 / self.zoom_factor)
                
                # Draw line from dam center to flood point
                center_x = (p1[0] + p2[0]) * self.width() / 2
                center_y = (p1[1] + p2[1]) * self.height() / 2
                painter.drawLine(
                    center_x,
                    center_y,
                    p3[0] * self.width(),
                    p3[1] * self.height()
                )

    def create_background_image(self):
        """Create visualization of the terrain"""
        if self.terrain_data is None:
            return
            
        # Normalize terrain data
        normalized = (self.terrain_data - np.min(self.terrain_data)) / (
            np.max(self.terrain_data) - np.min(self.terrain_data))
        
        # Scale to 0-255 and convert to uint8
        grayscale = (normalized * 255).astype(np.uint8)
        
        # Resize array to match widget size
        scale_y = self.height() / grayscale.shape[0]
        scale_x = self.width() / grayscale.shape[1]
        resized = zoom(grayscale, (scale_y, scale_x), order=0)
        
        # Create RGB image
        rgb = np.stack([resized] * 3, axis=-1)
        
        # Convert to QImage
        height, width = rgb.shape[:2]
        bytes_per_line = 3 * width
        self.background_image = QImage(
            rgb.data.tobytes(),
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_RGB888
        )
        
    def resizeEvent(self, event):
        self.background_image = None
        super().resizeEvent(event)

class DamSelectionDialog(QDialog):
    def __init__(self, terrain_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Dam Location")
        self.setModal(True)
        self.setMinimumSize(800, 800)
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel(
            "1. Click two points to set dam location\n"
            "2. Click a third point to indicate which side will be flooded\n"
            "Use mouse wheel to zoom, middle mouse button to pan"
        )
        layout.addWidget(instructions)
        
        # Status label
        self.status_label = QLabel("Click to set first dam point")
        layout.addWidget(self.status_label)
        
        # Create scroll area for preview
        scroll_area = QScrollArea()
        self.preview = DamPreviewWidget(terrain_data, self)
        scroll_area.setWidget(self.preview)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.accept_button = QPushButton("Create Dam")
        self.accept_button.setEnabled(False)
        self.accept_button.clicked.connect(self.accept)
        
        clear_button = QPushButton("Clear Points")
        clear_button.clicked.connect(self.clear_points)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.accept_button)
        button_layout.addWidget(clear_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
    def clear_points(self):
        self.preview.points = []
        self.accept_button.setEnabled(False)
        self.status_label.setText("Click to set first dam point")
        self.preview.update()
        
    def get_dam_points(self):
        """Return the selected points"""
        return self.preview.points 