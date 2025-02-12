from OpenGL.GL import *

class ShaderProgram:
    def __init__(self):
        self.program_id = glCreateProgram()
        self.shaders = []

    def add_shader(self, shader_type, source):
        """Add a shader to the program"""
        shader = glCreateShader(shader_type)
        glShaderSource(shader, source)
        glCompileShader(shader)
        
        # Check compilation status
        if not glGetShaderiv(shader, GL_COMPILE_STATUS):
            error = glGetShaderInfoLog(shader)
            raise RuntimeError(f"Shader compilation failed: {error}")
            
        glAttachShader(self.program_id, shader)
        self.shaders.append(shader)

    def link(self):
        """Link the shader program"""
        glLinkProgram(self.program_id)
        
        # Check link status
        if not glGetProgramiv(self.program_id, GL_LINK_STATUS):
            error = glGetProgramInfoLog(self.program_id)
            raise RuntimeError(f"Program linking failed: {error}")
            
        # Clean up individual shaders
        for shader in self.shaders:
            glDeleteShader(shader)
        self.shaders.clear()

    def use(self):
        """Use this shader program"""
        glUseProgram(self.program_id)

    def set_uniform_matrix4fv(self, name, value):
        """Set a uniform mat4 value"""
        location = glGetUniformLocation(self.program_id, name)
        glUniformMatrix4fv(location, 1, GL_FALSE, value)

    def set_uniform_1f(self, name, value):
        """Set a uniform float value"""
        location = glGetUniformLocation(self.program_id, name)
        glUniform1f(location, value)

    def set_uniform_3f(self, name, x, y, z):
        """Set a uniform vec3 value"""
        location = glGetUniformLocation(self.program_id, name)
        glUniform3f(location, x, y, z)

    def set_uniform_4f(self, name, x, y, z, w):
        """Set a uniform vec4 value"""
        location = glGetUniformLocation(self.program_id, name)
        glUniform4f(location, x, y, z, w)

    def set_uniform_1i(self, name, value):
        """Set a uniform integer value"""
        location = glGetUniformLocation(self.program_id, name)
        glUniform1i(location, value) 