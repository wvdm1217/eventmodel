from eventmodel.service import Service

class App(Service):
    """
    The root application that orchestrates the message broker client
    and merges all sub-services together.
    """
    def __init__(self):
        super().__init__()
        # self.broker = MyBrokerClient() # Inject Kafka/Redis here later
        
    def include(self, service: Service) -> None:
        """
        Merges a sub-service's routes into the main application.
        Fails fast if two handlers try to listen to the same topic.
        """
        for topic, wrapper in service.routes.items():
            if topic in self.routes:
                raise ValueError(
                    f"Routing collision: A handler is already registered for topic '{topic}'"
                )
            self.routes[topic] = wrapper
            print(f"[APP BOOT] Mounted listener for: '{topic}'")
