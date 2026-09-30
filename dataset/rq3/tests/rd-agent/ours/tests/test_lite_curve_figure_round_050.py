import matplotlib
matplotlib.use('Agg')

import pandas as pd
import matplotlib.pyplot as plt
from rdagent.log.ui.utils import lite_curve_figure


def test_lite_curve_figure_with_ensemble_and_sota_round_050():
    # Single competition with an 'ensemble' row present and sota_loop_id pointing to that loop
    summary = {
        "comp1": {
            # test_scores: two loops (0 and 1)
            "test_scores": {0: 0.5, 1: 0.6},
            # valid_scores: loop 0 has an 'ensemble' index row, loop 1 does not
            "valid_scores": {
                0: pd.DataFrame([[0.77]], index=["ensemble"], columns=["score"]),
                1: pd.DataFrame([[0.65]], index=["other"], columns=["score"]),
            },
            "bronze_threshold": 0.2,
            "silver_threshold": 0.4,
            "gold_threshold": 0.8,
            "sota_loop_id_new": 0,
        }
    }

    fig = lite_curve_figure(summary)
    # Function should return a matplotlib Figure
    assert isinstance(fig, matplotlib.figure.Figure)

    # Because there is a SOTA loop that exists in combined_df.index, a text label "L{loop}" should be present
    axes = fig.get_axes()
    # only one competition -> only one axis should remain
    assert len(axes) == 1
    ax = axes[0]

    # There should be at least the Valid Score and Test Score plot lines
    assert len(ax.get_lines()) >= 2

    # Look for the SOTA annotation text (e.g., 'L0') on the axis
    texts = [t.get_text() for t in ax.texts]
    assert "L0" in texts

    plt.close(fig)


def test_lite_curve_figure_without_ensemble_and_no_sota_round_050():
    # Two competitions without any 'ensemble' rows and no SOTA loop specified
    # This also tests removal of extra subplots when axes > len(summary)
    summary = {
        "a": {
            "test_scores": {0: 0.1},
            # valid_scores frames have no 'ensemble' index
            "valid_scores": {0: pd.DataFrame([[0.12]], index=["x"], columns=["score"])},
            "bronze_threshold": 0.0,
            "silver_threshold": 0.2,
            "gold_threshold": 0.5,
            "sota_loop_id_new": None,
        },
        "b": {
            "test_scores": {0: 0.3},
            "valid_scores": {0: pd.DataFrame([[0.25]], index=["y"], columns=["score"])},
            "bronze_threshold": 0.0,
            "silver_threshold": 0.2,
            "gold_threshold": 0.5,
            "sota_loop_id_new": None,
        },
    }

    fig = lite_curve_figure(summary)
    assert isinstance(fig, matplotlib.figure.Figure)

    axes = fig.get_axes()
    # There are 2 competitions; cols default to 3 so initial axes would be 3 but extra axes must be removed -> should have 2 axes
    assert len(axes) == 2

    # Ensure no SOTA annotation text like 'L' exists on any axis
    all_texts = [t.get_text() for ax in axes for t in ax.texts]
    assert all(not txt.startswith("L") for txt in all_texts)

    # Ensure lines plotted for each axis (Test and Valid) exist
    for ax in axes:
        assert len(ax.get_lines()) >= 1

    plt.close(fig)
