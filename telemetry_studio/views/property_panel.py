from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, 
    QSpinBox, QCheckBox, QLabel, QScrollArea, QDoubleSpinBox, QGroupBox
)
from PySide6.QtCore import Signal
from telemetry_studio.data_models import FieldDefinition, ProjectDefinition
from telemetry_studio.widgets.checkable_combo import CheckableComboBox

class FieldPropertyPanel(QWidget):
    """
    Master-Detail: Detail View
    edits properties of the currently selected FieldDefinition.
    Emits fieldChanged signal on any edit.
    """
    fieldChanged = Signal()
    discriminatorChanged = Signal()
    
    def __init__(self, project: ProjectDefinition, parent=None):
        super().__init__(parent)
        # Store project reference - will be refreshed in set_field
        self.project = project
        self.current_field: FieldDefinition = None
        self._blocking = False
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll Area for long forms
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.content_widget = QWidget()
        self.form_layout = QFormLayout(self.content_widget)
        scroll.setWidget(self.content_widget)
        self.layout.addWidget(scroll)
        
        self._init_ui()
        
    def _init_ui(self):
        # 1. Core Properties
        self.name_edit = QLineEdit()
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "UInt8", "UInt16", "UInt32", "UInt64", 
            "Int8", "Int16", "Int32", "Int64",
            "Float32", "Float64", "Bool", 
            "String", "Enum", "BitField", "Array", "FixedPoint"
        ])
        
        self.spl_combo = CheckableComboBox()
        self.spl_combo.addItems([c.name for c in self.project.spl_configs])
        
        self.form_layout.addRow("Name", self.name_edit)
        self.form_layout.addRow("Type", self.type_combo)
        
        self.default_value = QLineEdit()
        self.default_value.setPlaceholderText("Default Value")
        self.default_value.textChanged.connect(self._on_edit)
        self.form_layout.addRow("Default Value", self.default_value)
        
        self.form_layout.addRow("Active Configs", self.spl_combo)
        
        # 2. Type Specific Groups
        self.array_group = QGroupBox("Array Properties")
        self.array_form = QFormLayout(self.array_group)
        self.arr_mode = QComboBox()
        self.arr_mode.addItems(["Fixed", "Dynamic"])
        self.arr_count = QSpinBox()
        self.arr_count.setRange(0, 9999)
        self.arr_ref = QComboBox() # Filled dynamically
        self.arr_item_type = QComboBox()
        self.arr_item_type.addItems(["UInt8", "UInt16", "UInt32", "Float32"]) # Simplified for now
        self.array_form.addRow("Mode", self.arr_mode)
        self.array_form.addRow("Count (Fixed)", self.arr_count)
        self.array_form.addRow("Length Field", self.arr_ref)
        self.array_form.addRow("Item Type", self.arr_item_type)
        self.form_layout.addRow(self.array_group)
        self.array_group.hide()
        
        self.enum_group = QGroupBox("Enum Properties")
        self.enum_form = QFormLayout(self.enum_group)
        self.enum_selector = QComboBox()
        self.enum_selector.addItems([e.name for e in self.project.enums])
        self.enum_form.addRow("Enum Class", self.enum_selector)
        
        # Storage Type for Enum
        self.enum_storage = QComboBox()
        self.enum_storage.addItems(["UInt8", "UInt16", "UInt32", "UInt64", "Int8", "Int16", "Int32", "Int64"])
        self.enum_form.addRow("Storage Type", self.enum_storage)
        
        self.form_layout.addRow(self.enum_group)
        self.enum_group.hide()
        
        # 3. Flags
        self.flag_group = QGroupBox("Flags & Constraints")
        self.flag_layout = QVBoxLayout(self.flag_group)
        
        self.chk_discriminator = QCheckBox("Is Discriminator")
        self.chk_checksum = QCheckBox("Is Checksum")
        self.chk_timestamp = QCheckBox("Is Timestamp")
        self.chk_length = QCheckBox("Is Length")
        
        self.flag_layout.addWidget(self.chk_discriminator)
        self.flag_layout.addWidget(self.chk_checksum)
        self.flag_layout.addWidget(self.chk_timestamp)
        self.flag_layout.addWidget(self.chk_length)
        
        self.form_layout.addRow(self.flag_group)
        
        # Smart Field Options
        self.smart_opts = QWidget()
        self.smart_form = QFormLayout(self.smart_opts)
        self.start_field = QComboBox()
        self.end_field = QComboBox()
        self.smart_form.addRow("Start Field", self.start_field)
        self.smart_form.addRow("End Field", self.end_field)
        self.form_layout.addRow(self.smart_opts)
        self.smart_opts.hide()
        
        # Connect Signals
        self.name_edit.textChanged.connect(self._on_edit)
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        
        # Fix: Connect spl_combo model dataChanged signal
        self.spl_combo.model().dataChanged.connect(self._on_edit)
        
        self.arr_mode.currentTextChanged.connect(self._on_edit)
        self.arr_count.valueChanged.connect(self._on_edit)
        self.arr_ref.currentTextChanged.connect(self._on_edit)
        self.arr_item_type.currentTextChanged.connect(self._on_edit)
        
        # Fix: Connect enum selector and storage
        self.enum_selector.currentTextChanged.connect(self._on_edit)
        self.enum_storage.currentTextChanged.connect(self._on_edit)
        
        self.chk_discriminator.toggled.connect(self._on_edit)
        self.chk_discriminator.toggled.connect(lambda _: self.discriminatorChanged.emit())
        
        self.chk_checksum.toggled.connect(self._on_edit)
        self.chk_timestamp.toggled.connect(self._on_edit)
        self.chk_length.toggled.connect(self._on_edit)
        self.chk_length.toggled.connect(lambda c: self.smart_opts.setVisible(c or self.chk_checksum.isChecked()))
        
        self.start_field.currentTextChanged.connect(self._on_edit)
        self.end_field.currentTextChanged.connect(self._on_edit)
        
    def set_field(self, field: FieldDefinition, all_field_names: list, project: ProjectDefinition = None):
        self._blocking = True
        self.current_field = field
        
        # Update project reference if provided (ensures we have current SPL configs)
        if project is not None:
            self.project = project
        
        self.name_edit.setText(field.name)
        self.type_combo.setCurrentText(field.field_type)
        
        # Refresh Configs - now using current project state
        self.spl_combo.clear()
        spl_names = sorted([c.name for c in self.project.spl_configs])
        self.spl_combo.addItems(spl_names)
        
        if field.options.get("active_configs"):
            self.spl_combo.setCheckedItems(field.options.get("active_configs"))
        else:
            self.spl_combo.clearChecked()
            
        # Refresh Enums
        self.enum_selector.clear()
        self.enum_selector.addItems(sorted([e.name for e in self.project.enums]))
            
        # Default Value
        val = field.options.get("default", "")
        self.default_value.setText(str(val))
            
        # Update Reference Combos
        self.arr_ref.clear()
        self.arr_ref.addItems(all_field_names)
        self.start_field.clear()
        self.start_field.addItems(all_field_names)
        self.end_field.clear()
        self.end_field.addItems(all_field_names)
        
        # Type Logic
        self._update_visibility()
        
        # Load Sub-Options
        opts = field.options
        if field.field_type == "Array":
            self.arr_mode.setCurrentText(opts.get("mode", "Fixed"))
            self.arr_count.setValue(opts.get("count", 0))
            self.arr_ref.setCurrentText(opts.get("count_field", ""))
            self.arr_item_type.setCurrentText(opts.get("item_type", "UInt8"))
            
        if field.field_type == "Enum":
            self.enum_selector.setCurrentText(opts.get("enum_name", ""))
            # Load storage type (default to UInt32 for compatibility)
            storage_type = opts.get("storage_type", "UInt32")
            self.enum_storage.setCurrentText(storage_type)
            
        # Flags
        self.chk_discriminator.setChecked(opts.get("is_discriminator", False))
        self.chk_checksum.setChecked(opts.get("is_checksum", False))
        self.chk_timestamp.setChecked(opts.get("is_timestamp", False))
        self.chk_length.setChecked(opts.get("is_length", False))
        
        # Smart Opts
        self.start_field.setCurrentText(opts.get("start_field", ""))
        self.end_field.setCurrentText(opts.get("end_field", ""))
        
        self._blocking = False
        
    def _update_visibility(self):
        ft = self.type_combo.currentText()
        self.array_group.setVisible(ft == "Array")
        self.enum_group.setVisible(ft == "Enum")
        
        # Logic: Disable Smart Flags for Float
        is_float = "Float" in ft
        self.chk_checksum.setEnabled(not is_float)
        self.chk_length.setEnabled(not is_float)
        self.chk_timestamp.setEnabled(not is_float)
        
        # Logic: Disable Discriminator for Enum
        is_enum = (ft == "Enum")
        self.chk_discriminator.setEnabled(not is_enum)
        if is_enum: self.chk_discriminator.setChecked(False)

    def _on_type_changed(self, text):
        self._update_visibility()
        self._on_edit()

    def _on_edit(self):
        if self._blocking or not self.current_field:
            return
            
        # Write back to object
        f = self.current_field
        f.name = self.name_edit.text()
        f.field_type = self.type_combo.currentText()
        f.options['active_configs'] = self.spl_combo.checkedItems()
        
        
        if f.field_type == "Array":
            f.options['mode'] = self.arr_mode.currentText()
            f.options['count'] = self.arr_count.value()
            if f.options['mode'] == 'Dynamic':
                f.options['count_field'] = self.arr_ref.currentText()
            f.options['item_type'] = self.arr_item_type.currentText()
            
        if f.field_type == "Enum":
            f.options['enum_name'] = self.enum_selector.currentText()
            f.options['storage_type'] = self.enum_storage.currentText()
            
        f.options['is_discriminator'] = self.chk_discriminator.isChecked()
        f.options['is_checksum'] = self.chk_checksum.isChecked()
        f.options['is_timestamp'] = self.chk_timestamp.isChecked()
        f.options['is_length'] = self.chk_length.isChecked()
        
        if f.options['is_length'] or f.options['is_checksum']:
            f.options['start_field'] = self.start_field.currentText()
            f.options['end_field'] = self.end_field.currentText()
            
        # Default Value Logic
        val_str = self.default_value.text()
        if f.field_type in ["UInt8", "UInt16", "UInt32", "UInt64", "Int8", "Int16", "Int32", "Int64"]:
            if not val_str: f.options['default'] = 0
            elif val_str.isdigit(): f.options['default'] = int(val_str)
            elif val_str.startswith("0x"): 
                try: f.options['default'] = int(val_str, 16)
                except: f.options['default'] = 0
            else:
                 # Try parsing signed int if needed
                try: f.options['default'] = int(val_str)
                except: f.options['default'] = 0
        elif f.field_type in ["Float32", "Float64"]:
            if not val_str: f.options['default'] = 0.0
            else:
                try: f.options['default'] = float(val_str)
                except: f.options['default'] = 0.0
        elif f.field_type == "Bool":
             f.options['default'] = (val_str.lower() == "true")
        else:
             f.options['default'] = val_str
            
        self.fieldChanged.emit()
