from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableView, QPushButton, QHBoxLayout, 
    QHeaderView, QComboBox, QStyledItemDelegate, QLabel, QListWidget, 
    QTableWidget, QTableWidgetItem, QMenu, QCheckBox, QSplitter, QAbstractItemView,
    QFrame
)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Qt, QModelIndex, Signal, QSize
from telemetry_studio.qt_models import FieldTableModel
from telemetry_studio.data_models import MessageDefinition, ProjectDefinition
from telemetry_studio.widgets.checkable_combo import CheckableComboBox
from telemetry_studio.views.property_panel import FieldPropertyPanel

# Reusing TypeDelegate if needed, but editing is now in Panel.
# We might keep TypeDelegate for quick Type changing in the table if desired, 
# but requirement says "FieldPropertyPanel (Editable Details)". 
# Let's make Table mostly for structure management.

class FieldTableWidget(QTableWidget):
    """
    Compact List View: Name, Type, SPL, Actions
    """
    fieldSelected = Signal(int) # Row
    fieldMoved = Signal(int, int) # From, To
    fieldDeleted = Signal(int) # Row
    
    def __init__(self, parent=None):
        super().__init__(0, 4, parent)
        self.setHorizontalHeaderLabels(["Name", "Type", "Active Configs", "Actions"])
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.setColumnWidth(3, 90)
        
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setAlternatingRowColors(True)
        
        self.itemClicked.connect(self._on_click)
        self.currentItemChanged.connect(self._on_change)
        
    def _on_click(self, item):
        self.fieldSelected.emit(item.row())
        
    def _on_change(self, current, previous):
        if current:
            self.fieldSelected.emit(current.row())

    def refresh(self, fields: list):
        current_row = self.currentRow()
        self.setRowCount(0)
        
        for i, f in enumerate(fields):
            self.insertRow(i)
            # Name
            self.setItem(i, 0, QTableWidgetItem(f.name))
            # Type
            self.setItem(i, 1, QTableWidgetItem(f.field_type))
            # SPL
            spls = ",".join(f.options.get("active_configs", []))
            self.setItem(i, 2, QTableWidgetItem(spls))
            
            # Actions: Up/Down/Del
            # Need a widget container
            w = QWidget()
            layout = QHBoxLayout(w)
            layout.setContentsMargins(2, 2, 2, 2)
            layout.setSpacing(2)
            
            # Simple text buttons for now to avoid Icon resource dependency issues 
            # unless we use standard style icons
            btn_up = QPushButton("▲")
            btn_up.setFixedSize(20, 20)
            btn_up.setToolTip("Move Up")
            btn_up.clicked.connect(lambda _, r=i: self.fieldMoved.emit(r, -1))
            
            btn_down = QPushButton("▼")
            btn_down.setFixedSize(20, 20)
            btn_down.setToolTip("Move Down")
            btn_down.clicked.connect(lambda _, r=i: self.fieldMoved.emit(r, 1))
            
            btn_del = QPushButton("✖")
            btn_del.setFixedSize(20, 20)
            btn_del.setToolTip("Delete")
            btn_del.setStyleSheet("color: red;")
            btn_del.clicked.connect(lambda _, r=i: self.fieldDeleted.emit(r))
            
            if i == 0: btn_up.setEnabled(False)
            if i == len(fields) - 1: btn_down.setEnabled(False)
            
            layout.addWidget(btn_up)
            layout.addWidget(btn_down)
            layout.addWidget(btn_del)
            self.setCellWidget(i, 3, w)
            
        if current_row >= 0 and current_row < self.rowCount():
             self.selectRow(current_row)

class MessageEditorView(QWidget):
    def __init__(self, context: ProjectDefinition, parent=None):
        super().__init__(parent)
        self.project_context = context
        self.current_msg = None
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        
        # 1. Header Area (Discriminator & Configs)
        self.header_layout = QHBoxLayout()
        
        # Left Header: Discriminator Table
        disc_frame = QFrame()
        disc_frame.setFrameShape(QFrame.StyledPanel)
        disc_layout = QVBoxLayout(disc_frame)
        disc_layout.addWidget(QLabel("Discriminator Values:"))
        
        self.disc_table = QTableWidget(0, 2)
        self.disc_table.setHorizontalHeaderLabels(["Field", "Value (Hex/Str)"])
        self.disc_table.itemChanged.connect(self.on_disc_changed)
        self.disc_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.disc_table.setMaximumHeight(100)
        disc_layout.addWidget(self.disc_table)
        
        # Middle Header: SPL Configs
        config_frame = QFrame()
        config_frame.setFrameShape(QFrame.StyledPanel)
        config_layout = QVBoxLayout(config_frame)
        config_layout.addWidget(QLabel("Active Message Configs:"))
        self.msg_configs = CheckableComboBox()
        self.msg_configs.model().dataChanged.connect(self.on_config_changed)
        config_layout.addWidget(self.msg_configs)
        config_layout.addStretch()
        
        # Right Header: Endianness
        self.endian_widget = QFrame()
        self.endian_widget.setFrameShape(QFrame.StyledPanel)
        endian_layout = QVBoxLayout(self.endian_widget)
        endian_layout.addWidget(QLabel("Endianness:"))
        self.endian_combo = QComboBox()
        self.endian_combo.addItems(["Inherit", "Little", "Big"])
        self.endian_combo.currentTextChanged.connect(self.on_endian_changed)
        endian_layout.addWidget(self.endian_combo)
        endian_layout.addStretch()
        
        if self.project_context.protocol_mode == 'string':
            self.endian_widget.setVisible(False)
            
        self.header_layout.addWidget(disc_frame, stretch=1)
        self.header_layout.addWidget(config_frame, stretch=1)
        self.header_layout.addWidget(self.endian_widget, stretch=1)
        
        self.layout.addLayout(self.header_layout)
        
        # 2. Splitter Area
        self.splitter = QSplitter(Qt.Horizontal)
        
        # Left Panel: Table + Add Button
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.btn_add = QPushButton("Add Field (+)")
        self.btn_add.clicked.connect(self.add_field)
        
        self.field_table = FieldTableWidget()
        self.field_table.fieldSelected.connect(self.on_field_selected)
        self.field_table.fieldMoved.connect(self.move_field)
        self.field_table.fieldDeleted.connect(self.delete_field)
        
        left_layout.addWidget(self.btn_add)
        left_layout.addWidget(self.field_table)
        
        # Right Panel: Property Editor
        self.property_panel = FieldPropertyPanel(self.project_context)
        self.property_panel.fieldChanged.connect(self.on_field_edited)
        self.property_panel.discriminatorChanged.connect(self.refresh_header)
        
        self.splitter.addWidget(left_widget)
        self.splitter.addWidget(self.property_panel)
        self.splitter.setStretchFactor(0, 1) # Table
        self.splitter.setStretchFactor(1, 2) # Panel (Give more space)
        
        self.property_panel.setVisible(False) # Default hidden
        
        self.layout.addWidget(self.splitter)
        
    def set_message(self, msg_def: MessageDefinition):
        self.current_msg = msg_def
        
        # Refresh Header
        self.refresh_header()
        
        # Refresh Table
        self.refresh_table()
        
        # Select first if exists
        if msg_def and msg_def.fields:
            self.property_panel.setVisible(True)
            self.item_selected(0)
        else:
             self.property_panel.setVisible(False)

    def refresh_header(self):
        if not self.current_msg: return
        
        # Active Configs
        self.msg_configs.blockSignals(True)
        self.msg_configs.clear()
        
        all_tags = []
        if self.project_context:
            for spl in self.project_context.spl_configs:
                all_tags.append(spl.name)
        
        self.msg_configs.addItems(sorted(all_tags))
        
        if self.current_msg.active_configs:
            self.msg_configs.setCheckedItems(self.current_msg.active_configs)
        self.msg_configs.blockSignals(False)
        
        # Endianness
        self.endian_combo.blockSignals(True)
        end = getattr(self.current_msg, 'endianness', 'Inherit')
        self.endian_combo.setCurrentText(end if end else 'Inherit')
        self.endian_combo.blockSignals(False)
        
        # Discriminators
        self.disc_table.blockSignals(True)
        self.disc_table.setRowCount(0)
        row = 0
        
        is_string_mode = (self.project_context.protocol_mode == "string")
             
        for f in self.current_msg.fields:
            is_disc = f.options.get("is_discriminator")
            if is_string_mode and f.name in ["cmd_type", "cmd_str"]:
                is_disc = True
                f.options["is_discriminator"] = True
                
            if is_disc:
                self.disc_table.insertRow(row)
                item_name = QTableWidgetItem(f.name)
                item_name.setFlags(item_name.flags() ^ Qt.ItemIsEditable) 
                self.disc_table.setItem(row, 0, item_name)
                
                val = f.options.get("default", 0)
                val_str = str(val)
                if isinstance(val, int) and not is_string_mode:
                    val_str = hex(val)
                    
                self.disc_table.setItem(row, 1, QTableWidgetItem(val_str))
                row += 1
        self.disc_table.blockSignals(False)

    def refresh_table(self):
        if self.current_msg:
             self.field_table.refresh(self.current_msg.fields)

    def on_field_selected(self, row):
        self.item_selected(row)
        
    def item_selected(self, row):
        if not self.current_msg or row >= len(self.current_msg.fields): return
        field = self.current_msg.fields[row]
        
        # Gather all field names for references
        all_names = [f.name for f in self.current_msg.fields]
        self.property_panel.set_field(field, all_names)
        
    def on_field_edited(self):
        # Triggered when PropertyPanel changes something
        # Need to update Table Row (Name, Type changed?)
        row = self.field_table.currentRow()
        if row >= 0:
             # Optimization: Just update specific row logic if possible?
             # For now refresh table to be safe
             self.refresh_table()
             # Also refresh header (Discriminator names might have changed)
             self.refresh_header()
             # Restore selection
             self.field_table.selectRow(row)
             
    def add_field(self):
        if not self.current_msg: return
        from telemetry_studio.data_models import FieldDefinition
        # Default to 0 for new fields
        new_field = FieldDefinition(name=f"field_{len(self.current_msg.fields)}", options={"default": 0})
        self.current_msg.fields.append(new_field)
        self.refresh_table()
        # Select new
        last = len(self.current_msg.fields) - 1
        self.property_panel.setVisible(True)
        self.field_table.selectRow(last)
        self.item_selected(last)
        
    def move_field(self, row, direction):
        if not self.current_msg: return
        new_row = row + direction
        if 0 <= new_row < len(self.current_msg.fields):
            self.current_msg.fields[row], self.current_msg.fields[new_row] = \
                self.current_msg.fields[new_row], self.current_msg.fields[row]
            self.refresh_table()
            self.field_table.selectRow(new_row)
            
    def delete_field(self, row):
        if not self.current_msg: return
        del self.current_msg.fields[row]
        self.refresh_table()
        self.refresh_header() # Sync discriminators
        if self.current_msg.fields:
             idx = min(row, len(self.current_msg.fields)-1)
             self.field_table.selectRow(idx)
             self.item_selected(idx)
        else:
             self.property_panel.setVisible(False)

    def on_disc_changed(self, item):
        if item.column() != 1: return
        row = item.row()
        field_name = self.disc_table.item(row, 0).text()
        
        field = next((f for f in self.current_msg.fields if f.name == field_name), None)
        if field:
            val_str = item.text()
            if self.project_context.protocol_mode != "string":
                try:
                    val = int(val_str, 0)
                    field.options["default"] = val
                except ValueError: pass
            else:
                 field.options["default"] = val_str
                 
    def on_config_changed(self):
        if not self.current_msg: return
        self.current_msg.active_configs = self.msg_configs.checkedItems()
        
    def on_endian_changed(self, text):
        if not self.current_msg: return
        self.current_msg.endianness = text

    def refresh_view(self):
        if not self.project_context: return
        is_string = self.project_context.protocol_mode == 'string'
        self.endian_widget.setVisible(not is_string)
