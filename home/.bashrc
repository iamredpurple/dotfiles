#
# ~/.bashrc
#

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

#alias
#alias ls='ls --color=auto'
alias grep='grep --color=auto'
alias py='. ~/.python-env/bin/activate'
alias pyy='deactivate'

#lsd alias
alias ls='lsd --sort extension --color=auto'

#keyboard light alias - use this for your own keyboard lighting if exists/possible
#alias rgb='python ~/.rgb/keyboard.py'

#video download
alias vid='yt-dlp --cookies-from-browser chromium -S "res:1080" --embed-thumbnail -P "~/Videos" -o "%(title)s.%(ext)s"'

#audio download
#use this if you devide to use spotdl...change venv path
#alias aud='$HOME/.python-env/bin/spotdl --output "$HOME/Music/Unsorted/{title}"'

alias ff="fastfetch"
alias ff!="fastfetch --logo none"

PS1='[\u@\h \W]\$ '
export EDITOR=nvim
export VISUAL=nvim
export PATH="$HOME/.local/bin:$PATH"

eval "$(starship init bash)"

shopt -s cdspell
shopt -s dirspell
