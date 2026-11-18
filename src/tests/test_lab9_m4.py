import pytest

from lab9.stats import paired_bootstrap


def test_reproducible_and_paired():
    a, b = [1, 0.7, 0.2, 0.4], [0.4, 0.2, 0.1, 0.3]
    first = paired_bootstrap(a, b)
    assert first == paired_bootstrap(a, b)
    assert first[0] == pytest.approx(sum(x-y for x, y in zip(a,b)) / len(a))
    assert first[1] <= first[0] <= first[2]


@pytest.mark.parametrize("a,b", [([], []), ([1], [1, 2]), ([float('nan'), 1], [0, 1]), ([1], [0])])
def test_invalid_samples(a, b):
    with pytest.raises(ValueError):
        paired_bootstrap(a, b)


def test_identical_singleton():
    assert paired_bootstrap([1], [1]) == (0.0, 0.0, 0.0)
