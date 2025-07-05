import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import create_engine

DB_NAME = st.secrets["DB_NAME"]
DB_USER = st.secrets["DB_USER"]
DB_PASSWORD = st.secrets["DB_PASSWORD"]
DB_HOST = st.secrets["DB_HOST"]
DB_PORT = st.secrets["DB_PORT"]
SSL_MODE = st.secrets["SSL_MODE"]

# Create PostgreSQL connection string for pandas
connection_string = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode={SSL_MODE}"

@st.cache_resource
def get_db_engine():
    """Create and cache database engine"""
    try:
        engine = create_engine(connection_string)
        return engine
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None

@st.cache_data
def fetch_data(table_name, lookup_table):
    """
    Fetch data from PostgreSQL database using pandas
    """
    query = f"""
    WITH T AS (
        SELECT "id" AS t_id, COUNT(DISTINCT "ResponseId") AS cnt
        FROM "{table_name}"
        GROUP BY "id"
    ),
    W AS (
        SELECT "id" AS w_id, COUNT(DISTINCT "ResponseId") AS want_cnt
        FROM "{table_name}Want"
        GROUP BY "id"
    )
    SELECT LU.name, T.cnt, W.want_cnt
    FROM T INNER JOIN W ON T.t_id = W.w_id
    INNER JOIN "{lookup_table}" LU ON T.t_id = LU.id
    ORDER BY T.cnt + W.want_cnt DESC
    """
    try:
        engine = get_db_engine()
        if engine is None:
            st.error("Database connection failed")
            return pd.DataFrame()
        
        df = pd.read_sql_query(query, engine)
        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

def plot(df_pd, feature):
    if df_pd.empty:
        st.warning(f"No data available for {feature}")
        return
    # Create the stacked horizontal bar chart
    fig = go.Figure()

    # Add the `cnt` bar (bottom layer) - now horizontal
    fig.add_trace(go.Bar(
        y=df_pd["name"],  # Changed from x to y
        x=df_pd["cnt"],   # Changed from y to x
        name="Worked with in PAST year",
        marker_color="blue",
        orientation='h'   # Added horizontal orientation
    ))

    # Add the `want_cnt` bar (stacked on top) - now horizontal
    fig.add_trace(go.Bar(
        y=df_pd["name"],  # Changed from x to y
        x=df_pd["want_cnt"],  # Changed from y to x
        name="Want to work with NEXT year",
        marker_color="orange",
        orientation='h'   # Added horizontal orientation
    ))

    # Update layout for better visualization
    fig.update_layout(
        barmode="stack",  # Stacked bar chart
        title=f"{feature} Popularity and Demand",
        yaxis_title=feature,  # Swapped: now y-axis shows the feature names
        xaxis_title="Count",  # Swapped: now x-axis shows the count
        legend_title="Metric",
        yaxis=dict(
            automargin=True,  # Adjust margins automatically
            tickmode="linear"  # Ensure all labels are shown
        ),
        template="plotly_white",
        height=600,
        width=1200  # Increase width for better readability
    )

    # Show the plot
    st.plotly_chart(fig, use_container_width=True)


# Streamlit configuration
st.set_page_config(page_title="Technology Trends", page_icon="💻")

# Page Title and Description
st.title("Technology Trends in Software Development")
st.markdown("""
This page explores the popularity and demand for various technologies among developers, 
based on survey data. The analysis includes programming languages, databases, cloud platforms, 
web frameworks, and more. Each chart shows the number of developers who have worked with a 
technology in the past year and those who want to work with it in the next year.
""")

# Fetch and Plot Data
st.header("Programming Languages")
st.markdown("The chart below shows the popularity and demand for programming languages.")
pl_df = fetch_data("RespondentLanguage", "ProgrammingLanguage")
plot(pl_df, "Programming Language")

st.header("Databases")
st.markdown("The chart below shows the popularity and demand for databases.")
db_df = fetch_data("RespondentDatabase", "Database")
plot(db_df, "Database")

st.header("Cloud Platforms")
st.markdown("The chart below shows the popularity and demand for cloud platforms.")
cloud_df = fetch_data("RespondentCloud", "Cloud")
plot(cloud_df, "Cloud Platform")

st.header("Web Frameworks")
st.markdown("The chart below shows the popularity and demand for web frameworks and technologies.")
web_df = fetch_data("RespondentWebFramework", "WebFramework")
plot(web_df, "Web Framework/Technology")

st.header("Embedded Systems")
st.markdown("The chart below shows the popularity and demand for embedded systems and technologies.")
embed_df = fetch_data("RespondentEmbeddedSystem", "EmbeddedSystem")
plot(embed_df, "Embedded Systems/Technologies")

st.header("Miscellaneous Technologies")
st.markdown("The chart below shows the popularity and demand for other frameworks and technologies.")
misc_df = fetch_data("RespondentMiscTech", "MiscTech")
plot(misc_df, "Other Frameworks/Technologies")

st.header("Developer Tools")
st.markdown("The chart below shows the popularity and demand for developer tools used for compiling, building, and testing.")
dev_df = fetch_data("RespondentDevTool", "DevTool")
plot(dev_df, "Developer Tools for Compiling, Building and Testing")

st.header("Integrated Development Environments (IDEs)")
st.markdown("The chart below shows the popularity and demand for IDEs.")
ide_df = fetch_data("RespondentIDE", "IDE")
plot(ide_df, "Integrated Development Environment")

st.header("AI-Powered Tools")
st.markdown("The chart below shows the popularity and demand for AI-powered search and developer tools.")
ai_tool_df = fetch_data("RespondentAITool", "AITool")
plot(ai_tool_df, "AI-powered search and developer tools")