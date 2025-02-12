import numpy as np
from scipy.ndimage import zoom, gaussian_filter
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
        # First clean and smooth the terrain data
        cleaned_data = self.clean_terrain(data)
        
        if detail_level == 100:
            return cleaned_data
            
        # Calculate target size based on detail level while maintaining aspect ratio
        original_height, original_width = cleaned_data.shape
        aspect_ratio = original_width / original_height
        
        # Base the target size on the larger dimension
        if original_width >= original_height:
            target_width = max(10, int(original_width * detail_level / 100))
            target_height = max(10, int(target_width / aspect_ratio))
        else:
            target_height = max(10, int(original_height * detail_level / 100))
            target_width = max(10, int(target_height * aspect_ratio))
        
        # Use scipy's zoom for better interpolation
        processed_data = zoom(cleaned_data, 
                            (target_height / original_height,
                             target_width / original_width),
                            order=1)
        
        return processed_data
        
    def clean_terrain(self, data):
        """
        Clean terrain data by removing outliers and smoothing
        
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
        
        # Remove extreme outliers (z-score > 4) - increased threshold
        outlier_mask = np.abs(z_scores) > 4
        data_clean[outlier_mask] = np.mean(data_clean[~outlier_mask])
        
        # Reshape back to original shape
        cleaned_data = data_clean.reshape(data.shape)
        
        # Apply Gaussian smoothing
        sigma = max(1, min(cleaned_data.shape) / 200)  # Adaptive smoothing based on terrain size
        smoothed_data = gaussian_filter(cleaned_data, sigma=sigma)
        
        # Blend smoothed and original data to preserve some detail
        alpha = 0.7  # Blend factor (origina lvalue)
        final_data = alpha * cleaned_data + (1 - alpha) * smoothed_data
        
        return final_data