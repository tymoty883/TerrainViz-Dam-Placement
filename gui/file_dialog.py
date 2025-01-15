from PyQt6.QtWidgets import QFileDialog

class FileDialog:
    def get_terrain_file(self):
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        dialog.setNameFilter("Terrain Files (*.tif *.asc)")
        
        if dialog.exec():
            return dialog.selectedFiles()[0]
        return None 