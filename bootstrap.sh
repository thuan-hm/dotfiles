#!/bin/bash

set -e

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

PACKAGES=(
    zsh
    tmux
    git
    curl
    alacritty
    fastfetch
    lsd
)

detect_pm() {
    if command -v apt &>/dev/null; then
        PM="apt"
        PM_INSTALL="sudo apt install -y"
        PM_UPDATE="sudo apt update"
    elif command -v dnf &>/dev/null; then
        PM="dnf"
        PM_INSTALL="sudo dnf install -y"
        PM_UPDATE=""
    elif command -v pacman &>/dev/null; then
        PM="pacman"
        PM_INSTALL="sudo pacman -S --noconfirm"
        PM_UPDATE="sudo pacman -Sy"
    elif command -v brew &>/dev/null; then
        PM="brew"
        PM_INSTALL="brew install"
        PM_UPDATE="brew update"
    else
        error "No supported package manager found"
    fi
    info "Detected: $PM"
}

install_pkg() {
    local pkg="$1"
    if command -v "$pkg" &>/dev/null; then
        warn "$pkg already installed"
    else
        $PM_INSTALL "$pkg"
        info "$pkg installed"
    fi
}

list_packages() {
    echo "Available packages:"
    for pkg in "${PACKAGES[@]}"; do
        if command -v "$pkg" &>/dev/null; then
            echo -e "  ${GREEN}$pkg${NC} (installed)"
        else
            echo -e "  ${YELLOW}$pkg${NC} (missing)"
        fi
    done
}

install_all() {
    detect_pm
    [ -n "$PM_UPDATE" ] && $PM_UPDATE
    for pkg in "${PACKAGES[@]}"; do
        install_pkg "$pkg"
    done
    info "Done! Now run: ./install.sh"
}

install_one() {
    local pkg="$1"
    for p in "${PACKAGES[@]}"; do
        [ "$p" = "$pkg" ] && {
            detect_pm
            [ -n "$PM_UPDATE" ] && $PM_UPDATE
            install_pkg "$pkg"
            return
        }
    done
    error "Unknown package: $pkg (available: ${PACKAGES[*]})"
}

usage() {
    echo "Usage: ./bootstrap.sh [command] [package]"
    echo ""
    echo "Commands:"
    echo "  all           Install all packages (default)"
    echo "  list          List packages and their status"
    echo "  install PKG   Install a single package"
    echo "  help          Show this message"
    echo ""
    echo "Packages: ${PACKAGES[*]}"
}

main() {
    case "${1:-all}" in
    all) install_all ;;
    list) list_packages ;;
    install)
        [ -z "$2" ] && error "Specify a package: ./bootstrap.sh install PKG"
        install_one "$2"
        ;;
    help | --help | -h) usage ;;
    *) error "Unknown command: $1" ;;
    esac
}

main "$@"
