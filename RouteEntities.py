"""Route entities"""

class RouteStep(object):
    """One block step along a route."""
    def __init__(self, block_id, rating):
        self.block_id = block_id
        self.rating = rating
