# note.md

Everything about this dotfiles folder, in plain language.
This folder is a snapshot of the **configuration** of the old machine (user `sk`),
made ready to install on a fresh **Arch Linux + Hyprland** machine that may have a
**different username**.

---

## How to use it on the new machine

```bash
./install.sh --dry-run    # optional: only prints what would happen, changes nothing
./install.sh              # asks for the username, then a yes/no confirmation
```

Or non-interactive:

```bash
DOTFILES_USER=alice ./install.sh --yes
```

After installing: **log out and back in (or reboot)**, then run once:

```bash
theme-change gruvbox
```

That sets the wallpaper, icon theme and dark/light mode for the new machine.

Safety behaviour of `install.sh`:

* It refuses to run as root.
* Without `--yes` it asks before doing anything. If you answer no, **nothing is changed**.
* Files it replaces get backed up to `~/dotfiles-backup-<timestamp>`.
* `--dry-run` never touches anything.

---

## What is inside this folder

```
dot-files/
├── install.sh          # the installer (run it on the NEW machine)
├── note.md             # this file
├── home/               # a mirror of the old $HOME - copied to the new $HOME
│   ├── .bashrc, .bash_profile, .bash_logout, .inputrc, .gitconfig, .gtkrc-2.0
│   ├── .config/        # hypr, waybar, kitty, nvim, yazi, btop, dunst, walker, ...
│   ├── .dotfiles/      # the theme engine (themes/, templates, wallpapers)
│   ├── .local/bin/     # all your scripts (theme-change, wallpaper, recorder, ...)
│   └── .local/share/   # only applications/ (your .desktop files) and icons/
├── packages/
│   ├── official.txt    # installed with pacman
│   └── aur.txt         # installed with yay
└── sddm/
    ├── gruv-sddm/      # the login screen theme
    └── theme.conf      # goes to /etc/sddm.conf.d/theme.conf
```

---

## What was deliberately NOT copied

**User data / profiles (and one secret):**

* `.config/chromium`, `.config/mozilla`, `.config/obsidian` – browser & app profiles
* `.config/opencode/node_modules` – big folder of npm packages (62 MB)
* `.config/opencode/service.json` – it contains a **password**, so it was left out
* `.config/dconf` – stored personal GNOME settings (reader paths, window sizes)
* `.config/session`, `.config/tool_state`, mpd's `database`/`state` – program state
* `.config/libreoffice`, `.local/share/recently-used.xbel`, `Trash`, caches
* `.bash_history`, `.cache`, `.yay`, `.npm`, `.nv`, `.android`, `.ipython`
* `~/Documents`, `~/Music`, `~/Pictures`, `~/Videos`, `~/Downloads`, `~/Projects`, `~/go`
* `.local/state` (logs) and everything else under `.local/share` except
  `applications/` and `icons/`

**Left out because you said so:**

* `~/.python-env` (the python virtual environment)
* spotdl (`~/.config/spotdl` and the pip packages for it)
* `~/.rgb` (this keyboard's lighting – would not work on another machine)

**Left out because they are hardware-specific (you said audio/GPU is already set up):**

* `~/.config/pipewire`, `~/.config/pulse` (audio daemon configs)
* `~/.config/gpu-screen-recorder`, `~/.config/guvcview2`, `~/.config/predator`
* `.nvidia-settings-rc`
* Packages: kernel/firmware/bootloader tools, all GPU drivers (`nvidia*`, `vulkan*`,
  `xf86-video*`, `libva*`), the audio stack (`pipewire*`, `wireplumber`, `libpulse`,
  `alsa-utils`), networking/firewall (`iwd`, `ufw`), `intel-ucode`, `sof-firmware`,
  `zram-generator`, `plymouth`, filesystem tools (`btrfs-progs`, `ntfs-3g`, ...)
* `sway`, `swayidle`, `swaylock` (this setup uses Hyprland's own; `swaybg` is kept
  because hyprland.lua starts it for the wallpaper)

---

## Changes made so it works on the new machine

1. **Symlinks no longer contain a username.**
   On the old machine links looked like `/home/sk/.config/current_theme/...`.
   They are now stored **relative**, e.g.
   `.config/kitty/kitty-colors.conf -> ../current_theme/kitty.conf`.
   Same structure, same destinations – but they work for *any* username.
   This covers `~/.config/current_theme`, kitty/waybar/btop/dunst/gtk/swayosd/
   opencode/nvim/walker theme links, all `themes/*/current_wallpaper.png` links
   and the systemd `elephant.service` link.
   Links that point into the system (`/usr/lib/systemd/user/...`) were left
   absolute – they are correct on any machine.

2. **Hardcoded `/home/sk` paths are rewritten by `install.sh`** to the new home.
   Affected files: `.config/walker/config.toml`, `.config/mpd/mpd.conf`,
   `.config/mimeapps.list`, `.config/QtProject.conf`, `.gtkrc-2.0`,
   `.config/gtk-3.0/bookmarks`, `.config/yay/config.json`,
   `.dotfiles/matugen.toml`, `.dotfiles/chromium/scheme-newtab/newtab.js`.

3. **AUR helper is plain `yay`, not `yay-git`.**
   `install.sh` builds `yay` from https://aur.archlinux.org/yay.git if it is
   missing, then installs `packages/aur.txt` with it.

4. **Package lists were split** into `packages/official.txt` (pacman) and
   `packages/aur.txt` (yay). Everything hardware/setup-related was removed (see
   above). Added: `python`, `libnotify`, `wl-clipboard` – the scripts in
   `.local/bin` need them and a fresh install may not have them.

5. **gsettings/dconf is not copied.** On the new machine the icon theme and
   dark-mode are set by `install.sh` if a session is running, otherwise simply
   run `theme-change gruvbox` after your first login.

6. **SDDM theme** `gruv-sddm` was copied from `/usr/share/sddm/themes/` into
   this folder, together with `/etc/sddm.conf.d/theme.conf`. `install.sh`
   copies them back (needs sudo) and enables `sddm`, `bluetooth`, `cups` and
   `power-profiles-daemon` – but only if those units exist.

7. **Hyprland config is `hyprland.lua` (Lua), not `hyprland.conf`.**
   This needs a Hyprland new enough to read Lua configs (this system runs
   0.56.2). If the new machine's Hyprland is older, update it first
   (`pacman -Syu hyprland`).

8. **`.bashrc` kept the old aliases on purpose** (structure identical):
   * `py` / `pyy` → need `~/.python-env` (not copied) – will not work
   * `aud` → needs spotdl (not copied) – will not work
   * `rgb` → needs `~/.rgb` (not copied) – will not work
   They are harmless until you use them. Delete the three alias lines if you
   do not want them.

9. **The `keyboard` script** (started by hyprland.lua at login) calls
   `~/.rgb/facer_rgb.py`. Without `~/.rgb` it prints a harmless
   "No such file" error on login and does nothing else. Harmless on the new
   machine. Same for the `rgb` alias.

10. **12 `current_wallpaper.png` links are dangling** in the non-active themes
    (`themes/bamboo`, `themes/latte`, ...). They behave exactly like on the old
    machine – they only resolve while that theme is the active one, and
    `theme-change <name>` rewrites them anyway. The active theme (`gruvbox`)
    works.

11. **Wallpapers are included** (~100 MB of `~/.dotfiles/themes/*/wallpapers/`)
    because hyprlock, swaybg and the wallpaper switcher need them. The folder
    `home/` is about 109 MB in total.

12. **Optional:** opencode had a local plugin (`package.json` is kept, its
    `node_modules` is not). If you want it: `cd ~/.config/opencode && npm install`.

---

## Small differences from the old machine (normal, not problems)

* `.gitconfig` contains **no git identity on purpose** (public repo). After the
  install, set it once: `git config --global user.name "..."` and
  `git config --global user.email "..."`.
* `.local/share/applications/*.desktop` web-app launchers (gmail/youtube/...) are
  kept; they simply open chromium.
* Empty config folders (`~/.config/mpv`, `~/.config/nautilus`, ...) are kept so
  the structure matches; the programs refill them.
