# Domain entity for Event (no ORM or persistence logic)
class Event:
    def __init__(self, id, event_type, source, content, metadata, score, priority, timestamp):
        self.id = id
        self.event_type = event_type
        self.source = source
        self.content = content
        self.metadata = metadata
        self.score = score
        self.priority = priority
        self.timestamp = timestamp
