from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableView, QPushButton, QHBoxLayout, 
    QHeaderView, QComboBox, QStyledItemDelegate, QLabel, QListWidget, QTableWidget, QTableWidgetItem, QMenu, QCheckBox
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, QModelIndex
from telemetry_studio.qt_models import FieldTableModel
from telemetry_studio.data_models import MessageDefinition, ProjectDefinition
from telemetry_studio.widgets.checkable_combo import CheckableComboBox

class TypeDelegate(QStyledItemDelegate):
    TYPES = [
        "UInt8", "Int8", "UInt16", "Int16", "UInt32", "Int32", 
        "UInt64", "Int64", "Float32", "Float64", "Bool",
        "String", "BitField", "Enum", "Array", "FixedPoint"
    ]
    STRING_TYPES = ["String", "Enum"]

    def __init__(self, editor_view):
        super().__init__(editor_view)
        self.editor = editor_view

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        
        mode = "binary"
        if self.editor.project_context:
            mode = getattr(self.editor.project_context, 'protocol_mode', 'binary')
            
        if mode == 'string':
            combo.addItems(self.STRING_TYPES)
        else:
            combo.addItems(self.TYPES)
        return combo
        
    def setEditorData(self, editor, index):
        val = index.model().data(index, Qt.EditRole)
        idx = editor.findText(val)
        if idx >= 0: editor.setCurrentIndex(idx)
    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.EditRole)

class MessageEditorView(QWidget):
    def __init__(self, context: ProjectDefinition, parent=None):
        super().__init__(parent)
        self.project_context = context
        self.current_msg = None
        self.model = None
        
        self.layout = QVBoxLayout(self)
        
        # 1. Header Area (Discriminator & Configs)
        self.header_layout = QHBoxLayout()
        
        # Discriminator Table
        disc_layout = QVBoxLayout()
        disc_layout.addWidget(QLabel("Discriminator Values:"))
        
        self.disc_table = QTableWidget(0, 2)
        self.disc_table.setHorizontalHeaderLabels(["Field", "Value (Hex)"])
        disc_layout.addWidget(self.disc_table)
        
        # Message Configs
        config_layout = QVBoxLayout()
        config_layout.addWidget(QLabel("Active Message Configs:"))
        self.msg_configs = CheckableComboBox()
        # Populate later based on project SPL configs
        self.msg_configs.model().dataChanged.connect(self.on_config_changed)
        config_layout.addWidget(self.msg_configs)
        
        self.header_layout.addLayout(disc_layout)
        self.header_layout.addLayout(config_layout)
        self.layout.addLayout(self.header_layout)
        
        # 2. Main Editor Toolbar
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add Field")
        self.btn_add.clicked.connect(self.add_field)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addStretch()
        self.layout.addLayout(btn_layout)
        
        # 3. Table
        self.table = QTableView()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(self.table)
        
        self.table.clicked.connect(self.on_table_click)

    def set_message(self, msg_def: MessageDefinition):
        self.current_msg = msg_def
        self.model = FieldTableModel(msg_def)
        
        # Connect signals for Updates
        self.model.dataChanged.connect(lambda: self.refresh_header())
        self.model.rowsInserted.connect(lambda: self.refresh_header())
        self.model.rowsRemoved.connect(lambda: self.refresh_header())
        self.model.modelReset.connect(lambda: self.refresh_header())
        
        self.model.modelReset.connect(lambda: self.refresh_header())
        
        self.table.setModel(self.model)
        self.table.setItemDelegateForColumn(1, TypeDelegate(self))
        
        self.refresh_header()
        


    def refresh_header(self):
        if not self.current_msg: return
        
        # Active Configs
        self.msg_configs.blockSignals(True)
        self.msg_configs.clear()
        
        all_tags = []
        if self.project_context:
            for spl in self.project_context.spl_configs:
                all_tags.append(spl.config_id)
        
        self.msg_configs.addItems(sorted(all_tags))
        
        if self.current_msg.active_configs:
            self.msg_configs.setCheckedItems(self.current_msg.active_configs)
            
        self.msg_configs.blockSignals(False)
                
        # Discriminators
        self.disc_table.setRowCount(0)
        row = 0
        for f in self.current_msg.fields:
            if f.options.get("is_discriminator"):
                self.disc_table.insertRow(row)
                self.disc_table.setItem(row, 0, QTableWidgetItem(f.name))
                val = f.options.get("default", 0)
                self.disc_table.setItem(row, 1, QTableWidgetItem(hex(val) if isinstance(val, int) else str(val)))
                row += 1

    def on_config_changed(self):
        if not self.current_msg: return
        self.current_msg.active_configs = self.msg_configs.checkedItems()

    def add_field(self):
        if self.model: self.model.add_field()

    def on_table_click(self, index: QModelIndex):
        col = index.column()
        row = index.row()
        
        if col == 2: # Config
            self.open_config_dialog(row)
        elif col == 3: # Context Menu
            menu = QMenu(self)
            act_up = menu.addAction("Move Up")
            act_down = menu.addAction("Move Down")
            act_del = menu.addAction("Delete")
            
            res = menu.exec(self.table.viewport().mapToGlobal(self.table.visualRect(index).center()))
            
            if res == act_up:
                self.model.move_row(row, -1)
            elif res == act_down:
                self.model.move_row(row, 1)
            elif res == act_del:
                self.model.remove_field(row)
                self.refresh_header()

    def open_config_dialog(self, row):
        from telemetry_studio.views.dialogs import (
            PrimitiveConfigDialog, StringConfigDialog, BitFieldConfigDialog, 
            EnumConfigDialog, ArrayConfigDialog, FixedPointConfigDialog
        )
        
        field_def = self.model.msg_def.fields[row]
        ftype = field_def.field_type
        
        # Map types...
        dlg = None
        if ftype in ["UInt8", "Int8", "UInt16", "Int16", "UInt32", "Int32", 
                     "UInt64", "Int64", "Float32", "Float64", "Bool"]:
            all_fields = [f.name for f in self.current_msg.fields]
            dlg = PrimitiveConfigDialog(field_def.options, self.project_context, ftype, all_fields, self)
        elif ftype == "String":
            dlg = StringConfigDialog(field_def.options, self.project_context, self)
        elif ftype == "BitField":
            dlg = BitFieldConfigDialog(field_def.options, self.project_context, self)
        elif ftype == "Enum":
            dlg = EnumConfigDialog(field_def.options, self.project_context, self)
        elif ftype == "Array":
            prev = [f.name for i, f in enumerate(self.current_msg.fields) if i < row]
            dlg = ArrayConfigDialog(field_def.options, self.project_context, prev, self)
        elif ftype == "FixedPoint":
            dlg = FixedPointConfigDialog(field_def.options, self.project_context, self)
            
        if dlg:
            if dlg.exec():
                field_def.options.update(dlg.get_options())
                self.refresh_header()
                index = self.model.index(row, 2)
                self.model.dataChanged.emit(index, index, [Qt.DisplayRole])
