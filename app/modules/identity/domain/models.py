# Domain entity for User (no ORM or persistence logic)
class User:
    def __init__(self, id, email, password_hash, telegram_id, preferences, created_at, email_verified):
        self.id = id
        self.email = email
        self.password_hash = password_hash
        self.telegram_id = telegram_id
        self.preferences = preferences
        self.created_at = created_at
        self.email_verified = email_verified

class UserPreference:
    def __init__(self, id, user_id, preferences):
        self.id = id
        self.user_id = user_id
        self.preferences = preferences
