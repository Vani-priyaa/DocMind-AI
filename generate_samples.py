import os

files_to_sample = [
    r"e:\CDA\CDA\backend\app\main.py",
    r"e:\CDA\CDA\backend\models.py",
    r"e:\CDA\CDA\src\app\page.tsx",
    r"e:\CDA\CDA\src\components\Sidebar.tsx"
]

output_file = r"e:\CDA\CDA\cda_sample_codes.txt"

with open(output_file, "w", encoding="utf-8") as out_f:
    out_f.write("Conversational Data Analyst (CDA) - Sample Codes\n")
    out_f.write("="*50 + "\n\n")
    
    for file_path in files_to_sample:
        if os.path.exists(file_path):
            out_f.write(f"--- FILE: {file_path} ---\n")
            with open(file_path, "r", encoding="utf-8") as in_f:
                out_f.write(in_f.read())
            out_f.write("\n" + "="*50 + "\n\n")
        else:
            out_f.write(f"--- FILE: {file_path} (NOT FOUND) ---\n\n")

print(f"Sample codes written to {output_file}")
