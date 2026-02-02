import sys
import os
import unittest
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from telemetry_studio.data_models import ProjectDefinition, EnumDefinition, EnumItem
from telemetry_studio.codegen import CodeGenerator

class TestEnumSPL(unittest.TestCase):
    def test_enum_filtering(self):
        proj = ProjectDefinition()
        
        # Enum 1: Global (No active_configs)
        e1 = EnumDefinition(name="GlobalEnum")
        
        # Enum 2: Debug Only
        e2 = EnumDefinition(name="DebugEnum")
        e2.active_configs = ["DEBUG_ONLY"]
        
        # Enum 3: Release Only
        e3 = EnumDefinition(name="ReleaseEnum")
        e3.active_configs = ["RELEASE_ONLY"]
        
        proj.enums = [e1, e2, e3]
        
        codegen = CodeGenerator(proj)
        
        # Test 1: Generate for "DEBUG_ONLY"
        # Expect: GlobalEnum, DebugEnum
        out_debug = codegen.generate_enums(target_config="DEBUG_ONLY")
        print("\n--- DEBUG_ONLY Output ---")
        print(out_debug)
        
        self.assertIn("class GlobalEnum", out_debug)
        self.assertIn("class DebugEnum", out_debug)
        self.assertNotIn("class ReleaseEnum", out_debug)
        
        # Test 2: Generate for "RELEASE_ONLY"
        # Expect: GlobalEnum, ReleaseEnum
        out_release = codegen.generate_enums(target_config="RELEASE_ONLY")
        print("\n--- RELEASE_ONLY Output ---")
        print(out_release)
        
        self.assertIn("class GlobalEnum", out_release)
        self.assertNotIn("class DebugEnum", out_release)
        self.assertIn("class ReleaseEnum", out_release)
        
        # Test 3: Generate for None (or unknown) - Current logic implies filtering only happens if target provided?
        # If target_config is None, it should return ALL Enums?
        # Yes, line: if target_config and enum_def.active_configs:
        out_all = codegen.generate_enums(target_config=None)
        print("\n--- ALL Output ---")
        self.assertIn("class GlobalEnum", out_all)
        self.assertIn("class DebugEnum", out_all)
        self.assertIn("class ReleaseEnum", out_all)

if __name__ == '__main__':
    unittest.main()
