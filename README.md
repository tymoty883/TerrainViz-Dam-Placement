# 3D Terrain Visualization Project

## Features
- Load `.tif` and `.asc` terrain files for visualization.
- Simplify terrain models for improved performance on large datasets.
- Interactive 3D navigation with an arcball camera.
- Customizable terrain and background schemes.
- OpenGL-powered visualization for high-quality rendering.
- Geometric dam placement design and simulation of enclosed area flooding.

---

## Usage

1. **Launch the App**:
   Run `python main.py`. A graphical user interface will guide you.

2. **Select a File**:
   Use the file selection dialog to load a `.tif` or `.asc` terrain file.

3. **Customize Options**:
   - Choose terrain and background schemes.
   - Enable or disable terrain simplification.

4. **Interact with the 3D Model**:
   - Rotate: Left-click and drag.
   - Zoom: Use the scroll wheel.
   - Pan: Right-click and drag.

5. **View Terrain Statistics**:
   - Elevation range, resolution, and file details will be displayed in the GUI.

---

## Project Structure

```
project-root/
|-- main.py                # Entry point for the application
|-- requirements.txt       # List of dependencies
|-- gui/
|   |-- file_dialog.py     # File selection dialogs
|   |-- main_window.py     # Main graphical interface
|-- rendering/
|   |-- camera.py          # Arcball camera implementation
|   |-- dam_builder.py     # Utility for rendering
|   |-- shaders.py         # OpenGL shader management
|   |-- terrain_renderer.py# Core terrain rendering logic
|-- utils/
    |-- terrain_loader.py  # File parsing and loading
    |-- terrain_processor.py # Data processing and simplification
```

---

## Supported File Formats

1. **GeoTIFF (.tif)**: Raster format with geospatial metadata.
2. **ASCII Grid (.asc)**: Text-based elevation grid format.

---

## Dependencies

- Python 3.8+
- numpy
- pyopengl
- PyQt5
- gdal


## License

This project is licensed under the MIT License. Contributions and modifications are welcome.


