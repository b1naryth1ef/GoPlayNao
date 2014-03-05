

class Entity(object):
    def __init__(self, rank=0, impulse=0):
        self.rank = rank
        self.impulse = impulse

    def rank(self, other, scores):
        self.impulse = rank(self, other, scores)


def calc_impulse(ranks, scores):
    score_diff = (scores[1] - scores[0])
    rank_diff = (ranks[0] - ranks[1])
    return (rank_diff * score_diff)

# Applied rank to a based on b
def rank(a, b, scores):
    impulse = calc_impulse([a.rank, b.rank], scores)

    # I have same rank as the other player
    if a.rank == b.rank:
        # I do better than the other player
        if scores[0] > scores[1]:
            return impulse
        # We tie scores
        elif scores[0] == scores[1]:
            return 0
        # I do worse than the other player
        else:
            return -impulse
    elif a.rank > b.rank:
        if scores[0] < scores[1]:
            return -impulse
        else:
            return 0
    else:
        return -rank(b, a, [scores[1], scores[0]])
