import numpy as np
from scipy.ndimage import zoom
from scipy import stats

class TerrainProcessor:
    def process(self, data, detail_level):
        """
        Process terrain data based on detail level
        
        Args:
            data (numpy.ndarray): Raw terrain data
            detail_level (int): Detail level (1-100)
            
        Returns:
            numpy.ndarray: Processed terrain data
        """
        # First clean the terrain data (remove outliers only)
        cleaned_data = self.clean_terrain(data)
        
        if detail_level == 100:
            return cleaned_data
            
        # Calculate target size based on detail level
        scale = detail_level / 100.0
        target_shape = (
            max(10, int(cleaned_data.shape[0] * scale)),
            max(10, int(cleaned_data.shape[1] * scale))
        )
        
        # Use scipy's zoom for better interpolation
        processed_data = zoom(cleaned_data, 
                            (target_shape[0] / cleaned_data.shape[0],
                             target_shape[1] / cleaned_data.shape[1]),
                            order=1)
        
        return processed_data
        
    def clean_terrain(self, data):
        """
        Clean terrain data by removing outliers and extreme values
        
        Args:
            data (numpy.ndarray): Raw terrain data
            
        Returns:
            numpy.ndarray: Cleaned terrain data
        """
        # Remove NaN values if any
        data = np.nan_to_num(data, nan=np.nanmean(data))
        
        # Calculate z-scores to identify outliers
        z_scores = stats.zscore(data.flatten())
        data_clean = data.flatten()
        
        # Remove extreme outliers (z-score > 3)
        outlier_mask = np.abs(z_scores) > 3
        data_clean[outlier_mask] = np.mean(data_clean[~outlier_mask])
        
        # Reshape back to original shape
        cleaned_data = data_clean.reshape(data.shape)
        
        return cleaned_data 