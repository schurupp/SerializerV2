from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QDialogButtonBox, QCheckBox
)
from serializer_core.protocols import ProtocolConfig

class ProtocolSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("String Protocol Settings")
        
        self.config = ProtocolConfig.get()
        
        self.layout = QVBoxLayout(self)
        self.form = QFormLayout()
        
        self.start_sym = QLineEdit(self.config.START_SYMBOL)
        self.end_sym = QLineEdit(self.config.END_SYMBOL)
        
        self.delim_id = QLineEdit(self.config.DELIM_ID)
        self.delim_type = QLineEdit(self.config.DELIM_TYPE)
        self.delim_cmd = QLineEdit(self.config.DELIM_CMD)
        self.delim_field = QLineEdit(self.config.DELIM_FIELD)
        
        self.use_checksum = QCheckBox("Use Checksum")
        self.use_checksum.setChecked(self.config.USE_CHECKSUM)
        
        self.form.addRow("Start Symbol", self.start_sym)
        self.form.addRow("End Symbol", self.end_sym)
        self.form.addRow("Msg ID Delimiter", self.delim_id)
        self.form.addRow("CMD Type Delimiter", self.delim_type)
        self.form.addRow("CMD Delimiter", self.delim_cmd)
        self.form.addRow("Field Delimiter", self.delim_field)
        self.form.addRow(self.use_checksum)
        
        self.layout.addLayout(self.form)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons)
        
    def apply_settings(self):
        ProtocolConfig.configure(
            start=self.start_sym.text(),
            end=self.end_sym.text(),
            delim_id=self.delim_id.text(),
            delim_type=self.delim_type.text(),
            delim_cmd=self.delim_cmd.text(),
            delim_field=self.delim_field.text(),
            use_checksum=self.use_checksum.isChecked()
        )
