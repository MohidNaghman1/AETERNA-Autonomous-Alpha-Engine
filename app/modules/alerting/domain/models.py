# Domain entity for Alert (no ORM or persistence logic)
class Alert:
    def __init__(self, id, user_id, event_id, channels, status, sent_at, created_at):
        self.id = id
        self.user_id = user_id
        self.event_id = event_id
        self.channels = channels
        self.status = status
        self.sent_at = sent_at
        self.created_at = created_at
