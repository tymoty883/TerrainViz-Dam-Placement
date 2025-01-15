from osgeo import gdal
import numpy as np

class TerrainLoader:
    def load(self, file_path):
        """
        Load terrain data from a file
        
        Args:
            file_path (str): Path to the terrain file (.tif or .asc)
            
        Returns:
            numpy.ndarray: The terrain height data
        """
        try:
            dataset = gdal.Open(file_path)
            if dataset is None:
                raise ValueError("Could not open terrain file")
                
            band = dataset.GetRasterBand(1)
            data = band.ReadAsArray()
            
            return data
            
        except Exception as e:
            raise Exception(f"Error loading terrain: {str(e)}") 