import pandas as pd
import plotly.graph_objects as go

from visualization.charts import create_visualization


def test_categorical_and_numeric_results_create_bar_chart() -> None:
    figure = create_visualization(
        pd.DataFrame({"city": ["Mumbai", "Delhi"], "total_sales": [2250, 1800]})
    )

    assert isinstance(figure, go.Figure)
    assert figure.data[0].type == "bar"


def test_datetime_and_numeric_results_create_line_chart() -> None:
    figure = create_visualization(
        pd.DataFrame(
            {"month": pd.to_datetime(["2026-01-01", "2026-02-01"]), "sales": [1200, 1800]}
        )
    )

    assert isinstance(figure, go.Figure)
    assert figure.data[0].type == "scatter"
    assert figure.data[0].mode == "lines+markers"


def test_numeric_and_numeric_results_create_scatter_chart() -> None:
    figure = create_visualization(pd.DataFrame({"price": [10, 20], "quantity": [2, 5]}))

    assert isinstance(figure, go.Figure)
    assert figure.data[0].type == "scatter"


def test_distribution_results_create_donut_chart() -> None:
    figure = create_visualization(
        pd.DataFrame({"category": ["A", "B", "C"], "share": [50, 30, 20]})
    )

    assert isinstance(figure, go.Figure)
    assert figure.data[0].type == "pie"
    assert figure.data[0].hole == 0.45


def test_single_kpi_result_does_not_force_a_chart() -> None:
    assert create_visualization(pd.DataFrame({"total_sales": [5250]})) is None


def test_empty_result_does_not_create_a_chart() -> None:
    assert create_visualization(pd.DataFrame(columns=["city", "sales"])) is None


def test_one_column_result_does_not_create_an_invalid_chart() -> None:
    assert create_visualization(pd.DataFrame({"sales": [100, 200]})) is None


def test_null_values_and_numeric_strings_are_supported() -> None:
    figure = create_visualization(
        pd.DataFrame({"city": ["Mumbai", None, "Delhi"], "sales": ["100", None, "200"]})
    )

    assert isinstance(figure, go.Figure)
    assert figure.data[0].type == "bar"


def test_visualization_does_not_modify_original_dataframe() -> None:
    original = pd.DataFrame(
        {"month": ["2026-01-01", "2026-02-01"], "sales": ["1200", "1800"]}
    )
    before = original.copy(deep=True)

    create_visualization(original)

    pd.testing.assert_frame_equal(original, before)
