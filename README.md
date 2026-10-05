# READ-ME-PLEASE

Dotfiles for original user 'sk', edited to work with any username
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

## What was automatically created and might need manual tweaking

**User data / profiles:**

* `.config/chromium`, `.config/mozilla`, `.config/obsidian` – browser & app profiles
* `.config/dconf` – stored personal GNOME settings (reader paths, window sizes)
* `.config/session`, `.config/tool_state`, mpd's `database`/`state` – program state
* `.config/libreoffice`, `.local/share/recently-used.xbel`, `Trash`, caches
* `.bash_history`, `.cache`, `.yay`, `.npm`, `.nv`, `.android`, `.ipython`
* `~/Documents`, `~/Music`, `~/Pictures`, `~/Videos`, `~/Downloads`, `~/Projects`, `~/go` - the contents arent copied but some folders are needed for gpu screenrecorder or screenshot and those will be created
* `.local/state` (logs) and everything else under `.local/share` except
  `applications/` and `icons/`

**Left out:**

* `~/.python-env` (the python virtual environment) - since spotdl alias is set to use this venv with this particular name, maybe the same can be created in the home dir and the list of packages inside **py-venv-req.txt** can be installed, this has other not so needed packages as well like flask and stuff so maybe look first then install, or f it, install everything
* spotdl (`~/.config/spotdl` and the pip packages for it)
* `~/.rgb` (this keyboard's lighting – would not work on another machine, maybe the script that works can be added inside and configuration may need tweaks)

**Left out because they are hardware-specific:**

* `~/.config/pipewire`, `~/.config/pulse` (audio daemon configs)
* `~/.config/gpu-screen-recorder`, `~/.config/guvcview2`, `~/.config/predator`
* `.nvidia-settings-rc`
* Packages: kernel/firmware/bootloader tools, all GPU drivers (`nvidia*`, `vulkan*`,
  `xf86-video*`, `libva*`), the audio stack (`pipewire*`, `wireplumber`, `libpulse`,
  `alsa-utils`), networking/firewall (`iwd`, `ufw`), `intel-ucode`, `sof-firmware`,
  `zram-generator`, `plymouth`, filesystem tools (`btrfs-progs`, `ntfs-3g`, ...)
* `sway`, `swayidle`, `swaylock` (this setup uses Hyprland's own; `swaybg` is kept because hyprland.lua starts it for the wallpaper)

---
