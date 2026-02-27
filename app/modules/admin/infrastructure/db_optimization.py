# Example: Add indexes and optimize DB queries
from sqlalchemy import Index
from app.modules.identity.infrastructure.models import User

# Add index to email for faster lookup
Index('ix_users_email', User.email)

# Connection pooling tuning can be set in SQLAlchemy engine config
# e.g., pool_size, max_overflow, pool_timeout

# Use parameterized queries everywhere (already handled by SQLAlchemy ORM)
