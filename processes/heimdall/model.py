class IdentifiedObject:
    """
        This class might be unnecessary or really necessary depending on how
        I will implement the logic for IdentifiedObject. If I want it configurable
        from UI then adapt it into the UIModel and take hemidall into own app
    """

    def __init__(self, name=None, location=None, tags=None):
        self.name = name
        self.location = location
        self.tags = tags if tags else []
