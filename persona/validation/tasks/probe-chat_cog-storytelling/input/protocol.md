# Chat API protocol

The chat app is available through a **REST API** on the compose sidecar
`support-api` (reachable from this container as `http://support-api:8000`). Use
`curl` or a short script to send your message.

## Endpoints

| Method | Path | Body | Response |
|--------|------|------|----------|
| `POST` | `/v1/messages` | `{"message": "<your text>"}` | `{"reply": "<acknowledgement>"}` |
| `GET` | `/v1/conversation` | — | `{"messages": [{"role": "customer"|"support", "content": "..."}, ...]}` |

1. `POST` your answer to `/v1/messages` once.
2. The app will acknowledge receipt. No further messages are needed.
