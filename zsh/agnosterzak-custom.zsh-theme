# agnosterzak with the Tokyo Night gradient used by the tmux status bar.
# Sources the upstream theme and only overrides the segment colors, so
# re-downloading the upstream file doesn't lose the customization.
source "$ZSH/themes/agnosterzak.zsh-theme"

# Tokyo Night gradient (same hex as tmux status-left) with dark text
_GRAD_TEXT="#1a1b26"
_GRAD_1="#7aa2f7"  # time
_GRAD_2="#7dcfff"  # dir
_GRAD_3="#73daca"  # user / host

prompt_context() {
  if [[ -n "$SSH_CLIENT" ]]; then
    prompt_segment $_GRAD_3 $_GRAD_TEXT "%B$USER@%m%b"
  else
    prompt_segment $_GRAD_3 $_GRAD_TEXT "%B@$USER%b"
  fi
}

prompt_dir() {
  prompt_segment $_GRAD_2 $_GRAD_TEXT "%B%~%b"
}

prompt_time() {
  prompt_segment $_GRAD_1 $_GRAD_TEXT "%B%D{%a %e %b - %H:%M}%b"
}
