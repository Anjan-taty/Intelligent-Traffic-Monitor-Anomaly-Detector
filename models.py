# this is to define how data is stored, takes the base model from database and then buils how the model or the table looks like(Database shape)

from sqlalchemy import Integer, String, Float,DateTime
from datetime import datetime,timezone
from sqlalchemy.orm import Mapped,mapped_column
from database import Base

class RequestLog(Base):
    __tablename__="request_log"
    id:Mapped[int]=mapped_column(Integer,primary_key=True)
    ip_address:Mapped[str]=mapped_column(String(),index=True)      # Here Index=True because we are saying table to maintain a stricture to quickly accesss the ip when asked instead of searching all. SO, this creates a structure for storing them
    method:Mapped[str]=mapped_column(String(50))
    endpoint:Mapped[str]=mapped_column(String(50))
    status_code:Mapped[int]=mapped_column(Integer)
    response_time_ms:Mapped[float]=mapped_column(Float)
    timestamp:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc)) # Here lambda is written beacuse it needs to call this datetime.now for each cell not entirely for once
    


