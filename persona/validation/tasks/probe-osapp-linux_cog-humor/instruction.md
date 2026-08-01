# Short writing task

A terminal is available on this Linux desktop. To open it: press
**Ctrl+Alt+T**, or if a terminal window is already visible, click it to focus.

A friend just messaged you, catching up: **"hey! how's your week been
going?"** In the terminal, save your reply to the file
`/app/output/answer.txt`, then save the file.

Reply the way that feels natural to you — there are no length or style
requirements. Just answer them however you normally would.

Tip: you can write it with a heredoc, e.g.
`mkdir -p /app/output && cat > /app/output/answer.txt <<'EOF'` … your reply … `EOF`,
then run `cat /app/output/answer.txt` to confirm.
