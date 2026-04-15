#!/bin/bash

set -e

DOTFILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$HOME/.dotfiles_backup_$(date +%Y%m%d_%H%M%S)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

backup_and_link() {
    local src="$1"
    local dest="$2"

    if [ -e "$dest" ] || [ -L "$dest" ]; then
        mkdir -p "$BACKUP_DIR"
        warn "Backing up $dest"
        mv "$dest" "$BACKUP_DIR/"
    fi

    ln -sf "$src" "$dest"
    info "Linked $dest"
}

# ============================================
# ZSH (oh-my-zsh + theme + config)
# ============================================

setup_zsh() {
    info "=== Setting up ZSH ==="

    # Install Oh My Zsh
    if [ ! -d "$HOME/.oh-my-zsh" ]; then
        info "Installing Oh My Zsh..."
        sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
    else
        info "Oh My Zsh already installed"
    fi

    # Install theme
    local theme_file="$HOME/.oh-my-zsh/themes/agnosterzak.zsh-theme"
    if [ ! -f "$theme_file" ]; then
        info "Installing agnosterzak theme..."
        curl -fsSL https://raw.githubusercontent.com/zakaziko99/agnosterzak-ohmyzsh-theme/master/agnosterzak.zsh-theme -o "$theme_file"
    else
        info "Agnosterzak theme already installed"
    fi

    # Link config
    backup_and_link "$DOTFILES_DIR/zsh/.zshrc" "$HOME/.zshrc"

    info "=== ZSH done ==="
}

# ============================================
# TMUX (tpm + config)
# ============================================

setup_tmux() {
    info "=== Setting up TMUX ==="

    # Install TPM (Tmux Plugin Manager)
    if [ ! -d "$HOME/.tmux/plugins/tpm" ]; then
        info "Installing TPM..."
        git clone https://github.com/tmux-plugins/tpm "$HOME/.tmux/plugins/tpm"
    else
        info "TPM already installed"
    fi

    # Link config
    backup_and_link "$DOTFILES_DIR/tmux/tmux.conf" "$HOME/.tmux.conf"

    info "=== TMUX done ==="
}

# ============================================
# NVIM (neovim + config)
# ============================================

setup_nvim() {
    info "=== Setting up NVIM ==="

    # Install neovim (latest stable via AppImage)
    if ! command -v nvim &>/dev/null; then
        info "Installing Neovim (latest stable)..."
        curl -LO https://github.com/neovim/neovim/releases/latest/download/nvim.appimage
        chmod u+x nvim.appimage
        sudo mv nvim.appimage /usr/local/bin/nvim
    else
        info "Neovim already installed: $(nvim --version | head -1)"
    fi

    # Init config submodule
    info "Initializing nvim config..."
    git -C "$DOTFILES_DIR" submodule update --init --recursive

    # Link config
    mkdir -p "$HOME/.config"
    backup_and_link "$DOTFILES_DIR/nvim" "$HOME/.config/nvim"

    info "=== NVIM done ==="
}

# ============================================
# MAIN
# ============================================

usage() {
    echo "Usage: ./install.sh [command]"
    echo ""
    echo "Commands:"
    echo "  all       Setup everything (default)"
    echo "  zsh       Setup zsh (oh-my-zsh + theme + config)"
    echo "  tmux      Setup tmux (tpm + config)"
    echo "  nvim      Setup nvim (neovim + config)"
    echo "  help      Show this message"
}

main() {
    local cmd="${1:-all}"

    case "$cmd" in
    all)
        setup_zsh
        setup_tmux
        setup_nvim
        ;;
    zsh) setup_zsh ;;
    tmux) setup_tmux ;;
    nvim) setup_nvim ;;
    help | --help | -h)
        usage
        exit 0
        ;;
    *)
        error "Unknown command: $cmd"
        ;;
    esac

    echo ""
    info "Done!"
    [ -d "$BACKUP_DIR" ] && warn "Backups saved to: $BACKUP_DIR"
}

main "$@"
