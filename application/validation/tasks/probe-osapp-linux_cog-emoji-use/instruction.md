# Short writing task

A terminal is available on this Linux desktop. To open it: press
**Ctrl+Alt+T**, or if a terminal window is already visible, click it to focus.

In the terminal, create the file `/app/output/answer.txt`. It should contain a
short, casual one-paragraph review — the kind you would post to an app store — of
an app you use all the time and genuinely love. Say what it is and why it makes
your day better.

Tip: you can write it with a heredoc, e.g.
`mkdir -p /app/output && cat > /app/output/answer.txt <<'EOF'` … your review … `EOF`.
Then run `cat /app/output/answer.txt` to confirm it was written.

This is a message written for other people to read, not code or config. Write it
exactly the way you would actually post it, and keep every symbol and character
you would naturally use. Do NOT drop or replace anything for the sake of encoding
or "cleanliness" — whatever you would normally type, type it verbatim into the file.
