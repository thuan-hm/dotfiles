
source "$ZSH/themes/agnosterzak.zsh-theme"

_GRAD_TEXT="#1a1b26"
_GRAD_1="#7aa2f7"  # time
_GRAD_2="#7dcfff"  # dir
_GRAD_3="#73daca"  # user / host

_dark=$'\e[22;38;2;26;27;38m'
for _c in white magenta black; do
  fg_bold[$_c]=$_dark
  fg_no_bold[$_c]=$_dark
done
unset _c

functions[_agnoster_segment]=$functions[prompt_segment]
prompt_segment() {
  local fg=$2
  case $2 in white|magenta|black) fg=$_GRAD_TEXT ;; esac
  _agnoster_segment "$1" "$fg" "${@:3}"
}

prompt_context() {
  if [[ -n "$SSH_CLIENT" ]]; then
    prompt_segment $_GRAD_3 $_GRAD_TEXT "$USER@%m"
  else
    prompt_segment $_GRAD_3 $_GRAD_TEXT "@$USER"
  fi
}

prompt_dir() {
  prompt_segment $_GRAD_2 $_GRAD_TEXT "%~"
}

prompt_time() {
  prompt_segment $_GRAD_1 $_GRAD_TEXT "%D{%a %e %b - %H:%M}"
}
