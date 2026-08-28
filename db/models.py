from datetime import datetime, date, time
from sqlalchemy import (
    Column, BigInteger, String, Float, Integer, Boolean,
    DateTime, Date, Time, Text, ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, nullable=False)
    ref_code = Column(String(20), unique=True, nullable=False)
    invited_by = Column(BigInteger, ForeignKey("users.id"), nullable=True)  # ✅ ссылаемся на id
    
    fraud_score = Column(Integer, default=100, nullable=False)
    shadow_ban = Column(Boolean, default=False, nullable=False)
    is_vip = Column(Boolean, default=False, nullable=False)
    instagram_subscribed = Column(Boolean, default=False, nullable=False)
    total_visits = Column(Integer, default=0, nullable=False)
    total_checks = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow, nullable=False)

    rewards = relationship("Reward", back_populates="user")
    bookings = relationship("Booking", back_populates="user")
    spins = relationship("Spin", back_populates="user")
    content_tasks = relationship("ContentTask", back_populates="user")
    referrals_given = relationship("Referral", back_populates="referrer", foreign_keys="Referral.referrer_id")
    referrals_received = relationship("Referral", back_populates="referred_user", foreign_keys="Referral.referred_id")


class Reward(Base):
    __tablename__ = "rewards"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)  # ✅ users.id
    amount = Column(Float, nullable=False)
    source = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_expired = Column(Boolean, default=False, nullable=False)
    is_frozen = Column(Boolean, default=False, nullable=False)
    freeze_until = Column(DateTime, nullable=True)
    frozen_at_booking_id = Column(BigInteger, ForeignKey("bookings.id"), nullable=True)

    user = relationship("User", back_populates="rewards")


class Referral(Base):
    __tablename__ = "referrals"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    referrer_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)  # ✅ users.id
    referred_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)  # ✅ users.id
    visited = Column(Boolean, default=False, nullable=False)
    reward_given = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    referrer = relationship("User", back_populates="referrals_given", foreign_keys=[referrer_id])
    referred_user = relationship("User", back_populates="referrals_received", foreign_keys=[referred_id])


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)  # ✅ users.id
    service = Column(String(200), nullable=False)
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=False)
    duration = Column(Integer, default=60, nullable=False)
    comment = Column(Text, nullable=True)
    status = Column(String(20), default="pending", nullable=False)
    slot_booked = Column(Boolean, default=False, nullable=False)
    suggested_time = Column(Time, nullable=True)
    admin_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    confirmed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="bookings")


class Spin(Base):
    __tablename__ = "spins"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)  # ✅ users.id
    prize = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="spins")


class ContentTask(Base):
    __tablename__ = "content_tasks"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)  # ✅ users.id
    content_type = Column(String(20), nullable=False)
    link = Column(Text, nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    bonus = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="content_tasks")


class Admin(Base):
    __tablename__ = "admins"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    role = Column(String(20), default="admin", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class LogAction(Base):
    __tablename__ = "log_actions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)  # ✅ users.id
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Schedule(Base):
    __tablename__ = "schedule"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)
    max_patients = Column(Integer, default=1, nullable=False)
    current_patients = Column(Integer, default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint("date", "time", name="uq_schedule_date_time"),
    )


class Raffle(Base):
    __tablename__ = "raffles"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    prize_name = Column(String(200), nullable=False)
    status = Column(String(20), default="active", nullable=False)
    winner_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)  # ✅ users.id
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)


class RaffleParticipant(Base):
    __tablename__ = "raffle_participants"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    raffle_id = Column(BigInteger, ForeignKey("raffles.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)  # ✅ users.id
    weight = Column(Float, default=1.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
