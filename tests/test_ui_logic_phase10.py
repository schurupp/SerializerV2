
import unittest
import sys
from PySide6.QtWidgets import QApplication
from telemetry_studio.data_models import ProjectDefinition, MessageDefinition, FieldDefinition
from telemetry_studio.views.editor import MessageEditorView, FieldTableWidget
from telemetry_studio.views.property_panel import FieldPropertyPanel

# Ensure QApplication exists
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

class TestPhase10UI(unittest.TestCase):
    def setUp(self):
        self.project = ProjectDefinition()
        self.msg = MessageDefinition(name="TestMsg")
        self.project.messages.append(self.msg)
        
        self.editor = MessageEditorView(self.project)
        self.editor.set_message(self.msg)
        
    def test_add_field_updates_table(self):
        # 1. Add Field via Editor
        self.editor.add_field()
        self.assertEqual(len(self.msg.fields), 1)
        self.assertEqual(self.editor.field_table.rowCount(), 1)
        self.assertEqual(self.msg.fields[0].name, "field_0")
        
    def test_panel_sync_to_model(self):
        # 1. Add Field
        self.editor.add_field() # field_0
        field = self.msg.fields[0]
        
        # 2. Simulate Selection (Editor does this on add)
        # Verify Panel is loaded
        panel = self.editor.property_panel
        self.assertEqual(panel.current_field, field)
        
        # 3. Simulate Edit in Panel
        panel.name_edit.setText("NewName")
        # Trigger signal manually or rely on signal connection if textChanged fired
        # setText triggers textChanged? Yes usually. 
        # But let's verify logic: _on_edit called -> writes to field -> emits fieldChanged -> Editor refreshes table
        
        self.assertEqual(field.name, "NewName")
        
        # Verify Table Updated
        item_name = self.editor.field_table.item(0, 0).text()
        self.assertEqual(item_name, "NewName")
        
    def test_discriminator_sync(self):
        self.editor.add_field() # field_0
        panel = self.editor.property_panel
        
        # 1. Toggle Discriminator in Panel
        # Simulating click
        panel.chk_discriminator.setChecked(True)
        # This triggers _on_edit AND discriminatorChanged
        
        # Verify Field Updated
        self.assertTrue(self.msg.fields[0].options['is_discriminator'])
        
        # Verify Header Table Updated
        # Header table is self.editor.disc_table
        self.assertEqual(self.editor.disc_table.rowCount(), 1)
        self.assertEqual(self.editor.disc_table.item(0, 0).text(), "field_0")
        
        # 2. Rename field -> Should sync?
        panel.name_edit.setText("SyncTest")
        # fieldChanged -> on_field_edited -> refresh_table
        
        # Verify Disc Table Updated
        self.assertEqual(self.editor.disc_table.item(0, 0).text(), "SyncTest")
        
    def test_field_deletion_sync(self):
        self.editor.add_field()
        panel = self.editor.property_panel
        panel.chk_discriminator.setChecked(True) # Make it a discriminator
        
        self.assertEqual(self.editor.disc_table.rowCount(), 1)
        
        # Delete Field
        self.editor.delete_field(0)
        
        self.assertEqual(len(self.msg.fields), 0)
        # Verify Disc Table Empty
        self.assertEqual(self.editor.disc_table.rowCount(), 0)

if __name__ == '__main__':
    unittest.main()
