export ZSH="$HOME/.oh-my-zsh"

ZSH_THEME="agnosterzak"

plugins=(
    git
    zsh-autosuggestions
    zsh-syntax-highlighting
)

source $ZSH/oh-my-zsh.sh

# Tokyo Night file name colors (lsd and ls read LS_COLORS), exact RGB
export LS_COLORS="di=1;38;2;122;162;247:ln=38;2;125;207;255:so=38;2;187;154;247:pi=38;2;224;175;104:ex=1;38;2;158;206;106:bd=38;2;224;175;104:cd=38;2;224;175;104:su=30;48;2;247;118;142:sg=30;48;2;247;118;142:tw=30;48;2;158;206;106:ow=30;48;2;224;175;104"


# Show fastfetch
fastfetch

# Set-up icons for files/directories in terminal using lsd
alias ls='lsd'
alias l='ls -l'
alias la='ls -a'
alias lla='ls -la'
alias lt='ls --tree'
export PATH=$PATH:$HOME/.local/bin

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion
eval "$(direnv hook zsh)"

# pnpm
export PNPM_HOME="$HOME/.local/share/pnpm"
case ":$PATH:" in
  *":$PNPM_HOME:"*) ;;
  *) export PATH="$PNPM_HOME:$PATH" ;;
esac
# pnpm end

# Claude Code: separate accounts via isolated config dirs
alias claude-work='CLAUDE_CONFIG_DIR=$HOME/.claude-work claude'
alias claude-personal='CLAUDE_CONFIG_DIR=$HOME/.claude-personal claude'
