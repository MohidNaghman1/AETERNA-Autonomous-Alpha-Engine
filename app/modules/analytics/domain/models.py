"""Domain entity for Event.

Defines the core Event entity with business logic, independent of any persistence layer.
"""


class Event:
    """Domain model representing an event.
    
    Contains event data and behavior without any ORM or database specifics.
    
    Attributes:
        id: Unique event identifier
        event_type: Type or category of the event
        source: Source of the event (RSS feed, price api, etc.)
        content: Event message or description
        metadata: Additional contextual data
        score: Relevance or importance score (0-100)
        priority: Priority level (LOW, MEDIUM, HIGH)
        timestamp: When the event occurred
    """
    
    def __init__(self, id, event_type, source, content, metadata, score, priority, timestamp):
        """Initialize an Event.
        
        Args:
            id: Event ID
            event_type: Event type
            source: Event source
            content: Event content
            metadata: Additional metadata
            score: Relevance score
            priority: Priority level
            timestamp: Event timestamp
        """
        self.id = id
        self.event_type = event_type
        self.source = source
        self.content = content
        self.metadata = metadata
        self.score = score
        self.priority = priority
        self.timestamp = timestamp
