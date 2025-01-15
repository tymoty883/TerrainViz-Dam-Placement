import numpy as np
from PyQt6.QtGui import QVector3D

class DamBuilder:
    def __init__(self):
        self.points = []  # List of 3D points defining the dam
        self.height = 0.0  # Height of the dam
        self.width = 2.0   # Width of the dam wall
        
    def add_point(self, world_pos):
        """Add a point to the dam path"""
        self.points.append(world_pos)
        
    def clear_points(self):
        """Clear all dam points"""
        self.points = []
        
    def set_height(self, height):
        """Set the height of the dam"""
        self.height = height
        
    def generate_dam_mesh(self):
        """Generate dam mesh vertices and indices"""
        if len(self.points) < 2:
            return None, None
            
        vertices = []
        indices = []
        
        # Generate vertices for dam walls
        for i in range(len(self.points) - 1):
            p1 = self.points[i]
            p2 = self.points[i + 1]
            
            # Calculate perpendicular vector for width
            direction = (p2 - p1).normalized()
            perpendicular = QVector3D.crossProduct(direction, QVector3D(0, 1, 0))
            perpendicular *= self.width / 2
            
            # Create vertices for this segment
            v1 = p1 + perpendicular
            v2 = p1 - perpendicular
            v3 = p2 + perpendicular
            v4 = p2 - perpendicular
            
            # Add vertices for both sides of the wall
            base_idx = len(vertices) // 3
            vertices.extend([
                v1.x(), p1.y(), v1.z(),  # Bottom front
                v2.x(), p1.y(), v2.z(),  # Bottom back
                v1.x(), p1.y() + self.height, v1.z(),  # Top front
                v2.x(), p1.y() + self.height, v2.z(),  # Top back
                v3.x(), p2.y(), v3.z(),  # Bottom front next
                v4.x(), p2.y(), v4.z(),  # Bottom back next
                v3.x(), p2.y() + self.height, v3.z(),  # Top front next
                v4.x(), p2.y() + self.height, v4.z(),  # Top back next
            ])
            
            # Add indices for triangles
            indices.extend([
                base_idx + 0, base_idx + 2, base_idx + 4,  # Front face
                base_idx + 2, base_idx + 6, base_idx + 4,
                base_idx + 1, base_idx + 5, base_idx + 3,  # Back face
                base_idx + 3, base_idx + 5, base_idx + 7,
                base_idx + 2, base_idx + 3, base_idx + 6,  # Top face
                base_idx + 3, base_idx + 7, base_idx + 6,
                base_idx + 0, base_idx + 4, base_idx + 1,  # Bottom face
                base_idx + 1, base_idx + 4, base_idx + 5,
            ])
            
        return np.array(vertices, dtype=np.float32), np.array(indices, dtype=np.uint32) 