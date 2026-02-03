from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QRadioButton, QDialogButtonBox, QButtonGroup, QFormLayout
)

class ModeSelectionDialog(QDialog):
    def __init__(self, parent=None, current_mode="binary", current_endian="Little"):
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
        layout.addWidget(self.rb_binary)
        layout.addWidget(self.rb_string)

        self.endian_combo = None
        if current_mode != 'string':
            # Endianness option (only relevant for binary-ish, though actually relevant for mixed too)
            layout.addWidget(QLabel("Global Default Endianness:"))
            from PySide6.QtWidgets import QComboBox
            self.endian_combo = QComboBox()
            self.endian_combo.addItems(["Little", "Big"])
            self.endian_combo.setCurrentText(current_endian)
            layout.addWidget(self.endian_combo)
            
            # Disable if string mode selected
            self.rb_string.toggled.connect(lambda c: self.endian_combo.setDisabled(c))
        
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
            
        if self.endian_combo and self.endian_combo.isEnabled():
            self.selected_endian = self.endian_combo.currentText()
        else:
            self.selected_endian = "Little"
            
        super().accept()
