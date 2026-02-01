from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListView, QTableView, 
    QPushButton, QHeaderView, QSplitter
)
from telemetry_studio.qt_models import EnumListModel, EnumItemsModel
from telemetry_studio.data_models import ProjectDefinition

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
        
        # Right: Items Editor
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        self.items_table = QTableView()
        self.items_model = EnumItemsModel()
        self.items_table.setModel(self.items_model)
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
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
        
    def delete_enum(self):
        idx = self.enum_list.currentIndex()
        if idx.isValid():
            self.list_model.remove_enum(idx.row())
            self.items_model.set_enum(None)
            
    def delete_item(self):
        idx = self.items_table.currentIndex()
        if idx.isValid():
            self.items_model.remove_item(idx.row())
