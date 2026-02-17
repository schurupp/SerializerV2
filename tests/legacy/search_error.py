import os

root = r"c:\Users\fatihyes\Desktop\SerializerV2"

for dirpath, dirnames, filenames in os.walk(root):
    # Exclude
    if 'venv' in dirnames: dirnames.remove('venv')
    if '.git' in dirnames: dirnames.remove('.git')
    if '__pycache__' in dirnames: dirnames.remove('__pycache__')
    
    for f in filenames:
        if f.endswith(".py"):
            path = os.path.join(dirpath, f)
            with open(path, 'r', encoding='utf-8') as file:
                try:
                    content = file.read()
                    if "Cannot calculate offset" in content:
                        print(f"FOUND in {path}")
                        lines = content.splitlines()
                        for i, line in enumerate(lines):
                            if "Cannot calculate offset" in line:
                                print(f"{i+1}: {line}")
                except Exception as e:
                    pass
