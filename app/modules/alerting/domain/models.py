"""Domain entity for Alert.

Defines the core Alert entity with business logic, independent of any persistence layer.
"""


class Alert:
    """Domain model representing an alert.

    Contains all data and behavior related to an alert without any ORM or database specifics.

    Attributes:
        id: Unique alert identifier
        user_id: User who owns this alert
        event_id: Source event that triggered the alert
        channels: List of delivery channels (telegram, email, web)
        status: Current alert status (pending, sent, failed)
        sent_at: Timestamp when alert was sent
        created_at: Timestamp when alert was created
    """

    def __init__(self, id, user_id, event_id, channels, status, sent_at, created_at):
        """Initialize an Alert.

        Args:
            id: Alert ID
            user_id: User ID
            event_id: Event ID
            channels: List of delivery channels
            status: Alert status
            sent_at: Sent timestamp
            created_at: Creation timestamp
        """
        self.id = id
        self.user_id = user_id
        self.event_id = event_id
        self.channels = channels
        self.status = status
        self.sent_at = sent_at
        self.created_at = created_at
