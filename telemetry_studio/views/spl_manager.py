from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListView, QPushButton
)
from telemetry_studio.qt_models import SPLListModel
from telemetry_studio.data_models import ProjectDefinition

class SPLManagerView(QWidget):
    def __init__(self, project_def: ProjectDefinition, parent=None):
        super().__init__(parent)
        self.project = project_def
        
        layout = QVBoxLayout(self)
        self.list_view = QListView()
        self.model = SPLListModel(self.project)
        self.list_view.setModel(self.model)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Config")
        add_btn.clicked.connect(self.model.add_spl)
        del_btn = QPushButton("Remove")
        del_btn.clicked.connect(self.remove_spl)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)
        
        layout.addWidget(self.list_view)
        layout.addLayout(btn_layout)

    def remove_spl(self):
        idx = self.list_view.currentIndex()
        if idx.isValid():
            self.model.remove_spl(idx.row())
