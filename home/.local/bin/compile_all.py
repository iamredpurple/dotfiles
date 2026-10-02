#!/usr/bin/env python3
import os
import sys
import re
import tomllib

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    try:
        return f"{int(hex_str[0:2], 16)}, {int(hex_str[2:4], 16)}, {int(hex_str[4:6], 16)}"
    except ValueError:
        return hex_str

def parse_toml(toml_path):
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)
    flat_colors = {}
    def flatten(d):
        for k, v in d.items():
            if isinstance(v, dict):
                flatten(v)
            else:
                flat_colors[k] = v
    flatten(data)
    return flat_colors

def compile_file(template_path, output_path, variables):
    with open(template_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    pattern = re.compile(r'\{\{\s*([\w_]+)\s*\}\}')

    def replace_match(match):
        token = match.group(1)
        if token.endswith('_strip'):
            base_key = token[:-6]
            if base_key in variables:
                return str(variables[base_key]).lstrip('#')
        elif token.endswith('_rgb'):
            base_key = token[:-4]
            if base_key in variables:
                return hex_to_rgb(str(variables[base_key]))
        elif token in variables:
            return str(variables[token])
        return match.group(0)

    compiled_content = pattern.sub(replace_match, content)
    
    # Save directly to target flat folder
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(compiled_content)

def process_directory(toml_path, input_dir, output_root):
    if not os.path.exists(toml_path):
        print(f"Error: {toml_path} not found.")
        return
    
    variables = parse_toml(toml_path)
    input_dir = os.path.abspath(input_dir)
    output_root = os.path.abspath(os.path.expanduser(output_root))
    
    # Ensure staging folder exists
    os.makedirs(output_root, exist_ok=True)

    print(f"Reading variables from: {toml_path}")
    print(f"Scanning templates in:  {input_dir}")
    print(f"Outputting flat to:     {output_root}\n")

    count = 0
    # Walk through the template folder
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.tpl'):
                tpl_path = os.path.join(root, file)
                
                # Strip '.tpl' to get the final target filename
                target_filename = file[:-4]
                
                # Force output to drop flat inside output_root (ignoring subfolder structure)
                out_path = os.path.join(output_root, target_filename)

                compile_file(tpl_path, out_path, variables)
                print(f"✓ Processed: {file} -> {out_path}")
                count += 1
                
    print(f"\nSuccess! Successfully compiled {count} files flat.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python compile_all.py <path_to_colors.toml>")
        sys.exit(1)
        
    toml_file = sys.argv[1]

    # Absolute paths mapped to your central dotfiles setup
    template_folder = os.path.expanduser("~/.dotfiles/theme-compilation")
    output_folder = os.path.expanduser("~/.dotfiles/themes/custom")
    
    process_directory(toml_file, template_folder, output_folder)
