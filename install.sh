#!/usr/bin/env bash
#
# dot-files installer  ->  for a freshly installed Arch Linux + Hyprland machine
#
# What it does (in order):
#   1. Installs packages        (packages/official.txt via pacman, packages/aur.txt via yay)
#   2. Copies config files      (home/  ->  $HOME, old files are backed up)
#   3. Fixes old /home/sk paths (rewritten to the new user's home)
#   4. Installs the SDDM theme  (gruv-sddm + /etc/sddm.conf.d/theme.conf)
#   5. Enables services
#
# Usage:
#   ./install.sh                 # asks for username and confirmation
#   ./install.sh --dry-run       # only prints what would happen, touches nothing
#   ./install.sh --yes           # no confirmation question
#   DOTFILES_USER=alice ./install.sh --yes   # non-interactive, pick the username
#
# Symlinks need no fixing: every symlink inside home/ is stored RELATIVE,
# so it works with any username on any machine.

set -euo pipefail

REPO_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SRC="$REPO_DIR/home"
OLD_HOME="/home/sk"          # home of the machine this setup was captured from

DRY_RUN=0
ASSUME_YES=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --yes|-y)  ASSUME_YES=1 ;;
    -h|--help)
      sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) echo "unknown option: $arg (try --help)"; exit 1 ;;
  esac
done

info()  { printf '\n\033[1;32m==>\033[0m %s\n' "$*"; }
warn()  { printf '\033[1;33mwarning:\033[0m %s\n' "$*"; }
die()   { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

# run <cmd...>   -> print it in dry-run mode, otherwise execute it
run() {
  if [ "$DRY_RUN" = 1 ]; then
    printf '  [dry-run] %s\n' "$*"
  else
    "$@"
  fi
}

# ---------------------------------------------------------------- target user
[ "$(id -u)" = 0 ] && die "run this as a normal user (with sudo rights), not as root"

TARGET_USER="${DOTFILES_USER:-$(id -un)}"
if [ -z "${DOTFILES_USER:-}" ] && [ -t 0 ] && [ "$DRY_RUN" = 0 ]; then
  read -r -p "Install dotfiles for user [$TARGET_USER]: " answer
  [ -n "$answer" ] && TARGET_USER="$answer"
fi
TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"
[ -n "$TARGET_HOME" ] && [ -d "$TARGET_HOME" ] || die "user '$TARGET_USER' does not exist (or has no home)"
[ -d "$SRC" ] || die "broken repo: $SRC not found"

info "target user : $TARGET_USER"
info "target home : $TARGET_HOME"

if [ "$DRY_RUN" = 0 ] && [ "$ASSUME_YES" = 0 ]; then
  printf '\nThis will install packages and copy/replace config files in %s\n' "$TARGET_HOME"
  printf 'Replaced files are backed up in %s/dotfiles-backup-<timestamp>\n' "$TARGET_HOME"
  read -r -p 'Continue? [y/N] ' answer
  case "$answer" in y|Y|yes|YES) ;; *) echo "nothing was changed, exiting."; exit 0 ;; esac
fi

# ---------------------------------------------------------------- 1. packages
info "Step 1/5: packages"

if ! command -v rsync >/dev/null 2>&1; then
  run sudo pacman -S --needed --noconfirm rsync
fi

read_pkgs() { grep -vE '^\s*(#|$)' "$1"; }

if command -v pacman >/dev/null 2>&1; then
  mapfile -t OFFICIAL < <(read_pkgs "$REPO_DIR/packages/official.txt")
  if [ "$DRY_RUN" = 1 ]; then
    echo "  [dry-run] sudo pacman -S --needed ${OFFICIAL[*]}"
  else
    sudo pacman -S --needed --noconfirm "${OFFICIAL[@]}"
  fi
else
  warn "pacman not found - skipping package installation"
fi

# bootstrap 'yay' (the AUR helper - plain 'yay', not yay-git)
if ! command -v yay >/dev/null 2>&1; then
  info "installing yay (AUR helper) from source"
  if [ "$DRY_RUN" = 1 ]; then
    echo "  [dry-run] git clone https://aur.archlinux.org/yay.git && makepkg -si"
  else
    tmp="$(mktemp -d)"
    git clone https://aur.archlinux.org/yay.git "$tmp/yay"
    (cd "$tmp/yay" && makepkg -si --needed --noconfirm)
    rm -rf "$tmp"
    command -v yay >/dev/null 2>&1 || die "yay installation failed"
  fi
fi

if command -v yay >/dev/null 2>&1; then
  mapfile -t AURPKGS < <(read_pkgs "$REPO_DIR/packages/aur.txt")
  if [ "$DRY_RUN" = 1 ]; then
    echo "  [dry-run] yay -S --needed ${AURPKGS[*]}"
  else
    yay -S --needed "${AURPKGS[@]}"
  fi
fi

# ---------------------------------------------------------------- 2. files
info "Step 2/5: copying config files into $TARGET_HOME"

BACKUP_DIR="$TARGET_HOME/dotfiles-backup-$(date +%Y%m%d-%H%M%S)"
run rsync -a --backup --backup-dir="$BACKUP_DIR" "$SRC/" "$TARGET_HOME/"
if [ "$DRY_RUN" = 0 ] && [ -d "$BACKUP_DIR" ]; then
  info "old files backed up to: $BACKUP_DIR"
fi
echo "  (symlinks are stored relative - they already work for any username)"

# ---------------------------------------------------------------- 3. old paths
info "Step 3/5: rewriting $OLD_HOME -> $TARGET_HOME"

# every shipped text file that still mentions the old machine's home
mapfile -t FIX_FILES < <(grep -rIl "$OLD_HOME" "$SRC" 2>/dev/null || true)
for srcfile in "${FIX_FILES[@]}"; do
  relfile="${srcfile#$SRC/}"
  target="$TARGET_HOME/$relfile"
  if [ "$DRY_RUN" = 1 ]; then
    echo "  [dry-run] sed $relfile"
  elif [ -f "$target" ]; then
    sed -i "s|$OLD_HOME|$TARGET_HOME|g" "$target"
    echo "  fixed: $relfile"
  fi
done

# ---------------------------------------------------------------- 4. sddm theme
info "Step 4/5: SDDM theme (gruv-sddm)"

if [ -d "$REPO_DIR/sddm/gruv-sddm" ]; then
  run sudo install -d -m 0755 /usr/share/sddm/themes
  run sudo cp -a "$REPO_DIR/sddm/gruv-sddm" /usr/share/sddm/themes/
  run sudo install -Dm644 "$REPO_DIR/sddm/theme.conf" /etc/sddm.conf.d/theme.conf
else
  warn "sddm/gruv-sddm not found in repo, skipping"
fi

# ---------------------------------------------------------------- 5. services
info "Step 5/5: services"

unit_exists() { systemctl list-unit-files --no-legend "$1" 2>/dev/null | grep -q .; }

# system services (only enabled if they exist - skipped otherwise)
for svc in sddm bluetooth cups power-profiles-daemon; do
  if unit_exists "$svc.service"; then
    run sudo systemctl enable "$svc.service"
  else
    echo "  skipped (not installed): $svc.service"
  fi
done

# user services (daemon-reload only when actually installing, never in dry-run)
if [ "$DRY_RUN" = 1 ]; then
  echo "  [dry-run] systemctl --user enable elephant.service hypridle.service mpd.service"
elif command -v systemctl >/dev/null 2>&1 && systemctl --user daemon-reload 2>/dev/null; then
  systemctl --user enable elephant.service hypridle.service mpd.service || warn "could not enable user services"
else
  warn "no user systemd session here - the shipped symlinks in .config/systemd already enable them"
fi

# best effort: apply icon theme / light-dark mode (works when a session is running)
if command -v gsettings >/dev/null 2>&1 && [ "$DRY_RUN" = 0 ]; then
  variant="$(tr -d ' \t\r\n' < "$TARGET_HOME/.config/current_theme/icons.theme" 2>/dev/null || true)"
  if [ -n "$variant" ]; then
    gsettings set org.gnome.desktop.interface icon-theme "$variant" 2>/dev/null || true
    if [ -f "$TARGET_HOME/.config/current_theme/light.mode" ]; then
      gsettings set org.gnome.desktop.interface color-scheme 'prefer-light' 2>/dev/null || true
    else
      gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark' 2>/dev/null || true
    fi
  fi
fi

# ---------------------------------------------------------------- done
info "Done!"
cat <<EOF

  * Log out and back in (or reboot) so SDDM + Hyprland pick everything up.
  * First thing after login, run:   theme-change gruvbox
    (sets wallpaper, icons and the rest of the theme for the new machine)
  * Things that were deliberately not copied are listed in note.md
    (python venv, spotdl, .rgb keyboard lighting, browser/user profiles)
EOF
if [ "$DRY_RUN" = 1 ]; then
  echo -e "\n(dry-run: nothing was changed)"
fi
