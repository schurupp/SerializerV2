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
from telemetry_studio.views.protocol_config import ProtocolSettingsDialog
from telemetry_studio.views.mode_selection import ModeSelectionDialog
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
        
        # Init Dialog check
        # Postpone slightly to ensure window is ready? Or just exec
        # But we need to do this after UI setup so reset works.
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self.check_initial_setup)

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
        
        act_proto = menu.addAction("Protocol Configuration")
        act_proto.triggered.connect(self.open_protocol_config)
        
        act_switch = menu.addAction("Switch Protocol Mode...")
        act_switch.triggered.connect(self.switch_protocol_mode)
        
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
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load: {e}")

    def open_protocol_config(self):
        dlg = ProtocolSettingsDialog(self, self.project)
        if dlg.exec():
            dlg.apply_settings()
            QMessageBox.information(self, "Settings", "Protocol settings updated.")
                
    def check_initial_setup(self):
        # Always ask on startup for new session logic?
        # Or only if empty?
        # User requirement: "Ask on initialization"
        if not self.project.messages:
             self.switch_protocol_mode(force_init=True)

    def switch_protocol_mode(self, force_init=False):
        if not force_init:
            # Confirm reset
            ret = QMessageBox.warning(
                self, "Switch Mode", 
                "Switching protocol mode will RESET the current project.\nUnsaved changes will be lost.\n\nDo you want to continue?",
                QMessageBox.Yes | QMessageBox.No
            )
            if ret == QMessageBox.No:
                return

        current_endian = getattr(self.project, 'global_endianness', 'Little')
        dlg = ModeSelectionDialog(self, self.project.protocol_mode, current_endian)
        if dlg.exec():
            selected_mode = dlg.selected_mode
            selected_endian = dlg.selected_endian
            
            # Reset Project
            self.project = ProjectDefinition(protocol_mode=selected_mode)
            self.project.global_endianness = selected_endian
            
            # Refresh All Views
            self.msg_list_model.project = self.project # Update ref
            self.msg_list_model.modelReset.emit() # Signal reset
            
            self.editor_view.project_context = self.project
            self.editor_view.refresh_view()
            self.editor_view.set_message(None)
            
            # Enums/SPL
            # We need to update their references too!
            # They hold 'self.project' reference?
            # Check views __init__. They store 'project'.
            
            self.enum_manager.project = self.project
            self.enum_manager.list_model.project = self.project
            self.enum_manager.list_model.modelReset.emit()
            
            self.spl_manager.project = self.project
            self.spl_manager.model.project = self.project
            self.spl_manager.model.modelReset.emit()
            
            self.setWindowTitle(f"Telemetry Studio V2 [{selected_mode.upper()}]")
            
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
