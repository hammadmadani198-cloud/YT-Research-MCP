import json
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from phase3_helpers import metrics, seed

from youtube_niche_mcp.analysis.bounds import bounds
from youtube_niche_mcp.analysis.numerics import blend, log_baseline, quantile
from youtube_niche_mcp.analysis.service import AnalysisService


@pytest.mark.parametrize("name", list("ABCDEFGH"))
def test_bias_cohort_bundle(repository, observation_factory, now, name):
    datasets = json.loads((Path(__file__).parent / "fixtures/phase3_cohorts.json").read_text())
    data = datasets[name]
    vd, cd, _, opt = seed(
        repository,
        observation_factory,
        now,
        data["channels"],
        topics=data["topics"],
        shared=data.get("shared_group", False),
    )
    bundle = AnalysisService(repository).analyze(cd, opt, video_cohort_id=vd)
    result = metrics(bundle)
    assert set(result) == {
        "F1",
        "F2",
        "F3",
        "F4",
        "F5",
        "F6",
        "F7",
        "F8",
        "F9",
        "F19",
        "F22",
        "floor",
    }
    assert all(m.formula_version == "phase3-v1" and m.input_manifest_hash for m in result.values())
    assert "probability" in result["F3"].warnings[0]
    if name == "A":
        assert result["floor"].value == 0 and result["F3"].value == 1
    if name == "B":
        assert result["F6"].value > Decimal(".99") and result["F5"].value < 10
    if name == "C":
        assert result["F19"].value == 1 and result["F19"].details["upload_fraction"] == str(
            Decimal(1) / 6
        )
    if name == "D":
        assert result["F19"].details["entrants"] == 3 and result["F19"].details["zero_output"] == 1
        assert result["F19"].details["attempts"] == 4 and result["F19"].value == 0
    if name == "E":
        assert result["F3"].value is None and result["F3"].unknown == 4
    if name == "F":
        assert (
            result["F8"].independent_units == 1
            and len(result["F8"].details["qualifying_independent_units"]) == 1
        )
    if name == "G":
        assert result["F8"].value == 1 and result["F9"].details["topics"]["HHI"] == "1"
    if name == "H":
        assert result["F8"].value == 3


@pytest.mark.parametrize(
    "values,expected", [([0], 0), ([200, 800, 2000], 800), ([1, 2, 3, 4], Decimal("2.5"))]
)
def test_quantile_median(values, expected):
    assert quantile(values) == expected


def test_f2_source_equation_log_shrinkage():
    b, _, weight = blend(Decimal(9), Decimal(8), 5, 10)
    assert weight == Decimal(1) / 3 and abs(b - (Decimal(8) + Decimal(1) / 3)) < Decimal("1e-26")
    # Raw median example is not a replacement for the authoritative log-shrinkage equation.
    assert quantile([1500, 2000, 6000, 1200]) == 1750
    assert log_baseline([1500, 2000, 6000, 1200]).exp() - 1 != 1750


@pytest.mark.parametrize(
    "own,peers,minimum,mode",
    [
        ([100, 100, 100, 100, 100, 300], [[100]], 5, "own_log_median"),
        ([100, 300], [[100]], 5, "F2_cold_start"),
        ([300], [[100]], 5, "F2_cold_start"),
        ([0, 0, 0, 0, 0, 300], [[100]], 5, "own_log_median"),
    ],
)
def test_f1_leave_one_out_cold_start_zero_absolute(
    repository, observation_factory, now, own, peers, minimum, mode
):
    vd, _, ids, opt = seed(
        repository, observation_factory, now, [own, *peers], topics=["a"] * (1 + len(peers))
    )
    opt = opt.model_copy(
        update={"candidate_id": ids[len(own) - 1], "baseline_cutoff": now, "own_minimum": minimum}
    )
    result = metrics(AnalysisService(repository).analyze(vd, opt))
    f = result["F1"]
    assert f.details["f1_baseline_mode"] == mode and opt.candidate_id not in f.details["own_ids"]
    assert f.details["absolute_views"] == 300
    if own[0] == 0:
        assert f.value == 301 and any("Tiny baseline" in w for w in f.warnings)
    elif mode == "own_log_median":
        assert abs(f.value - Decimal(301) / 101) < Decimal("1e-25")


def test_baseline_landmark_and_prolific_peer_balancing(repository, observation_factory, now):
    vd, _, ids, opt = seed(
        repository, observation_factory, now, [[100, 100, 300], [10] * 20, [1000]], topics=["a"] * 3
    )
    options_now = opt.model_copy(update={"candidate_id": ids[2], "baseline_cutoff": now})
    r = metrics(AnalysisService(repository).analyze(vd, options_now))
    assert (
        r["F2"].details["peer_videos"] == 3
    )  # only publications before candidate, no later peer uploads
    assert r["F2"].details["peer_channels"] == 2
    too_early = options_now.model_copy(update={"baseline_cutoff": now - timedelta(days=300)})
    assert (
        metrics(AnalysisService(repository).analyze(vd, too_early))["F1"].state
        == "insufficient_sample"
    )


@pytest.mark.parametrize("goal,expected", [(100, 3), (101, 2), (10000, 1), (25000, 0)])
def test_f3_explicit_goal(repository, observation_factory, now, goal, expected):
    vd, _, _, opt = seed(repository, observation_factory, now, [[0, 100, 200, 12000]])
    f = metrics(AnalysisService(repository).analyze(vd, opt.model_copy(update={"goal": goal})))[
        "F3"
    ]
    assert f.numerator == expected and f.denominator == 4 and f.value == Decimal(expected) / 4


def test_f5_channel_q25_not_global_median(repository, observation_factory, now):
    vd, _, _, opt = seed(repository, observation_factory, now, [[200] * 20, [800] * 5, [2000] * 5])
    f = metrics(AnalysisService(repository).analyze(vd, opt))["F5"]
    assert f.value == 800 and Decimal(f.details["video_weighted_median"]) == 200
    assert Decimal(f.details["video_weighted_q25"]) == 200
    assert Decimal(f.details["channel_floor_q25"]) == 500


@pytest.mark.parametrize(
    "values,top1,top3",
    [
        ([1], Decimal(1), Decimal(1)),
        ([1, 1, 1], Decimal(1) / 3, Decimal(1)),
        ([1, 1, 1, 1], Decimal(".25"), Decimal(".75")),
        ([90000] + [1000] * 9, Decimal(10) / 11, Decimal(92) / 99),
    ],
)
def test_f6_top_shares(repository, observation_factory, now, values, top1, top3):
    vd, _, _, opt = seed(repository, observation_factory, now, [values])
    f = metrics(AnalysisService(repository).analyze(vd, opt))["F6"]
    assert f.value == top1 and Decimal(f.details["videos"]["top3"]) == top3


@pytest.mark.parametrize("n", [0, 1, 3, 5, 10, 12])
def test_f7_actual_next5_next10(repository, observation_factory, now, n):
    vd, _, ids, opt = seed(
        repository, observation_factory, now, [[20000] + [15000] * n], topics=["a"]
    )
    opt = opt.model_copy(update={"anchor_id": ids[0]})
    f = metrics(AnalysisService(repository).analyze(vd, opt))["F7"]
    assert f.details["anchor_id"] == ids[0]
    for k in (5, 10):
        w = f.details["windows"][str(k)]
        assert w["actual_followups"] == min(n, k) and w["absent"] == max(0, k - n)
        assert ids[0] not in [p["video_id"] for p in w["positions"]]
        assert w["R_k"] == ("1" if n >= k else None)


def test_rule_anchor_first_known_not_future_best(repository, observation_factory, now):
    vd, _, ids, opt = seed(repository, observation_factory, now, [[0, 20000, 1000000, 100]])
    opt = opt.model_copy(update={"anchor_channel_id": "UC" + f"{1:022d}", "anchor_cutoff": now})
    f = metrics(AnalysisService(repository).analyze(vd, opt))["F7"]
    assert f.details["anchor_id"] == ids[1] and f.details["anchor_mode"] == "first_known_goal_hit"


@pytest.mark.parametrize(
    "known,shared,k,expected", [(True, False, 1, 3), (True, True, 2, 0), (False, False, 1, 0)]
)
def test_f8_ownership_and_threshold(
    repository, observation_factory, now, known, shared, k, expected
):
    vd, _, _, opt = seed(
        repository,
        observation_factory,
        now,
        [[20000], [20000], [20000]],
        topics=["a", "b", "c"],
        known_groups=known,
        shared=shared,
    )
    f = metrics(AnalysisService(repository).analyze(vd, opt.model_copy(update={"breadth_k": k})))[
        "F8"
    ]
    assert f.value == expected and f.unresolved_ownership_channels == (0 if known else 3)


@pytest.mark.parametrize(
    "values,expected",
    [([60, 20, 20], Decimal(".44")), ([1, 1, 1, 1], Decimal(".25")), ([100], Decimal(1))],
)
def test_f9_channel_hhi(repository, observation_factory, now, values, expected):
    vd, _, _, opt = seed(repository, observation_factory, now, [[v] for v in values])
    f = metrics(AnalysisService(repository).analyze(vd, opt))["F9"]
    assert f.value == expected and "sample" not in str(f.value)


def test_f19_eighty_vs_ten(repository, observation_factory, now):
    channels = [[10000] + [0] * 9 for _ in range(8)] + [[0] * 10, [0] * 10]
    channels[0][1] = 10000
    channels[1][1] = 10000
    vd, cd, _, opt = seed(repository, observation_factory, now, channels)
    f = metrics(AnalysisService(repository).analyze(cd, opt, video_cohort_id=vd))["F19"]
    assert f.value == Decimal(".8") and f.details["upload_fraction"] == "0.1"
    assert f.details["attempts"] == 100 and f.details["entrants"] == 10


@pytest.mark.parametrize("k", [5, 10, None])
def test_f19_first_k_calendar_stopped_zero(repository, observation_factory, now, k):
    vd, cd, _, opt = seed(
        repository, observation_factory, now, [[100] * 20, [100], [100] * 3, []], spacing=6
    )
    f = metrics(
        AnalysisService(repository).analyze(
            cd, opt.model_copy(update={"first_k": k}), video_cohort_id=vd
        )
    )["F19"]
    expected = min(k or 100, 15) + 1 + 3
    assert (
        f.details["attempts"] == expected
        and f.details["entrants"] == 4
        and f.details["zero_output"] == 1
    )
    assert f.value == 0


@pytest.mark.parametrize(
    "n,h,u,lower,upper",
    [
        (40, 8, 12, ".2", ".5"),
        (10, 3, 0, ".3", ".3"),
        (10, 0, 10, "0", "1"),
        (10, 0, 0, "0", "0"),
        (10, 10, 0, "1", "1"),
    ],
)
def test_f22_exact_bounds(n, h, u, lower, upper):
    r = bounds(n, h, u, True)
    assert r["lower"] == Decimal(lower) and r["upper"] == Decimal(upper)


@pytest.mark.parametrize("n,h,u", [(0, 0, 0), (2, 3, 0), (2, 1, 2), (-1, 0, 0)])
def test_f22_invalid_and_empty(n, h, u):
    if n == 0:
        assert bounds(n, h, u, True)["lower"] is None
    else:
        with pytest.raises(ValueError):
            bounds(n, h, u, True)


def test_open_discovery_has_no_bounds(repository, observation_factory, now):
    vd, _, _, opt = seed(repository, observation_factory, now, [[10000, None]])
    f = metrics(
        AnalysisService(repository).analyze(
            vd, opt.model_copy(update={"finite_frame_reference": None})
        )
    )["F22"]
    assert f.state == "finite_frame_not_established" and f.value is None


@pytest.mark.parametrize("values", [[], [None], [0]])
def test_empty_unknown_zero_distinct(repository, observation_factory, now, values):
    vd, _, _, opt = seed(repository, observation_factory, now, [values])
    r = metrics(AnalysisService(repository).analyze(vd, opt))
    if values == [0]:
        assert r["F3"].value == 0 and r["F5"].value == 0 and r["F9"].value is None
    else:
        assert r["F3"].value is None and r["F5"].value is None
