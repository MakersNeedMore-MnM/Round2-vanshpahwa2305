import os

import streamlit as st
from dotenv import load_dotenv

from ai.provider import LLMConfig, LLMProviderError, create_llm_provider
from ai.sql_generator import SQLGenerationError, SQLGenerator
from core.execution_service import DatabaseExecutionError, ExecutionService
from core.query_engine import QueryEngine
from core.schema_service import SchemaService
from database.mysql import MySQLAdapter, MySQLConfig, MySQLConnectionError
from security.query_limits import QueryLimits
from security.validator import SQLValidationError
from visualization.charts import create_visualization

load_dotenv()

DEMO_QUESTIONS = [
    "Which city generated the highest sales?",
    "What are the top 3 products by revenue?",
    "How many orders did each customer place?",
    "What is the average order value by region?",
    "Which product category generated the most revenue?",
    "How much revenue did each employee manage?",
    "Show monthly sales for the latest year.",
    "Which customers placed orders over 500?",
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
            "Demo database secrets are incomplete. Configure DEMO_DATABASE_HOST, "
            "DEMO_DATABASE_NAME, DEMO_DATABASE_USER, and DEMO_DATABASE_PASSWORD."
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
def _query_engine() -> tuple[QueryEngine, ExecutionService]:
    _, schema_service, execution_service = _database_services()
    provider = create_llm_provider(
        LLMConfig(
            provider=_setting("LLM_PROVIDER", "openrouter"),
            api_key=_setting("LLM_API_KEY"),
            model=_setting("LLM_MODEL"),
        )
    )
    return QueryEngine(
        schema_service,
        SQLGenerator(provider),
        execution_service,
        QueryLimits.from_environment(),
    ), execution_service


st.set_page_config(page_title="QueryPeek", page_icon="🔎", layout="wide")
st.title("QueryPeek")
st.caption("Ask a read-only MySQL database questions in plain English.")

try:
    _, _, execution_service = _database_services()
    if execution_service.health_check():
        st.success("Demo database connected")
    else:
        st.error("Demo database is unavailable. Check the hosted MySQL secrets.")
except (AppConfigurationError, ValueError) as error:
    execution_service = None
    st.warning(str(error))
except MySQLConnectionError as error:
    execution_service = None
    st.error(str(error))
except Exception:
    execution_service = None
    st.error("Demo database connection failed. Check the deployment configuration.")

st.subheader("Ask a question")
selected_question = st.selectbox("Demo questions", ["(Choose an example)", *DEMO_QUESTIONS])
question = st.text_area(
    "Natural-language question",
    value="" if selected_question == "(Choose an example)" else selected_question,
    height=80,
)

if st.button("Generate and run", type="primary"):
    if not question.strip():
        st.warning("Enter a question first.")
    else:
        try:
            engine, _ = _query_engine()
            result = engine.run(question)
            st.subheader("Generated SQL")
            st.code(result.generated.sql, language="sql")
            st.caption("Only the validated SQL below was sent to MySQL.")
            st.code(result.validated.sql, language="sql")
            st.subheader("Results")
            st.dataframe(result.rows, use_container_width=True, hide_index=True)
            if not result.rows.empty:
                st.subheader("Visualization")
                figure = create_visualization(result.rows)
                if figure is not None:
                    st.plotly_chart(figure, use_container_width=True)
        except (SQLGenerationError, SQLValidationError, DatabaseExecutionError) as error:
            st.error(str(error))
        except LLMProviderError as error:
            st.error(str(error))
        except MySQLConnectionError as error:
            st.error(str(error))
        except Exception:
            st.error("Query failed. Check the database, model, and deployment configuration.")
