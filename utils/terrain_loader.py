from osgeo import gdal
import numpy as np
import os

class TerrainLoader:
    def load(self, file_path, region=None):
        """
        Load terrain data from a file
        
        Args:
            file_path (str): Path to the terrain file (.tif, .asc, or .hgt)
            region (tuple): Optional (x_min, y_min, width, height) for cropping
            
        Returns:
            numpy.ndarray: The terrain height data
        """
        try:
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == '.hgt':
                return self._load_hgt(file_path, region)
            else:
                return self._load_gdal(file_path, region)
                
        except Exception as e:
            raise Exception(f"Error loading terrain: {str(e)}")
            
    def _load_gdal(self, file_path, region=None):
        """Load terrain using GDAL (for .tif and .asc files)"""
        dataset = gdal.Open(file_path)
        if dataset is None:
            raise ValueError("Could not open terrain file")
            
        band = dataset.GetRasterBand(1)
        
        if region is not None:
            x_min, y_min, width, height = region
            data = band.ReadAsArray(
                xoff=x_min,
                yoff=y_min,
                win_xsize=width,
                win_ysize=height
            )
        else:
            data = band.ReadAsArray()
            
        return data
        
    def _load_hgt(self, file_path, region=None):
        """Load SRTM HGT file"""
        # HGT files are 16-bit signed integers in big-endian format
        # Standard SRTM3 files are 1201x1201 pixels
        with open(file_path, 'rb') as f:
            # Get file size to determine resolution
            file_size = os.path.getsize(file_path)
            if file_size == 1201 * 1201 * 2:  # SRTM3 (3 arc-second)
                width = height = 1201
            elif file_size == 3601 * 3601 * 2:  # SRTM1 (1 arc-second)
                width = height = 3601
            else:
                raise ValueError("Unsupported HGT file format")
                
            # Read the entire file as a 16-bit signed integer array
            data = np.fromfile(f, dtype='>i2')  # Big-endian 16-bit signed integer
            data = data.reshape((height, width))
            
            # Handle region selection if specified
            if region is not None:
                x_min, y_min, reg_width, reg_height = region
                data = data[y_min:y_min+reg_height, x_min:x_min+reg_width]
            
            # Replace no-data values (-32768) with NaN
            data = data.astype(np.float32)
            data[data == -32768] = np.nan
            
            return data 