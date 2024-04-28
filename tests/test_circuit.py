from itertools import combinations, permutations
import pytest

from pylacc.circuit import Series, Parallel, Load, Source, Component
from pylacc.circuit import e, r, xc, xl, c, l


C1 = {'E': 12, 'I': 4, 'Z': 3}

class TestComponent:
    def test_unknown(self):
        C = Component()
        assert repr(C) == '?(Z=? E=? I=?)'
        C.verify()

    @pytest.mark.parametrize('T', combinations(C1.items(), 2))
    def test_solve(self, T):
        C = Component(**dict(T))
        C.solve()
        for k, v in C1.items():
            assert C[k] == v
        C.verify()

    def test_incongruency(self):
        C = Component(**{K: V + 1 for K, V in C1.items()})
        with pytest.raises(AssertionError):
            C.verify()

class TestSeries:
    @pytest.mark.parametrize('T', permutations(C1.items(), 2))
    def test_split_solve(self, T):
        L = Load(**dict(T[1:]))
        C = Series(L, **dict(T[:1]))
        C.solve()
        for k, v in C1.items():
            assert C[k] == v
            assert L[k] == v
        C.verify()

    @pytest.mark.parametrize('T', [dict([p]) for p in C1.items() if p[0] != 'E'])
    def test_voltage_source(self, T):
        S = Source(12)
        L = Load(**T)
        C = Series(S, L)
        C.solve()
        for k, v in C1.items():
            assert C[k] == v
            assert S[k] == v
            assert L[k] == v
        C.verify()

    @pytest.mark.parametrize('T', [dict([p]) for p in C1.items() if p[0] != 'I'])
    def test_current_source(self, T):
        S = Source(I=4)
        L = Load(**T)
        C = Series(S, L)
        C.solve()
        for k, v in C1.items():
            assert C[k] == v
            assert S[k] == v
            assert L[k] == v
        C.verify()

    def test_loads(self):
        C = Series(Load(Z=1), Load(Z=2), E=12)
        assert repr(C) == '''\
+[12V](4A)
+-R[1Ω](4V 4A)
+-R[2Ω](8V 4A)\
'''
        C.verify()

class TestParallel:
    @pytest.mark.parametrize('T', permutations(C1.items(), 2))
    def test_split_solve(self, T):
        L = Load(**dict(T[1:]))
        C = Parallel(L, **dict(T[:1]))
        C.solve()
        for k, v in C1.items():
            assert C[k] == v
            assert L[k] == v
        C.verify()

    def test_loads(self):
        C = Parallel(Load(Z=6), Load(Z=6), E=12)
        assert repr(C) == '''\
/[12V](4A)
/-R[6Ω](12V 2A)
/-R[6Ω](12V 2A)\
'''
        C.verify()

class TestShorthand:
    def test_calculator_mode(self):
        C = e(12) + (r(9) / r(9) / r(9)) + r(3)
        assert repr(C) == '''\
+(12V 2A)
+-S[12V](2A 24W)
+-/(6V 2A)
+ /-R[9Ω](6V 667mA)
+ /-R[9Ω](6V 667mA)
+ /-R[9Ω](6V 667mA)
+-R[3Ω](6V 2A)\
'''
        C.verify()

    def test_phasor(self):
        C = e((12, 45))
        assert repr(C) == 'S[12∠45°V](I=? PA=?)'
        C.verify()

    def test_power_mode(self):
        C = e(12) + r(3) / r(3)
        assert repr(C.p) == '''\
+(96W)
+-S[12V](96W)
+-/(96W)
+ /-R[3Ω](48W)
+ /-R[3Ω](48W)\
'''
        C.verify()

    def test_impedence_mode(self):
        C = e(12) + r(3) / r(3)
        assert repr(C.z) == '''\
+(1.5Ω)
+-S[12V](1.5Ω)
+-/(1.5Ω)
+ /-R[3Ω]
+ /-R[3Ω]\
'''
        C.verify()

C2 = {'E': 120, 'I': 20 - 20j, 'Z': 3 + 3j}

class TestAlernatingCurrent:
    @pytest.mark.parametrize(('D'), [-1, 1])
    def test_no_frequency(self, D):
        C = e(120, z=100 + 100j * D)
        assert repr(C) == f'S[120V 141∠{D * 45}°Ω](849∠{-D * 45}°mA 102VA)'
        C.verify()

    @pytest.mark.parametrize('T', combinations(C2.items(), 2))
    def test_solve(self, T):
        C = Component(F=60, **dict(T))
        C.solve()
        for k, v in C2.items():
            assert C[k] == v
        C.verify()

    def test_capacitor(self):
        C = e(120, 60) + r(24.1e3) + c(110e-9)
        assert 'S[120V 60Hz](3.52∠45°mA 422mVA)' in repr(C)
        C.verify()

    def test_inductor(self):
        C = e(120, 60) + r(829e-3) + l(2.2e-3)
        assert 'S[120V 60Hz](102∠-45°A 12.3kVA)' in repr(C)
        C.verify()

    def test_reverse_impedence(self):
        C = e(120, 60) + r(2) + xl(2) + xc(2)
        assert 'S[120V 60Hz](60A 7.2kVA)' in repr(C)
        assert 'L[2Ω](120∠90°V 60A 5.31mH)' in repr(C)
        assert 'C[2Ω](120∠-90°V 60A 1.33mF)' in repr(C)
        C.verify()

    def test_reverse_cap_frequency(self):
        C = e(120) + r(2) + xl(2) + c(2.654e-3, xc=2)
        assert 'S[120V](60A 7.2kVA 30Hz)' in repr(C)
        C.verify()

    def test_reverse_ind_frequency(self):
        C = e(120) + r(2) + l(2.654e-3, xl=2) + xc(2)
        assert 'S[120V](60A 7.2kVA 120Hz)' in repr(C)
        C.verify()

class TestFilter:
    @pytest.mark.parametrize('n', range(-4, 5))
    def test_rc_low_pass(self, n):
        fc = 339e3
        f = fc * 2 ** n
        CAP = c(0.0047e-6)
        C = e(10, f) + r(100) + CAP
        C.solve()
        if f <= fc:
            assert abs(CAP.E) >= 7.06
        else:
            assert abs(CAP.E) < 7.06
        C.verify()

    @pytest.mark.parametrize('n', range(-4, 5))
    def test_rc_high_pass(self, n):
        fc = 339e3
        f = fc * 2 ** n
        R = r(100)
        C = e(10, f) + c(0.0047e-6) + R
        C.solve()
        if f < fc:
            assert abs(R.E) < 7.06
        else:
            assert abs(R.E) >= 7.06
        C.verify()

    @pytest.mark.parametrize('n', range(-4, 5))
    def test_rl_low_pass(self, n):
        fc = 74.5e3
        f = fc * 2 ** n
        R = r(2.2e3)
        C = e(10, f) + l(4.7e-3) + R
        C.solve()
        if f <= fc:
            assert abs(R.E) >= 7.06
        else:
            assert abs(R.E) < 7.06
        C.verify()

    @pytest.mark.parametrize('n', range(-4, 5))
    def test_rl_high_pass(self, n):
        fc = 74.5e3
        f = fc * 2 ** n
        IND = l(4.7e-3)
        C = e(10, f) + r(2.2e3) + IND
        C.solve()
        if f < fc:
            assert abs(IND.E) < 7.06
        else:
            assert abs(IND.E) >= 7.06
        C.verify()

    @pytest.mark.parametrize('n', range(-4, 5))
    def test_series_band_pass(self, n):
        fc = 107e3
        f = fc * 2 ** n
        R = r(100)
        C = e(10, f) + l(1e-3) + c(0.0022e-6) + R
        C.solve()
        if f == fc:
            assert abs(R.E) > 9.9
        else:
            assert abs(R.E) < 7.07
        C.verify()

    @pytest.mark.parametrize('n', range(-4, 5))
    def test_parallel_band_pass(self, n):
        fc = 107e3
        f = fc * 2 ** n
        TANK = (l(1e-3) / c(0.0022e-6)).g
        C = e(10, f) + r(100) + TANK
        C.solve()
        if f == fc:
            assert abs(TANK.E) > 9.9
        else:
            assert abs(TANK.E) < 9.9
        C.verify()

    @pytest.mark.parametrize('n', range(-4, 5))
    def test_series_band_stop(self, n):
        fc = 107e3
        f = fc * 2 ** n
        SINK = (l(1e-3) + c(0.0022e-6)).g
        C = e(10, f) + r(100) + SINK
        C.solve()
        if f == fc:
            assert abs(SINK.E) < 0.4
        else:
            assert abs(SINK.E) > 9
        C.verify()

    @pytest.mark.parametrize('n', range(-4, 5))
    def test_parallel_band_stop(self, n):
        fc = 107e3
        f = fc * 2 ** n
        R = r(100)
        C = e(10, f) + (l(1e-3) / c(0.0022e-6)) + R
        C.solve()
        if f == fc:
            assert abs(R.E) < 0.1
        else:
            assert abs(R.E) > 2
        C.verify()
