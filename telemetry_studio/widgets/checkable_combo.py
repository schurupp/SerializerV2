from PySide6.QtWidgets import QComboBox, QStyledItemDelegate
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QStandardItemModel, QStandardItem, QPalette

class CheckableComboBox(QComboBox):
    class Delegate(QStyledItemDelegate):
        def sizeHint(self, option, index):
            size = super().sizeHint(option, index)
            size.setHeight(20)
            return size

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        self.lineEdit().installEventFilter(self)
        
        self.delegate = self.Delegate()
        self.setItemDelegate(self.delegate)
        
        self.model_ = QStandardItemModel(self)
        self.setModel(self.model_)
        
        # Connect signal to update display text
        self.model_.dataChanged.connect(self.update_display_text)
        
        # Keep popup open when clicking items?
        # QComboBox closes by default. We can use view().viewport().installEventFilter(self)?
        self.view().viewport().installEventFilter(self)

    def eventFilter(self, widget, event):
        # Prevent popup closing when clicking an item
        if widget == self.view().viewport():
            if event.type() == QEvent.MouseButtonRelease:
                index = self.view().indexAt(event.pos())
                item = self.model_.itemFromIndex(index)
                if item.flags() & Qt.ItemIsEnabled:
                    # Toggle check state
                    if item.checkState() == Qt.Checked:
                        item.setCheckState(Qt.Unchecked)
                    else:
                        item.setCheckState(Qt.Checked)
                    return True # Consume event to prevent close
        
        # Clicking line edit should show popup
        if widget == self.lineEdit() and event.type() == QEvent.MouseButtonPress:
             self.showPopup()
             return True

        return super().eventFilter(widget, event)

    def addItem(self, text, data=None):
        item = QStandardItem(text)
        item.setData(data)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
        item.setData(Qt.Unchecked, Qt.CheckStateRole)
        self.model_.appendRow(item)
        self.update_display_text()

    def addItems(self, texts):
        for text in texts:
            self.addItem(text)

    def update_display_text(self):
        checked_items = []
        for i in range(self.model_.rowCount()):
            item = self.model_.item(i)
            if item.checkState() == Qt.Checked:
                checked_items.append(item.text())
        
        text = ", ".join(checked_items) if checked_items else "None"
        self.lineEdit().setText(text)
        
    def checkedItems(self):
        """Returns list of checked item TEXTs"""
        checked = []
        for i in range(self.model_.rowCount()):
            item = self.model_.item(i)
            if item.checkState() == Qt.Checked:
                checked.append(item.text())
        return checked

    def setCheckedItems(self, items):
        """Sets checked state for items matching check_items list"""
        for i in range(self.model_.rowCount()):
            item = self.model_.item(i)
            if item.text() in items:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
        self.update_display_text()

    def clear(self):
        """Clear all items from the combobox"""
        self.model_.clear()
        self.update_display_text()

    def clearChecked(self):
        """Unchecks all items"""
        for i in range(self.model_.rowCount()):
            self.model_.item(i).setCheckState(Qt.Unchecked)
        self.update_display_text()
