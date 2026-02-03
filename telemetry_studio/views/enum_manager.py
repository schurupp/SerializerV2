from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListView, QTableView, 
    QPushButton, QHeaderView, QSplitter
)
from telemetry_studio.qt_models import EnumListModel, EnumItemsModel
from telemetry_studio.data_models import ProjectDefinition
from telemetry_studio.widgets.checkable_combo import CheckableComboBox
from PySide6.QtWidgets import QLabel, QStyledItemDelegate, QLineEdit, QSpinBox
from PySide6.QtCore import Qt

class EnumItemDelegate(QStyledItemDelegate):
    def __init__(self, project_def, parent=None):
        super().__init__(parent)
        self.project = project_def
        
    def createEditor(self, parent, option, index):
        if index.column() == 1: # Value Column
            # User request: Always use generic text input, handle conversion in backend/model.
            return QLineEdit(parent)
        return super().createEditor(parent, option, index)
    
    def setEditorData(self, editor, index):
        # Default behavior is fine, but ensures lineEdit gets text
        super().setEditorData(editor, index)
    
    def setModelData(self, editor, model, index):
        # Validate for SpinBox happens automatically.
        # For LineEdit, model.setData handles validation (e.g. strict types)
        super().setModelData(editor, model, index)

class EnumManagerView(QWidget):
    def __init__(self, project_def: ProjectDefinition, parent=None):
        super().__init__(parent)
        self.project = project_def
        
        layout = QHBoxLayout(self)
        splitter = QSplitter()
        layout.addWidget(splitter)
        
        # Left: Enum List
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        self.enum_list = QListView()
        self.list_model = EnumListModel(self.project)
        self.enum_list.setModel(self.list_model)
        self.enum_list.clicked.connect(self.on_enum_selected)
        
        l_btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Enum")
        add_btn.clicked.connect(self.list_model.add_enum)
        del_btn = QPushButton("Remove")
        del_btn.clicked.connect(self.delete_enum)
        l_btn_layout.addWidget(add_btn)
        l_btn_layout.addWidget(del_btn)
        
        left_layout.addWidget(self.enum_list)
        left_layout.addLayout(l_btn_layout)
        
        # Right: Items Editor & Properties
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Properties
        props_layout = QHBoxLayout()
        props_layout.addWidget(QLabel("Active Configs:"))
        self.config_combo = CheckableComboBox()
        self.config_combo.model().dataChanged.connect(self.on_config_changed)
        props_layout.addWidget(self.config_combo)
        right_layout.addLayout(props_layout)
        
        self.items_table = QTableView()
        self.items_model = EnumItemsModel(project=self.project)
        self.items_table.setModel(self.items_model)
        self.items_table.setModel(self.items_model)
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # Custom Delegate
        self.items_delegate = EnumItemDelegate(self.project, self.items_table)
        self.items_table.setItemDelegate(self.items_delegate)
        
        r_btn_layout = QHBoxLayout()
        add_item_btn = QPushButton("Add Item")
        add_item_btn.clicked.connect(self.items_model.add_item)
        del_item_btn = QPushButton("Remove Item")
        del_item_btn.clicked.connect(self.delete_item)
        r_btn_layout.addWidget(add_item_btn)
        r_btn_layout.addWidget(del_item_btn)
        
        right_layout.addWidget(self.items_table)
        right_layout.addLayout(r_btn_layout)
        
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(1, 1)

    def on_enum_selected(self, index):
        row = index.row()
        enum_def = self.project.enums[row]
        self.items_model.set_enum(enum_def)
        
        # Update Configs
        self.config_combo.blockSignals(True)
        self.config_combo.clear()
        
        all_configs = [cfg.name for cfg in self.project.spl_configs]
        self.config_combo.addItems(sorted(all_configs))
        
        if enum_def.active_configs:
            self.config_combo.setCheckedItems(enum_def.active_configs)
            
        self.config_combo.blockSignals(False)

    def on_config_changed(self):
        enum_def = self.items_model.enum_def
        if not enum_def: return
        
        enum_def.active_configs = self.config_combo.checkedItems()
        
    def delete_enum(self):
        idx = self.enum_list.currentIndex()
        if idx.isValid():
            self.list_model.remove_enum(idx.row())
            self.items_model.set_enum(None)
            
    def delete_item(self):
        idx = self.items_table.currentIndex()
        if idx.isValid():
            self.items_model.remove_item(idx.row())
