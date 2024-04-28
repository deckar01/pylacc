# ruff: noqa: E701, E731, E741

from cmath import polar, sqrt, rect
from math import log10, floor, pi

try:
    # HACK: TI-nspire renders dashes at double width
    import ti_system as _ # noqa: F401
    DELIM = ('-', '  ')
except ImportError:
    DELIM = ('-', ' ')


k = 1e3
M = 1e6
G = 1e9
T = 1e12
m = 1e-3
u = 1e-6
n = 1e-9
p = 1e-12

MAG = {
    0: '',
    1: 'k',
    2: 'M',
    3: 'G',
    4: 'T',
    -1: 'm',
    -2: 'μ',
    -3: 'n',
    -4: 'p',
}

UNITS = {
    'E': 'V',
    'I': 'A',
    'Z': 'Ω',
    'XL': 'Ω',
    'XC': 'Ω',
    'P': 'W',
    'PT': 'W',
    'PA': 'VA',
    'PR': 'VAR',
    'F': 'Hz',
    'C': 'F',
    'L': 'H',
}

PHASED = ('E', 'I', 'Z')

def isclose(a, b):
    return abs(a - b) < 1e-9

OPS = ('!',)

def name(P):
    return P[1:] if P[0] in OPS else P

def op(P, V):
    if P[0] == '!':
        return True if V is None else None
    return V

def norm(t, v, AC, given):
    if not AC and t == 'PA':
        t = 'P'
    if not AC and t in ('PT', 'PR'):
        return None
    if v is None:
        return t + '=?'
    if (t in PHASED and AC) and not (given and isclose(v, abs(v))) and not isclose(v.imag, 0):
        v, a = polar(v)
        phase = '∠' + '{:.3g}°'.format(360 * a / 2 / pi)
    else:
        v = abs(v)
        phase = ''
    mag10 = floor(log10(abs(v)))
    mag1k = floor(mag10 / 3)
    v /= 10 ** mag10
    v = round(v, 2)
    v *= 10 ** mag10
    v /= 1000 ** mag1k
    return '{:.3g}{}{}{}'.format(v, phase, MAG[mag1k], UNITS[t])

def count(*V):
    T = 0
    for v in V:
        if v is not None: T += 1
    return T

def given(*V):
    return len(V) > 0 and len(V) == count(*V)

def all(prop, G):
    return [c[prop] for c in G]

class Filter:
    def __init__(self, value):
        self.value = value
    
    def __repr__(self):
        return self.value

class Component:
    show = ('Z', 'E', 'I')
    optional = ()
    laws = {}
    props = set()
    name = '?'

    def __init__(self, **kwargs):
        self.given = []
        for n, v in kwargs.items():
            n = n.upper()
            if n == 'R': n = 'Z'
            if n == 'P': n = 'PA'
            self.given.append(n)
            if isinstance(v, (tuple, list)):
                r, a = v
                self[n] = rect(r, 2 * pi * a / 360)
            else:
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
        P = {k: op(k, self[name(k)]) for k in D}
        P = {k: v for k, v in P.items() if v is not None}
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
                if V is None:
                    continue
                if not isclose(self[K], V):
                    errors.append('{} -> {}: {} != {}'.format(D, K, self[K], V))
        if errors:
            raise AssertionError('\n'.join(errors))

    def __call__(self, *props):
        self.solve()
        return Filter(self.__str__(props))
        
    @property
    def p(self):
        return self('PT', 'PR', 'PA')
        
    @property
    def z(self):
        return self('Z')

    def __str__(self, Q=None, indent=''):
        G = tuple(self.given)
        if Q is None:
            Q = self.show + tuple(p for p in self.optional if self[p] is not None)
        Q = tuple(q for q in Q if q not in G)
        V = ''
        GN = [norm(p, self[p], self.AC, True) for p in G]
        GN = [p for p in GN if p]
        if GN:
            V += '[' + ' '.join(GN) + ']'
        QN = [norm(p, self[p], self.AC, False) for p in Q]
        QN = [p for p in QN if p]
        if QN:
            V += '(' + ' '.join(QN) + ')'
        return self.name + V
    
    def __repr__(self):
        self.solve()
        return str(self)

Component.law(Z=('E', 'I'))(lambda E, I: E / I)
Component.law(PA=('E', 'I'))(lambda E, I: E * I)
Component.law(PA=('E', 'Z'))(lambda E, Z: E * E / Z)
Component.law(PA=('I', 'Z'))(lambda I, Z: I * I * Z)
Component.law(E=('I', 'Z'))(lambda I, Z: I * Z)
Component.law(I=('E', 'Z'))(lambda E, Z: E / Z)

Component.law(PT=('E', 'Z'))(lambda E, Z: E * E / Z.real if not isclose(Z.real, 0) else None)
Component.law(PR=('E', 'Z'))(lambda E, Z: 1j * E * E / Z.imag if not isclose(Z.imag, 0) else None)

Component.law(R=('Z',))(lambda Z: Z.real)
Component.law(XC=('Z',))(lambda Z: -Z.imag if Z.imag < 0 and not isclose(Z.imag, 0) else None)
Component.law(XL=('Z',))(lambda Z: Z.imag if Z.imag > 0 and not isclose(Z.imag, 0) else None)
Component.law(Z=('R', 'XC'))(lambda R, XC: R - 1j * XC)
Component.law(Z=('R', 'XL'))(lambda R, XL: R + 1j * XL)
Component.law(Z=('XC', '!R'))(lambda XC, **_: -1j * XC)
Component.law(Z=('XL', '!R'))(lambda XL, **_: 1j * XL)
Component.law(Z=('R', '!XC', '!XL'))(lambda R, **_: R)

Component.law(XC=('C', 'F'))(lambda C, F: 1 / (2 * pi * F * C))
Component.law(XL=('L', 'F'))(lambda L, F: 2 * pi * F * L)
Component.law(C=('XC', 'F'))(lambda XC, F: 1 / (2 * pi * F * XC))
Component.law(L=('XL', 'F'))(lambda XL, F: XL / (2 * pi * F))
Component.law(F=('XC', 'C'))(lambda XC, C: 1 / (2 * pi * C * XC))
Component.law(F=('XL', 'L'))(lambda XL, L: XL / (2 * pi * L))

Component.law(Y=('Z',))(lambda Z: 1 / Z)
Component.law(Z=('Y',))(lambda Y: 1 / Y)

Component.law(AC=('F',))(lambda F: True if F is not None else None)
for P in PHASED:
    Component.law(AC=(P,))(lambda **V: True if not isclose(next(iter(V.values())).imag, 0) else None)

class Load(Component):
    show = ('E', 'I')
    optional = ('L', 'C', 'XL', 'XC')

    @property
    def name(self):
        R = self.R is not None and not isclose(self.R, 0)
        C = count(self.XC, self.C) > 0
        L = count(self.XL, self.L) > 0
        U = sum(int(v) for v in [R, C, L]) - 1
        if U: return '?'
        if R: return 'R'
        if C: return 'C'
        if L: return 'L'

class Source(Component):
    name = 'S'
    show = ('E', 'I', 'PA')
    optional = ('F',)

    def __init__(self, e=None, f=None, **kwargs):
        extra = {}
        if e is not None:
            extra['e'] = e
        if f is not None:
            extra['f'] = f
        super().__init__(**{k: v for k, v in tuple(extra.items()) + tuple(kwargs.items())})

class Circuit(Component):
    show = ('E', 'I')
    lock = False

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        self.nodes = list(args)

    @property
    def loads(self):
        return [L for L in self.nodes if not isinstance(L, Source)]

    @property
    def sources(self):
        return [S for S in self.nodes if isinstance(S, Source)]

    @property
    def g(self):
        self.lock = True
        return self
    
    def constant(self, prop, G=None):
        if G is None:
            G = self.nodes
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
    
    def linear(self, prop):
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

    def __str__(self, Q=None, indent=''):
        indent = indent.replace(DELIM[0], DELIM[1]) + self.name + DELIM[0]
        return super().__str__(Q, indent) + ''.join(
            '\n' + indent + c.__str__(Q, indent)
            for c in self.nodes
        )

class Series(Circuit):
    name = '+'
    def _solve(self):
        change = super()._solve()
        # TODO: Fix multiple sources
        change |= self.constant('E', self.sources)
        change |= self.constant('I', self.sources)
        change |= self.constant('I', self.loads)
        change |= self.constant('F')
        change |= self.linear('Z')
        change |= self.linear('E')
        change |= self.linear('PA')
        return change
    
    def __add__(self, other):
        if self.lock:
            return super().__add__(other)
        self.nodes.append(other)
        return self

class Parallel(Circuit):
    name = '/'
    def _solve(self):
        change = super()._solve()
        change |= self.constant('E', self.sources)
        change |= self.constant('I', self.sources)
        change |= self.constant('E')
        change |= self.constant('F')
        change |= self.linear('I')
        change |= self.linear('PA')
        change |= self.linear('Y')
        return change

    def __truediv__(self, other):
        if self.lock:
            return super().__truediv__(other)
        self.nodes.append(other)
        return self

e = lambda v=None, f=None, **k: Source(e=v, f=f, **k)
i = lambda v=None, f=None, **k: Source(i=v, f=f, **k)
r = lambda v=None, **k: Load(r=v, **k)
xc = lambda v=None, **k: Load(xc=v, **k)
xl = lambda v=None, **k: Load(xl=v, **k)
c = lambda v=None, **k: Load(c=v, **k)
l = lambda v=None, **k: Load(l=v, **k)
