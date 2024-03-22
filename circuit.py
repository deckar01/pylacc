from collections import defaultdict
from math import log10, floor


k = 1e3
M = 1e6
G = 1e9
m = 1e-3
u = 1e-6
n = 1e-9

MAG = {
    0: '',
    1: 'k',
    2: 'M',
    3: 'G',
    -1: 'm',
    -2: 'u',
    -3: 'n',
}

UNITS = {
    'E': 'V',
    'I': 'A',
    'Z': 'Ω',
    'P': 'W',
}

def norm(t, v):
    if v is None:
        return '?'
    mag10 = floor(log10(v))
    mag1k = floor(mag10 / 3)
    v /= 10 ** mag10
    v = round(v, 2)
    v *= 10 ** mag10
    v /= 1000 ** mag1k
    return '{:.3g}{}{}'.format(v, MAG[mag1k], UNITS[t])

def count(*V):
    T = 0
    for v in V:
        if v is not None: T += 1
    return T

def given(*V):
    return len(V) > 0 and len(V) == count(*V)

def all(prop, G):
    return [c[prop] for c in G]

def identity(v):
    return v

def inverse(v):
    return 1 / v

class Component:
    laws = defaultdict(list)
    counter = defaultdict(lambda: 0)

    def __init__(self, *, E=None, I=None, Z=None, P=None, **kwargs):
        p = self.__class__.__name__
        Component.counter[p] += 1
        self.name = p + str(Component.counter[p])
        self.E, self.I, self.Z, self.P = E, I, Z, P
        for n, v in kwargs.items():
            n = n.upper()
            if n == 'R':
                n = 'Z'
            self[n] = v
    
    def __add__(self, other):
        return Series(self, other)
    
    def __truediv__(self, other):
        return Parallel(self, other)
    
    def __getitem__(self, prop):
        return getattr(self, prop, None)
    
    def __setitem__(self, prop, value):
        setattr(self, prop, value)

    @classmethod
    def law(cls, D, **paths):
        for K, P in paths.items():
            cls.laws[K].append((P, D))
    
    @property
    def unknowns(self):
        return (p for p in 'EIZP' if self[p] is None)
    
    def have(self, D):
        P = {k: self[k] for k in D if self[k] is not None}
        return P if len(P) == len(D) else None

    def solve(self):
        change = False
        for K in self.unknowns:
            for law, D in self.laws[K]:
                P = self.have(D)
                if P:
                    self[K] = law(**P)
                    change = True
                    break
        if change and self.unknowns:
            self.solve()
        return change
    
    def __str__(self, indent=''):
        parts = [p + '=' + norm(p, self[p]) for p in 'EIZP']
        return '{}( {} )'.format(self.name, ', '.join(parts))
    
    def __repr__(self):
        self.solve()
        Component.counter.clear()
        return str(self)

Component.law('EI', Z=lambda E, I: E / I, P=lambda E, I: E * I)
Component.law('EZ', I=lambda E, Z: E / Z, P=lambda E, Z: E * E / Z)
Component.law('IZ', E=lambda I, Z: I * Z, P=lambda I, Z: I * I / Z)
Component.law('PE', I=lambda P, E: P / E, Z=lambda P, E: E * E / P)
Component.law('PI', E=lambda P, I: P / I, Z=lambda P, I: P / I / I)
Component.law('PZ', I=lambda P, Z: (P / Z) ** 0.5, Z=lambda P, Z: (P * Z) ** 0.5)

class Load(Component):
    pass

class Source(Component):
    pass

class Circuit(Component):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        self.C = list(args)

    def __call__(self, *C):
        self.C.extend(C)
        return self

    @property
    def loads(self):
        return [L for L in self.C if not isinstance(L, Source)]

    @property
    def sources(self):
        return [S for S in self.C if isinstance(S, Source)]
    
    def solve_constant(self, prop, G):
        change = False
        if not given(self[prop]):
            for c in G:
                if given(c[prop]):
                    self[prop] = c[prop]
                    change = True
                    break
        if given(self[prop]):
            for c in G:
                if given(c[prop]):
                    continue
                c[prop] = self[prop]
                change = True
        return change
    
    def solve_linear(self, prop, T=identity):
        change = False
        if not given(self[prop]) and given(*all(prop, self.loads)):
            self[prop] = T(sum([T(value) for value in all(prop, self.loads)]))
            change = True
        if given(self[prop]) and count(*all(prop, self.loads)) == len(self.loads) - 1:
            c, = (c for c in self.loads if not given(c[prop]))
            s = sum([T(value) for value in all(prop, self.loads) if value])
            c[prop] = T(T(self[prop]) - s)
            change = True
        return change

    def solve(self):
        change = False
        while self._solve():
            change = True
        return change

    def _solve(self):
        change = super().solve()
        for c in self.C:
            change |= c.solve()
        return change
    
    def __str__(self, indent=''):
        indent += '  '
        return super().__str__(indent) + ''.join(
            '\n' + indent + c.__str__(indent)
            for c in self.C
        )

class Series(Circuit):
    def _solve(self):
        change = super()._solve()
        # TODO: Fix multiple sources
        change |= self.solve_constant('E', self.sources)
        change |= self.solve_constant('I', self.sources)
        change |= self.solve_constant('I', self.loads)
        change |= self.solve_linear('Z')
        change |= self.solve_linear('E')
        change |= self.solve_linear('P')
        return change
    
    def __add__(self, other):
        self.C.append(other)
        return self

class Parallel(Circuit):
    def _solve(self):
        change = super()._solve()
        change |= self.solve_constant('E', self.C)
        change |= self.solve_linear('I')
        change |= self.solve_linear('P')
        change |= self.solve_linear('Z', inverse)
        return change

    def __truediv__(self, other):
        self.C.append(other)
        return self

l = Load
s = Source
