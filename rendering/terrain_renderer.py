from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QVector3D, QPainter, QColor, QFont
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
from .camera import Camera
from utils.terrain_loader import TerrainLoader
from utils.terrain_processor import TerrainProcessor
from OpenGL.arrays import vbo
from .shaders import ShaderProgram
from PyQt6.QtWidgets import QMainWindow
import math
from .dam_builder import DamBuilder

class TerrainRenderer(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.camera = Camera()
        self.terrain_data = None
        self.render_scheme = "Color Height"
        self.detail_level = 100
        self.vertex_vbo = None
        self.index_vbo = None
        self.shader_program = None
        
        # Mouse tracking for camera control
        self.setMouseTracking(True)
        self.last_pos = None
        self.left_mouse_pressed = False   # Track left button for panning
        self.right_mouse_pressed = False  # Track right button for rotation
        self.isoline_spacing = 500.0
        
        # Replace dam attributes with DamBuilder
        self.dam_builder = DamBuilder()
        
    def initializeGL(self):
        glClearColor(0.5, 0.7, 1.0, 1.0)  # Sky blue background
        glEnable(GL_DEPTH_TEST)
        
        # Initialize shaders
        self.init_shaders()

    def init_shaders(self):
        self.shader_program = ShaderProgram()
        
        vertex_shader = """
        #version 330
        layout(location = 0) in vec3 position;
        
        uniform mat4 model;
        uniform mat4 view;
        uniform mat4 projection;
        
        out float raw_height;
        out vec2 texCoord;
        
        void main() {
            gl_Position = projection * view * model * vec4(position, 1.0);
            raw_height = position.y / 0.000025;
            texCoord = vec2(
                (position.x + 0.5),
                (position.z + 0.5)
            );
        }
        """
        
        fragment_shader = """
        #version 330
        in float raw_height;
        in vec2 texCoord;
        out vec4 fragColor;
        
        uniform float min_height;
        uniform float max_height;
        uniform bool show_isolines;
        uniform int color_scheme;
        uniform float isoline_spacing;
        uniform vec3 override_color;
        uniform vec4 override_color_with_alpha;  // Add alpha version
        uniform bool use_override_color;
        
        vec3 getColorForScheme(float h) {
            if (color_scheme == 0) {
                vec3 lowColor = vec3(51.0/255.0, 128.0/255.0, 26.0/255.0);
                vec3 highColor = vec3(204.0/255.0, 204.0/255.0, 204.0/255.0);
                return mix(lowColor, highColor, h);
            } else {
                vec3 lowColor = vec3(1.0, 204.0/255.0, 0.0);
                vec3 highColor = vec3(204.0/255.0, 0.0, 0.0);
                return mix(lowColor, highColor, h);
            }
        }
        
        void main() {
            if (use_override_color) {
                if (override_color_with_alpha.a > 0.0) {
                    fragColor = override_color_with_alpha;  // Use version with alpha
                } else {
                    fragColor = vec4(override_color, 1.0);  // Use opaque version
                }
                return;
            }
            
            float h = (raw_height - min_height) / (max_height - min_height);
            h = clamp(h, 0.0, 1.0);
            vec3 color = getColorForScheme(h);
            
            if (show_isolines) {
                float normalized_height = raw_height / isoline_spacing;
                float frac = fract(normalized_height);
                float line_width = 0.03;
                
                if (frac < line_width || frac > (1.0 - line_width)) {
                    color = vec3(0.0);
                }
            }
            
            fragColor = vec4(color, 1.0);
        }
        """
        
        self.shader_program.add_shader(GL_VERTEX_SHADER, vertex_shader)
        self.shader_program.add_shader(GL_FRAGMENT_SHADER, fragment_shader)
        self.shader_program.link()

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        self.camera.set_aspect_ratio(w / h)
        
    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        if self.terrain_data is not None:
            self.render_terrain()

    def generate_terrain_mesh(self):
        if self.terrain_data is None:
            return
            
        rows, cols = self.terrain_data.shape
        
        # Calculate decimation factor based on detail level
        # Higher numbers mean more decimation (fewer vertices)
        decimation = max(1, int((100 - self.detail_level) / 10))
        
        # Use fewer vertices based on decimation
        used_rows = max(50, rows // decimation)  # Ensure minimum resolution
        used_cols = max(50, cols // decimation)
        
        # Sample terrain data
        row_indices = np.linspace(0, rows-1, used_rows, dtype=int)
        col_indices = np.linspace(0, cols-1, used_cols, dtype=int)
        sampled_terrain = self.terrain_data[row_indices][:, col_indices]
        
        vertices = []
        indices = []
        
        # Calculate terrain scale and center
        height_scale = 0.00003  # Scale down height values
        
        # Calculate scale factors to maintain aspect ratio
        aspect_ratio = cols / rows
        if aspect_ratio >= 1:
            scale_x = 1.0
            scale_z = 1.0 / aspect_ratio
        else:
            scale_x = aspect_ratio
            scale_z = 1.0
            
        # Generate vertices using NumPy operations
        x_coords = np.linspace(-scale_x/2, scale_x/2, used_cols)
        z_coords = np.linspace(-scale_z/2, scale_z/2, used_rows)
        X, Z = np.meshgrid(x_coords, z_coords)
        Y = sampled_terrain * height_scale
        
        vertices = np.column_stack((X.flatten(), Y.flatten(), Z.flatten()))
        
        # Generate indices for triangle strips
        indices = []
        for i in range(used_rows - 1):
            row1 = i * used_cols
            row2 = (i + 1) * used_cols
            for j in range(used_cols):
                indices.extend([row1 + j, row2 + j])
            # Add degenerate triangles if not at the end
            if i < used_rows - 2:
                indices.extend([row2 + used_cols - 1, row2])
        
        # Create VBOs
        self.vertex_vbo = vbo.VBO(vertices.astype(np.float32))
        self.index_vbo = vbo.VBO(np.array(indices, dtype=np.uint32),
                                target=GL_ELEMENT_ARRAY_BUFFER)

    def render_terrain(self):
        if self.terrain_data is None or self.vertex_vbo is None:
            return
            
        self.shader_program.use()
        
        # Set common uniforms
        model = np.identity(4, dtype=np.float32)
        self.shader_program.set_uniform_matrix4fv("model", model)
        self.shader_program.set_uniform_matrix4fv("view", self.camera.get_view_matrix())
        self.shader_program.set_uniform_matrix4fv("projection", self.camera.get_projection_matrix())
        
        # Disable face culling for terrain
        glDisable(GL_CULL_FACE)
        
        # Set height range uniforms using original height values (not scaled)
        min_height = np.min(self.terrain_data)
        max_height = np.max(self.terrain_data)
        self.shader_program.set_uniform_1f("min_height", min_height)
        self.shader_program.set_uniform_1f("max_height", max_height)
        
        # Set color scheme and isolines flags based on render scheme
        show_isolines = "Isolines" in self.render_scheme
        use_yellow_red = self.render_scheme.startswith("Yellow-Red")
        
        self.shader_program.set_uniform_1i("show_isolines", show_isolines)
        self.shader_program.set_uniform_1i("color_scheme", 1 if use_yellow_red else 0)
        self.shader_program.set_uniform_1f("isoline_spacing", self.isoline_spacing)
        
        # Enable vertex attributes
        self.vertex_vbo.bind()
        self.index_vbo.bind()
        
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)
        
        # Draw terrain
        glDrawElements(GL_TRIANGLE_STRIP, self.index_vbo.size, GL_UNSIGNED_INT, None)
        
        # Render dam if exists
        self.dam_builder.render(self.shader_program)
        
        # Cleanup
        glDisableVertexAttribArray(0)
        self.vertex_vbo.unbind()
        self.index_vbo.unbind()

    def load_terrain(self, file_path, region=None):
        try:
            loader = TerrainLoader()
            processor = TerrainProcessor()
            
            # Load and store original data
            self.original_terrain_data = loader.load(file_path, region)
            
            # Process with current detail level
            self.terrain_data = processor.process(self.original_terrain_data, self.detail_level)
            
            # Generate the mesh after loading new terrain data
            self.generate_terrain_mesh()
            
            # Update statistics in the main window
            parent = self.parent()
            while parent is not None:
                if isinstance(parent, QMainWindow):
                    parent.update_statistics(self.terrain_data)
                    break
                parent = parent.parent()
            
            self.update()
            
        except Exception as e:
            print(f"Error loading terrain: {str(e)}")
            
    def set_render_scheme(self, scheme):
        self.render_scheme = scheme
        self.update()
        
            
    def reset_camera(self):
        self.camera.reset()
        self.update() 

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.left_mouse_pressed = True
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_mouse_pressed = True
        self.last_pos = event.position()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.left_mouse_pressed = False
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_mouse_pressed = False

    def mouseMoveEvent(self, event):
        if not (self.left_mouse_pressed or self.right_mouse_pressed):
            return
        
        current_pos = event.position()
        dx = current_pos.x() - self.last_pos.x()
        dy = self.last_pos.y() - current_pos.y()
        self.last_pos = current_pos
        
        if self.left_mouse_pressed:
            self.camera.process_mouse_pan(dx, dy)
        elif self.right_mouse_pressed:
            self.camera.process_mouse_movement(dx, dy)
        
        self.update()

    def wheelEvent(self, event):
        self.camera.process_mouse_scroll(event.angleDelta().y())
        self.update()

    def screen_to_world(self, x, y):
        """Convert screen coordinates to world coordinates on terrain"""
        if self.terrain_data is None:
            return None
            
        # Get normalized device coordinates
        viewport = glGetIntegerv(GL_VIEWPORT)
        winX = float(x)
        winY = float(viewport[3] - y)
        winZ = glReadPixels(int(x), int(winY), 1, 1, GL_DEPTH_COMPONENT, GL_FLOAT)[0][0]
        
        # Unproject point
        model = np.identity(4, dtype=np.float64)
        projection = np.array(self.camera.get_projection_matrix(), dtype=np.float64).reshape(4, 4)
        view = np.array(self.camera.get_view_matrix(), dtype=np.float64).reshape(4, 4)
        
        # Combine matrices for unprojection
        modelview = np.dot(view, model)
        
        try:
            world_pos = gluUnProject(
                winX, winY, winZ,
                modelview.flatten(),
                projection.flatten(),
                viewport
            )
            return QVector3D(*world_pos)
        except Exception as e:
            print(f"Error in screen_to_world: {str(e)}")
            return None

    def create_dam(self, dam_points, flood_point):
        """Create a dam from the given points and flood direction"""
        if self.terrain_data is None:
            return
            
        self.dam_builder.create_dam(
            self.terrain_data,
            dam_points,
            flood_point,
            self.terrain_data.shape
        )
        self.update()

    def clear_dam(self):
        """Clear the dam"""
        self.dam_builder.clear()
        
        # Update statistics in main window
        parent = self.parent()
        while parent is not None:
            if isinstance(parent, QMainWindow):
                parent.update_dam_statistics()
                break
            parent = parent.parent()
            
        self.update()
