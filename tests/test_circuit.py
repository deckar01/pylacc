from itertools import combinations, permutations
import pytest

from src.lilacs.circuit import Series, Parallel, Load, Source, Component, s, l


C1 = {'E': 12, 'I': 4, 'Z': 3, 'P': 48}

class TestComponent:
    def test_unknown(self):
        c = Component()
        assert repr(c) == 'Component1( E=?, I=?, Z=?, P=? )'

    @pytest.mark.parametrize('K,law,D', [(K, law, D) for K in Component.props for law, D in Component.laws[K]])
    def test_laws(self, K, law, D):
        c = Component(**C1)
        assert repr(c) == 'Component1( E=12V, I=4A, Z=3Ω, P=48W )'
        if c.have(D):
            assert c[K] == law(**c.have(D))

    @pytest.mark.parametrize('T', combinations(C1.items(), 2))
    def test_solve(self, T):
        c = Component(**dict(T))
        assert repr(c) == 'Component1( E=12V, I=4A, Z=3Ω, P=48W )'

class TestSeries:
    @pytest.mark.parametrize('T', permutations(C1.items(), 2))
    def test_split_solve(self, T):
        c = Series(**dict(T[:1]))(Load(**dict(T[1:])))
        assert repr(c) == 'Series1( E=12V, I=4A, Z=3Ω, P=48W )\n  Load1( E=12V, I=4A, Z=3Ω, P=48W )'

    @pytest.mark.parametrize('T', [dict([p]) for p in C1.items() if p[0] != 'E'])
    def test_voltage_source(self, T):
        c = Series()(Source(E=12), Load(**T))
        assert repr(c) == 'Series1( E=12V, I=4A, Z=3Ω, P=48W )\n  Source1( E=12V, I=4A, Z=3Ω, P=48W )\n  Load1( E=12V, I=4A, Z=3Ω, P=48W )'

    @pytest.mark.parametrize('T', [dict([p]) for p in C1.items() if p[0] != 'I'])
    def test_current_source(self, T):
        c = Series()(Source(I=4), Load(**T))
        assert repr(c) == 'Series1( E=12V, I=4A, Z=3Ω, P=48W )\n  Source1( E=12V, I=4A, Z=3Ω, P=48W )\n  Load1( E=12V, I=4A, Z=3Ω, P=48W )'

    def test_loads(self):
        c = Series(E=12)(Load(Z=1), Load(Z=2))
        assert repr(c) == 'Series1( E=12V, I=4A, Z=3Ω, P=48W )\n  Load1( E=4V, I=4A, Z=1Ω, P=16W )\n  Load2( E=8V, I=4A, Z=2Ω, P=32W )'

class TestParallel:
    @pytest.mark.parametrize('T', permutations(C1.items(), 2))
    def test_split_solve(self, T):
        c = Parallel(**dict(T[:1]))(Load(**dict(T[1:])))
        assert repr(c) == 'Parallel1( E=12V, I=4A, Z=3Ω, P=48W )\n  Load1( E=12V, I=4A, Z=3Ω, P=48W )'

    def test_loads(self):
        c = Parallel(E=12)(Load(Z=6), Load(Z=6))
        assert repr(c) == 'Parallel1( E=12V, I=4A, Z=3Ω, P=48W )\n  Load1( E=12V, I=2A, Z=6Ω, P=24W )\n  Load2( E=12V, I=2A, Z=6Ω, P=24W )'

class TestShorthand:
    def test_calculator_mode(self):
        c = s(e=12) + (l(r=9) / l(r=9) / l(r=9)) + l(r=3)
        assert Component.counter['Series'] == 1
        assert Component.counter['Parallel'] == 1
        assert Component.counter['Load'] == 4
        assert repr(c).startswith('Series1( E=12V, I=2A, Z=6Ω, P=24W )')

class TestAlernatingCurrent:
    @pytest.mark.parametrize('Z', [-100j, 100j])
    def test_no_frequency(self, Z):
        c = s(e=120) + l(r=24.1e3) + l(z=Z)
        with pytest.raises(ValueError, match='Reactive loads require an AC frequency'):
            repr(c)

    def test_capacitor(self):
        c = s(e=120, f=60) + l(r=24.1e3) + l(c=110e-9)
        assert repr(c).startswith('Series1( E=120V∠0°, I=3.52mA∠45°, Z=34.1kΩ∠-45°, P=422mW∠45°, F=60Hz )')

    def test_inductor(self):
        c = s(e=120, f=60) + l(r=829e-3) + l(l=2.2e-3)
        assert repr(c).startswith('Series1( E=120V∠0°, I=102A∠-45°, Z=1.17Ω∠45°, P=12.3kW∠-45°, F=60Hz )')

    def test_reverse_impedence(self):
        c = s(e=120, f=60) + l(z=1) + l(z=1j) + l(z=-1j)
        assert repr(c).startswith('Series1( E=120V∠0°, I=120A∠0°, Z=1Ω∠0°, P=14.4kW∠0°, F=60Hz )')
        assert 'Load2( E=120V∠90°, I=120A∠0°, Z=1Ω∠90°, P=14.4kW∠90°, L=377H, F=60Hz )' in repr(c)
        assert 'Load3( E=120V∠-90°, I=120A∠0°, Z=1Ω∠-90°, P=14.4kW∠-90°, C=2.65mF, F=60Hz )' in repr(c)

    def test_reverse_cap_frequency(self):
        c = s(e=120) + l(z=1) + l(z=1j) + l(z=-1j, c=2.654e-3)
        assert repr(c).startswith('Series1( E=120V∠0°, I=120A∠0°, Z=1Ω∠0°, P=14.4kW∠0°, F=60Hz )')
        assert 'Load2( E=120V∠90°, I=120A∠0°, Z=1Ω∠90°, P=14.4kW∠90°, L=377H, F=60Hz )' in repr(c)
        assert 'Load3( E=120V∠-90°, I=120A∠0°, Z=1Ω∠-90°, P=14.4kW∠-90°, C=2.65mF, F=60Hz )' in repr(c)

    def test_reverse_ind_frequency(self):
        c = s(e=120) + l(z=1) + l(z=1j, l=377) + l(z=-1j)
        print(repr(c))
        assert repr(c).startswith('Series1( E=120V∠0°, I=120A∠0°, Z=1Ω∠0°, P=14.4kW∠0°, F=60Hz )')
        assert 'Load2( E=120V∠90°, I=120A∠0°, Z=1Ω∠90°, P=14.4kW∠90°, L=377H, F=60Hz )' in repr(c)
        assert 'Load3( E=120V∠-90°, I=120A∠0°, Z=1Ω∠-90°, P=14.4kW∠-90°, C=2.65mF, F=60Hz )' in repr(c)
