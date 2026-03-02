"""Domain entities for user identity management.

Defines core User and UserPreference entities with business logic,
independent of any persistence layer.
"""


class User:
    """Domain model representing a user.

    Contains user data and behavior without any ORM or database specifics.

    Attributes:
        id: Unique user identifier
        email: User email address
        password_hash: Bcrypt password hash
        telegram_id: Optional Telegram chat ID for alerts
        preferences: User preferences dict
        created_at: Account creation timestamp
        email_verified: Whether email has been verified
    """

    def __init__(
        self, id, email, password_hash, telegram_id, preferences, created_at, email_verified
    ):
        """Initialize a User.

        Args:
            id: User ID
            email: Email address
            password_hash: Hashed password
            telegram_id: Telegram chat ID
            preferences: User preferences
            created_at: Creation timestamp
            email_verified: Email verification status
        """
        self.id = id
        self.email = email
        self.password_hash = password_hash
        self.telegram_id = telegram_id
        self.preferences = preferences
        self.created_at = created_at
        self.email_verified = email_verified


class UserPreference:
    """Domain model for user preferences.

    Encapsulates user-specific alert and delivery preferences.

    Attributes:
        id: Unique preference record ID
        user_id: Associated user ID
        preferences: Preferences dict (channels, quiet_hours, etc.)
    """

    def __init__(self, id, user_id, preferences):
        """Initialize UserPreference.

        Args:
            id: Preference record ID
            user_id: User ID
            preferences: Preferences dict
        """
        self.id = id
        self.user_id = user_id
        self.preferences = preferences
