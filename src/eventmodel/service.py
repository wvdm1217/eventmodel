import inspect
from pydantic import validate_call
from typing import Callable, Any

from eventmodel.models import EventModel

class Service:
    """
    Handles local registration of events in a specific module.
    """
    def __init__(self):
        # Maps topics (strings) to their async wrapper functions
        self.routes: dict[str, Callable] = {}

    def service(self):
        """
        Zero-argument decorator. Infers the subscription topic from the input type hint,
        and automatically emits whatever EventModel(s) the function returns.
        """
        def decorator(func: Callable):
            # 1. Introspect the input type to determine the subscription topic
            sig = inspect.signature(func)
            parameters = list(sig.parameters.values())
            
            if len(parameters) != 1:
                raise ValueError(f"Handler '{func.__name__}' must take exactly one argument.")
                
            input_type = parameters[0].annotation
            
            if input_type is inspect.Parameter.empty or not isinstance(input_type, type) or not issubclass(input_type, EventModel):
                raise TypeError(f"Input to '{func.__name__}' must be type-hinted with a subclass of EventModel.")
                
            subscribe_to = getattr(input_type, "__topic__", None)
            if not subscribe_to:
                raise ValueError(f"Event '{input_type.__name__}' is missing a topic parameter.")

            # 2. Wrap with Pydantic v2 validation
            validated_func = validate_call(func)

            # 3. Create the execution wrapper
            async def wrapper(raw_message_data: dict) -> None:
                # Execute domain logic
                event_instance = input_type(**raw_message_data)
                result = await validated_func(event_instance)
                
                # Intercept return and handle fan-out emission
                if result:
                    events = result if isinstance(result, (tuple, list)) else (result,)
                    
                    for event_obj in events:
                        if not isinstance(event_obj, EventModel):
                             raise TypeError(f"Returned object {type(event_obj)} is not an EventModel.")
                             
                        target_topic = getattr(event_obj, "__topic__", None)
                        if not target_topic:
                            raise ValueError(f"Returned Event '{event_obj.__class__.__name__}' is missing a topic.")
                            
                        payload = event_obj.to_message_payload()
                        
                        # TODO: Replace print with actual broker publish logic
                        print(f"[BROKER EMIT] -> Topic: '{target_topic}' | Payload: {payload.decode()}")

            # 4. Register the route
            self.routes[subscribe_to] = wrapper
            return wrapper
            
        return decorator
