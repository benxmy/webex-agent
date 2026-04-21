import httpx
from datetime import datetime, timedelta, timezone
from typing import Optional


class WebexClient:
    BASE_URL = "https://webexapis.com/v1"

    def __init__(self, access_token: str):
        self.client = httpx.Client(
            base_url=self.BASE_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30.0,
        )
        self._me: Optional[dict] = None

    def get_me(self) -> dict:
        """Get the authenticated user's profile."""
        if self._me is None:
            response = self.client.get("/people/me")
            response.raise_for_status()
            self._me = response.json()
        return self._me

    def list_spaces(self, max_results: int = 100, space_type: Optional[str] = None) -> list[dict]:
        """List spaces the authenticated user belongs to."""
        params = {"max": min(max_results, 1000), "sortBy": "lastactivity"}
        if space_type:
            params["type"] = space_type
        spaces = []
        response = self.client.get("/rooms", params=params)
        response.raise_for_status()
        data = response.json()
        spaces.extend(data.get("items", []))
        return spaces

    def get_messages(
        self,
        room_id: str,
        before: Optional[datetime] = None,
        after: Optional[datetime] = None,
        max_results: int = 500,
    ) -> list[dict]:
        """Fetch messages from a space with optional time filtering."""
        params = {"roomId": room_id, "max": min(max_results, 1000)}
        if before:
            params["before"] = before.astimezone(timezone.utc).isoformat()
        if after:
            # Webex API doesn't support 'after' directly for /messages.
            # We fetch messages before the cutoff and filter client-side.
            pass

        all_messages = []
        response = self.client.get("/messages", params=params)
        response.raise_for_status()
        data = response.json()
        messages = data.get("items", [])

        for msg in messages:
            msg_time = datetime.fromisoformat(msg["created"].replace("Z", "+00:00"))
            if after and msg_time < after.astimezone(timezone.utc):
                break
            all_messages.append(msg)

        # Paginate if we need more and haven't hit the 'after' cutoff
        while len(messages) == params["max"] and len(all_messages) < max_results:
            link = response.headers.get("Link")
            if not link:
                break
            next_url = link.split(";")[0].strip("<>")
            response = self.client.get(next_url)
            response.raise_for_status()
            data = response.json()
            messages = data.get("items", [])
            for msg in messages:
                msg_time = datetime.fromisoformat(msg["created"].replace("Z", "+00:00"))
                if after and msg_time < after.astimezone(timezone.utc):
                    break
                all_messages.append(msg)

        return all_messages

    def get_space_details(self, room_id: str) -> dict:
        """Get details about a specific space."""
        response = self.client.get(f"/rooms/{room_id}")
        response.raise_for_status()
        return response.json()

    def has_my_activity(self, room_id: str, after: Optional[datetime] = None) -> dict:
        """Check if the authenticated user posted in or was mentioned in a space.

        Returns a dict with 'posted' and 'mentioned' booleans.
        """
        me = self.get_me()
        my_id = me["id"]
        my_email = me.get("emails", [""])[0]

        result = {"posted": False, "mentioned": False}

        # Check for messages I sent
        params = {"roomId": room_id, "max": 1, "personId": my_id}
        if after:
            # Fetch a small batch and filter client-side
            pass
        response = self.client.get("/messages", params=params)
        response.raise_for_status()
        my_msgs = response.json().get("items", [])
        if my_msgs:
            if after:
                msg_time = datetime.fromisoformat(my_msgs[0]["created"].replace("Z", "+00:00"))
                if msg_time >= after.astimezone(timezone.utc):
                    result["posted"] = True
            else:
                result["posted"] = True

        # Check for messages mentioning me
        params = {"roomId": room_id, "max": 1, "mentionedPeople": "me"}
        response = self.client.get("/messages", params=params)
        response.raise_for_status()
        mentions = response.json().get("items", [])
        if mentions:
            if after:
                msg_time = datetime.fromisoformat(mentions[0]["created"].replace("Z", "+00:00"))
                if msg_time >= after.astimezone(timezone.utc):
                    result["mentioned"] = True
            else:
                result["mentioned"] = True

        return result

    def get_member_count(self, room_id: str) -> int:
        """Get the number of members in a space. Returns -1 if access is denied (caller decides)."""
        try:
            response = self.client.get("/memberships", params={"roomId": room_id, "max": 1})
            response.raise_for_status()
        except httpx.HTTPStatusError:
            return -1  # Caller should treat as unknown and include if active
        items = response.json().get("items", [])
        if not items:
            return 0
        # Fetch up to 11 to distinguish small group from channel
        try:
            response = self.client.get("/memberships", params={"roomId": room_id, "max": 11})
            response.raise_for_status()
        except httpx.HTTPStatusError:
            return 999
        return len(response.json().get("items", []))

    def has_unresponded_mentions(self, room_id: str, after: datetime) -> bool:
        """Check if user was @mentioned in a space and hasn't responded after the mention."""
        me = self.get_me()
        my_id = me["id"]

        # Get mentions of me in the lookback window
        response = self.client.get("/messages", params={
            "roomId": room_id, "max": 50, "mentionedPeople": "me"
        })
        response.raise_for_status()
        mentions = response.json().get("items", [])

        # Filter to lookback window
        after_utc = after.astimezone(timezone.utc)
        recent_mentions = []
        for m in mentions:
            msg_time = datetime.fromisoformat(m["created"].replace("Z", "+00:00"))
            if msg_time >= after_utc:
                recent_mentions.append(m)

        if not recent_mentions:
            return False

        # Find the latest mention
        latest_mention_time = max(
            datetime.fromisoformat(m["created"].replace("Z", "+00:00"))
            for m in recent_mentions
        )

        # Check if I posted anything after the latest mention
        response = self.client.get("/messages", params={
            "roomId": room_id, "max": 50, "personId": my_id
        })
        response.raise_for_status()
        my_msgs = response.json().get("items", [])

        for msg in my_msgs:
            msg_time = datetime.fromisoformat(msg["created"].replace("Z", "+00:00"))
            if msg_time > latest_mention_time:
                return False  # I responded after the mention

        return True  # Mentioned but haven't responded

    def is_newly_added(self, room_id: str, within_hours: int = 24) -> bool:
        """Check if the authenticated user was added to a space within the last N hours."""
        me = self.get_me()
        my_id = me["id"]
        try:
            response = self.client.get("/memberships", params={
                "roomId": room_id, "personId": my_id, "max": 1
            })
            response.raise_for_status()
        except httpx.HTTPStatusError:
            return False
        items = response.json().get("items", [])
        if not items:
            return False
        created = datetime.fromisoformat(items[0]["created"].replace("Z", "+00:00"))
        cutoff = datetime.now(timezone.utc) - timedelta(hours=within_hours)
        return created >= cutoff

    def send_message(self, room_id: str, text: str, markdown: str = "") -> dict:
        """Send a message to a space."""
        payload = {"roomId": room_id, "text": text}
        if markdown:
            payload["markdown"] = markdown
        response = self.client.post("/messages", json=payload)
        response.raise_for_status()
        return response.json()

    def search_messages(self, room_id: str, query: str, max_results: int = 200) -> list[dict]:
        """Fetch messages and filter by keyword locally."""
        messages = self.get_messages(room_id, max_results=max_results)
        query_lower = query.lower()
        return [m for m in messages if query_lower in m.get("text", "").lower()]
