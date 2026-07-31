# Short writing task

A terminal is available on this Linux desktop. To open it: press
**Ctrl+Alt+T**, or if a terminal window is already visible, click it to focus.

In the terminal, create the file `/app/output/answer.txt` containing a short
paragraph answering this question, in your own words:

> When you type a website's address into your browser and hit Enter, what
> actually happens between your computer and that website so the page ends up on
> your screen?

Tip: you can write it with a heredoc, e.g.
`mkdir -p /app/output && cat > /app/output/answer.txt <<'EOF'` … your paragraph …
`EOF`. Then run `cat /app/output/answer.txt` to confirm it was saved.

Write the explanation the way that feels natural to you — there are no length or
style requirements.
