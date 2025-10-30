"""
Session Memory Manager - Persists conversational context across requests
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from config import Config


if TYPE_CHECKING:
    from supabase import Client


class SessionMemoryManager:
    """
    Lightweight memory layer backed by Supabase for storing short-term
    conversational context. The manager keeps track of the most recent
    exchanges for each UI session so we can provide prior turns as context
    on subsequent requests.
    """

    def __init__(self, supabase_client: Optional["Client"] = None):
        # Import lazily to avoid circular import during testing
        if supabase_client is None:
            from supabase import create_client

            self.supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        else:
            self.supabase = supabase_client

    # ------------------------------------------------------------------
    # Session helpers
    # ------------------------------------------------------------------
    def start_session(self, session_id: Optional[str] = None) -> str:
        """Ensure a session record exists and return the session id."""

        sid = session_id or str(uuid.uuid4())
        now_iso = datetime.utcnow().isoformat()

        try:
            self.supabase.table("agent_sessions").upsert(
                {
                    "session_id": sid,
                    "created_at": now_iso,
                    "last_interaction_at": now_iso,
                },
                on_conflict="session_id",
            ).execute()
        except Exception as exc:
            # We log but do not fail the request if the metadata table is missing.
            print(f"Warning: Unable to ensure agent session record: {exc}")

        return sid

    # ------------------------------------------------------------------
    # Message persistence
    # ------------------------------------------------------------------
    def append_message(self, session_id: str, role: str, content: str) -> Optional[Dict[str, Any]]:
        """Persist a single chat message for a session."""

        if not session_id or not content:
            return None

        message_index = self._get_next_message_index(session_id)
        message_payload = {
            "session_id": session_id,
            "message_index": message_index,
            "role": role,
            "content": content,
            "created_at": datetime.utcnow().isoformat(),
        }

        try:
            result = (
                self.supabase.table("session_messages")
                .insert(message_payload)
                .execute()
            )

            # Update session metadata timestamp
            try:
                (
                    self.supabase.table("agent_sessions")
                    .update({"last_interaction_at": datetime.utcnow().isoformat()})
                    .eq("session_id", session_id)
                    .execute()
                )
            except Exception:
                # Metadata table is optional. Ignore failures silently.
                pass

            return result.data[0] if result.data else message_payload

        except Exception as exc:
            print(f"Warning: Failed to append session message: {exc}")
            return None

    def get_recent_messages(self, session_id: str, limit: int = 4) -> List[Dict[str, Any]]:
        """Return the most recent messages for the given session."""

        if not session_id:
            return []

        try:
            result = (
                self.supabase.table("session_messages")
                .select("role, content, message_index")
                .eq("session_id", session_id)
                .order("message_index", desc=True)
                .limit(limit)
                .execute()
            )

            if not result.data:
                return []

            # Reverse so oldest message comes first for downstream prompts
            return list(reversed(result.data))

        except Exception as exc:
            print(f"Warning: Failed to fetch session messages: {exc}")
            return []

    def build_prompt_with_context(self, session_id: Optional[str], user_prompt: str) -> str:
        """Append recent conversation history as context to the prompt if available."""

        if not session_id:
            return user_prompt

        recent_messages = self.get_recent_messages(session_id, limit=10)
        if not recent_messages:
            return user_prompt

        formatted_context = []
        for message in recent_messages:
            role = message.get("role", "assistant").strip().lower()
            role_label = "User" if role == "user" else "Assistant"
            formatted_context.append(f"{role_label}: {message.get('content', '')}")

        context_block = "\n".join(formatted_context)
        return (
            f"{user_prompt}\n\n"
            "Context from the previous exchange (use only if relevant):\n"
            f"{context_block}"
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _get_next_message_index(self, session_id: str) -> int:
        try:
            result = (
                self.supabase.table("session_messages")
                .select("message_index")
                .eq("session_id", session_id)
                .order("message_index", desc=True)
                .limit(1)
                .execute()
            )

            if result.data:
                return (result.data[0].get("message_index") or 0) + 1

        except Exception as exc:
            print(f"Warning: Failed to determine message index: {exc}")

        return 0


