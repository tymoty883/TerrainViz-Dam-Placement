from PyQt6.QtGui import  QVector3D, QMatrix4x4
import math

class Camera:
    def __init__(self):
        self.position = QVector3D(0, 0.5, 2)
        self.target = QVector3D(0, 0, 0)
        self.up = QVector3D(0, 1, 0)
        self.right = QVector3D(1, 0, 0)
        
        self.fov = 45.0
        self.aspect_ratio = 1.0
        self.near = 0.01
        self.far = 1000.0
        
        self.yaw = -90.0
        self.pitch = -30.0
        self.min_distance = 0.1
        self.max_distance = 10.0
        self.distance = 2.0
        
        self.update_vectors()
        
    def update_vectors(self):
        """Update camera position based on spherical coordinates"""
        rad_pitch = math.radians(self.pitch)
        rad_yaw = math.radians(self.yaw)
        
        x = self.distance * math.cos(rad_pitch) * math.cos(rad_yaw)
        y = self.distance * math.sin(rad_pitch)
        z = self.distance * math.cos(rad_pitch) * math.sin(rad_yaw)
        
        self.position = QVector3D(x, y, z) + self.target
        
    def get_view_matrix(self):
        """Get the view matrix for OpenGL"""
        matrix = QMatrix4x4()
        matrix.lookAt(self.position, self.target, self.up)
        return matrix.data()
        
    def get_projection_matrix(self):
        """Get the projection matrix for OpenGL"""
        matrix = QMatrix4x4()
        matrix.perspective(self.fov, self.aspect_ratio, self.near, self.far)
        return matrix.data()
        
    def process_mouse_movement(self, dx, dy, constrain_pitch=True):
        """Process mouse movement for camera rotation"""
        sensitivity = 0.1
        self.yaw += dx * sensitivity
        self.pitch += dy * sensitivity
        
        if constrain_pitch:
            self.pitch = max(-89.0, min(89.0, self.pitch))
            
        self.update_vectors()
        
    def process_mouse_scroll(self, delta):
        """Process mouse scroll for camera zoom"""
        zoom_speed = 0.8
        if delta > 0:
            self.distance = max(self.min_distance, self.distance * (1.0 - 0.1 * zoom_speed))
        else:
            self.distance = min(self.max_distance, self.distance * (1.0 + 0.1 * zoom_speed))
            
        self.update_vectors()
        
    def set_aspect_ratio(self, ratio):
        self.aspect_ratio = ratio
        
    def process_mouse_pan(self, dx, dy):
        """Process mouse movement for camera panning"""
        pan_speed = 0.001 * self.distance
        
        forward = (self.target - self.position).normalized()
        self.right = QVector3D.crossProduct(forward, self.up).normalized()
        
        offset = self.right * (-dx * pan_speed) + self.up * (dy * pan_speed)
        self.position += offset
        self.target += offset
        
    def reset(self):
        self.position = QVector3D(0, 0.5, 2)
        self.target = QVector3D(0, 0, 0)
        self.up = QVector3D(0, 1, 0)
        self.yaw = -90.0
        self.pitch = -30.0
        self.distance = 2.0
        self.update_vectors() 