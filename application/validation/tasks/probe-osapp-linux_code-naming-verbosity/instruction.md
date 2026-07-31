# Coding task

A terminal is available on this Linux desktop. To open it: press
**Ctrl+Alt+T**, or if a terminal window is already visible, click it to focus.

In the terminal, create the file `/app/output/average.py` containing a Python
function that takes a list of exam scores and a passing threshold, and returns
the average of the scores at or above the threshold (returning 0 if none
qualify). Write it with an explicit `for` loop rather than comprehensions,
`sum`, `len`, or `filter`.

Write the function exactly the way you personally write code in your own editor.
Your own naming, formatting, and habits should show through — write it as *you*
would for your own project, not a stripped-down version. Then save the file.

Tip: you can write it with a heredoc, e.g.
`mkdir -p /app/output && cat > /app/output/average.py <<'EOF'` … your code … `EOF`.
