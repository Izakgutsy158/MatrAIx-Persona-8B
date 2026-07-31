# Chat protocol

The other person is reachable through a **REST API** on the compose sidecar
`support-api` (reachable from this container as `http://support-api:8000`). Use
`curl` or a short script to have a real multi-turn chat.

## Endpoints

| Method | Path | Body | Response |
|--------|------|------|----------|
| `POST` | `/v1/messages` | `{"message": "<your text>"}` | `{"reply": "<their reply>"}` |
| `GET` | `/v1/conversation` | — | `{"messages": [{"role": "customer"|"support", "content": "..."}, ...]}` |

1. `POST` your reply telling them the story they asked for.
2. `POST` at least once more, reacting to what they say back.

Send messages one at a time and reply the way you naturally would.
