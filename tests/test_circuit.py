from itertools import combinations, permutations
import pytest

from lilacs.circuit import Series, Parallel, Load, Source, Component, s, l


C1 = {'E': 12, 'I': 4, 'Z': 3, 'P': 48}

class TestComponent:
    def test_unknown(self):
        c = Component()
        assert repr(c) == 'Component1( E=?, I=?, Z=?, P=? )'
        c.verify()

    @pytest.mark.parametrize('T', combinations(C1.items(), 2))
    def test_solve(self, T):
        c = Component(**dict(T))
        assert repr(c) == 'Component1( E=12V, I=4A, Z=3Ω, P=48W )'
        c.verify()

    def test_incongruency(self):
        c = Component(**{K: V + 1 for K, V in C1.items()})
        with pytest.raises(AssertionError):
            c.verify()

class TestSeries:
    @pytest.mark.parametrize('T', permutations(C1.items(), 2))
    def test_split_solve(self, T):
        c = Series(**dict(T[:1]))(Load(**dict(T[1:])))
        assert repr(c) == 'Series1( E=12V, I=4A, P=48W )\n  Load1( E=12V, I=4A, Z=3Ω, P=48W )'
        c.verify()

    @pytest.mark.parametrize('T', [dict([p]) for p in C1.items() if p[0] != 'E'])
    def test_voltage_source(self, T):
        c = Series()(Source(E=12), Load(**T))
        assert repr(c) == 'Series1( E=12V, I=4A, P=48W )\n  Source1( E=12V, I=4A, P=48W )\n  Load1( E=12V, I=4A, Z=3Ω, P=48W )'
        c.verify()

    @pytest.mark.parametrize('T', [dict([p]) for p in C1.items() if p[0] != 'I'])
    def test_current_source(self, T):
        c = Series()(Source(I=4), Load(**T))
        assert repr(c) == 'Series1( E=12V, I=4A, P=48W )\n  Source1( E=12V, I=4A, P=48W )\n  Load1( E=12V, I=4A, Z=3Ω, P=48W )'
        c.verify()

    def test_loads(self):
        c = Series(E=12)(Load(Z=1), Load(Z=2))
        assert repr(c) == 'Series1( E=12V, I=4A, P=48W )\n  Load1( E=4V, I=4A, Z=1Ω, P=16W )\n  Load2( E=8V, I=4A, Z=2Ω, P=32W )'
        c.verify()

class TestParallel:
    @pytest.mark.parametrize('T', permutations(C1.items(), 2))
    def test_split_solve(self, T):
        c = Parallel(**dict(T[:1]))(Load(**dict(T[1:])))
        assert repr(c) == 'Parallel1( E=12V, I=4A, P=48W )\n  Load1( E=12V, I=4A, Z=3Ω, P=48W )'
        c.verify()

    def test_loads(self):
        c = Parallel(E=12)(Load(Z=6), Load(Z=6))
        assert repr(c) == 'Parallel1( E=12V, I=4A, P=48W )\n  Load1( E=12V, I=2A, Z=6Ω, P=24W )\n  Load2( E=12V, I=2A, Z=6Ω, P=24W )'
        c.verify()

class TestShorthand:
    def test_calculator_mode(self):
        c = s(e=12) + (l(r=9) / l(r=9) / l(r=9)) + l(r=3)
        assert Component.counter['Series'] == 1
        assert Component.counter['Parallel'] == 1
        assert Component.counter['Load'] == 4
        assert repr(c).startswith('Series1( E=12V, I=2A, P=24W )')
        c.verify()

    def test_phasor(self):
        c = l(e=(12, 45))
        assert repr(c) == 'Load1( E=12V∠45°, I=?, Z=?, P=? )'
        c.verify()

C2 = {'E': 120, 'I': 20 - 20j, 'Z': 3 + 3j, 'P': 2400-2400j}

class TestAlernatingCurrent:
    @pytest.mark.parametrize(('Z', 'A'), [(-100j, 1), (100j, -1)])
    def test_no_frequency(self, Z, A):
        c = l(e=120, z=100 + Z)
        assert repr(c) == f'Load1( E=120V∠0°, I=849mA∠{A * 45}°, Z=141Ω∠{-A * 45}°, P=102W∠{A * 45}° )'
        c.verify()

    @pytest.mark.parametrize('T', combinations(C2.items(), 2))
    def test_solve(self, T):
        c = Component(F=60, **dict(T))
        assert repr(c) == 'Component1( E=120V∠0°, I=28.3A∠-45°, Z=4.24Ω∠45°, P=3.39kW∠-45° )'
        c.verify()

    def test_capacitor(self):
        c = s(e=120, f=60) + l(r=24.1e3) + l(c=110e-9)
        assert repr(c).startswith('Series1( E=120V∠0°, I=3.52mA∠45°, P=422mW∠45° )')
        c.verify()

    def test_inductor(self):
        c = s(e=120, f=60) + l(r=829e-3) + l(l=2.2e-3)
        assert repr(c).startswith('Series1( E=120V∠0°, I=102A∠-45°, P=12.3kW∠-45° )')
        c.verify()

    def test_reverse_impedence(self):
        c = s(e=120, f=60) + l(z=2) + l(z=2j) + l(z=-2j)
        assert 'Series1( E=120V∠0°, I=60A∠0°, P=7.2kW∠0° )' in repr(c)
        assert 'Load2( E=120V∠90°, I=60A∠0°, Z=2Ω∠90°, P=7.2kW∠90°, L=5.31mH )' in repr(c)
        assert 'Load3( E=120V∠-90°, I=60A∠0°, Z=2Ω∠-90°, P=7.2kW∠-90°, C=1.33mF )' in repr(c)
        c.verify()

    def test_reverse_cap_frequency(self):
        c = s(e=120) + l(z=2) + l(z=2j) + l(z=-2j, c=2.654e-3)
        assert 'Source1( E=120V∠0°, I=60A∠0°, P=7.2kW∠0°, F=30Hz )' in repr(c)
        c.verify()

    def test_reverse_ind_frequency(self):
        c = s(e=120) + l(z=2) + l(z=2j, l=2.654e-3) + l(z=-2j)
        assert 'Source1( E=120V∠0°, I=60A∠0°, P=7.2kW∠0°, F=120Hz )' in repr(c)
        c.verify()
