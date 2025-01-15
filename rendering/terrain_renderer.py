from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QVector3D
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
from .camera import Camera
from utils.terrain_loader import TerrainLoader
from utils.terrain_processor import TerrainProcessor
from OpenGL.arrays import vbo
from .shaders import ShaderProgram
from PyQt6.QtWidgets import QMainWindow
from .dam_builder import DamBuilder

class TerrainRenderer(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.camera = Camera()
        self.terrain_data = None
        self.render_scheme = "Color Height"
        self.detail_level = 50
        self.vertex_vbo = None
        self.index_vbo = None
        self.shader_program = None
        
        # Mouse tracking for camera control
        self.setMouseTracking(True)
        self.last_pos = None
        self.left_mouse_pressed = False   # Track left button for panning
        self.right_mouse_pressed = False  # Track right button for rotation
        self.dam_mode = False
        self.dam_builder = DamBuilder()
        self.dam_vbo = None
        self.dam_ibo = None

    def initializeGL(self):
        glClearColor(0.5, 0.7, 1.0, 1.0)  # Sky blue background
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)
        
        # Initialize shaders
        self.init_shaders()
        self.init_dam_shader()
        
    def init_shaders(self):
        self.shader_program = ShaderProgram()
        
        # Vertex shader
        vertex_shader = """
        #version 330
        layout(location = 0) in vec3 position;
        
        uniform mat4 model;
        uniform mat4 view;
        uniform mat4 projection;
        
        out float raw_height;
        
        void main() {
            gl_Position = projection * view * model * vec4(position, 1.0);
            raw_height = position.y / 0.005;  // Convert back to original height
        }
        """
        
        # Fragment shader with isolines
        fragment_shader = """
        #version 330
        in float raw_height;
        out vec4 fragColor;
        
        uniform float min_height;
        uniform float max_height;
        uniform bool show_isolines;
        uniform int color_scheme;  // 0: Green-Gray, 1: Yellow-Red
        
        vec3 getColorForScheme(float h) {
            if (color_scheme == 0) {
                vec3 lowColor = vec3(51.0/255.0, 128.0/255.0, 26.0/255.0);   // Dark green
                vec3 highColor = vec3(204.0/255.0, 204.0/255.0, 204.0/255.0); // Light gray
                return mix(lowColor, highColor, h);
            } else {
                vec3 lowColor = vec3(1.0, 204.0/255.0, 0.0);                  // Yellow
                vec3 highColor = vec3(204.0/255.0, 0.0, 0.0);                 // Red
                return mix(lowColor, highColor, h);
            }
        }
        
        void main() {
            // Normalize height for color gradient
            float h = (raw_height - min_height) / (max_height - min_height);
            h = clamp(h, 0.0, 1.0);
            vec3 color = getColorForScheme(h);
            
            if (show_isolines) {
                // Create isolines every 10 units of actual height
                float isoline_interval = 10.0;
                float isoline = mod(raw_height, isoline_interval);
                float isoline_width = 0.2;  // Width in actual height units
                
                if (isoline < isoline_width || isoline > isoline_interval - isoline_width) {
                    color = vec3(0.0, 0.0, 0.0);  // Black isolines
                }
            }
            
            fragColor = vec4(color, 1.0);
        }
        """
        
        self.shader_program.add_shader(GL_VERTEX_SHADER, vertex_shader)
        self.shader_program.add_shader(GL_FRAGMENT_SHADER, fragment_shader)
        self.shader_program.link()

    def init_dam_shader(self):
        """Initialize shader for dam rendering"""
        self.dam_shader = ShaderProgram()
        
        # Simple vertex shader for dam
        vertex_shader = """
        #version 330
        layout(location = 0) in vec3 position;
        
        uniform mat4 model;
        uniform mat4 view;
        uniform mat4 projection;
        
        void main() {
            gl_Position = projection * view * model * vec4(position, 1.0);
        }
        """
        
        # Simple fragment shader for dam (solid blue color)
        fragment_shader = """
        #version 330
        out vec4 fragColor;
        
        void main() {
            fragColor = vec4(0.2, 0.3, 0.8, 1.0);  // Blue color for dam
        }
        """
        
        self.dam_shader.add_shader(GL_VERTEX_SHADER, vertex_shader)
        self.dam_shader.add_shader(GL_FRAGMENT_SHADER, fragment_shader)
        self.dam_shader.link()

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
        vertices = []
        indices = []
        
        # Calculate terrain scale and center
        height_scale = 0.005  # Scale down height values
        min_height = np.min(self.terrain_data)
        
        # Generate vertices
        scale_x = 1.0 / cols
        scale_z = 1.0 / rows
        for i in range(rows):
            for j in range(cols):
                x = j * scale_x - 0.5
                y = self.terrain_data[i, j] * height_scale  # Just scale, don't normalize
                z = i * scale_z - 0.5
                vertices.extend([x, y, z])
                
        # Generate indices for triangle strips
        for i in range(rows - 1):
            for j in range(cols):
                indices.extend([i * cols + j, (i + 1) * cols + j])
            # Add degenerate triangle if not at the end
            if i < rows - 2:
                indices.extend([(i + 1) * cols + (cols - 1), (i + 1) * cols])
                
        # Create VBOs
        self.vertex_vbo = vbo.VBO(np.array(vertices, dtype=np.float32))
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
        
        # Set height range uniforms using original height values
        min_height = np.min(self.terrain_data)
        max_height = np.max(self.terrain_data)
        self.shader_program.set_uniform_1f("min_height", min_height)
        self.shader_program.set_uniform_1f("max_height", max_height)
        
        # Set color scheme and isolines flags based on render scheme
        show_isolines = "Isolines" in self.render_scheme
        use_yellow_red = self.render_scheme.startswith("Yellow-Red")
        
        self.shader_program.set_uniform_1i("show_isolines", show_isolines)
        self.shader_program.set_uniform_1i("color_scheme", 1 if use_yellow_red else 0)
        
        # Render mesh
        self.vertex_vbo.bind()
        self.index_vbo.bind()
        
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)
        
        glDrawElements(GL_TRIANGLE_STRIP, self.index_vbo.size, GL_UNSIGNED_INT, None)
        
        glDisableVertexAttribArray(0)
        self.vertex_vbo.unbind()
        self.index_vbo.unbind()
        
        # Render dam if exists
        if self.dam_vbo is not None and self.dam_ibo is not None:
            # Use a simple shader for the dam
            self.dam_shader.use()
            self.dam_shader.set_uniform_matrix4fv("model", model)
            self.dam_shader.set_uniform_matrix4fv("view", self.camera.get_view_matrix())
            self.dam_shader.set_uniform_matrix4fv("projection", self.camera.get_projection_matrix())
            
            self.dam_vbo.bind()
            self.dam_ibo.bind()
            
            glEnableVertexAttribArray(0)
            glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)
            
            glDrawElements(GL_TRIANGLES, self.dam_ibo.size, GL_UNSIGNED_INT, None)
            
            glDisableVertexAttribArray(0)
            self.dam_vbo.unbind()
            self.dam_ibo.unbind()

    def load_terrain(self, file_path):
        try:
            loader = TerrainLoader()
            processor = TerrainProcessor()
            
            # Load and store original data
            self.original_terrain_data = loader.load(file_path)
            
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
        
    def set_detail_level(self, value):
        """Update the detail level and regenerate the terrain if loaded"""
        self.detail_level = value
        if self.terrain_data is not None:
            try:
                # Store the original data if not already stored
                if not hasattr(self, 'original_terrain_data'):
                    self.original_terrain_data = self.terrain_data.copy()
                
                # Process the original data with new detail level
                processor = TerrainProcessor()
                self.terrain_data = processor.process(self.original_terrain_data, value)
                
                # Regenerate the mesh with new data
                self.generate_terrain_mesh()
                
                # Update statistics
                parent = self.parent()
                while parent is not None:
                    if isinstance(parent, QMainWindow):
                        parent.update_statistics(self.terrain_data)
                        break
                    parent = parent.parent()
                
                self.update()
                
            except Exception as e:
                print(f"Error updating detail level: {str(e)}")
            
    def reset_camera(self):
        self.camera.reset()
        self.update() 

    def mousePressEvent(self, event):
        self.last_pos = event.position()
        
        if self.dam_mode:
            if event.button() == Qt.MouseButton.LeftButton:
                # Add point to dam when in dam mode
                world_pos = self.screen_to_world(event.position().x(), event.position().y())
                if world_pos is not None:
                    self.dam_builder.add_point(world_pos)
                    self.update_dam_mesh()
                    self.update()
        else:
            # Normal camera control when not in dam mode
            if event.button() == Qt.MouseButton.LeftButton:
                self.left_mouse_pressed = True
            elif event.button() == Qt.MouseButton.RightButton:
                self.right_mouse_pressed = True

    def mouseReleaseEvent(self, event):
        if not self.dam_mode:  # Only handle releases when not in dam mode
            if event.button() == Qt.MouseButton.LeftButton:
                self.left_mouse_pressed = False
            elif event.button() == Qt.MouseButton.RightButton:
                self.right_mouse_pressed = False

    def mouseMoveEvent(self, event):
        if self.dam_mode:
            return  # Ignore mouse movement in dam mode
        
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
        if not self.dam_mode:  # Only allow zooming when not in dam mode
            self.camera.process_mouse_scroll(event.angleDelta().y())
            self.update()

    def set_dam_mode(self, enabled):
        """Enable/disable dam creation mode"""
        self.dam_mode = enabled
        if not enabled:
            self.dam_builder.clear_points()
            
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
        
    def update_dam_mesh(self):
        """Update the dam mesh VBOs"""
        vertices, indices = self.dam_builder.generate_dam_mesh()
        if vertices is not None:
            self.dam_vbo = vbo.VBO(vertices)
            self.dam_ibo = vbo.VBO(indices, target=GL_ELEMENT_ARRAY_BUFFER) 

    def clear_dams(self):
        """Clear all dams and points"""
        self.dam_builder.clear_points()
        self.dam_vbo = None
        self.dam_ibo = None
        self.update() 