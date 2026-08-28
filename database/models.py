from sqlalchemy import (
    Column, Integer, String, BigInteger, DateTime, Float,
    Boolean, ForeignKey, Text, JSON, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

Base = declarative_base()

class Business(Base):
    __tablename__ = "businesses"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    owner_id = Column(BigInteger)
    settings = Column(JSON, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    users = relationship("User", back_populates="business")
    bookings = relationship("Booking", back_populates="business")

class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True)
    username = Column(String)
    full_name = Column(String)
    phone = Column(String, unique=True)
    instagram = Column(String)
    instagram_subscribed = Column(Boolean, default=False)
    points = Column(Integer, default=0)
    level = Column(Integer, default=1)
    experience = Column(Integer, default=0)
    coins = Column(Integer, default=0)
    referral_code = Column(String, unique=True)
    referrer_id = Column(BigInteger, ForeignKey("users.id"))
    business_id = Column(Integer, ForeignKey("businesses.id"))
    registered_at = Column(DateTime, server_default=func.now())
    last_activity = Column(DateTime, onupdate=func.now())
    streak_days = Column(Integer, default=0)
    last_daily_bonus = Column(DateTime)
    business = relationship("Business", back_populates="users")
    referrals = relationship("User", backref="referrer", remote_side=[id])
    bookings = relationship("Booking", back_populates="user")
    points_history = relationship("PointsHistory", back_populates="user")
    lottery_entries = relationship("LotteryEntry", back_populates="user")
    shop_purchases = relationship("ShopPurchase", back_populates="user")
    missions_completed = relationship("MissionCompletion", back_populates="user")
    review_submissions = relationship("ReviewSubmission", back_populates="user")

class PointsHistory(Base):
    __tablename__ = "points_history"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    points = Column(Integer)
    reason = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    user = relationship("User", back_populates="points_history")

class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    business_id = Column(Integer, ForeignKey("businesses.id"))
    service = Column(String)
    amount = Column(Float)
    status = Column(String, default="pending")
    created_at = Column(DateTime, server_default=func.now())
    user = relationship("User", back_populates="bookings")
    business = relationship("Business", back_populates="bookings")

class Lottery(Base):
    __tablename__ = "lotteries"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    prize_pool = Column(JSON)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    ticket_cost = Column(Integer, default=10)
    is_active = Column(Boolean, default=True)
    winner_id = Column(BigInteger, ForeignKey("users.id"))
    created_at = Column(DateTime, server_default=func.now())
    entries = relationship("LotteryEntry", back_populates="lottery")

class LotteryEntry(Base):
    __tablename__ = "lottery_entries"
    id = Column(Integer, primary_key=True)
    lottery_id = Column(Integer, ForeignKey("lotteries.id"))
    user_id = Column(BigInteger, ForeignKey("users.id"))
    tickets = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())
    lottery = relationship("Lottery", back_populates="entries")
    user = relationship("User", back_populates="lottery_entries")

class Mission(Base):
    __tablename__ = "missions"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(Text)
    reward_points = Column(Integer, default=0)
    reward_coins = Column(Integer, default=0)
    type = Column(String)
    required_count = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)

class MissionCompletion(Base):
    __tablename__ = "mission_completions"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    mission_id = Column(Integer, ForeignKey("missions.id"))
    progress = Column(Integer, default=0)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime)
    user = relationship("User", back_populates="missions_completed")

class ShopItem(Base):
    __tablename__ = "shop_items"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(Text)
    cost_coins = Column(Integer, default=0)
    cost_points = Column(Integer, default=0)
    type = Column(String)
    effect = Column(JSON)
    quantity = Column(Integer, default=-1)
    is_active = Column(Boolean, default=True)

class ShopPurchase(Base):
    __tablename__ = "shop_purchases"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    item_id = Column(Integer, ForeignKey("shop_items.id"))
    quantity = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())
    user = relationship("User", back_populates="shop_purchases")

class ReviewSubmission(Base):
    __tablename__ = "review_submissions"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    type = Column(String)  # 'link' или 'video'
    content = Column(Text)  # ссылка или file_id видео
    status = Column(String, default="pending")  # pending, approved, rejected
    created_at = Column(DateTime, server_default=func.now())
    user = relationship("User", back_populates="review_submissions")
