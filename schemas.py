# This is to define how the data is sent/received by the API's(API shape)
# Pydantic is a python library which is used for the data validation and serialization
#->We define the shape of the data in the python class
#->Pydantic helps to convert the SQLAlchemy objects to the json format
# SQLAlchemy   → talks to DATABASE
# Pydantic     → validates and shapes DATA
from pydantic import BaseModel,ConfigDict

class UserSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    age: int

# Pretend this is a SQLAlchemy object
class FakeDBObject:
    name = "Arjun"
    age = 21

obj = FakeDBObject()

# Try to create a Pydantic model from it
user = UserSchema.model_validate(obj)
print(user)