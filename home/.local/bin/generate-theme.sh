#!/usr/bin/env bash

# Exit immediately if no wallpaper is provided
if [ -z "$1" ]; then
  echo "Usage: generate-theme.sh /path/to/wallpaper.jpg"
  exit 1
fi

# Define absolute paths based on your new layout
WALLPAPER="$1"
DOTFILES_DIR="$HOME/.dotfiles"
TEMPLATE_DIR="$DOTFILES_DIR/theme-compilation"
STAGING_DIR="$DOTFILES_DIR/themes/custom"

# Safely wipe the directory if it exists to prevent stale file accumulation
if [ -d "$STAGING_DIR" ]; then
  rm -rf "$STAGING_DIR"
fi

# Ensure the output directory exists before writing anything
mkdir -p "$STAGING_DIR"

# Generates colors.toml out of your template mapping file
matugen -c "$DOTFILES_DIR/matugen.toml" image "$WALLPAPER" --source-color-index 0 --quiet

echo "Compiling template blueprints into flat target files..."
# Runs the python script using absolute configurations
python3 "$HOME/.local/bin/compile_all.py" "$STAGING_DIR/colors.toml"

echo "Yaru-sage" >$STAGING_DIR/icons.theme
echo -en "255\n255\n255" >$STAGING_DIR/rgb.txt

echo -e "\n Theme generated successfully!"
echo "Flat output ready in: $STAGING_DIR"

cp "$WALLPAPER" "$STAGING_DIR/current_wallpaper.png"
cp "$WALLPAPER" "$STAGING_DIR/preview.png"
mkdir -p "$STAGING_DIR/wallpapers/"
cp "$WALLPAPER" "$STAGING_DIR/wallpapers/1-wallpaper.png"

$HOME/.local/bin/theme-change custom
# \cp -r $STAGING_DIR/. $STAGING_DIR/../.custom/
#
# $HOME/.local/bin/theme-change .custom
# rm -rf $STAGING_DIR
