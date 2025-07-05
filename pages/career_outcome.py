import streamlit as st
import pandas as pd
import plotly.express as px
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
def fetch_data():
    query = """
    SELECT "CompTotal(USD)" AS salary, "EdLevel", "YearsCodePro", "DevType", "Industry",
            "LearnCode"."name" AS learn_code_method,
            "ProgrammingLanguage"."name" AS programming_language
    FROM "Respondent"
    LEFT JOIN "RespondentLearnCode" ON "Respondent"."ResponseId" = "RespondentLearnCode"."ResponseId"
    LEFT JOIN "LearnCode" ON "RespondentLearnCode"."id" = "LearnCode"."id"
    LEFT JOIN "RespondentLanguage" ON "Respondent"."ResponseId" = "RespondentLanguage"."ResponseId"
    LEFT JOIN "ProgrammingLanguage" ON "RespondentLanguage"."id" = "ProgrammingLanguage"."id"
    WHERE "CompTotal(USD)" IS NOT NULL AND "CompTotal(USD)" > 0 AND "CompTotal(USD)" < 1000000
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
def salary_distribution_data(_df):
    return _df[["salary"]].copy()  # Return DataFrame instead of Series

def histogram_plot(df):
    fig = px.histogram(df, x="salary", nbins=100, title="Salary Distribution (USD)")
    fig.update_layout(
        xaxis_title="Salary (USD)",
        yaxis_title="Frequency",
        bargap=0.1,
        template="plotly_white"
    )
    st.plotly_chart(fig)

def bar_plot(df_pd, x_label, y_label, title, labels, if_adjust):
    fig = px.bar(
        df_pd,
        x=x_label,
        y=y_label,
        orientation="h",
        title=title,
        labels=labels
    )
    if if_adjust:
        fig.update_layout(
            template="plotly_white",
            height=1000,  # Increase height for developer types
            margin=dict(l=250, r=50, t=50, b=50),  # Adjust left margin for long labels
        )
    else:
        fig.update_layout(template="plotly_white")
    st.plotly_chart(fig)

@st.cache_data
def avg_salary_by_education_data(_df):
    filtered_df = _df[_df["EdLevel"] != "Something else"]
    return filtered_df.groupby("EdLevel")["salary"].mean().reset_index().rename(columns={"salary": "average_salary"}).sort_values("average_salary")

@st.cache_data
def avg_salary_by_learn_code_data(_df):
    filtered_df = _df[_df["learn_code_method"] != "Not Specified"]
    return filtered_df.groupby("learn_code_method")["salary"].mean().reset_index().rename(columns={"salary": "average_salary"}).sort_values("average_salary")

@st.cache_data
def avg_salary_by_years_code_pro_data(_df):
    return _df.groupby("YearsCodePro")["salary"].mean().reset_index().rename(columns={"salary": "average_salary"}).sort_values("YearsCodePro")

@st.cache_data
def avg_salary_by_dev_type_data(_df):
    df_filtered = _df[~_df["DevType"].isin(["Other (please specify):", "NA"])]
    return df_filtered.groupby("DevType")["salary"].mean().reset_index().rename(columns={"salary": "average_salary"}).sort_values("average_salary")

@st.cache_data
def avg_salary_by_industry_data(_df):
    df_filtered = _df[~_df["Industry"].isin(["Other:", "NA"])]
    return df_filtered.groupby("Industry")["salary"].mean().reset_index().rename(columns={"salary": "average_salary"}).sort_values("average_salary")

@st.cache_data
def avg_salary_by_programming_language_data(_df):
    return _df.groupby("programming_language")["salary"].mean().reset_index().rename(columns={"salary": "average_salary"}).sort_values("average_salary")



# Page configuration
st.set_page_config(page_title="Career Outcomes Analysis", page_icon="📊")
# Page title and description
st.markdown("# 📊 Career Outcomes Analysis")
st.write(
    """
    This dashboard provides insights into career outcomes based on various factors such as education level, 
    years of professional coding experience, developer type, industry, and programming languages used. 
    Explore the visualizations below to understand how these factors influence average salaries.
    """
)
df = fetch_data()

st.markdown("## Salary Distribution")
st.write("Explore the distribution of salaries across all respondents.")
df_pd_salary = salary_distribution_data(df)
histogram_plot(df_pd_salary)

st.markdown("## Average Salary by Education Level")
st.write("Analyze how education level impacts average salary.")
df_pd_edu = avg_salary_by_education_data(df)
bar_plot(df_pd_edu, 
            "average_salary", 
            "EdLevel", 
            "Average Salary by Education Level", 
            {"average_salary": "Average Salary (USD)", "EdLevel": "Education Level"},
            False)

st.markdown("## Average Salary by Learning Code Method")
st.write("Understand how different methods of learning to code influence average salary.")
df_pd_learn_code = avg_salary_by_learn_code_data(df)
bar_plot(df_pd_learn_code, 
            "average_salary", 
            "learn_code_method", 
            "Average Salary by Learning Code Method", 
            {"average_salary": "Average Salary (USD)", "learn_code_method": "Learning Code Method"},
            False)

st.markdown("## Average Salary by Years of Professional Coding Experience")
st.write("See how years of professional coding experience affect average salary.")
df_pd_years_code_pro = avg_salary_by_years_code_pro_data(df)
bar_plot(df_pd_years_code_pro, 
            "average_salary", 
            "YearsCodePro", 
            "Average Salary by Years of Professional Coding Experience", 
            {"average_salary": "Average Salary (USD)", "YearsCodePro": "Years of Professional Coding"},
            False)

st.markdown("## Average Salary by Developer Type")
st.write("Compare average salaries across different developer roles.")
df_pd_dev_type = avg_salary_by_dev_type_data(df)
bar_plot(df_pd_dev_type, 
            "average_salary",
            "DevType",
            "Average Salary by Developer Type",
            {"average_salary": "Average Salary (USD)", "DevType": "Developer Type"},
            True)

st.markdown("## Average Salary by Industry")
st.write("Explore how average salaries vary across industries.")
df_pd_industry = avg_salary_by_industry_data(df)
bar_plot(df_pd_industry, 
            "average_salary",
            "Industry",
            "Average Salary by Industry",
            {"average_salary": "Average Salary (USD)", "Industry": "Industry"},
            False)    

st.markdown("## Average Salary by Programming Language")
st.write("Discover how the choice of programming language impacts average salary.")
df_pd_pro_lang =avg_salary_by_programming_language_data(df)
bar_plot(df_pd_pro_lang, 
            "average_salary",
            "programming_language",
            "Average Salary by Programming Language",
            {"average_salary": "Average Salary (USD)", "programming_language": "Programming Language"},
            True)