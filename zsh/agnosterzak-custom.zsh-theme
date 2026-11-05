# agnosterzak with the blue-to-cyan gradient used by the tmux status bar.
# Sources the upstream theme and only overrides the segment colors, so
# re-downloading the upstream file doesn't lose the customization.
source "$ZSH/themes/agnosterzak.zsh-theme"

# 256-color gradient (same values as tmux status-left) with dark text
_GRAD_TEXT=234
_GRAD_1=67   # time
_GRAD_2=74   # dir
_GRAD_3=116  # user / host

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
