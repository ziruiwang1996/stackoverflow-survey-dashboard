import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from scipy.stats import chi2_contingency

load_dotenv()
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
SSL_MODE = os.getenv("SSL_MODE", "prefer")

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
def fetch_education_data():
    """Fetch education level distribution data"""
    query = """
    SELECT "EdLevel", COUNT(*) as count
    FROM "Respondent"
    WHERE "EdLevel" IS NOT NULL AND "EdLevel" != 'NA'
    GROUP BY "EdLevel"
    ORDER BY count DESC
    """
    return fetch_data(query)

@st.cache_data
def fetch_learning_methods_data():
    """Fetch learning code methods data"""
    query = """
    SELECT LC."name" as learning_method, COUNT(*) as count
    FROM "RespondentLearnCode" RLC
    INNER JOIN "LearnCode" LC ON RLC."id" = LC."id"
    GROUP BY LC."name"
    ORDER BY count DESC
    """
    return fetch_data(query)

def create_bar_chart(df, x_col, y_col, title, x_title, y_title):
    """Create a bar chart using Plotly"""
    fig = go.Figure(data=[
        go.Bar(x=df[x_col], y=df[y_col], marker_color='skyblue')
    ])
    
    fig.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis_title=y_title,
        template="plotly_white",
        xaxis_tickangle=-45
    )
    st.plotly_chart(fig, use_container_width=True)

@st.cache_data
def fetch_respondent():
    query = """
    SELECT "ResponseId", "EdLevel","DevType", "Industry"
    FROM "Respondent"
    WHERE "EdLevel" IS NOT NULL AND "DevType" IS NOT NULL AND "Industry" IS NOT NULL
        AND "EdLevel" != 'NA' AND "DevType" != 'NA' AND "Industry" != 'NA'
        AND "DevType" NOT LIKE 'Other (please specify):%%' AND "Industry" NOT LIKE 'Other:%%'
    """
    return fetch_data(query)

@st.cache_data
def fetch_learn_code_data():
    query = """
    SELECT "ResponseId", "LearnCode"."name"
    FROM "RespondentLearnCode"
    INNER JOIN "LearnCode" ON "RespondentLearnCode"."id" = "LearnCode"."id"
    """
    return fetch_data(query) 

def create_sankey(flows, title):
    # Remove duplicate rows in flows
    flows = flows.drop_duplicates()
    # Strip whitespace and clean source and target columns
    flows["source"] = flows["source"].str.strip()
    flows["target"] = flows["target"].str.strip()
    # Create a list of unique nodes
    nodes = pd.Index(pd.concat([flows["source"], flows["target"]]).unique())
    nodes = nodes.str.strip()  # Ensure all labels are clean
    node_map = {node: i for i, node in enumerate(nodes)}  # Map nodes to indices
    # Map source and target to their indices
    flows["source_idx"] = flows["source"].map(node_map)
    flows["target_idx"] = flows["target"].map(node_map)
    # Create the Sankey Diagram
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=20,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=nodes.tolist()  # Convert Index to list
        ),
        link=dict(
            source=flows["source_idx"],
            target=flows["target_idx"],
            value=flows["count"]
        )
    )])
    # Update layout
    fig.update_layout(
        title_text=title,
        font_size=10,
        height=600,  # Adjust height for better readability
        width=1000,  # Adjust width for better readability
        template="plotly_white",  # Use a clean template
        font=dict(size=12, color="black")  # Set consistent font size and color
    )
    # Show the Sankey Diagram in Streamlit
    st.plotly_chart(fig, use_container_width=True)

@st.cache_data
def data_prep_for_sankey(_df_learn_code, _df_respondent):
    # Merge the two DataFrames on ResponseId
    combined_df = _df_learn_code.merge(_df_respondent, on="ResponseId", how="inner")
    # Prepare the data for the Sankey Diagrams
    # Group by each pair of columns to calculate the flow counts
    edlevel_to_learn = combined_df.groupby(["EdLevel", "name"]).size().reset_index(name="count")
    learn_to_devtype = combined_df.groupby(["name", "DevType"]).size().reset_index(name="count")
    learn_to_industry = combined_df.groupby(["name", "Industry"]).size().reset_index(name="count")
    return edlevel_to_learn, learn_to_devtype, learn_to_industry

def create_sankey_plots(edlevel_to_learn, learn_to_devtype, learn_to_industry):
    # Plot 1: Education → Learn Code → Dev Type
    flows_1 = pd.concat([
        edlevel_to_learn.rename(columns={"EdLevel": "source", "name": "target"}),
        learn_to_devtype.rename(columns={"name": "source", "DevType": "target"})
    ])
    create_sankey(flows_1, "Education Level → Learning Code Method → Developer Type")
    # Plot 2: Education → Learn Code → Industry
    flows_2 = pd.concat([
        edlevel_to_learn.rename(columns={"EdLevel": "source", "name": "target"}),
        learn_to_industry.rename(columns={"name": "source", "Industry": "target"})
    ])
    create_sankey(flows_2, "Education Level → Learning Code Method → Industry")

@st.cache_data
def association_analysis_data(df_respondent, df_learn_code):
    df_respondent_copy = df_respondent.copy()
    df_respondent_copy['value'] = 1
    edlevel_pivot = df_respondent_copy.pivot_table(
        index='ResponseId', columns='EdLevel', values='value', fill_value=0, aggfunc='sum'
    ).reset_index()
    devtype_pivot = df_respondent_copy.pivot_table(
        index='ResponseId', columns='DevType', values='value', fill_value=0, aggfunc='sum'  
    ).reset_index()
    industry_pivot = df_respondent_copy.pivot_table(
        index='ResponseId', columns='Industry', values='value', fill_value=0, aggfunc='sum'
    ).reset_index()
     # Combine all pivoted DataFrames using pandas merge
    df_respondent_pivot_combined = edlevel_pivot.merge(devtype_pivot, on="ResponseId", how="inner")
    df_respondent_pivot_combined = df_respondent_pivot_combined.merge(industry_pivot, on="ResponseId", how="inner")
    rename_map = {
        "Associate degree (A.A., A.S., etc.)": "Associate degree",
        "Bachelor’s degree (B.A., B.S., B.Eng., etc.)": "Bachelor degree",
        "Master’s degree (M.A., M.S., M.Eng., MBA, etc.)": "Master degree",
        "Primary/elementary school": "Primary or elementary school",
        "Professional degree (JD, MD, Ph.D, Ed.D, etc.)": "Professional degree",
        "Secondary school (e.g. American high school, German Realschule or Gymnasium, etc.)": "Secondary school",
        "Some college/university study without earning a degree": "Some college or university study without earning a degree",
        "Books / Physical media": "Books or physical media",
        "Other online resources (e.g., videos, blogs, forum, online community)": "Other online resources",
        "School (i.e., University, College, etc)": "School (University or College)",
        "Senior Executive (C-Suite, VP, etc.)": "Senior Executive"
    }
    df_respondent_pivot_combined = df_respondent_pivot_combined.rename(columns=rename_map)
    df_respondent_pivot_combined = df_respondent_pivot_combined.fillna(0)

    df_learn_code_copy = df_learn_code.copy()
    df_learn_code_copy['value'] = 1
    # Pivot the DataFrame to reshape it
    learn_code_pivot = df_learn_code_copy.pivot_table(
        index='ResponseId', columns='name', values='value', fill_value=0, aggfunc='sum'
    ).reset_index()
    rename_map = {
        "Books / Physical media": "Books or physical media",
        "Other online resources (e.g., videos, blogs, forum, online community)": "Other online resources",
        "School (i.e., University, College, etc)": "School (University or College)",
    }
    learn_code_pivot = learn_code_pivot.rename(columns=rename_map)
    learn_code_pivot = learn_code_pivot.fillna(0)

    df = df_respondent_pivot_combined.merge(learn_code_pivot, on="ResponseId", how="inner")
    return df

def cramers_v(x, y):
    confusion_matrix = pd.crosstab(x, y)
    chi2, p, dof, ex = chi2_contingency(confusion_matrix, correction=False)
    n = confusion_matrix.sum().sum()
    phi2 = chi2 / n
    r, k = confusion_matrix.shape
    return np.sqrt(phi2 / min(k-1, r-1))

@st.cache_data
def association_analysis(_df, features, targets):
    results = []
    for f in features:
        for t in targets:
            v = cramers_v(_df[f], _df[t])
            results.append((f, t, v))
    # Create a DataFrame to store the results
    correlation_df = pd.DataFrame(results, columns=["Feature", "Target", "CramersV"])
    correlation_df = correlation_df.sort_values("CramersV", ascending=False).head(10)
    return correlation_df

def association_plot(df, f, t):
    # Create a table using Plotly
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=[f, t, "Cramér's V"],
            fill_color="lightgrey",
            align="left",
            font=dict(size=12, color="black")
        ),
        cells=dict(
            values=[df["Feature"], df["Target"], df["CramersV"]],
            fill_color="white",
            align="left",
            font=dict(size=11),
            format=["", "", ".4f"]  # Format Cramér's V to 4 decimal places
        )
    )])
    # Set the title and layout
    fig.update_layout(
        title=f"Top 10 {f}-{t} Associations by Cramér's V",
        title_x=0.5,  # Center the title
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig)

# Streamlit app
st.set_page_config(page_title="Education Pathway Analysis", page_icon="🎓")
st.title("🎓 Education Pathway Analysis")

st.markdown("""
    This analysis explores the relationship between education levels, learning methods, and career outcomes 
    in the software development field. Understanding these pathways can help aspiring developers make 
    informed decisions about their educational journey.
    """)

# Education Level Distribution
st.header("📚 Education Level Distribution")
st.write("Distribution of education levels among survey respondents.")
education_data = fetch_education_data()
if not education_data.empty:
    create_bar_chart(
        education_data, 
        "EdLevel", 
        "count", 
        "Distribution of Education Levels",
        "Education Level",
        "Number of Respondents"
    )

# Learning Methods
st.header("💡 How Developers Learn to Code")
st.write("Most popular methods for learning programming skills.")
learning_data = fetch_learning_methods_data()
if not learning_data.empty:
    create_bar_chart(
        learning_data,  # Top 10 learning methods
        "learning_method", 
        "count", 
        "Distribution of Learning Methods",
        "Learning Method",
        "Number of Respondents"
    )

# Sankey Diagrams Section
st.header("🔄 Education to Career Pathways")
st.write("Interactive flow diagrams showing how education levels connect to learning methods and career outcomes.")
respondent_data = fetch_respondent()
learn_code_data = fetch_learn_code_data()
    
if not respondent_data.empty and not learn_code_data.empty:
    edlevel_to_learn, learn_to_devtype, learn_to_industry = data_prep_for_sankey(learn_code_data, respondent_data)
    create_sankey_plots(edlevel_to_learn, learn_to_devtype, learn_to_industry)


st.subheader("🔗 Association Analysis")
st.markdown(
    """
    This analysis identifies the strongest relationships between education levels, industries, and developer roles 
    using Cramér's V statistic. A Cramér's V value close to 1 indicates a strong association, while a value close to 0 indicates a weak association.
    The top associations are visualized in tables below.
    """
)

learn_code_features = [
    "Books or physical media", "Coding Bootcamp", "Colleague", "Friend or family member",
    "On the job training", "Online Courses or Certification", "Other online resources", "School (University or College)"
]
education_features = [
    "Associate degree", "Bachelor degree", "Master degree", "Primary or elementary school", "Professional degree",
    "Secondary school", "Some college or university study without earning a degree"
]
industry_targets = [
    "Banking/Financial Services", "Computer Systems Design and Services", "Energy", "Fintech", "Government", "Healthcare", 
    "Higher Education", "Insurance", "Internet, Telecomm or Information Services", "Manufacturing", 
    "Media & Advertising Services", "Retail and Consumer Services", "Software Development", "Transportation, or Supply Chain"
]
dev_type_targets = [
    "Academic researcher", "Blockchain", "Cloud infrastructure engineer", "Data engineer", "Data or business analyst", "Student", "System administrator",
    "Data scientist or machine learning specialist", "Database administrator", "Designer", "DevOps specialist", "Developer Advocate", 
    "Developer Experience", "Developer, AI", "Developer, QA or test", "Developer, back-end", "Developer, desktop or enterprise applications", 
    "Developer, embedded applications or devices", "Developer, front-end", "Developer, full-stack", "Developer, game or graphics", 
    "Developer, mobile", "Educator", "Engineer, site reliability", "Engineering manager", "Hardware Engineer", "Marketing or sales professional", 
    "Product manager", "Project manager", "Research & Development role", "Scientist", "Security professional", "Senior Executive"
]
if not respondent_data.empty and not learn_code_data.empty:
    features_pd = association_analysis_data(respondent_data, learn_code_data)
    indus_association = association_analysis(features_pd, education_features, industry_targets)
    association_plot(indus_association, "Education", "Industry")
    dev_association = association_analysis(features_pd, education_features, dev_type_targets)
    association_plot(dev_association, "Education", "DevType")

st.markdown("""We observe the strongest associations between holding a professional degree (e.g., JD, MD, Ph.D., Ed.D.) and working in higher 
            education, as well as between holding a professional degree and roles such as academic researcher or scientist. However, 
            the Cramér's V values remain relatively low across all comparisons, indicating that there are no strong or significant associations 
            among education levels, industries, and developer roles.""")

st.markdown("""
### Key Insights
- **Formal Education Impact**: Higher formal education levels generally correlate with higher average salaries
- **Learning Diversity**: Developers use multiple learning methods, including online courses, bootcamps, and self-teaching
- **Career Paths**: There are multiple valid pathways to a successful development career, not just traditional computer science degrees
""")