import itertools

class ChoiceEnum(object):
    def __init__(self, choices):
        if isinstance(choices, basestring):
            choices=choices.split()
        if isinstance(choices, (list,tuple)) and all(isinstance(x, tuple) and len(x)==2 for x in choices):
            values=choices
        else:
            values=zip(itertools.count(1), choices)
        for v, n in values:
            setattr(self, n.upper(), v)
        self._choices=values

    def __getitem__(self, idx):
        return self._choices[idx]

