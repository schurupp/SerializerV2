import ast
from typing import List, Dict, Any
from telemetry_studio.data_models import ProjectDefinition, MessageDefinition, FieldDefinition, EnumDefinition, EnumItem, SPLDefinition

class PythonImporter:
    def __init__(self):
        self.project = ProjectDefinition()

    def import_files(self, message_file_path: str, enum_file_path: str = None) -> ProjectDefinition:
        if enum_file_path:
            with open(enum_file_path, 'r') as f:
                self.parse_enums(f.read())
                
        with open(message_file_path, 'r') as f:
            self.parse_messages(f.read())
            
        return self.project

    def parse_enums(self, source: str):
        tree = ast.parse(source)
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                is_enum = any(b.id == 'IntEnum' for b in node.bases if isinstance(b, ast.Name))
                if is_enum:
                    items = []
                    for item in node.body:
                        if isinstance(item, ast.Assign):
                            name = item.targets[0].id
                            val = item.value.value if isinstance(item.value, ast.Constant) else 0 
                            items.append(EnumItem(name, val))
                    self.project.enums.append(EnumDefinition(node.name, items))

    def parse_messages(self, source: str):
        tree = ast.parse(source)
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                active_configs = []
                is_registered = False
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Name) and dec.id == 'register':
                        is_registered = True
                    elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name) and dec.func.id == 'register':
                        is_registered = True
                        for kw in dec.keywords:
                            if kw.arg == 'system_config_id':
                                if isinstance(kw.value, ast.Constant):
                                    active_configs.append(kw.value.value)
                
                if is_registered:
                    msg = MessageDefinition(node.name)
                    msg.active_configs = active_configs
                    
                    for item in node.body:
                        if isinstance(item, ast.Assign):
                            fname = item.targets[0].id
                            
                            if isinstance(item.value, ast.Call):
                                ftype = item.value.func.id if isinstance(item.value.func, ast.Name) else "Unknown"
                                
                                if ftype in ["UInt8", "Int8", "UInt16", "Int16", "UInt32", "Int32", 
                                             "UInt64", "Int64", "Float32", "Float64", "Bool", "StringField", 
                                             "BitField", "EnumField", "ArrayField", "FixedPointField"]:
                                    
                                    ui_type = ftype
                                    if ftype == "StringField": ui_type = "String"
                                    if ftype == "EnumField": ui_type = "Enum"
                                    if ftype == "ArrayField": ui_type = "Array"
                                    if ftype == "FixedPointField": ui_type = "FixedPoint"
                                    
                                    options = self._parse_keywords(item.value.keywords)
                                    
                                    if item.value.args:
                                        if ui_type == "BitField":
                                            options["bits"] = self._parse_bit_list(item.value.args[0])
                                        elif ui_type == "Enum":
                                            if isinstance(item.value.args[0], ast.Name):
                                                options["enum_name"] = item.value.args[0].id
                                    
                                    f_def = FieldDefinition(fname, ui_type, options)
                                    msg.fields.append(f_def)
                                    
                    self.project.messages.append(msg)

    def _parse_keywords(self, keywords: List[ast.keyword]) -> Dict[str, Any]:
        opts = {}
        for kw in keywords:
            val = kw.value
            if isinstance(val, ast.Constant):
                opts[kw.arg] = val.value
            elif hasattr(ast, 'NameConstant') and isinstance(val, ast.NameConstant):
                opts[kw.arg] = val.value 
        return opts

    def _parse_bit_list(self, list_node: ast.List) -> List[Dict]:
        bits = []
        for elt in list_node.elts:
            if isinstance(elt, ast.Call):
                width = 0
                name = ""
                if len(elt.args) >= 2:
                    if isinstance(elt.args[0], ast.Constant): width = elt.args[0].value
                    if isinstance(elt.args[1], ast.Constant): name = elt.args[1].value
                bits.append({"name": name, "width": width})
        return bits
