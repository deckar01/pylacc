from itertools import combinations, permutations
import pytest

from circuit import Series, Parallel, Load, Source, Component, reset


C1 = {'E': 12, 'I': 4, 'Z': 3, 'P': 48}

class Base:
    def teardown(self):
        reset()

class TestComponent(Base):
    def test_unknown(self):
        c = Component()
        assert repr(c()) == 'Component1( E=?, I=?, Z=?, P=? )'

    @pytest.mark.parametrize('T', combinations(C1.items(), 2))
    def test_solve(self, T):
        c = Component(**dict(T))
        assert repr(c()) == 'Component1( E=12V, I=4A, Z=3Ω, P=48W )'

    def test_lowercase(self):
        c = Component(e=1)
        assert repr(c()) == 'Component1( E=1V, I=?, Z=?, P=? )'

class TestSeries(Base):
    @pytest.mark.parametrize('T', permutations(C1.items(), 2))
    def test_split_solve(self, T):
        c = Series(**dict(T[:1]))(Load(**dict(T[1:])))
        assert repr(c()) == 'Series1( E=12V, I=4A, Z=3Ω, P=48W )\n  Load1( E=12V, I=4A, Z=3Ω, P=48W )'

    @pytest.mark.parametrize('T', [dict([p]) for p in C1.items() if p[0] != 'E'])
    def test_voltage_source(self, T):
        c = Series()(Source(E=12), Load(**T))
        assert repr(c()) == 'Series1( E=12V, I=4A, Z=3Ω, P=48W )\n  Source1( E=12V, I=4A, Z=3Ω, P=48W )\n  Load1( E=12V, I=4A, Z=3Ω, P=48W )'

    @pytest.mark.parametrize('T', [dict([p]) for p in C1.items() if p[0] != 'I'])
    def test_current_source(self, T):
        c = Series()(Source(I=4), Load(**T))
        assert repr(c()) == 'Series1( E=12V, I=4A, Z=3Ω, P=48W )\n  Source1( E=12V, I=4A, Z=3Ω, P=48W )\n  Load1( E=12V, I=4A, Z=3Ω, P=48W )'

    def test_loads(self):
        c = Series(E=12)(Load(Z=1), Load(Z=2))
        assert repr(c()) == 'Series1( E=12V, I=4A, Z=3Ω, P=48W )\n  Load1( E=4V, I=4A, Z=1Ω, P=16W )\n  Load2( E=8V, I=4A, Z=2Ω, P=32W )'

class TestParallel(Base):
    @pytest.mark.parametrize('T', permutations(C1.items(), 2))
    def test_split_solve(self, T):
        c = Parallel(**dict(T[:1]))(Load(**dict(T[1:])))
        assert repr(c()) == 'Parallel1( E=12V, I=4A, Z=3Ω, P=48W )\n  Load1( E=12V, I=4A, Z=3Ω, P=48W )'

    def test_loads(self):
        c = Parallel(E=12)(Load(Z=6), Load(Z=6))
        assert repr(c()) == 'Parallel1( E=12V, I=4A, Z=3Ω, P=48W )\n  Load1( E=12V, I=2A, Z=6Ω, P=24W )\n  Load2( E=12V, I=2A, Z=6Ω, P=24W )'
