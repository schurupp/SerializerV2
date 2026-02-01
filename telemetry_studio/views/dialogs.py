from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox, 
    QDialogButtonBox, QCheckBox, QComboBox, QWidget, QListWidget, 
    QHBoxLayout, QPushButton, QInputDialog, QLabel, QDoubleSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from typing import Dict, Any, List
from telemetry_studio.data_models import FieldDefinition, EnumDefinition, ProjectDefinition

class BaseConfigDialog(QDialog):
    def __init__(self, current_options: Dict[str, Any], project: ProjectDefinition, title="Field Config", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.project = project
        self.current_options = current_options
        
        self.layout = QVBoxLayout(self)
        self.form = QFormLayout()
        self.layout.addLayout(self.form)
        
        # Active Configs
        self.config_list = QListWidget()
        self.config_list.setSelectionMode(QListWidget.MultiSelection)
        # Populate
        all_configs = self.project.spl_configs
        current_active = current_options.get("active_configs", [])
        
        for cfg in all_configs:
            from PySide6.QtWidgets import QListWidgetItem
            item = QListWidgetItem(cfg.name)
            self.config_list.addItem(item)
            if cfg.name in current_active:
                item.setSelected(True)
        
        self.layout.addWidget(QLabel("Active Configs:"))
        self.layout.addWidget(self.config_list)
        
        # Actions
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)
        
    def get_base_options(self) -> Dict[str, Any]:
        # Collect active configs
        selected_items = self.config_list.selectedItems()
        active = [i.text() for i in selected_items]
        return {"active_configs": active}

class PrimitiveConfigDialog(BaseConfigDialog):
    def __init__(self, current_options, project, field_type="UInt32", parent=None):
        super().__init__(current_options, project, f"{field_type} Config", parent)
        self.field_type = field_type
        
        # Default Value Widget logic
        if field_type == "Bool":
             self.default_val = QComboBox()
             self.default_val.addItems(["False", "True"])
             if current_options.get("default") == True:
                 self.default_val.setCurrentIndex(1)
             else:
                 self.default_val.setCurrentIndex(0)
                 
        elif "Float" in field_type:
             self.default_val = QDoubleSpinBox()
             self.default_val.setRange(-1e9, 1e9)
             self.default_val.setDecimals(6)
             try:
                 val = current_options.get("default")
                 if val is not None: self.default_val.setValue(float(val))
             except: pass
        else:
             self.default_val = QSpinBox()
             # Range depends on type ideally, but generic safe range:
             self.default_val.setRange(-2147483648, 2147483647)
             try:
                 val = current_options.get("default")
                 if val is not None: self.default_val.setValue(int(val))
             except: pass
             
        self.checks = {
            "is_discriminator": QCheckBox("Is Discriminator"),
            "is_checksum": QCheckBox("Is Checksum"),
            "is_timestamp": QCheckBox("Is Timestamp"),
        }
        
        self.form.addRow("Default Value", self.default_val)
        
        # Only show relevant checks
        if field_type != "Bool":
             for k, v in self.checks.items():
                 if current_options.get(k): v.setChecked(True)
                 self.form.addRow(v)

    def get_options(self):
        opts = self.get_base_options()
        if self.field_type == "Bool":
            opts["default"] = (self.default_val.currentIndex() == 1)
        else:
            opts["default"] = self.default_val.value()
            
        if self.field_type != "Bool":
            for k, v in self.checks.items():
                if v.isChecked(): opts[k] = True
        return opts

class StringConfigDialog(BaseConfigDialog):
    def __init__(self, current_options, project, parent=None):
        super().__init__(current_options, project, "String Config", parent)
        
        self.default_val = QLineEdit()
        self.default_val.setText(str(current_options.get("default", "")))
        
        self.mode = QComboBox()
        self.mode.addItems(["Fixed", "Dynamic"])
        self.length = QSpinBox()
        self.length.setRange(0, 65535)
        self.encoding = QComboBox()
        self.encoding.addItems(["utf-8", "ascii"])
        
        self.mode.setCurrentText(current_options.get("size_mode", "Fixed"))
        self.length.setValue(current_options.get("length", 10))
        self.encoding.setCurrentText(current_options.get("encoding", "utf-8"))
        
        self.form.addRow("Default Value", self.default_val)
        self.form.addRow("Size Mode", self.mode)
        self.form.addRow("Length (Fixed)", self.length)
        self.form.addRow("Encoding", self.encoding)
        
    def get_options(self):
        opts = self.get_base_options()
        opts.update({
            "default": self.default_val.text(),
            "size_mode": self.mode.currentText(),
            "length": self.length.value(),
            "encoding": self.encoding.currentText()
        })
        return opts

class BitFieldConfigDialog(BaseConfigDialog):
    def __init__(self, current_options, project, parent=None):
        super().__init__(current_options, project, "BitField Config", parent)
        
        self.bits = current_options.get("bits", [])
        self.project = project
        self.project_enums = [e.name for e in project.enums]
        
        # Cols: Name, Type, Width, Enum, Default
        self.table = QTableWidget(0, 5) 
        self.table.setHorizontalHeaderLabels(["Name", "Type", "Width", "Enum Class", "Default"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        self.refresh_table()
        
        btn_box = QHBoxLayout()
        add_btn = QPushButton("Add Bit")
        add_btn.clicked.connect(self.add_bit)
        del_btn = QPushButton("Remove Bit")
        del_btn.clicked.connect(self.del_bit)
        btn_box.addWidget(add_btn)
        btn_box.addWidget(del_btn)
        
        self.layout.insertWidget(0, self.table)
        self.layout.addLayout(btn_box)
        
    def refresh_table(self):
        self.table.setRowCount(0)
        for i, b in enumerate(self.bits):
            self.insert_row(i, b)
            
    def insert_row(self, row, data):
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(data.get('name', 'new_bit')))
        
        # Type Combo
        type_cb = QComboBox()
        type_cb.addItems(["UInt", "Int", "Bool", "Enum"])
        type_cb.setCurrentText(data.get('data_type', 'UInt'))
        type_cb.currentIndexChanged.connect(lambda idx, r=row: self.on_type_changed(r))
        self.table.setCellWidget(row, 1, type_cb)
        
        # Width Spin
        width_sb = QSpinBox()
        width_sb.setRange(1, 64)
        width_sb.setValue(data.get('width', 1))
        self.table.setCellWidget(row, 2, width_sb)

        # Enum Combo
        enum_cb = QComboBox()
        enum_cb.addItems(self.project_enums)
        cur_enum = data.get('enum_name')
        if cur_enum and cur_enum in self.project_enums:
             enum_cb.setCurrentText(cur_enum)
        enum_cb.setEnabled(type_cb.currentText() == "Enum")
        self.table.setCellWidget(row, 3, enum_cb)
        
        # Default Value Spin
        def_sb = QSpinBox()
        def_sb.setRange(-2147483648, 2147483647)
        def_sb.setValue(data.get('default_value', 0))
        self.table.setCellWidget(row, 4, def_sb)
        
    def on_type_changed(self, row):
        type_cb = self.table.cellWidget(row, 1)
        enum_cb = self.table.cellWidget(row, 3)
        width_sb = self.table.cellWidget(row, 2)
        
        is_enum = (type_cb.currentText() == "Enum")
        enum_cb.setEnabled(is_enum)
        
        # Smart Default Widget
        # Remove old widget
        self.table.removeCellWidget(row, 4)
        
        curr_type = type_cb.currentText()
        if curr_type == "Bool":
            def_w = QComboBox()
            def_w.addItems(["False", "True"])
            self.table.setCellWidget(row, 4, def_w)
        elif curr_type == "Enum":
            def_w = QComboBox()
            # Populate with keys of currently selected enum
            self.update_enum_defaults(row, enum_cb.currentText())
            # Connect enum change to update default
            try:
                enum_cb.currentTextChanged.disconnect()
            except RuntimeError:
                pass
            except TypeError:
                pass
            enum_cb.currentTextChanged.connect(lambda txt, r=row: self.update_enum_defaults(r, txt))
            self.table.setCellWidget(row, 4, def_w)
        else:
            def_w = QSpinBox()
            def_w.setRange(-2147483648, 2147483647)
            self.table.setCellWidget(row, 4, def_w)

    def update_enum_defaults(self, row, enum_name):
        def_w = self.table.cellWidget(row, 4)
        if not isinstance(def_w, QComboBox): return
        
        def_w.clear()
        if enum_name in self.project.enums_dict: # Need efficient lookup
            # Wait, project.enums is a list. I should map it inside init or just iterate
            # In init I did: self.project_enums = [e.name...]
            # Need to access EnumDef items
            for e in self.project.enums:
                if e.name == enum_name:
                    for item in e.items:
                        def_w.addItem(f"{item.name} ({item.value})", item.value)
                    break

    def add_bit(self):
        self.bits.append({'name': 'new_bit', 'width': 1, 'data_type': 'UInt'})
        self.refresh_table()
                
    def del_bit(self):
        row = self.table.currentRow()
        if row >= 0:
            del self.bits[row]
            self.refresh_table()
            
    def get_options(self):
        opts = self.get_base_options()
        new_bits = []
        
        # Calculate combined integer default
        combined_default = 0
        current_shift = 0
        
        for r in range(self.table.rowCount()):
            name_item = self.table.item(r, 0)
            name = name_item.text() if name_item else "bit"
            
            type_cb = self.table.cellWidget(r, 1)
            d_type = type_cb.currentText()
            
            width_sb = self.table.cellWidget(r, 2)
            width = width_sb.value()
            
            enum_cb = self.table.cellWidget(r, 3)
            enum_name = enum_cb.currentText() if enum_cb.isEnabled() else None
            
            def_w = self.table.cellWidget(r, 4)
            current_def = 0
            if isinstance(def_w, QComboBox):
                # For Bool: Index 0=False, 1=True. But check text maybe?
                # Bool Items: ["False", "True"]
                # Enum Items: "Name (Val)", UserData=Val
                current_def = def_w.currentData()
                if current_def is None: # Maybe Bool or no data set
                     if def_w.count() > 0:
                         # If Bool, text is "False"/"True"
                         txt = def_w.currentText()
                         if txt == "True": current_def = 1
                         elif txt == "False": current_def = 0
                         else: current_def = def_w.currentData() or 0
            elif isinstance(def_w, QSpinBox):
                current_def = def_w.value()
            
            new_bits.append({
                'name': name, 
                'width': width, 
                'data_type': d_type,
                'enum_name': enum_name,
                'default_value': current_def
            })
            
            # Combine defaults
            mask = (1 << width) - 1
            val = current_def & mask
            combined_default |= (val << current_shift)
            current_shift += width
            
        opts["bits"] = new_bits
        opts["default"] = combined_default
        return opts

class EnumConfigDialog(BaseConfigDialog):
    def __init__(self, current_options, project, parent=None):
        super().__init__(current_options, project, "Enum Config", parent)
        
        self.combo = QComboBox()
        self.project_enums = {e.name: e for e in project.enums}
        
        for name in self.project_enums.keys():
            self.combo.addItem(name)
        
        self.combo.currentTextChanged.connect(self.on_enum_changed)
        
        self.default_combo = QComboBox()
        
        cur = current_options.get("enum_name")
        if cur: 
            self.combo.setCurrentText(cur)
        
        # Trigger populate
        self.on_enum_changed(self.combo.currentText())
        
        # Set default
        cur_def = current_options.get("default")
        if cur_def is not None:
             self.set_default_by_val(cur_def)
             
        self.form.addRow("Select Enum", self.combo)
        self.form.addRow("Default Value", self.default_combo)
        
    def on_enum_changed(self, name):
        self.default_combo.clear()
        if name in self.project_enums:
            enum_def = self.project_enums[name]
            for item in enum_def.items:
                self.default_combo.addItem(f"{item.name} ({item.value})", item.value)
                
    def set_default_by_val(self, val):
        for i in range(self.default_combo.count()):
            if self.default_combo.itemData(i) == val:
                self.default_combo.setCurrentIndex(i)
                break

    def get_options(self):
        opts = self.get_base_options()
        opts["enum_name"] = self.combo.currentText()
        opts["default"] = self.default_combo.currentData()
        return opts

class ArrayConfigDialog(BaseConfigDialog):
    def __init__(self, current_options, project, fields_before: List[str], parent=None):
        super().__init__(current_options, project, "Array Config", parent)
        
        self.mode = QComboBox()
        self.mode.addItems(["Fixed", "Dynamic"])
        
        self.item_type = QComboBox()
        self.item_type.addItems([
            "UInt8", "UInt16", "UInt32", "UInt64",
            "Int8", "Int16", "Int32", "Int64",
            "Float32", "Float64", "String", "Enum", "BitField"
        ])
        
        self.count = QSpinBox()
        self.count.setRange(0, 99999)
        self.count.setValue(current_options.get("count", 0))
        
        self.count_field = QComboBox()
        self.count_field.addItems(fields_before)
        cur_cf = current_options.get("count_field")
        if cur_cf: self.count_field.setCurrentText(cur_cf)
        
        self.mode.setCurrentText(current_options.get("mode", "Fixed"))
        self.item_type.setCurrentText(current_options.get("item_type", "UInt8"))
        
        self.form.addRow("Mode", self.mode)
        self.form.addRow("Item Type", self.item_type)
        self.form.addRow("Fixed Count", self.count)
        self.form.addRow("Count Field (Dynamic)", self.count_field)
        
    def get_options(self):
        opts = self.get_base_options()
        opts.update({
            "mode": self.mode.currentText(),
            "count": self.count.value(),
            "count_field": self.count_field.currentText(),
            "item_type": self.item_type.currentText()
        })
        return opts

class FixedPointConfigDialog(BaseConfigDialog):
    def __init__(self, current_options, project, parent=None):
        super().__init__(current_options, project, "Fixed Point Config", parent)
        self.int_bits = QSpinBox()
        self.frac_bits = QSpinBox()
        
        self.encoding = QComboBox()
        self.encoding.addItems(["Unsigned", "Signed (2's Comp)", "Direction-Magnitude (MSB)"])
        
        self.default_val = QDoubleSpinBox()
        self.default_val.setRange(-999999, 999999)
        
        self.int_bits.setValue(current_options.get("integer_bits", 8))
        self.frac_bits.setValue(current_options.get("fractional_bits", 8))
        self.encoding.setCurrentIndex(current_options.get("encoding", 0))
        self.default_val.setValue(float(current_options.get("default", 0.0)))
        
        self.form.addRow("Default Value", self.default_val)
        self.form.addRow("Integer Bits", self.int_bits)
        self.form.addRow("Fractional Bits", self.frac_bits)
        self.form.addRow("Encoding", self.encoding)
        
    def get_options(self):
        opts = self.get_base_options()
        opts.update({
            "default": self.default_val.value(),
            "integer_bits": self.int_bits.value(),
            "fractional_bits": self.frac_bits.value(),
            "encoding": self.encoding.currentIndex()
        })
        return opts
