# ruff: noqa: E741, E701

from cmath import polar, sqrt, isclose
from math import log10, floor, pi


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
    4: 'T',
    -1: 'm',
    -2: 'u',
    -3: 'n',
    -4: 'p',
}

UNITS = {
    'E': 'V',
    'I': 'A',
    'Z': 'Ω',
    'P': 'W',
    'F': 'Hz',
    'C': 'F',
    'L': 'H',
}

PHASED = 'EIZP'

def norm(t, v, f):
    if v is None:
        return t + '=?'
    if f is None and v.imag:
        raise ValueError('Reactive loads require an AC frequency')
    if t in PHASED and f is not None:
        v, a = polar(v)
        phase = '∠' + '{:.3g}°'.format(360 * a / 2 / pi)
    else:
        v = v.real
        phase = ''
    mag10 = floor(log10(abs(v)))
    mag1k = floor(mag10 / 3)
    v /= 10 ** mag10
    v = round(v, 2)
    v *= 10 ** mag10
    v /= 1000 ** mag1k
    return '{}={:.3g}{}{}{}'.format(t, v, MAG[mag1k], UNITS[t], phase)

def count(*V):
    T = 0
    for v in V:
        if v is not None: T += 1
    return T

def given(*V):
    return len(V) > 0 and len(V) == count(*V)

def all(prop, G):
    return [c[prop] for c in G]

class Component:
    show = ('E', 'I', 'Z', 'P')
    optional = ()
    laws = {}
    counter = {}
    props = set()

    def __init__(self, **kwargs):
        name = self.__class__.__name__
        if name not in Component.counter:
            Component.counter[name] = 0
        Component.counter[name] += 1
        self.name = name + str(Component.counter[name])
        self.given = []
        for n, v in kwargs.items():
            n = n.upper()
            if n == 'R': n = 'Z'
            self.given.append(n)
            # HACK: Python 3.4 requires int to complex promotion
            self[n] = complex(v)
    
    def __add__(self, other):
        return Series(self, other)
    
    def __truediv__(self, other):
        return Parallel(self, other)
    
    def __getitem__(self, prop):
        return getattr(self, prop, None)
    
    def __setitem__(self, prop, value):
        setattr(self, prop, value)

    @classmethod
    def law(cls, **paths):
        def _law(fn):
            for K, D in paths.items():
                cls.props.add(K)
                setattr(cls, K, None)
                if K not in cls.laws:
                    cls.laws[K] = []
                cls.laws[K].append((D, fn))
        return _law
    
    @property
    def unknowns(self):
        return (p for p in self.props if self[p] is None)
    
    def have(self, D):
        P = {k: self[k] for k in D if self[k] is not None}
        return P if len(P) == len(D) else None

    def solve(self):
        change = False
        for K in self.unknowns:
            for D, law in self.laws[K]:
                P = self.have(D)
                if not P:
                    continue
                self[K] = law(**P)
                if self[K] is not None:
                    change = True
                    break
        if change and self.unknowns:
            self.solve()
        return change

    def verify(self):
        errors = []
        for K in self.props:
            if not given(self[K]):
                continue
            for D, law in self.laws[K]:
                P = self.have(D)
                if not P:
                    continue
                V = law(**P)
                if not isclose(self[K], V):
                    errors.append(f'{D} -> {K}: {self[K]} != {V}')
        if errors:
            raise AssertionError('\n'.join(errors))

    def __str__(self, indent=''):
        K = self.show + tuple(p for p in self.optional if self[p] is not None)
        parts = [norm(p, self[p], self['F']) for p in K]
        return '{}( {} )'.format(self.name, ', '.join(parts))
    
    def __repr__(self):
        self.solve()
        Component.counter.clear()
        return str(self)

Component.law(Z=('E', 'I'))(lambda E, I: E / I)
Component.law(Z=('P', 'E'))(lambda P, E: E * E / P)
Component.law(Z=('P', 'I'))(lambda P, I: P / (I * I))
Component.law(P=('E', 'I'))(lambda E, I: E * I)
Component.law(P=('E', 'Z'))(lambda E, Z: E * E / Z)
Component.law(P=('I', 'Z'))(lambda I, Z: I * I * Z)
Component.law(E=('I', 'Z'))(lambda I, Z: I * Z)
Component.law(E=('P', 'I'))(lambda P, I: P / I)
# Component.law(E=('P', 'Z'))(lambda P, Z: sqrt(P * Z)) # TODO: Reactive signs are lost in sqrt
Component.law(I=('E', 'Z'))(lambda E, Z: E / Z)
Component.law(I=('P', 'E'))(lambda P, E: P / E)
Component.law(I=('P', 'Z'))(lambda P, Z: sqrt(P / Z))

Component.law(Z=('C', 'F'))(lambda C, F: -1j / (2 * pi * F * C))
Component.law(Z=('L', 'F'))(lambda L, F: 1j * 2 * pi * F * L)
Component.law(C=('Z', 'F'))(lambda Z, F: -1 / (2 * pi * F * Z.imag) if Z.imag < 0 and isclose(Z.real, 0) else None)
Component.law(L=('Z', 'F'))(lambda Z, F: Z.imag / (2 * pi * F) if Z.imag > 0 and isclose(Z.real, 0) else None)
Component.law(F=('Z', 'C'))(lambda Z, C: -1 / (2 * pi * C * Z.imag))
Component.law(F=('Z', 'L'))(lambda Z, L: Z.imag / (2 * pi * L))

Component.law(Y=('Z',))(lambda Z: 1 / Z)
Component.law(Z=('Y',))(lambda Y: 1 / Y)

class Load(Component):
    optional = ('L', 'C')

class Source(Component):
    show = ('E', 'I', 'P')
    optional = ('F',)

class Circuit(Component):
    show = ('E', 'I', 'P')

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        self.nodes = list(args)

    def __call__(self, *nodes):
        self.nodes.extend(nodes)
        return self

    @property
    def loads(self):
        return [L for L in self.nodes if not isinstance(L, Source)]

    @property
    def sources(self):
        return [S for S in self.nodes if isinstance(S, Source)]
    
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
    
    def solve_linear(self, prop):
        change = False
        if not given(self[prop]) and given(*all(prop, self.loads)):
            self[prop] = sum([value for value in all(prop, self.loads)])
            change = True
        if given(self[prop]) and count(*all(prop, self.loads)) == len(self.loads) - 1:
            c, = (c for c in self.loads if not given(c[prop]))
            s = sum([value for value in all(prop, self.loads) if value])
            c[prop] = self[prop] - s
            change = True
        return change

    def solve(self):
        change = False
        while self._solve():
            change = True
        return change

    def _solve(self):
        change = super().solve()
        for c in self.nodes:
            change |= c.solve()
        return change

    def verify(self):
        super().verify()
        for c in self.nodes:
            c.verify()
    
    def __str__(self, indent=''):
        indent += '  '
        return super().__str__(indent) + ''.join(
            '\n' + indent + c.__str__(indent)
            for c in self.nodes
        )

class Series(Circuit):
    def _solve(self):
        change = super()._solve()
        # TODO: Fix multiple sources
        change |= self.solve_constant('E', self.sources)
        change |= self.solve_constant('I', self.sources)
        change |= self.solve_constant('I', self.loads)
        change |= self.solve_constant('F', self.nodes)
        change |= self.solve_linear('Z')
        change |= self.solve_linear('E')
        change |= self.solve_linear('P')
        return change
    
    def __add__(self, other):
        self.nodes.append(other)
        return self

class Parallel(Circuit):
    def _solve(self):
        change = super()._solve()
        change |= self.solve_constant('E', self.nodes)
        change |= self.solve_constant('F', self.nodes)
        change |= self.solve_linear('I')
        change |= self.solve_linear('P')
        change |= self.solve_linear('Y')
        return change

    def __truediv__(self, other):
        self.nodes.append(other)
        return self

l = Load
s = Source
