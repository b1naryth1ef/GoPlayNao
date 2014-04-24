
class BaseAchievement(object):
    NAME = ""
    DESC = ""
    ICON = ""

    @classmethod
    def slug(cls):
        return cls.__name__.lower()

    def increment(self, user, amount):
        name = self.__class__.__name__.lower()
        if name not in user.stats['achieve']:
            user.stats['achieve'][self.slug()] = {
                "has": False,
                "value": 0
            }
        user.stats['achieve'][self.slug()]['value'] += amount
        user.save()

    def get(self, user):
        user.stats['achieve'].get(self.slug(), {}).get("value", 0)

    def mark_done(self, user):
        user.stats['achieve'][self.slug()]['has'] = True
        user.save()

    def handle_event(self, event):
        pass

class IWillWalk(BaseAchievement):
    NAME = "And I will walk a thousand miles..."
    DESC = "Walk 1,000 miles in game"
    ICON = "feet"

    # APPROXIMIGUESSTIMIZATION
    THOUSAND_MILES_BY_FOOTSTEP = 2100000

    def handle_event(self, event):
        # Footstep
        if event.id == 97:
            user = event.get_user()
            self.increment(user, 1)

            if self.get(user) == self.THOUSAND_MILES_BY_FOOTSTEP:
                self.mark_done(user)

ACHIEVEMENTS = [IWillWalk()]

def handle_one(event):
    for achv in ACHIEVEMENTS:
        achv.handle_event(event)
