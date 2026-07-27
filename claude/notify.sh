#!/bin/bash
TITLE="Claude Code"
ICON="$HOME/.claude/claude-icon.png"

done_msgs=(
    "Aight I'm done"
    "Yo it's finished, come look"
    "Done, where you at"
    "Finished bro, you seeing this"
    "Okay that's a wrap"
    "It's done, I'm out"
    "Bro I finished, wyd"
    "Done deal, pull up and check"
    "Aight that's cooked, come look"
    "Finished, told you I got it"
    "Done, stop scrolling and check"
    "Wrapped it up, your turn"
)
input_msgs=(
    "Bro wake up, I need you"
    "Yo where you at"
    "Hello?? you there"
    "Bro come here real quick"
    "Aye I need you for a sec"
    "You alive? need your input"
    "Pull up, I got a question"
    "Yo respond, I'm stuck"
    "Where'd you go bro"
    "Need a hand over here"
    "Oi, kinda stuck without you"
    "You good? I need something"
)

case "$1" in
done)
    SOUND="Glass"
    MESSAGE="${done_msgs[$((RANDOM % ${#done_msgs[@]}))]}"
    ;;
input)
    SOUND="Ping"
    MESSAGE="${input_msgs[$((RANDOM % ${#input_msgs[@]}))]}"
    ;;
*)
    MESSAGE="${1:-Claude Code}"
    TITLE="${2:-$TITLE}"
    SOUND="${3:-Glass}"
    ;;
esac

if command -v terminal-notifier &>/dev/null; then
    ARGS=(-title "$TITLE" -message "$MESSAGE" -sound "$SOUND")
    [ -f "$ICON" ] && ARGS+=(-appIcon "$ICON" -contentImage "$ICON")
    terminal-notifier "${ARGS[@]}"
else
    osascript -e "display notification \"$MESSAGE\" with title \"$TITLE\" sound name \"$SOUND\""
fi
