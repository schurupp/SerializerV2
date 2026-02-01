import sys
import os

# Ensure project root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget, 
    QSplitter, QListView, QPushButton, QHBoxLayout, QMenuBar, QMenu, QFileDialog, QMessageBox
)
from PySide6.QtGui import QAction
from telemetry_studio.data_models import ProjectDefinition
from telemetry_studio.qt_models import MessageListModel
from telemetry_studio.views.editor import MessageEditorView
from telemetry_studio.views.enum_manager import EnumManagerView
from telemetry_studio.views.spl_manager import SPLManagerView
from telemetry_studio.project_io import ProjectIO
from telemetry_studio.codegen import CodeGenerator
from telemetry_studio.importer import PythonImporter

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Telemetry Studio V2")
        self.resize(1200, 800)
        
        # Singleton Project State
        self.project = ProjectDefinition()
        
        # UI Components
        self.setup_menu()
        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Top Tab Widget: [Messages] [Enums] [SPL Manager]
        self.main_tabs = QTabWidget()
        main_layout.addWidget(self.main_tabs)
        
        # 1. Message Tab (Sidebar + Editor)
        self.message_tab = QWidget()
        self.setup_message_tab()
        self.main_tabs.addTab(self.message_tab, "Messages")
        
        # 2. Enum Manager
        self.enum_manager = EnumManagerView(self.project)
        self.main_tabs.addTab(self.enum_manager, "Enum Manager")
        
        # 3. SPL Manager
        self.spl_manager = SPLManagerView(self.project)
        self.main_tabs.addTab(self.spl_manager, "SPL Manager")

    def setup_message_tab(self):
        layout = QHBoxLayout(self.message_tab)
        splitter = QSplitter()
        layout.addWidget(splitter)
        
        # Sidebar: Message List
        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_widget)
        
        self.msg_list_view = QListView()
        self.msg_list_model = MessageListModel(self.project)
        self.msg_list_view.setModel(self.msg_list_model)
        self.msg_list_view.clicked.connect(self.on_message_selected)
        
        sb_btns = QHBoxLayout()
        add_msg_btn = QPushButton("New Message")
        add_msg_btn.clicked.connect(self.add_message)
        del_msg_btn = QPushButton("Delete")
        del_msg_btn.clicked.connect(self.delete_message)
        sb_btns.addWidget(add_msg_btn)
        sb_btns.addWidget(del_msg_btn)
        
        sidebar_layout.addWidget(self.msg_list_view)
        sidebar_layout.addLayout(sb_btns)
        
        # Editor Area
        self.editor_view = MessageEditorView(context=self.project)
        
        splitter.addWidget(sidebar_widget)
        splitter.addWidget(self.editor_view)
        splitter.setStretchFactor(1, 1)

    def setup_menu(self):
        menu = self.menuBar().addMenu("&File")
        
        act_save = menu.addAction("Save Project (.json)")
        act_save.triggered.connect(self.save_project)
        
        act_load = menu.addAction("Load Project (.json)")
        act_load.triggered.connect(self.load_project)
        
        menu.addSeparator()
        
        act_export = menu.addAction("Export Python Code")
        act_export.triggered.connect(self.export_python)
        
        act_import = menu.addAction("Import Python Code")
        act_import.triggered.connect(self.import_python)

    def save_project(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Project", "", "JSON Files (*.json)")
        if path:
            try:
                ProjectIO.save_project(self.project, path)
                QMessageBox.information(self, "Success", "Project saved successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save: {e}")

    def load_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Project", "", "JSON Files (*.json)")
        if path:
            try:
                new_proj = ProjectIO.load_project(path)
                # Replace singleton state
                self.project.messages[:] = new_proj.messages
                self.project.enums[:] = new_proj.enums
                self.project.spl_configs[:] = new_proj.spl_configs
                
                # Refresh views
                self.msg_list_model.modelReset.emit()
                self.enum_manager.list_model.modelReset.emit()
                self.spl_manager.model.modelReset.emit()
                self.editor_view.set_message(None)
                
                QMessageBox.information(self, "Success", "Project loaded.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load: {e}")
                
    def export_python(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Python", "", "Python Files (*.py)")
        if path:
            try:
                gen = CodeGenerator(self.project)
                msgs = gen.generate_messages()
                enums = gen.generate_enums()
                
                import os
                d = os.path.dirname(path)
                
                with open(path, 'w') as f:
                    f.write(msgs)
                    
                enum_path = os.path.join(d, "enums.py")
                with open(enum_path, 'w') as f:
                    f.write(enums)
                    
                QMessageBox.information(self, "Success", f"Exported to {path} and {enum_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed: {e}")

    def import_python(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Messages", "", "Python Files (*.py)")
        if path:
            try:
                enum_path = None
                import os
                d = os.path.dirname(path)
                e_cand = os.path.join(d, "enums.py")
                if os.path.exists(e_cand):
                    enum_path = e_cand
                    
                imp = PythonImporter()
                new_proj = imp.import_files(path, enum_path)
                
                self.project.messages[:] = new_proj.messages
                self.project.enums[:] = new_proj.enums
                
                seen_spl = set()
                for m in self.project.messages:
                    for c in m.active_configs:
                        seen_spl.add(c)
                from telemetry_studio.data_models import SPLDefinition
                self.project.spl_configs[:] = [SPLDefinition(name=s) for s in seen_spl]
                
                self.msg_list_model.modelReset.emit()
                self.enum_manager.list_model.modelReset.emit()
                self.spl_manager.model.modelReset.emit()
                self.editor_view.set_message(None)
                
                QMessageBox.information(self, "Success", "Import successful.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Import failed: {e}")

    def add_message(self):
        self.msg_list_model.add_message()
        
    def delete_message(self):
        idx = self.msg_list_view.currentIndex()
        if idx.isValid():
            self.msg_list_model.remove_message(idx.row())
            self.editor_view.set_message(None)

    def on_message_selected(self, index):
        row = index.row()
        msg_def = self.project.messages[row]
        self.editor_view.set_message(msg_def)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
