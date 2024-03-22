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
    'R': 'Ω',
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

def identity(v):
    return v

def inverse(v):
    return 1 / v

def reset():
    global counter
    counter = {
        'L': 1,
        'S': 1,
        'P': 1,
    }

reset()

class Component:
    def __init__(self, *, E=None, I=None, R=None, P=None, **kwargs):
        global counter
        p = self.__class__.__name__[0]
        self.name = p + str(counter[p])
        counter[p] += 1
        self.E, self.I, self.R, self.P = E, I, R, P
        for n, v in kwargs.items():
            self[n.upper()] = v
    
    def __getitem__(self, prop):
        return getattr(self, prop, None)
    
    def __setitem__(self, prop, value):
        setattr(self, prop, value)
    
    def solve(self):
        E, I, R, P = self.E, self.I, self.R, self.P
        if count(E, I, R, P) not in (2, 3):
            return False
        elif not given(P):
            if not given(R): R = E / I
            if not given(I): I = E / R
            if not given(E): E = I * R
            P = E * I
        elif not given(R):
            if not given(I): I = P / E
            if not given(E): E = P / I
            R = E / I
        else:
            if not given(E): E = (P * R) ** (1 / 2)
            if not given(I): I = E / R
        self.E, self.I, self.R, self.P = E, I, R, P
        return True
    
    def __call__(self):
        self.solve()
        return self
    
    def __str__(self, indent=''):
        parts = [p + '=' + norm(p, self[p]) for p in 'EIRP']
        return '{}( {} )'.format(self.name, ', '.join(parts))
    
    def __repr__(self):
        return str(self)

class Load(Component):
    pass

class Source(Component):
    pass

class Circuit(Component):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        self.C = list(args)

    def __add__(self, c):
        self.C.append(c)
        return self

    def __call__(self, *C):
        self.C.extend(C)
        if not C:
            super().__call__()
            reset()
        return self
    
    def __len__(self):
        return len(self.C)
    
    def all(self, prop):
        return [c[prop] for c in self.C]
    
    def solve_constant(self, prop):
        change = False
        if not given(self[prop]):
            for c in self.C:
                if given(c[prop]):
                    self[prop] = c[prop]
                    change = True
                    break
        if given(self[prop]):
            for c in self.C:
                if given(c[prop]):
                    continue
                c[prop] = self[prop]
                change = True
        return change
    
    def solve_linear(self, prop, T=identity):
        change = False
        if not given(self[prop]) and given(*self.all(prop)):
            self[prop] = T(sum([T(value) for value in self.all(prop)]))
            change = True
        if given(self[prop]) and count(*self.all(prop)) == len(self) - 1:
            for c in self.C:
                if not given(c[prop]):
                    s = sum([T(value) for value in self.all(prop) if value])
                    c[prop] = T(T(self[prop]) - s)
                    break
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
        change |= self.solve_constant('I')
        change |= self.solve_linear('R')
        change |= self.solve_linear('E')
        change |= self.solve_linear('P')
        return change

class Parallel(Circuit):
    def _solve(self):
        change = super()._solve()
        change |= self.solve_constant('E')
        change |= self.solve_linear('I')
        change |= self.solve_linear('P')
        change |= self.solve_linear('R', inverse)
        return change

l = Load
s = Series
p = Parallel
lr = lambda x: l(r=x)
li = lambda x: l(i=x)
le = lambda x: l(e=x)
lp = lambda x: l(p=x)
sr = lambda x, *a: s(*a, r=x)
si = lambda x, *a: s(*a, i=x)
se = lambda x, *a: s(*a, e=x)
sp = lambda x, *a: s(*a, p=x)
pr = lambda x, *a: p(*a, r=x)
pi = lambda x, *a: p(*a, i=x)
pe = lambda x, *a: p(*a, e=x)
pp = lambda x, *a: p(*a, p=x)
