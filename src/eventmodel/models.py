from typing import ClassVar, Optional

from pydantic import BaseModel, ConfigDict


class EventModel(BaseModel):
    """
    Base class for all domain events. 
    Uses __init_subclass__ to capture routing metadata exactly like SQLModel.
    """
    __topic__: ClassVar[Optional[str]] = None
    
    model_config = ConfigDict(strict=True)

    def __init_subclass__(cls, topic: str | None = None, **kwargs):
        # Pass remaining kwargs up to Pydantic's BaseModel
        super().__init_subclass__(**kwargs) 
        
        # Bind the infrastructure topic to the class
        if topic:
            cls.__topic__ = topic

    def to_message_payload(self) -> bytes:
        """Serializes the Pydantic model into a raw byte payload for brokers."""
        return self.model_dump_json().encode('utf-8')
