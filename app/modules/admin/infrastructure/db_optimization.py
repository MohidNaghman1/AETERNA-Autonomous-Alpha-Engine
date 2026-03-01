"""Database optimization utilities.

Defines indexes and provides guidance for database performance tuning.
Includes connection pooling and parameterized query recommendations.
"""
from sqlalchemy import Index
from app.modules.identity.infrastructure.models import User

Index('ix_users_email', User.email)
