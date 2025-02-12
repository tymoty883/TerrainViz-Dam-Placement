from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QDoubleSpinBox, QGroupBox, QWidget)
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QImage
import numpy as np
from osgeo import gdal

class TerrainPreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 400)
        self.terrain_data = None
        self.selection_rect = QRectF(0.25, 0.25, 0.5, 0.5)  # Default selection
        self.dragging = False
        self.resize_handle = None
        self.handle_size = 10
        self.last_pos = None
        self.drag_mode = None
        self.background_image = None  # Cache for the terrain image
        
    def set_terrain_data(self, dataset):
        """Set the terrain data and compute preview"""
        band = dataset.GetRasterBand(1)
        
        # Read a downsampled version for preview
        preview_width = 400
        preview_height = 400
        
        self.terrain_data = band.ReadAsArray(
            buf_xsize=preview_width,
            buf_ysize=preview_height
        )
        
        self.full_width = dataset.RasterXSize
        self.full_height = dataset.RasterYSize
        self.geo_transform = dataset.GetGeoTransform()
        
        # Create cached background image
        self.create_background_image()
        self.update()
        
    def create_background_image(self):
        """Create cached image of the terrain"""
        if self.terrain_data is None:
            return
            
        self.background_image = QImage(self.width(), self.height(), QImage.Format.Format_RGB32)
        self.background_image.fill(Qt.GlobalColor.black)
        
        painter = QPainter(self.background_image)
        
        # Draw terrain preview
        normalized = (self.terrain_data - np.min(self.terrain_data)) / (np.max(self.terrain_data) - np.min(self.terrain_data))
        height, width = normalized.shape
        
        for y in range(height):
            for x in range(width):
                value = int(normalized[y, x] * 255)
                painter.setPen(QColor(value, value, value))
                painter.drawPoint(x * self.width() / width, y * self.height() / height)
                
        painter.end()
        
    def resizeEvent(self, event):
        """Recreate background image when widget is resized"""
        super().resizeEvent(event)
        if self.terrain_data is not None:
            self.create_background_image()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        
        # Draw cached background
        if self.background_image:
            painter.drawImage(0, 0, self.background_image)
        
        if self.terrain_data is None:
            return
            
        # Draw selection rectangle
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(255, 0, 0), 2))
        rect = QRectF(
            self.selection_rect.x() * self.width(),
            self.selection_rect.y() * self.height(),
            self.selection_rect.width() * self.width(),
            self.selection_rect.height() * self.height()
        )
        painter.drawRect(rect)
        
        # Draw resize handles
        painter.setBrush(QColor(255, 0, 0))
        for handle in self.get_handle_rects():
            painter.drawRect(handle)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            normalized_pos = QPointF(pos.x() / self.width(), pos.y() / self.height())
            
            # Check if clicking on a handle
            handle_idx = self.get_handle_at(pos)
            if handle_idx is not None:
                self.drag_mode = 'resize'
                self.resize_handle = handle_idx
            # Check if clicking inside rectangle
            elif self.selection_rect.contains(normalized_pos):
                self.drag_mode = 'move'
            else:
                self.drag_mode = None
                
            self.last_pos = normalized_pos
            self.dragging = True
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.drag_mode = None
            self.resize_handle = None
            # Update coordinate inputs when done dragging
            if isinstance(self.parent(), QDialog):
                self.parent().update_coordinate_inputs()
            
    def mouseMoveEvent(self, event):
        if not self.dragging or not self.last_pos:
            return
            
        pos = event.position()
        normalized_pos = QPointF(pos.x() / self.width(), pos.y() / self.height())
        
        # Calculate movement delta
        delta = normalized_pos - self.last_pos
        
        if self.drag_mode == 'move':
            # Move the entire rectangle
            new_rect = QRectF(
                self.selection_rect.x() + delta.x(),
                self.selection_rect.y() + delta.y(),
                self.selection_rect.width(),
                self.selection_rect.height()
            )
            # Ensure rectangle stays within bounds
            if new_rect.left() >= 0 and new_rect.right() <= 1 and \
               new_rect.top() >= 0 and new_rect.bottom() <= 1:
                self.selection_rect = new_rect
                
        elif self.drag_mode == 'resize':
            # Resize based on which handle is being dragged
            new_rect = QRectF(self.selection_rect)
            if self.resize_handle == 0:  # Top-left
                new_rect.setLeft(min(new_rect.right() - 0.1, new_rect.left() + delta.x()))
                new_rect.setTop(min(new_rect.bottom() - 0.1, new_rect.top() + delta.y()))
            elif self.resize_handle == 1:  # Top-right
                new_rect.setRight(max(new_rect.left() + 0.1, new_rect.right() + delta.x()))
                new_rect.setTop(min(new_rect.bottom() - 0.1, new_rect.top() + delta.y()))
            elif self.resize_handle == 2:  # Bottom-left
                new_rect.setLeft(min(new_rect.right() - 0.1, new_rect.left() + delta.x()))
                new_rect.setBottom(max(new_rect.top() + 0.1, new_rect.bottom() + delta.y()))
            elif self.resize_handle == 3:  # Bottom-right
                new_rect.setRight(max(new_rect.left() + 0.1, new_rect.right() + delta.x()))
                new_rect.setBottom(max(new_rect.top() + 0.1, new_rect.bottom() + delta.y()))
                
            # Ensure rectangle stays within bounds and maintains minimum size
            if new_rect.left() >= 0 and new_rect.right() <= 1 and \
               new_rect.top() >= 0 and new_rect.bottom() <= 1 and \
               new_rect.width() >= 0.1 and new_rect.height() >= 0.1:
                self.selection_rect = new_rect
        
        self.last_pos = normalized_pos
        self.update()
        
    def get_handle_at(self, pos):
        """Return the index of the handle at the given position, or None"""
        normalized_pos = QPointF(pos.x() / self.width(), pos.y() / self.height())
        handles = self.get_handle_rects()
        
        for i, handle in enumerate(handles):
            if handle.contains(pos):
                return i
        return None
        
    def get_handle_rects(self):
        """Get the rectangles for the resize handles"""
        rect = QRectF(
            self.selection_rect.x() * self.width(),
            self.selection_rect.y() * self.height(),
            self.selection_rect.width() * self.width(),
            self.selection_rect.height() * self.height()
        )
        
        size = self.handle_size
        return [
            QRectF(rect.left() - size/2, rect.top() - size/2, size, size),        # Top-left
            QRectF(rect.right() - size/2, rect.top() - size/2, size, size),       # Top-right
            QRectF(rect.left() - size/2, rect.bottom() - size/2, size, size),     # Bottom-left
            QRectF(rect.right() - size/2, rect.bottom() - size/2, size, size)     # Bottom-right
        ]
        
    def get_selected_region(self):
        """Get the selected region in dataset coordinates"""
        if self.terrain_data is None:
            return None
            
        x_min = int(self.selection_rect.x() * self.full_width)
        y_min = int(self.selection_rect.y() * self.full_height)
        width = int(self.selection_rect.width() * self.full_width)
        height = int(self.selection_rect.height() * self.full_height)
        
        return (x_min, y_min, width, height)
        
    def get_selected_coordinates(self):
        """Get the selected region in world coordinates"""
        if self.terrain_data is None:
            return None
            
        region = self.get_selected_region()
        x_min = self.geo_transform[0] + region[0] * self.geo_transform[1]
        y_max = self.geo_transform[3] + region[1] * self.geo_transform[5]
        x_max = x_min + region[2] * self.geo_transform[1]
        y_min = y_max + region[3] * self.geo_transform[5]
        
        return (x_min, x_max, y_min, y_max)

class RegionSelectorDialog(QDialog):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Region of Interest")
        self.setModal(True)
        
        # Load dataset
        self.dataset = gdal.Open(file_path)
        if self.dataset is None:
            raise ValueError("Could not open terrain file")
            
        # Create layout
        layout = QVBoxLayout(self)
        
        # Preview widget
        self.preview = TerrainPreviewWidget()
        self.preview.set_terrain_data(self.dataset)
        layout.addWidget(self.preview)
        
        # Coordinate inputs
        coord_group = QGroupBox("Coordinates")
        coord_layout = QVBoxLayout()
        
        # Add coordinate spinboxes
        self.coord_inputs = {}
        for coord in ['x_min', 'x_max', 'y_min', 'y_max']:
            hlayout = QHBoxLayout()
            hlayout.addWidget(QLabel(f"{coord.replace('_', ' ').title()}:"))
            spinbox = QDoubleSpinBox()
            spinbox.setDecimals(6)
            spinbox.setRange(-180, 180)
            self.coord_inputs[coord] = spinbox
            hlayout.addWidget(spinbox)
            coord_layout.addLayout(hlayout)
            
        coord_group.setLayout(coord_layout)
        layout.addWidget(coord_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        # Update coordinate inputs with initial selection
        self.update_coordinate_inputs()
        
    def update_coordinate_inputs(self):
        """Update coordinate inputs based on preview selection"""
        coords = self.preview.get_selected_coordinates()
        if coords:
            self.coord_inputs['x_min'].setValue(coords[0])
            self.coord_inputs['x_max'].setValue(coords[1])
            self.coord_inputs['y_min'].setValue(coords[2])
            self.coord_inputs['y_max'].setValue(coords[3])
            
    def get_selected_region(self):
        """Get the selected region in dataset coordinates"""
        return self.preview.get_selected_region() 