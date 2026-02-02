from PySide6.QtCore import QAbstractTableModel, QAbstractListModel, Qt, QModelIndex
from typing import Any, List
from telemetry_studio.data_models import MessageDefinition, FieldDefinition, ProjectDefinition, EnumDefinition, EnumItem, SPLDefinition

# --- Message Editor Models ---

class FieldTableModel(QAbstractTableModel):
    HEADERS = ["Field Name", "Type", "Config", "Actions"]
    
    def __init__(self, message_def: MessageDefinition = None, parent=None):
        super().__init__(parent)
        self.msg_def = message_def

    def set_message(self, message_def: MessageDefinition):
        self.beginResetModel()
        self.msg_def = message_def
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self.msg_def.fields) if self.msg_def else 0

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.HEADERS)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None
        
        row = index.row()
        col = index.column()
        field_def = self.msg_def.fields[row]
        
        if role == Qt.DisplayRole or role == Qt.EditRole:
            if col == 0:
                return field_def.name
            elif col == 1:
                return field_def.field_type
            elif col == 2:
                return str(field_def.options) if field_def.options else "Default"
            elif col == 3:
                return "" 
        
        return None

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        if not index.isValid() or role != Qt.EditRole:
            return False
            
        row = index.row()
        col = index.column()
        field_def = self.msg_def.fields[row]
        
        if col == 0:
            field_def.name = value
            self.dataChanged.emit(index, index, [role])
            return True
        elif col == 1:
            field_def.field_type = value
            self.dataChanged.emit(index, index, [role])
            return True
            
        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid(): return Qt.NoItemFlags
        col = index.column()
        base = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if col in [0, 1]: return base | Qt.ItemIsEditable
        return base

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return None
        
    def add_field(self):
        self.beginInsertRows(QModelIndex(), len(self.msg_def.fields), len(self.msg_def.fields))
        self.msg_def.fields.append(FieldDefinition())
        self.endInsertRows()
        
    def remove_field(self, row: int):
        self.beginRemoveRows(QModelIndex(), row, row)
        del self.msg_def.fields[row]
        self.endRemoveRows()
        
    def move_row(self, row: int, direction: int):
        new_row = row + direction
        if 0 <= new_row < len(self.msg_def.fields):
            self.beginMoveRows(QModelIndex(), row, row, QModelIndex(), new_row + (1 if direction > 0 else 0))
            self.msg_def.fields[row], self.msg_def.fields[new_row] = self.msg_def.fields[new_row], self.msg_def.fields[row]
            self.endMoveRows()

# --- Sidebar Models ---

class MessageListModel(QAbstractListModel):
    def __init__(self, project: ProjectDefinition, parent=None):
        super().__init__(parent)
        self.project = project

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self.project.messages)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid(): return None
        if role == Qt.DisplayRole or role == Qt.EditRole:
            return self.project.messages[index.row()].name
        return None

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        if role == Qt.EditRole:
            self.project.messages[index.row()].name = value
            self.dataChanged.emit(index, index, [role])
            return True
        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def add_message(self):
        self.beginInsertRows(QModelIndex(), len(self.project.messages), len(self.project.messages))
        msg = MessageDefinition("NewMessage")
        
        # Check Global Protocol Mode
        if getattr(self.project, 'protocol_mode', 'binary') == 'string':
            msg.protocol_mode = 'string'
            # Auto-add mandatory fields
            msg.fields.append(FieldDefinition(name="cmd_type", field_type="String", options={'default': "CMD"}))
            msg.fields.append(FieldDefinition(name="cmd_str", field_type="String", options={'default': "SUB"}))
            
        self.project.messages.append(msg)
        self.endInsertRows()

    def remove_message(self, row: int):
        self.beginRemoveRows(QModelIndex(), row, row)
        del self.project.messages[row]
        self.endRemoveRows()

# --- Enum Manager Models ---

class EnumListModel(QAbstractListModel):
    def __init__(self, project: ProjectDefinition, parent=None):
        super().__init__(parent)
        self.project = project

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self.project.enums)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid(): return None
        if role == Qt.DisplayRole or role == Qt.EditRole:
            return self.project.enums[index.row()].name
        return None
        
    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        if role == Qt.EditRole:
            self.project.enums[index.row()].name = value
            self.dataChanged.emit(index, index, [role])
            return True
        return False
        
    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def add_enum(self):
        self.beginInsertRows(QModelIndex(), len(self.project.enums), len(self.project.enums))
        self.project.enums.append(EnumDefinition("NewEnum"))
        self.endInsertRows()
        
    def remove_enum(self, row: int):
        self.beginRemoveRows(QModelIndex(), row, row)
        del self.project.enums[row]
        self.endRemoveRows()

class EnumItemsModel(QAbstractTableModel):
    HEADERS = ["Name", "Value"]
    
    def __init__(self, enum_def: EnumDefinition = None, parent=None):
        super().__init__(parent)
        self.enum_def = enum_def

    def set_enum(self, enum_def: EnumDefinition):
        self.beginResetModel()
        self.enum_def = enum_def
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self.enum_def.items) if self.enum_def else 0

    def columnCount(self, parent=QModelIndex()) -> int:
        return 2

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not self.enum_def or not index.isValid(): return None
        item = self.enum_def.items[index.row()]
        
        if role == Qt.DisplayRole or role == Qt.EditRole:
            if index.column() == 0: return item.name
            if index.column() == 1: return item.value
        return None
        
    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        if not self.enum_def: return False
        item = self.enum_def.items[index.row()]
        if index.column() == 0:
            item.name = value
        elif index.column() == 1:
            try:
                item.value = int(value)
            except:
                return False
        self.dataChanged.emit(index, index, [role])
        return True

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return None

    def add_item(self):
        if not self.enum_def: return
        self.beginInsertRows(QModelIndex(), len(self.enum_def.items), len(self.enum_def.items))
        self.enum_def.items.append(EnumItem("ITEM", 0))
        self.endInsertRows()
        
    def remove_item(self, row: int):
        if not self.enum_def: return
        self.beginRemoveRows(QModelIndex(), row, row)
        del self.enum_def.items[row]
        self.endRemoveRows()

# --- SPL Config Models ---

class SPLListModel(QAbstractListModel):
    def __init__(self, project: ProjectDefinition, parent=None):
        super().__init__(parent)
        self.project = project

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self.project.spl_configs) 

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid(): return None
        if role == Qt.DisplayRole or role == Qt.EditRole:
            return self.project.spl_configs[index.row()].name
        return None

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        if role == Qt.EditRole:
            self.project.spl_configs[index.row()].name = value
            self.dataChanged.emit(index, index, [role])
            return True
        return False
        
    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def add_spl(self):
        self.beginInsertRows(QModelIndex(), len(self.project.spl_configs), len(self.project.spl_configs))
        self.project.spl_configs.append(SPLDefinition("Config_New"))
        self.endInsertRows()
        
    def remove_spl(self, row: int):
        self.beginRemoveRows(QModelIndex(), row, row)
        del self.project.spl_configs[row]
        self.endRemoveRows()
