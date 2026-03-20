from sqlalchemy import Column, Integer, String, ForeignKey
from app.db.base import Base

class UserBinAssignment(Base):
    __tablename__ = "user_bin_assignments"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    bin_id = Column(String, ForeignKey("bins.bin_id"))
