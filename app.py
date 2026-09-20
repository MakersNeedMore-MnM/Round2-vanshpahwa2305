import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from ai.provider import (
    DEFAULT_GEMINI_MODEL,
    LLMConfig,
    LLMProviderError,
    LLMRateLimitError,
    create_llm_provider,
    normalize_model_name,
)
from ai.sql_generator import SQLGenerationError, SQLGenerator
from core.database_metadata import (
    DatabaseMetadataError,
    DatabaseMetadataService,
    DatabaseOverview,
    build_preview_query,
)
from core.execution_service import DatabaseExecutionError, ExecutionService
from core.query_engine import QueryEngine
from core.schema_service import SchemaService
from database.mysql import MySQLAdapter, MySQLConfig, MySQLConnectionError
from database.schema import DatabaseSchema
from security.query_limits import QueryLimits
from security.validator import SQLValidationError
from visualization.charts import create_visualization

load_dotenv()

DEMO_QUESTIONS = [
    "Which city generated the highest sales?",
    "Show total sales by product.",
    "Show monthly sales.",
    "Show the top 5 customers by total order amount.",
    "How many orders did each customer place?",
]


class AppConfigurationError(RuntimeError):
    """Raised when required deployment configuration is unavailable."""


def _setting(name: str, default: str = "") -> str:
    """Read a Streamlit secret first, then fall back to local environment."""

    try:
        value = st.secrets.get(name, None)
    except Exception:
        value = None
    if value is None or str(value) == "":
        value = os.getenv(name, default)
    return str(value)


@st.cache_resource(show_spinner=False)
def _database_services() -> tuple[MySQLAdapter, SchemaService, ExecutionService]:
    host = _setting("DEMO_DATABASE_HOST").strip()
    database = _setting("DEMO_DATABASE_NAME").strip()
    user = _setting("DEMO_DATABASE_USER").strip()
    password = _setting("DEMO_DATABASE_PASSWORD")
    if not all((host, database, user, password)):
        raise AppConfigurationError(
            "Demo database secrets are incomplete. Configure the hosted MySQL secrets."
        )

    config = MySQLConfig(
        host=host,
        port=int(_setting("DEMO_DATABASE_PORT", "3306").strip()),
        database=database,
        user=user,
        password=password,
    )
    limits = QueryLimits.from_environment()
    adapter = MySQLAdapter(config)
    return adapter, SchemaService(adapter), ExecutionService(adapter, limits)


@st.cache_resource(show_spinner=False)
def _metadata_service() -> DatabaseMetadataService:
    adapter, _, _ = _database_services()
    return DatabaseMetadataService(adapter)


@st.cache_resource(show_spinner=False)
def _query_engine() -> QueryEngine:
    _, schema_service, execution_service = _database_services()
    provider_name = _setting("LLM_PROVIDER", "gemini").strip().lower()
    api_key_name = "GEMINI_API_KEY" if provider_name == "gemini" else "LLM_API_KEY"
    model_name = normalize_model_name(
        provider_name,
        _setting("LLM_MODEL", "") or _setting("GEMINI_MODEL", "") or DEFAULT_GEMINI_MODEL,
    )
    provider = create_llm_provider(
        LLMConfig(
            provider=provider_name,
            api_key=_setting(api_key_name),
            model=model_name,
        )
    )
    return QueryEngine(
        schema_service,
        SQLGenerator(provider),
        execution_service,
        QueryLimits.from_environment(),
    )


def _configure_page() -> None:
    st.set_page_config(page_title="Query Peek", page_icon="◉", layout="wide")
    st.markdown(
        """
        <style>
        :root { --qp-bg: #090d13; --qp-card: #111722; --qp-border: #202b3b;
                --qp-muted: #8d9aae; --qp-blue: #3d8bfd; --qp-purple: #9b7cff;
                --qp-green: #3bd38a; }
        .stApp { background: var(--qp-bg); }
        [data-testid="stSidebar"] { background: #0d121a; border-right: 1px solid var(--qp-border); }
        [data-testid="stSidebar"] hr { border-color: var(--qp-border); }
        .qp-eyebrow { color: var(--qp-muted); font-size: .72rem; letter-spacing: .16em;
                      font-weight: 700; text-transform: uppercase; }
        .qp-brand { color: #f4f7fb; font-size: 1.25rem; font-weight: 800; letter-spacing: .08em; }
        .qp-subtitle { color: var(--qp-muted); font-size: .8rem; }
        .qp-status { color: var(--qp-green); font-size: .78rem; font-weight: 700;
                     letter-spacing: .08em; }
        .qp-card { background: var(--qp-card); border: 1px solid var(--qp-border);
                   border-radius: 12px;
                   padding: 16px 18px; min-height: 88px; }
        .qp-card-label { color: var(--qp-muted); font-size: .7rem;
                         letter-spacing: .12em; font-weight: 700; }
        .qp-card-value { color: #f4f7fb; font-size: 1.45rem; font-weight: 750; margin-top: 8px; }
        .qp-card-blue { border-top: 2px solid var(--qp-blue); }
        .qp-card-purple { border-top: 2px solid var(--qp-purple); }
        .qp-card-green { border-top: 2px solid var(--qp-green); }
        .qp-section { color: #f4f7fb; font-size: 1.05rem; font-weight: 750; letter-spacing: .03em; }
        div[data-testid="stMetric"] { background: var(--qp-card);
                                      border: 1px solid var(--qp-border);
                                      border-radius: 12px; padding: 12px; }
        .stButton > button { border-radius: 8px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _metric_card(label: str, value: str, accent: str = "blue") -> None:
    st.markdown(
        f'<div class="qp-card qp-card-{accent}"><div class="qp-card-label">{label}</div>'
        f'<div class="qp-card-value">{value}</div></div>',
        unsafe_allow_html=True,
    )


def _load_dashboard_data() -> tuple[
    DatabaseSchema, DatabaseOverview, SchemaService, ExecutionService
]:
    _, schema_service, execution_service = _database_services()
    if not execution_service.health_check():
        raise MySQLConnectionError("MySQL connection failure.")
    schema = schema_service.load_schema()
    overview = _metadata_service().load(schema)
    return schema, overview, schema_service, execution_service


def _render_sidebar(overview: DatabaseOverview | None) -> str | None:
    with st.sidebar:
        st.markdown('<div class="qp-brand">QUERY PEEK</div>', unsafe_allow_html=True)
        st.markdown('<div class="qp-subtitle">Natural Language → SQL</div>', unsafe_allow_html=True)
        st.divider()
        st.markdown('<div class="qp-eyebrow">TABLES</div>', unsafe_allow_html=True)

        if overview is None or not overview.tables:
            st.caption("No tables available")
            return None

        table_names = [table.name for table in overview.tables]
        selected_table = st.radio(
            "Tables",
            table_names,
            format_func=lambda name: next(
                f"{name}  ·  {table.row_count:,} rows"
                for table in overview.tables
                if table.name == name
            ),
            label_visibility="collapsed",
        )
        st.divider()
        st.markdown('<div class="qp-status">● MYSQL · CONNECTED</div>', unsafe_allow_html=True)
        return selected_table


def _render_header(connected: bool) -> None:
    left, right = st.columns([4, 1])
    with left:
        st.markdown('<div class="qp-eyebrow">QUERY PEEK</div>', unsafe_allow_html=True)
        st.markdown("# DATABASE DASHBOARD")
        st.caption(f"{_setting('DEMO_DATABASE_NAME', 'querypeek_demo')} · MySQL")
    with right:
        st.markdown(
            f'<div class="qp-status" style="text-align:right">● '
            f'{"CONNECTED" if connected else "UNAVAILABLE"}</div>',
            unsafe_allow_html=True,
        )


def _render_overview(overview: DatabaseOverview) -> None:
    st.markdown('<div class="qp-section">OVERVIEW</div>', unsafe_allow_html=True)
    metric_columns = st.columns(5)
    largest = overview.largest_table
    metrics = [
        ("TABLES", f"{len(overview.tables):,}", "blue"),
        ("TOTAL ROWS", f"{overview.total_rows:,}", "blue"),
        ("DB SIZE", overview.total_size_label, "purple"),
        ("LARGEST TABLE", largest.name if largest else "N/A", "green"),
        ("SCHEMA CACHE", "IN-MEMORY", "purple"),
    ]
    for column, (label, value, accent) in zip(metric_columns, metrics, strict=True):
        with column:
            _metric_card(label, value, accent)

    st.write("")
    chart_columns = st.columns(2)
    with chart_columns[0]:
        st.markdown('<div class="qp-section">SIZE BY TABLE</div>', unsafe_allow_html=True)
        size_data = overview.sizes_frame()
        if size_data.empty:
            st.info("N/A — MySQL did not expose table size metadata.")
        else:
            figure = create_visualization(size_data)
            if figure is not None:
                st.plotly_chart(figure, width="stretch", key="size_by_table")
    with chart_columns[1]:
        st.markdown('<div class="qp-section">ROW COUNT BY TABLE</div>', unsafe_allow_html=True)
        figure = create_visualization(overview.rows_frame())
        if figure is not None:
            st.plotly_chart(figure, width="stretch", key="row_count_by_table")

    st.markdown('<div class="qp-section">ALL TABLES</div>', unsafe_allow_html=True)
    st.dataframe(overview.as_frame(), width="stretch", hide_index=True)


def _render_table_explorer(
    schema: DatabaseSchema,
    selected_table: str | None,
    execution_service: ExecutionService,
) -> None:
    st.markdown('<div class="qp-section">TABLE EXPLORER</div>', unsafe_allow_html=True)
    if selected_table is None:
        st.info("Select a table from the sidebar.")
        return

    table = next(table for table in schema.tables if table.name == selected_table)
    st.subheader(table.name)
    metadata_columns = st.columns(3)
    with metadata_columns[0]:
        st.metric("COLUMNS", len(table.columns))
    with metadata_columns[1]:
        primary_key = ", ".join(
            column.name for column in table.columns if column.is_primary_key
        ) or "N/A"
        st.metric("PRIMARY KEY", primary_key)
    with metadata_columns[2]:
        st.metric("FOREIGN KEYS", len(table.foreign_keys))

    column_frame = pd.DataFrame(
        [
            {
                "COLUMN": column.name,
                "TYPE": column.data_type,
                "NULLABLE": "YES" if column.nullable else "NO",
                "PRIMARY KEY": "YES" if column.is_primary_key else "NO",
            }
            for column in table.columns
        ]
    )
    st.dataframe(column_frame, width="stretch", hide_index=True)
    st.caption(f"Safe preview — maximum {execution_service.limits.max_rows:,} rows")
    try:
        preview_query = build_preview_query(selected_table, execution_service.limits)
        preview = execution_service.execute(preview_query)
        st.dataframe(preview, width="stretch", hide_index=True)
    except DatabaseExecutionError:
        st.error("QUERY EXECUTION ERROR")
        st.caption("The safe table preview could not be loaded.")


def _render_er_diagram(schema: DatabaseSchema) -> None:
    st.markdown('<div class="qp-section">ER DIAGRAM</div>', unsafe_allow_html=True)
    st.caption("Relationships below are loaded from MySQL foreign-key metadata.")
    table_columns = st.columns(min(4, max(1, len(schema.tables))))
    for index, table in enumerate(schema.tables):
        with table_columns[index % len(table_columns)]:
            st.markdown(f"**{table.name}**")
            st.caption(" · ".join(column.name for column in table.columns) or "No columns")
            for foreign_key in table.foreign_keys:
                st.write(
                    f"{table.name}.{foreign_key.column_name}  →  "
                    f"{foreign_key.referenced_table}.{foreign_key.referenced_column}"
                )
    if not any(table.foreign_keys for table in schema.tables):
        st.info("No foreign-key relationships were returned by MySQL.")


def _render_query_tuner() -> None:
    st.markdown('<div class="qp-section">QUERY TUNER</div>', unsafe_allow_html=True)
    st.info(
        "Placeholder for a future read-only SQL explanation. QueryPeek will not "
        "rewrite or execute SQL from this panel."
    )


def _render_copilot() -> None:
    st.markdown('<div class="qp-section">AI COPILOT</div>', unsafe_allow_html=True)
    st.caption("ASK YOUR DATABASE")
    selected_question = st.selectbox("Demo questions", ["(Choose an example)", *DEMO_QUESTIONS])
    question = st.text_area(
        "Natural-language question",
        value="" if selected_question == "(Choose an example)" else selected_question,
        height=100,
        placeholder="Which city generated the highest sales?",
    )

    if not st.button("GENERATE & RUN", type="primary", key="generate_query"):
        return
    if not question.strip():
        st.warning("Enter a question first.")
        return

    try:
        result = _query_engine().run(question)
        st.markdown('<div class="qp-section">GENERATED SQL</div>', unsafe_allow_html=True)
        st.code(result.generated.sql, language="sql")
        st.caption("Validated SQL sent to MySQL")
        st.code(result.validated.sql, language="sql")
        st.success("✓ Read-only SQL validated")
        st.markdown('<div class="qp-section">RESULTS</div>', unsafe_allow_html=True)
        st.dataframe(result.rows, width="stretch", hide_index=True)
        figure = create_visualization(result.rows)
        if figure is not None:
            st.markdown('<div class="qp-section">VISUALIZATION</div>', unsafe_allow_html=True)
            st.plotly_chart(figure, width="stretch", key="query_result_chart")
    except LLMRateLimitError:
        st.error("AI PROVIDER RATE LIMITED")
        st.info("The configured model is temporarily rate-limited. Please try again shortly.")
    except SQLValidationError:
        st.error("SQL SECURITY REJECTION")
        st.warning("QUERY REJECTED")
        st.caption("Only read-only SELECT queries are permitted. The query was not executed.")
    except SQLGenerationError as error:
        st.error("SQL GENERATION ERROR")
        st.caption(str(error))
    except DatabaseExecutionError:
        st.error("QUERY EXECUTION ERROR")
        st.caption("The validated query could not be executed against the demo database.")
    except LLMProviderError:
        st.error("SQL GENERATION ERROR")
        st.caption("The configured AI provider could not generate SQL.")


def main() -> None:
    _configure_page()
    try:
        schema, overview, schema_service, execution_service = _load_dashboard_data()
        connected = True
    except (AppConfigurationError, ValueError) as error:
        schema = None
        overview = None
        schema_service = None
        execution_service = None
        connected = False
        st.error("DATABASE UNAVAILABLE")
        st.caption(str(error))
    except MySQLConnectionError as error:
        schema = None
        overview = None
        schema_service = None
        execution_service = None
        connected = False
        st.error("DATABASE UNAVAILABLE")
        st.caption(str(error))
    except DatabaseMetadataError:
        schema = None
        overview = None
        schema_service = None
        execution_service = None
        connected = False
        st.error("DATABASE UNAVAILABLE")
        st.caption("The database connected, but metadata could not be loaded.")

    _render_header(connected)
    selected_table = _render_sidebar(overview)
    if overview is None or schema is None or execution_service is None:
        st.info("Connect the hosted demo database to load the dashboard.")
        return

    if st.sidebar.button("Refresh schema and stats"):
        schema_service.invalidate()
        _metadata_service().invalidate()
        st.rerun()

    overview_tab, explorer_tab, er_tab, tuner_tab, copilot_tab = st.tabs(
        ["Overview", "Table Explorer", "ER Diagram", "Query Tuner", "AI Copilot"]
    )
    with overview_tab:
        _render_overview(overview)
    with explorer_tab:
        _render_table_explorer(schema, selected_table, execution_service)
    with er_tab:
        _render_er_diagram(schema)
    with tuner_tab:
        _render_query_tuner()
    with copilot_tab:
        _render_copilot()


if __name__ == "__main__":
    main()
