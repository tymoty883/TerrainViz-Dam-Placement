from PyQt6.QtGui import QVector3D
import numpy as np
from OpenGL.arrays import vbo
from OpenGL.GL import *
from scipy.ndimage import binary_fill_holes

class DamBuilder:
    def __init__(self):
        self.vertices = None
        self.vbo = None
        self.thickness = 0.005
        self.color = QVector3D(0.0, 0.0, 0.0)  # Black color
        self.water_color = QVector3D(0.2, 0.4, 0.8)  # Blue color for water
        self.height_scale = 0.00003
        
        # Add water mesh attributes
        self.water_vertices = None
        self.water_vbo = None
        self.water_alpha = 0.6  # Water transparency
        self.dam_height = None  # Add dam height attribute

    def find_terrain_height_at(self, terrain_data, x, z, terrain_shape):
        """Find terrain height at given world coordinates"""
        rows, cols = terrain_shape
        
        # Convert from world space [-0.5, 0.5] to terrain space [0, 1]
        x_normalized = x + 0.5
        z_normalized = z + 0.5
        
        # Convert to array indices
        col = int(x_normalized * (cols - 1))
        row = int(z_normalized * (rows - 1))
        
        # Clamp indices to valid range
        col = max(0, min(col, cols - 1))
        row = max(0, min(row, rows - 1))
        
        return terrain_data[row, col]

    def find_terrain_heights_under_dam(self, terrain_data, p1, p2, terrain_shape, samples=20):
        """Sample terrain heights along and around the dam line"""
        heights = []
        
        # Convert to world space
        world_x1 = (p1[0] - 0.5)
        world_z1 = (p1[1] - 0.5)
        world_x2 = (p2[0] - 0.5)
        world_z2 = (p2[1] - 0.5)
        
        # Calculate dam direction and perpendicular
        dam_dir = QVector3D(world_x2 - world_x1, 0, world_z2 - world_z1).normalized()
        dam_perp = QVector3D(-dam_dir.z(), 0, dam_dir.x())
        
        # Sample points along the dam length
        for i in range(samples):
            t = i / (samples - 1)
            center = QVector3D(
                world_x1 + (world_x2 - world_x1) * t,
                0,
                world_z1 + (world_z2 - world_z1) * t
            )
            
            # Sample points across dam width
            for j in range(3):  # Sample at left edge, center, and right edge
                offset = (j - 1) * self.thickness
                sample_point = center + dam_perp * offset
                
                height = self.find_terrain_height_at(
                    terrain_data,
                    sample_point.x(),
                    sample_point.z(),
                    terrain_shape
                )
                heights.append(height)
        
        return min(heights), max(heights)  # Return both min and max heights

    def calculate_flood_area(self, terrain_data, dam_points, flood_point, terrain_shape):
        """Calculate the area that would be flooded by the dam"""
        rows, cols = terrain_shape
        
        # Convert dam points to terrain indices
        x1 = int(dam_points[0][0] * cols)
        y1 = int(dam_points[0][1] * rows)
        x2 = int(dam_points[1][0] * cols)
        y2 = int(dam_points[1][1] * rows)
        flood_x = int(flood_point[0] * cols)
        flood_y = int(flood_point[1] * rows)
        
        # Create a mask for the dam line
        mask = np.zeros((rows, cols), dtype=bool)
        
        # Draw dam line on mask using Bresenham's line algorithm
        def draw_line(x0, y0, x1, y1):
            dx = abs(x1 - x0)
            dy = abs(y1 - y0)
            x, y = x0, y0
            sx = 1 if x0 < x1 else -1
            sy = 1 if y0 < y1 else -1
            err = dx - dy
            
            while True:
                mask[y, x] = True
                if x == x1 and y == y1:
                    break
                e2 = 2 * err
                if e2 > -dy:
                    err -= dy
                    x += sx
                if e2 < dx:
                    err += dx
                    y += sy
        
        # Draw dam line
        draw_line(x1, y1, x2, y2)
        
        # Get dam height based on terrain at dam location
        dam_height = np.max(terrain_data[mask]) * 1.2  # This is the top of the dam
        water_height = dam_height * 0.95  # Set water slightly below dam top
        
        # Create containment mask based on terrain height
        containment_mask = terrain_data < water_height  # Use water height for containment
        
        # Check which side of the dam line the flood point is on
        dam_dir_x = x2 - x1
        dam_dir_y = y2 - y1
        flood_vec_x = flood_x - x1
        flood_vec_y = flood_y - y1
        cross_product = dam_dir_x * flood_vec_y - dam_dir_y * flood_vec_x
        
        # Create side mask
        side_mask = np.zeros((rows, cols), dtype=bool)
        for i in range(rows):
            for j in range(cols):
                point_vec_x = j - x1
                point_vec_y = i - y1
                point_cross = dam_dir_x * point_vec_y - dam_dir_y * point_vec_x
                side_mask[i, j] = (point_cross * cross_product > 0)
        
        # Create initial flood mask
        flood_mask = containment_mask & side_mask
        flood_mask[mask] = False  # Block dam line
        
        # Start flood fill from flood point
        fill_mask = np.zeros_like(flood_mask)
        fill_mask[flood_y, flood_x] = True
        
        # Perform flood fill
        flood_area = np.zeros_like(flood_mask)
        stack = [(flood_y, flood_x)]
        while stack:
            y, x = stack.pop()
            if not flood_area[y, x] and flood_mask[y, x]:
                flood_area[y, x] = True
                # Check neighbors
                for ny, nx in [(y+1,x), (y-1,x), (y,x+1), (y,x-1)]:
                    if (0 <= ny < rows and 0 <= nx < cols and 
                        not flood_area[ny, nx] and flood_mask[ny, nx]):
                        stack.append((ny, nx))
        
        # Create water mesh with proper height based on terrain
        water_vertices = []
        water_indices = []
        vertex_count = 0
        vertex_map = {}  # Map to store vertex indices
        
        # Create vertices for flooded area
        for i in range(rows):
            for j in range(cols):
                if flood_area[i, j]:
                    # Convert to world coordinates
                    x = (j / cols) - 0.5
                    z = (i / rows) - 0.5
                    
                    # Set water height to be slightly below dam top
                    y = water_height * self.height_scale
                    
                    # Store vertex and its index
                    vertex_map[(i,j)] = vertex_count
                    water_vertices.extend([x, y, z])
                    vertex_count += 1
        
        # Create triangles
        for i in range(rows-1):
            for j in range(cols-1):
                if (flood_area[i,j] and flood_area[i+1,j] and 
                    flood_area[i,j+1] and flood_area[i+1,j+1]):
                    # Get vertex indices
                    v1 = vertex_map[(i,j)]
                    v2 = vertex_map[(i+1,j)]
                    v3 = vertex_map[(i,j+1)]
                    v4 = vertex_map[(i+1,j+1)]
                    
                    # Create two triangles
                    water_indices.extend([v1, v2, v3, v3, v2, v4])
        
        # Store water mesh if vertices exist
        if water_vertices:
            self.water_vertices = np.array(water_vertices, dtype=np.float32)
            self.water_indices = np.array(water_indices, dtype=np.uint32)
            self.water_vbo = vbo.VBO(self.water_vertices)
            self.water_ibo = vbo.VBO(self.water_indices, target=GL_ELEMENT_ARRAY_BUFFER)

    def create_dam(self, terrain_data, dam_points, flood_point, terrain_shape):
        """Create a dam mesh from the given points"""
        rows, cols = terrain_shape
        
        # Convert normalized points to terrain coordinates
        p1 = dam_points[0]
        p2 = dam_points[1]
        
        # Convert normalized coordinates to world space
        world_x1 = (p1[0] - 0.5)
        world_z1 = (p1[1] - 0.5)
        world_x2 = (p2[0] - 0.5)
        world_z2 = (p2[1] - 0.5)
        
        # Calculate dam direction and perpendicular
        dam_dir = QVector3D(world_x2 - world_x1, 0, world_z2 - world_z1).normalized()
        dam_perp = QVector3D(-dam_dir.z(), 0, dam_dir.x())
        
        # Calculate the four corners of the dam
        front_left = QVector3D(world_x1, 0, world_z1) + dam_perp * self.thickness
        front_right = QVector3D(world_x2, 0, world_z2) + dam_perp * self.thickness
        back_left = QVector3D(world_x1, 0, world_z1) - dam_perp * self.thickness
        back_right = QVector3D(world_x2, 0, world_z2) - dam_perp * self.thickness
        
        # Get terrain heights at corners and under dam
        min_height, max_height = self.find_terrain_heights_under_dam(
            terrain_data, p1, p2, terrain_shape
        )
        
        # Use minimum height for bottom of dam to ensure closure
        base_height = min_height
        # Set dam height based on maximum terrain height
        dam_height = max_height * 1.2
        
        # Store raw dam height for statistics (before scaling)
        self.dam_height = dam_height
        
        # Scale heights for rendering
        base_height_scaled = base_height * self.height_scale
        dam_height_scaled = dam_height * self.height_scale
        
        # Create vertices for all six faces
        vertices = []
        
        # Front face
        vertices.extend([
            front_left.x(), base_height_scaled, front_left.z(),
            front_right.x(), base_height_scaled, front_right.z(),
            front_left.x(), dam_height_scaled, front_left.z(),
            front_right.x(), dam_height_scaled, front_right.z(),
        ])
        
        # Back face
        vertices.extend([
            back_right.x(), base_height_scaled, back_right.z(),
            back_left.x(), base_height_scaled, back_left.z(),
            back_right.x(), dam_height_scaled, back_right.z(),
            back_left.x(), dam_height_scaled, back_left.z(),
        ])
        
        # Top face
        vertices.extend([
            front_left.x(), dam_height_scaled, front_left.z(),
            front_right.x(), dam_height_scaled, front_right.z(),
            back_left.x(), dam_height_scaled, back_left.z(),
            back_right.x(), dam_height_scaled, back_right.z(),
        ])
        
        # Bottom face - at lowest terrain point
        vertices.extend([
            front_right.x(), base_height_scaled, front_right.z(),
            front_left.x(), base_height_scaled, front_left.z(),
            back_right.x(), base_height_scaled, back_right.z(),
            back_left.x(), base_height_scaled, back_left.z(),
        ])
        
        # Left face
        vertices.extend([
            back_left.x(), base_height_scaled, back_left.z(),
            front_left.x(), base_height_scaled, front_left.z(),
            back_left.x(), dam_height_scaled, back_left.z(),
            front_left.x(), dam_height_scaled, front_left.z(),
        ])
        
        # Right face
        vertices.extend([
            front_right.x(), base_height_scaled, front_right.z(),
            back_right.x(), base_height_scaled, back_right.z(),
            front_right.x(), dam_height_scaled, front_right.z(),
            back_right.x(), dam_height_scaled, back_right.z(),
        ])
        
        # Store vertices and create VBO
        self.vertices = np.array(vertices, dtype=np.float32)
        self.vbo = vbo.VBO(self.vertices)
        
        # Calculate flood area after creating dam
        self.calculate_flood_area(terrain_data, dam_points, flood_point, terrain_shape)

    def render(self, shader_program):
        """Render the dam and water area"""
        # Render dam
        if self.vbo is not None:
            shader_program.use()
            # Use override_color (not override_color_with_alpha) for solid black dam
            shader_program.set_uniform_3f("override_color", 
                                        self.color.x(),
                                        self.color.y(),
                                        self.color.z())
            shader_program.set_uniform_1i("use_override_color", True)
            shader_program.set_uniform_4f("override_color_with_alpha", 0, 0, 0, 0)  # Reset alpha uniform
            
            self.vbo.bind()
            glEnableVertexAttribArray(0)
            glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)
            glDrawArrays(GL_TRIANGLE_STRIP, 0, len(self.vertices) // 3)
            glDisableVertexAttribArray(0)
            self.vbo.unbind()
        
        # Render water area
        if self.water_vbo is not None:
            # Enable transparency for water only
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            
            # Use override_color_with_alpha for transparent blue water
            shader_program.set_uniform_4f("override_color_with_alpha", 
                                        self.water_color.x(),
                                        self.water_color.y(),
                                        self.water_color.z(),
                                        self.water_alpha)
            shader_program.set_uniform_1i("use_override_color", True)
            
            self.water_vbo.bind()
            self.water_ibo.bind()
            glEnableVertexAttribArray(0)
            glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)
            glDrawElements(GL_TRIANGLES, len(self.water_indices), GL_UNSIGNED_INT, None)
            glDisableVertexAttribArray(0)
            self.water_vbo.unbind()
            self.water_ibo.unbind()
            
            glDisable(GL_BLEND)
        
        # Reset shader state
        shader_program.set_uniform_1i("use_override_color", False)
        shader_program.set_uniform_4f("override_color_with_alpha", 0, 0, 0, 0)

    def clear(self):
        """Clear all dam and water data"""
        self.vertices = None
        self.vbo = None
        self.water_vertices = None
        self.water_vbo = None
        self.water_ibo = None
        self.dam_height = None  # Reset dam height

    def get_dam_stats(self):
        """Return dam statistics"""
        if self.dam_height is None:
            return None
            
        # Convert from world scale to original terrain units (no height_scale division)
        return {
            'height': self.dam_height  # Return raw height value
        } 