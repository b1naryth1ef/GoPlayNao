
BADGES = {}

class Badge(object):
    def __init__(self, id, name, description, public=True):
        self.id = id
        self.name = name
        self.description = description
        self.public = public
        BADGES[self.id] = self

    def to_dict(self, with_count=True):
        data = {
            "id": self.id,
            "name": self.name,
            "desc": self.description
        }

        if with_count:
            data['have'] = self.get_have_count()

        return data

    def get_have_count(self):
        # TODO: move this to stats/cache
        from database import User
        return User.select().where(User.badges.contains(self.id)).count()


BADGE_BETA_TESTER = Badge(
    1,
    "Beta Tester",
    "Helped during the beta of GoPlayMM"
)
