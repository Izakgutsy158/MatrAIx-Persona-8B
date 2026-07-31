# Messaging API protocol

Your coworker Sam is reachable through a **REST API** on the compose sidecar
`support-api` (reachable from this container as `http://support-api:8000`). Use
`curl` or a short script to send Sam your message and read their reply.

## Endpoints

| Method | Path | Body | Response |
|--------|------|------|----------|
| `POST` | `/v1/messages` | `{"message": "<your text>"}` | `{"reply": "<Sam's reply>"}` |
| `GET` | `/v1/conversation` | — | `{"messages": [{"role": "customer"|"support", "content": "..."}, ...]}` |

1. `POST` to `/v1/messages` with the message you would send Sam asking them to
   resend the file they forgot to attach.
2. Read Sam's reply and `POST` at least once more, reacting to it.
