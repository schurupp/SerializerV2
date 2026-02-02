from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QRadioButton, QDialogButtonBox, QButtonGroup, QFormLayout
)

class ModeSelectionDialog(QDialog):
    def __init__(self, parent=None, current_mode="binary"):
        super().__init__(parent)
        self.setWindowTitle("Select Protocol Mode")
        self.resize(300, 150)
        
        self.selected_mode = current_mode
        
        layout = QVBoxLayout(self)
        
        lbl = QLabel("Choose the message protocol mode for this project:")
        layout.addWidget(lbl)
        
        self.rb_binary = QRadioButton("Binary Protocol (Hex)")
        self.rb_string = QRadioButton("String Protocol (ASCII)")
        
        self.bg = QButtonGroup(self)
        self.bg.addButton(self.rb_binary)
        self.bg.addButton(self.rb_string)
        
        if current_mode == 'string':
            self.rb_string.setChecked(True)
        else:
            self.rb_binary.setChecked(True)
            
        layout.addWidget(self.rb_binary)
        layout.addWidget(self.rb_string)
        
        layout.addWidget(QLabel("<i>Note: Switching mode will reset the current project.</i>"))
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def accept(self):
        if self.rb_string.isChecked():
            self.selected_mode = 'string'
        else:
            self.selected_mode = 'binary'
        super().accept()
