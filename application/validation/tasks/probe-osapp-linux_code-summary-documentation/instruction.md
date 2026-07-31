# Coding task

A teammate asked you to send over a small `stats.py` helper module with three
functions they can drop into their script:

- `mean(nums)` — the arithmetic average of a list of numbers
- `median(nums)` — the middle value (average of the two middle values if the
  list length is even)
- `mode(nums)` — the most frequently occurring value

A terminal is already open on this Linux desktop (if you don't see one, press
**Ctrl+Alt+T**). You only need one command: paste exactly what you'd send your
teammate into `/app/output/stats.py` using a heredoc, like this —

```
mkdir -p /app/output && cat > /app/output/stats.py <<'EOF'
<your code here>
EOF
```

Then run `cat /app/output/stats.py` to confirm it was written.

Write it exactly the way you normally would when handing code to a teammate —
your own natural style, not a stripped-down version. There are no style
requirements either way.
