from circuit import Series, Parallel, Source, Load


class TestSeries:
    def test_internal_resistance(self):
        assert repr(Series(E=12, R=5)()) == 'S1( E=12V, I=2.4A, R=5Ω, P=28.8W )'
