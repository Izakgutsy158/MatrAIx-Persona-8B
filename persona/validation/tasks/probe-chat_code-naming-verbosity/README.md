# probe-chat_code-naming-verbosity

**Attribute:** `code_naming_verbosity` — X=`Highly verbose (long descriptive names)` / Y=`Single-letter names`  **Env:** Chat (acme-support sidecar, reused as coding-review chat)
Persona pastes its own Python function into the chat and asks for a review; the
attribute shows in the code (variable/function naming) the persona writes. A/B
over 5+5 personas. Judge from trajectory with judge_adherence.py (reward not needed).
