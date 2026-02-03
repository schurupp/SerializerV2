from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox, 
    QDialogButtonBox, QCheckBox, QComboBox, QWidget, QListWidget, 
    QHBoxLayout, QPushButton, QInputDialog, QLabel, QDoubleSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from typing import Dict, Any, List
from telemetry_studio.data_models import FieldDefinition, EnumDefinition, ProjectDefinition
from telemetry_studio.widgets.checkable_combo import CheckableComboBox

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
        self.config_list = CheckableComboBox()
        
        # Populate
        all_configs = [cfg.name for cfg in self.project.spl_configs]
        self.config_list.addItems(sorted(all_configs))
        
        current_active = current_options.get("active_configs", [])
        if current_active:
             self.config_list.setCheckedItems(current_active)
        
        self.layout.addWidget(QLabel("Active Configs:"))
        self.layout.addWidget(self.config_list)
        
        # Actions
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)
        
    def get_base_options(self) -> Dict[str, Any]:
        # Collect active configs
        active = self.config_list.checkedItems()
        return {"active_configs": active}

class PrimitiveConfigDialog(BaseConfigDialog):
    def __init__(self, current_options, project, field_type="UInt32", available_fields=None, parent=None):
        super().__init__(current_options, project, f"{field_type} Config", parent)
        self.field_type = field_type
        self.available_fields = available_fields or []
        
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
             self.default_val.setRange(-2147483648, 2147483647)
             try:
                 val = current_options.get("default")
                 if val is not None: self.default_val.setValue(int(val))
             except: pass
             
        # Byte Order
        self.byte_order = QComboBox()
        self.byte_order.addItems(["Little Endian (<)", "Big Endian (>)"])
        b_order = current_options.get("byte_order", "<")
        self.byte_order.setCurrentIndex(1 if b_order == ">" else 0)

        self.checks = {
            "is_discriminator": QCheckBox("Is Discriminator"),
            "is_checksum": QCheckBox("Is Checksum"),
            "is_length": QCheckBox("Is Length"),
            "is_timestamp": QCheckBox("Is Timestamp"),
        }
        
        # Exclusive Logic
        self.checks["is_checksum"].toggled.connect(lambda c: self.on_exclusive_toggled("is_checksum", c))
        self.checks["is_length"].toggled.connect(lambda c: self.on_exclusive_toggled("is_length", c))
        self.checks["is_timestamp"].toggled.connect(lambda c: self.on_exclusive_toggled("is_timestamp", c))
        
        self.form.addRow("Default Value", self.default_val)
        
        if field_type != "Bool":
             self.form.addRow("Byte Order", self.byte_order)
             for k, v in self.checks.items():
                 if current_options.get(k): v.setChecked(True)
                 self.form.addRow(v)

             # Checksum Config
             self.checksum_widget = QWidget()
             self.checksum_layout = QFormLayout(self.checksum_widget)
             self.checksum_algo = QComboBox()
             self.checksum_algo.addItems(["CRC16", "CRC32", "XOR", "ByteSum", "ByteSum1C", "ByteSum2C", "AdditiveWord"])
             
             self.start_field = QComboBox()
             self.start_field.addItems(self.available_fields)
             self.end_field = QComboBox()
             self.end_field.addItems(self.available_fields)
             
             self.checksum_layout.addRow("Algorithm", self.checksum_algo)
             self.checksum_layout.addRow("Start Field", self.start_field)
             self.checksum_layout.addRow("End Field", self.end_field)
             
             self.form.addRow(self.checksum_widget)
             self.checksum_widget.setVisible(False)
             self.checks["is_checksum"].toggled.connect(self.checksum_widget.setVisible)
             
             # Load existing checksum opts
             if current_options.get("is_checksum"):
                 self.checksum_widget.setVisible(True)
                 self.checksum_algo.setCurrentText(current_options.get("algorithm", "CRC16"))
                 self.start_field.setCurrentText(current_options.get("start_field", ""))
                 self.end_field.setCurrentText(current_options.get("end_field", ""))

             # Timestamp Config
             self.timestamp_widget = QWidget()
             self.timestamp_layout = QFormLayout(self.timestamp_widget)
             self.time_resolution = QComboBox()
             self.time_resolution.addItems(["s", "ms"])
             self.timestamp_layout.addRow("Resolution", self.time_resolution)
             
             self.form.addRow(self.timestamp_widget)
             self.timestamp_widget.setVisible(False)
             self.checks["is_timestamp"].toggled.connect(self.timestamp_widget.setVisible)
             
             if current_options.get("is_timestamp"):
                 self.timestamp_widget.setVisible(True)
                 self.time_resolution.setCurrentText(current_options.get("resolution", "s"))
    
    def on_exclusive_toggled(self, name, checked):
        if not checked: return
        if name == "is_checksum":
            self.checks["is_timestamp"].setChecked(False)
            self.checks["is_length"].setChecked(False)
        elif name == "is_timestamp":
            self.checks["is_checksum"].setChecked(False)
            self.checks["is_length"].setChecked(False)
        elif name == "is_length":
            self.checks["is_checksum"].setChecked(False)
            self.checks["is_timestamp"].setChecked(False)

    def get_options(self):
        opts = self.get_base_options()
        if self.field_type == "Bool":
            opts["default"] = (self.default_val.currentIndex() == 1)
        else:
            opts["default"] = self.default_val.value()
            
        if self.field_type != "Bool":
            opts["byte_order"] = ">" if self.byte_order.currentIndex() == 1 else "<"
            for k, v in self.checks.items():
                if v.isChecked(): opts[k] = True
            
            if opts.get("is_checksum"):
                 opts["algorithm"] = self.checksum_algo.currentText()
                 opts["start_field"] = self.start_field.currentText()
                 opts["end_field"] = self.end_field.currentText()
                 
            if opts.get("is_timestamp"):
                 opts["resolution"] = self.time_resolution.currentText()
                 
            if opts.get("is_length"):
                 opts["start_field"] = self.len_start_field.currentText()
                 opts["end_field"] = self.len_end_field.currentText()
                  
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

        self.is_discriminator = QCheckBox("Is Discriminator")
        if current_options.get("is_discriminator"):
            self.is_discriminator.setChecked(True)
        self.form.addRow(self.is_discriminator)
        
    def get_options(self):
        opts = self.get_base_options()
        opts.update({
            "default": self.default_val.text(),
            "size_mode": self.mode.currentText(),
            "length": self.length.value(),
            "encoding": self.encoding.currentText(),
            "is_discriminator": self.is_discriminator.isChecked()
        })
        return opts

class BitFieldConfigDialog(BaseConfigDialog):
    def __init__(self, current_options, project, parent=None):
        super().__init__(current_options, project, "BitField Config", parent)
        
        self.bits = current_options.get("bits", [])
        self.project = project
        self.project_enums = [e.name for e in project.enums]
        
        # Byte Order
        self.byte_order = QComboBox()
        self.byte_order.addItems(["Little Endian (<)", "Big Endian (>)"])
        b_order = current_options.get("byte_order", "<")
        self.byte_order.setCurrentIndex(1 if b_order == ">" else 0)
        self.byte_order.setCurrentIndex(1 if b_order == ">" else 0)
        self.byte_order.setCurrentIndex(1 if b_order == ">" else 0)
        self.form.addRow("Byte Order", self.byte_order)
        
        # Bit Order
        self.bit_order = QComboBox()
        self.bit_order.addItems(["LSB", "MSB"])
        self.bit_order.setCurrentText(current_options.get("bit_order", "LSB"))
        self.form.addRow("Bit Order", self.bit_order)
        
        # Bit Order
        self.bit_order = QComboBox()
        self.bit_order.addItems(["LSB", "MSB"])
        self.bit_order.setCurrentText(current_options.get("bit_order", "LSB"))
        self.form.addRow("Bit Order", self.bit_order)
        
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
        
        self.layout.insertWidget(0, self.table) # Insert table above form/buttons? No strict order
        # Layout: [Title], Form(active configs), Table, Buttons
        # Our BaseConfigDialog puts Form first.
        # We can add table to layout.
        self.layout.addWidget(self.table)
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
        if enum_name in self.project.enums_dict: 
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
        opts["byte_order"] = ">" if self.byte_order.currentIndex() == 1 else "<"
        opts["bit_order"] = self.bit_order.currentText()
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
                current_def = def_w.currentData()
                if current_def is None: 
                     if def_w.count() > 0:
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
        self.storage_type = QComboBox()
        
        is_string_mode = getattr(project, 'protocol_mode', 'binary') == 'string'
        if is_string_mode:
            self.storage_type.addItems(["String"])
        else:
            self.storage_type.addItems(["UInt8", "Int8", "UInt16", "Int16", "UInt32", "Int32", "String"])
        
        cur = current_options.get("enum_name")
        if cur: 
            self.combo.setCurrentText(cur)
        
        st_type = current_options.get("storage_type", "UInt8")
        self.storage_type.setCurrentText(st_type)

        # Byte Order
        self.byte_order = QComboBox()
        self.byte_order.addItems(["Inherit", "Little Endian (<)", "Big Endian (>)"])
        
        cur_byte_order = current_options.get("byte_order", "Inherit")
        if cur_byte_order == "<": self.byte_order.setCurrentIndex(1)
        elif cur_byte_order == ">": self.byte_order.setCurrentIndex(2)
        else: self.byte_order.setCurrentIndex(0) # Inherit

        # Trigger populate
        self.on_enum_changed(self.combo.currentText())
        
        # Set default
        cur_def = current_options.get("default")
        if cur_def is not None:
             self.set_default_by_val(cur_def)
             
        self.form.addRow("Select Enum", self.combo)
        self.form.addRow("Default Value", self.default_combo)
        self.form.addRow("Default Value", self.default_combo)
        self.form.addRow("Storage Type", self.storage_type)
        self.form.addRow("Byte Order", self.byte_order)
        
        self.is_discriminator = QCheckBox("Is Discriminator")
        if current_options.get("is_discriminator"):
            self.is_discriminator.setChecked(True)
        self.form.addRow(self.is_discriminator)
        
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
        opts["storage_type"] = self.storage_type.currentText()
        opts["is_discriminator"] = self.is_discriminator.isChecked()
        
        idx = self.byte_order.currentIndex()
        if idx == 1: opts["byte_order"] = "<"
        elif idx == 2: opts["byte_order"] = ">"
        else:
             if "byte_order" in opts: del opts["byte_order"] # Inherit
             
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
        
        # Byte Order
        self.byte_order = QComboBox()
        self.byte_order.addItems(["Little Endian (<)", "Big Endian (>)"])
        b_order = current_options.get("byte_order", "<")
        self.byte_order.setCurrentIndex(1 if b_order == ">" else 0)
        
        self.int_bits.setValue(current_options.get("integer_bits", 8))
        self.frac_bits.setValue(current_options.get("fractional_bits", 8))
        self.encoding.setCurrentIndex(current_options.get("encoding", 0))
        self.default_val.setValue(float(current_options.get("default", 0.0)))
        
        self.form.addRow("Default Value", self.default_val)
        self.form.addRow("Byte Order", self.byte_order)
        self.form.addRow("Integer Bits", self.int_bits)
        self.form.addRow("Fractional Bits", self.frac_bits)
        self.form.addRow("Encoding", self.encoding)
        
    def get_options(self):
        opts = self.get_base_options()
        opts.update({
            "default": self.default_val.value(),
            "integer_bits": self.int_bits.value(),
            "fractional_bits": self.frac_bits.value(),
            "encoding": self.encoding.currentIndex(),
            "byte_order": ">" if self.byte_order.currentIndex() == 1 else "<"
        })
        return opts
