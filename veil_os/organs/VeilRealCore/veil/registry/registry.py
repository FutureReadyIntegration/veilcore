class OrganRegistry:
    def __init__(self):
        self._organs = {}

    def register(self, organ):
        self._organs[organ.name] = organ

    def get(self, name):
        return self._organs.get(name)

    def all_organs(self):
        return list(self._organs.values())
