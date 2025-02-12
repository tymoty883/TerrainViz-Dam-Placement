from PyQt6.QtWidgets import QFileDialog, QMessageBox
from .region_selector_dialog import RegionSelectorDialog
import os

class FileDialog:
    def get_terrain_file(self):
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        dialog.setNameFilter("Terrain Files (*.tif *.asc *.hgt)")
        
        if dialog.exec():
            file_path = dialog.selectedFiles()[0]
            
            # Check file size (in MB)
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            
            if file_size_mb > 10:
                # Show info message about ROI selection
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setWindowTitle("Large File Detected")
                msg.setText("The selected file is larger than 10MB.")
                msg.setInformativeText("You will now be prompted to select a region of interest to optimize performance.")
                msg.exec()
                
                # Show region selector
                region_dialog = RegionSelectorDialog(file_path)
                if region_dialog.exec():
                    return file_path, region_dialog.get_selected_region()
                return None, None
            else:
                # For small files, return full file without region selection
                return file_path, None
                
        return None, None 