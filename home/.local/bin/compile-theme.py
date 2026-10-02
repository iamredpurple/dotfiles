#!/usr/bin/env python3
import sys
import os
import re
import tomllib

# Usage compile-theme.py ~/pathtocolors.toml ~/pathtotpl ~/pathtostoreoutput

def hex_to_rgb(hex_str):
    """Converts #7aa2f7 to 122,162,247"""
    hex_str = hex_str.lstrip('#')
    try:
        return f"{int(hex_str[0:2], 16)}, {int(hex_str[2:4], 16)}, {int(hex_str[4:6], 16)}"
    except ValueError:
        return hex_str

def parse_toml(toml_path):
    """Reads the TOML file and flattens nested keys (like [colors]) into a single dict."""
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)
    
    # Flatten if colors are nested under [colors] or similar sections
    flat_colors = {}
    def flatten(d):
        for k, v in d.items():
            if isinstance(v, dict):
                flatten(v)
            else:
                flat_colors[k] = v
    flatten(data)
    return flat_colors

def compile_template(template_path, output_path, colors):
    """Replaces {{ variable }} tokens with actual color values."""
    with open(template_path, "r") as f:
        content = f.read()

    # Regex to catch {{ variable }}, {{variable}}, {{ variable_strip }}, etc.
    pattern = re.compile(r'\{\{\s*([\w_]+)\s*\}\}')

    def replace_match(match):
        token = match.group(1)
        
        # Handle '_strip' modifier (removes #)
        if token.endswith('_strip'):
            base_key = token[:-6]
            if base_key in colors:
                return str(colors[base_key]).lstrip('#')
        
        # Handle '_rgb' modifier (converts hex to 255,255,255)
        elif token.endswith('_rgb'):
            base_key = token[:-4]
            if base_key in colors:
                return hex_to_rgb(str(colors[base_key]))
        
        # Standard replacement
        elif token in colors:
            return str(colors[token])
            
        # Return untouched if the key wasn't found in colors.toml
        return match.group(0)

    compiled_content = pattern.sub(replace_match, content)

    # Write the completed file out
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(compiled_content)
    print(f"✓ Compiled: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python compile_theme.py <path_to_colors.toml> <path_to_template.tpl> <target_output_file>")
        sys.exit(1)

    toml_file = sys.argv[1]
    template_file = sys.argv[2]
    output_file = sys.argv[3]

    try:
        color_map = parse_toml(toml_file)
        compile_template(template_file, output_file, color_map)
    except Exception as e:
        print(f"Error: {e}")
