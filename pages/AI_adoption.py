import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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

def fetch_data(query):
    """
    Helper function to fetch data from the database using a SQL query.
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

@st.cache_data
def ai_use_by_industry_data():
    query = """
    WITH industry_totals AS (
        SELECT 
            "Industry", 
            COUNT(*) AS total_respondents
        FROM "Respondent"
        WHERE "Industry" IS NOT NULL AND "Industry" != 'NA' AND "Industry" != 'Other:'
        GROUP BY "Industry"
    )
    SELECT 
        R."Industry", R."AISelect", COUNT(*) * 100.0 / DTR.total_respondents AS percentage
    FROM "Respondent" R
    INNER JOIN industry_totals DTR
    ON R."Industry" = DTR."Industry"
    WHERE R."AISelect" IS NOT NULL AND R."AISelect" != 'NA'
    GROUP BY R."Industry", R."AISelect", DTR.total_respondents
    """
    df = fetch_data(query)
    # Pivot the data so that AISelect becomes columns
    df_pivot = df.pivot(index='Industry', columns='AISelect', values='percentage').fillna(0)
    # Sort by 'Yes' column in descending order
    if "Yes" in df_pivot.columns:
        df_pivot = df_pivot.sort_values('Yes', ascending=False)
    return df_pivot.reset_index()

@st.cache_data
def ai_use_by_devtype_data():
    query = """
    WITH dev_type_responses AS (
        SELECT
            "DevType", COUNT(*) AS total_respondents
        FROM "Respondent"
        WHERE "DevType" IS NOT NULL AND "DevType" != 'NA' AND "DevType" != 'Other (please specify):'
        GROUP BY "DevType"
    )
    SELECT 
        R."DevType", R."AISelect", COUNT(*) * 100.0 / DTR.total_respondents AS percentage
    FROM "Respondent" R
    INNER JOIN dev_type_responses DTR
    ON R."DevType" = DTR."DevType"
    WHERE R."AISelect" IS NOT NULL AND R."AISelect" != 'NA'
    GROUP BY R."DevType", R."AISelect", DTR.total_respondents
    """
    df = fetch_data(query)
    # Pivot the data so that AISelect becomes columns
    df_pivot = df.pivot(index='DevType', columns='AISelect', values='percentage').fillna(0)
    # Sort by 'Yes' column in descending order
    if "Yes" in df_pivot.columns:
        df_pivot = df_pivot.sort_values('Yes', ascending=False)
    return df_pivot.reset_index()

def stacked_bar_plot(df_pd, feature, title, x_title, y_title, legend_title): 
    # Create a stacked bar chart using Plotly
    fig = go.Figure()
    dev_types = df_pd[feature] 
    ai_selects = ["Yes", "No, but I plan to soon", "No, and I don't plan to"]  # Order of stacking
    for ai_select in ai_selects:
        if ai_select in df_pd.columns:
            fig.add_trace(go.Bar(
                x=dev_types,
                y=df_pd[ai_select],
                name=ai_select,
                hoverinfo="x+y+name"  # Show details on hover
            ))
    # Update layout for better readability
    fig.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis_title=y_title,
        barmode="stack",  # Stacked bar chart
        legend_title=legend_title,
        xaxis_tickangle=45
    )
    # Display the plot in Streamlit
    st.plotly_chart(fig)

@st.cache_data
def ai_trust_data():
    query = """
    SELECT "AIAcc", COUNT(*) AS count
    FROM "Respondent"
    WHERE "AIAcc" IS NOT NULL AND "WorkExp" IS NOT NULL AND "AIAcc" != 'NA'
    GROUP BY "AIAcc"
    """
    df = fetch_data(query)

    order_mapping = {
        "Highly trust": 1,
        "Somewhat trust": 2,
        "Neither trust nor distrust": 3,
        "Somewhat distrust": 4,
        "Highly distrust": 5
    }

    # Add a new column for sorting based on the desired order
    df['order'] = df['AIAcc'].map(order_mapping).fillna(6)

    # Sort the data based on the custom order
    df = df.sort_values('order')
    return df[['AIAcc', 'count']]

@st.cache_data
def ai_threat_data():
    query = """
    SELECT "AIThreat", COUNT(*) AS count
    FROM "Respondent"
    WHERE "AIThreat" IS NOT NULL AND "AIThreat" != 'NA'
    GROUP BY "AIThreat"
    """
    df = fetch_data(query)
    return df
    
def bar_plot(df_pd, x_col, y_col, title, x_title, y_title):
    # Create an interactive bar chart using Plotly
    fig = go.Figure(data=[
        go.Bar(
            x=df_pd[x_col],
            y=df_pd[y_col],
            marker_color="skyblue",
            hoverinfo="x+y"  # Show details on hover
        )
    ])
    # Update layout for better readability
    fig.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis_title=y_title,
        xaxis_tickangle=45
    )
    # Display the plot in Streamlit
    st.plotly_chart(fig)


# Function to group <1% categories into "Other"
def group_small_categories(df, label_col, value_col, threshold=1):
    # Calculate the total count
    total_count = df[value_col].sum()
    # Add a percentage column
    df['percentage'] = (df[value_col] / total_count) * 100
    # Separate large and small categories
    large_categories = df[df['percentage'] >= threshold]
    small_categories = df[df['percentage'] < threshold]
    # Aggregate small categories into "Other"
    if len(small_categories) > 0:
        other_row = pd.DataFrame({
            label_col: ["Other"],
            value_col: [small_categories[value_col].sum()],
            'percentage': [small_categories['percentage'].sum()]
        })
        # Combine large categories and "Other"
        df = pd.concat([large_categories, other_row], ignore_index=True)
    else:
        df = large_categories
    # Select only the label and value columns
    return df[[label_col, value_col]]

@st.cache_data
def ai_trust_details_data(ai_acc):
    ai_acc_escaped = ai_acc.replace("'", "''")
    query_devtype = f"""
    SELECT "DevType", COUNT(*) AS count
    FROM "Respondent"
    WHERE "AIAcc" = '{ai_acc_escaped}' AND "DevType" IS NOT NULL AND "DevType" != 'NA' AND "DevType" != 'Other (please specify):'
    GROUP BY "DevType"
    """
    query_industry = f"""
    SELECT "Industry", COUNT(*) AS count
    FROM "Respondent"
    WHERE "AIAcc" = '{ai_acc_escaped}' AND "Industry" IS NOT NULL AND "Industry" != 'NA' AND "Industry" != 'Other:'
    GROUP BY "Industry"
    """
    # Load data from the database
    df_devtype = fetch_data(query_devtype)
    df_industry = fetch_data(query_industry)
    devtype_data = group_small_categories(df_devtype, "DevType", "count")
    industry_data = group_small_categories(df_industry, "Industry", "count")
    return devtype_data, industry_data

@st.cache_data
def ai_threat_details_data(ai_threat):
    ai_threat_escaped = ai_threat.replace("'", "''")
    query_devtype = f"""
    SELECT "DevType", COUNT(*) AS count
    FROM "Respondent"
    WHERE "AIThreat" = '{ai_threat_escaped}' AND "DevType" IS NOT NULL AND "DevType" != 'NA' AND "DevType" != 'Other (please specify):'
    GROUP BY "DevType"
    """
    query_industry = f"""
    SELECT "Industry", COUNT(*) AS count
    FROM "Respondent"
    WHERE "AIThreat" = '{ai_threat_escaped}' AND "Industry" IS NOT NULL AND "Industry" != 'NA' AND "Industry" != 'Other:'
    GROUP BY "Industry"
    """
    # Load data from the database
    df_devtype = fetch_data(query_devtype)
    df_industry = fetch_data(query_industry)
    devtype_data = group_small_categories(df_devtype, "DevType", "count")
    industry_data = group_small_categories(df_industry, "Industry", "count")
    return devtype_data, industry_data

def pie_plot(df_pd_devtype, df_pd_industry, trust_or_threat, level):
    # Create side-by-side pie charts
    fig = make_subplots(
        rows=1, cols=2, specs=[[{'type': 'domain'}, {'type': 'domain'}]],
        subplot_titles=["Developer Type Breakdown", "Industry Breakdown"]
    )
    # Add pie chart for developer type
    fig.add_trace(
        go.Pie(
            labels=df_pd_devtype["DevType"],
            values=df_pd_devtype["count"],
            name="Developer Type",
            showlegend=False  # Remove legend
        ),
        row=1, col=1
    )
    # Add pie chart for industry
    fig.add_trace(
        go.Pie(
            labels=df_pd_industry["Industry"],
            values=df_pd_industry["count"],
            name="Industry",
            showlegend=False  # Remove legend
        ),
        row=1, col=2
    )
    # Update layout for better readability
    fig.update_layout(
        title_text=f"Details for AI {trust_or_threat} Level: {level}",
        title_x=0.5,  # Center the title
        height=500  # Adjust height for side-by-side layout
    )
    # Display the plot in Streamlit
    st.plotly_chart(fig)



st.set_page_config(page_title="AI Adoption Analysis", page_icon="📈")
st.markdown("# 📊 AI Adoption Analysis")
st.write(
    """
    This analysis explores the adoption and perception of AI across different industries and developer roles. 
    It provides insights into how developers are using AI tools, their trust levels in AI, and their views on AI as a potential threat.

    ### Key Highlights:
    - **AI Use by Industry:** A breakdown of AI adoption across various industries, showing the percentage of respondents who currently use AI, plan to use it, or do not intend to use it.
    - **AI Use by Developer Type:** An analysis of AI adoption among different developer roles, highlighting how AI usage varies by profession.
    - **AI Trust Levels:** A distribution of trust levels in AI, ranging from "Highly trust" to "Highly distrust," providing insights into developers' confidence in AI technologies.
    - **AI Threat Levels:** An exploration of how developers perceive AI as a potential threat, categorized into different levels of concern.

    These visualizations aim to provide a comprehensive understanding of the current state of AI adoption and attitudes toward AI in the developer community.
    """
)

# Section: AI Use by Industry
st.markdown("## 🏭 AI Use by Industry")
st.write("Explore how AI adoption varies across different industries.")
df_pd_industry = ai_use_by_industry_data()
stacked_bar_plot(df_pd_industry, "Industry", "AI Adoption by Industry", "Industry", "Percentage (%)", "AI Use")

# Section: AI Use by Developer Type
st.markdown("## 👩‍💻 AI Use by Developer Type")
st.write("Analyze how AI adoption differs among various developer roles.")
df_pd_devtype = ai_use_by_devtype_data()
stacked_bar_plot(df_pd_devtype, "DevType", "AI Adoption by Developer Type", "Developer Type", "Percentage (%)", "AI Use")

# Section: AI Trust Levels
st.markdown("## 🤝 AI Trust Levels")
st.write("Understand developers' trust levels in AI technologies.")
ai_trust_df = ai_trust_data()
bar_plot(ai_trust_df, "AIAcc", "count",
          title="AI Trust Levels Distribution",
          x_title="AI Trust Levels",
          y_title="Number of Respondents")  

# Detailed Analysis: AI Trust Levels
st.markdown("### 🔍 Detailed Analysis: AI Trust Levels")
st.write("Select an AI trust level to view a detailed breakdown by developer type and industry.")
aiacc = st.selectbox(
    "Select AI Trust Level:",
    ["Highly trust", "Somewhat trust", "Neither trust nor distrust", "Somewhat distrust", "Highly distrust"]
)
trust_by_devtype_df, trust_by_industry_df = ai_trust_details_data(aiacc)
pie_plot(trust_by_devtype_df, trust_by_industry_df, "Trust", aiacc)

# Section: AI Threat Levels
st.markdown("## ⚠️ AI Threat Levels")
st.write("Explore how developers perceive AI as a potential threat.")
ai_threat_df = ai_threat_data()
bar_plot(ai_threat_df, "AIThreat", "count",
         title="AI Threat Levels Distribution",
         x_title="AI Threat Levels",
         y_title="Number of Respondents")    

# Detailed Analysis: AI Threat Levels
st.markdown("### 🔍 Detailed Analysis: AI Threat Levels")
st.write("Select an AI threat level to view a detailed breakdown by developer type and industry.")
aithreat = st.selectbox(
    "Select AI Threat Level:",
    ["Yes", "No", "I'm not sure"]
)
threat_by_devtype_df, threat_by_industry_df = ai_threat_details_data(aithreat)
pie_plot(threat_by_devtype_df, threat_by_industry_df, "Threat", aithreat)