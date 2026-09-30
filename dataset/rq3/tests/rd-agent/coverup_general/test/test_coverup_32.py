# file: rdagent/log/ui/utils.py:818-881
# asked: {"lines": [818, 819, 820, 822, 823, 824, 826, 827, 828, 829, 830, 833, 834, 835, 836, 838, 839, 841, 842, 844, 845, 846, 847, 850, 851, 852, 853, 854, 855, 858, 859, 861, 862, 863, 864, 865, 866, 867, 870, 871, 872, 873, 874, 877, 878, 880, 881], "branches": [[826, 827], [826, 877], [834, 835], [834, 838], [835, 834], [835, 836], [858, 859], [858, 870], [877, 878], [877, 880]]}
# gained: {"lines": [818, 819, 820, 822, 823, 824, 826, 827, 828, 829, 830, 833, 834, 835, 836, 838, 839, 841, 842, 844, 845, 846, 847, 850, 851, 852, 853, 854, 855, 858, 859, 861, 862, 863, 864, 865, 866, 867, 870, 871, 872, 873, 874, 877, 878, 880, 881], "branches": [[826, 827], [826, 877], [834, 835], [834, 838], [835, 834], [835, 836], [858, 859], [858, 870], [877, 878], [877, 880]]}

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import pytest

from rdagent.log.ui.utils import lite_curve_figure


def _use_agg_backend():
    """
    Switch to Agg backend for tests and return a callable to restore the original backend.
    """
    orig_backend = matplotlib.get_backend()
    try:
        # switch to a non-interactive backend
        plt.switch_backend("Agg")
    except Exception:
        # Some environments may not allow switch_backend; ignore if so.
        pass

    def restore():
        try:
            plt.switch_backend(orig_backend)
        except Exception:
            pass

    return restore


def test_lite_curve_figure_with_sota_and_extra_axes():
    restore_backend = _use_agg_backend()
    try:
        # Prepare summary with one competition so there will be extra axes to delete (cols=3 -> 3 axes, 1 used)
        summary = {
            "compA": {
                "test_scores": {1: 0.80, 2: 0.85},
                # valid_scores: both loops have 'ensemble' entry
                "valid_scores": {
                    1: pd.DataFrame({"score": [0.75]}, index=["ensemble"]),
                    2: pd.DataFrame({"score": [0.82]}, index=["ensemble"]),
                },
                "bronze_threshold": 0.6,
                "silver_threshold": 0.7,
                "gold_threshold": 0.9,
                "sota_loop_id_new": 1,  # should trigger axvline and text
            }
        }

        fig = lite_curve_figure(summary)

        # After deleting extra axes, only one axis should remain
        assert len(fig.axes) == 1

        ax = fig.axes[0]
        # Title should be the competition name
        assert ax.get_title() == "compA"

        # There should be a text annotation for the SOTA loop 'L1'
        texts = [t.get_text() for t in ax.texts]
        assert "L1" in texts

        # Lines: two plotted series + three horizontal threshold lines + one vertical sota line = 6
        # Be permissive in case backend differences add lines; assert at least 6
        assert len(ax.lines) >= 6

        # Ensure there is a vertical line (linestyle ':') for SOTA and horizontal dashed lines '--' for thresholds
        assert any(line.get_linestyle() == ":" for line in ax.lines)
        assert any(line.get_linestyle() == "--" for line in ax.lines)

    finally:
        plt.close("all")
        restore_backend()


def test_lite_curve_figure_without_sota_and_missing_ensemble():
    restore_backend = _use_agg_backend()
    try:
        # Prepare summary where one valid_scores entry lacks 'ensemble' and sota_loop_id is None
        summary = {
            "compB": {
                "test_scores": {1: 0.55, 3: 0.65},
                # valid_scores: loop 1 has no 'ensemble', loop 3 has 'ensemble'
                "valid_scores": {
                    1: pd.DataFrame({"score": [0.50]}, index=["not_ensemble"]),
                    3: pd.DataFrame({"score": [0.60]}, index=["ensemble"]),
                },
                "bronze_threshold": 0.4,
                "silver_threshold": 0.6,
                "gold_threshold": 0.85,
                "sota_loop_id_new": None,  # should NOT trigger axvline/text
            }
        }

        fig = lite_curve_figure(summary)

        # Only one axis should remain after deletion
        assert len(fig.axes) == 1

        ax = fig.axes[0]
        assert ax.get_title() == "compB"

        # There should be no SOTA text annotations
        texts = [t.get_text() for t in ax.texts]
        assert not any(t.startswith("L") for t in texts)

        # Ensure threshold horizontal dashed lines exist
        assert any(line.get_linestyle() == "--" for line in ax.lines)

        # There should not be a vertical ':' linestyle (no sota)
        assert not any(line.get_linestyle() == ":" for line in ax.lines)

    finally:
        plt.close("all")
        restore_backend()
