import json
from dataclasses import asdict
from typing import Dict, Any
from telemetry_studio.data_models import ProjectDefinition, MessageDefinition, FieldDefinition, EnumDefinition, EnumItem, SPLDefinition

class ProjectIO:
    @staticmethod
    def save_project(project: ProjectDefinition, filepath: str):
        data = {
            "enums": [asdict(e) for e in project.enums],
            "messages": [asdict(m) for m in project.messages],
            "spl_configs": [asdict(s) for s in project.spl_configs]
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)

    @staticmethod
    def load_project(filepath: str) -> ProjectDefinition:
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        proj = ProjectDefinition()
        
        # Enums
        for e_data in data.get("enums", []):
            items = [EnumItem(**i) for i in e_data.get("items", [])]
            e_def = EnumDefinition(name=e_data["name"], items=items)
            proj.enums.append(e_def)
            
        # SPLs
        for s_data in data.get("spl_configs", []):
            proj.spl_configs.append(SPLDefinition(name=s_data["name"]))
            
        # Messages
        for m_data in data.get("messages", []):
            msg = MessageDefinition(name=m_data["name"])
            msg.active_configs = m_data.get("active_configs", [])
            
            for f_data in m_data.get("fields", []):
                # f_data: {name, field_type, options}
                f_def = FieldDefinition(
                    name=f_data["name"],
                    field_type=f_data["field_type"],
                    options=f_data.get("options", {})
                )
                msg.fields.append(f_def)
            proj.messages.append(msg)
            
        return proj
