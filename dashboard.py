import streamlit as st
import pandas as pd

# -----------------------
# Page title
# -----------------------
st.set_page_config(page_title="Student Dashboard", layout="wide")

st.title("📊 Big Data Analytics Dashboard")

st.write("This is a simple Streamlit dashboard.")

# -----------------------
# Read CSV
# -----------------------
df = pd.read_csv("students.csv")

# -----------------------
# Show data
# -----------------------
st.header("Student Data")

st.dataframe(df)

# -----------------------
# Statistics
# -----------------------
st.header("Summary Statistics")

st.write(df.describe())

# -----------------------
# Average score
# -----------------------
st.metric("Average Score", round(df["Score"].mean(),1))

# -----------------------
# Bar chart
# -----------------------
st.header("Student Scores")

st.bar_chart(df.set_index("Name")["Score"])

# -----------------------
# Filter
# -----------------------
course = st.selectbox(
    "Choose a course",
    df["Course"].unique()
)

filtered = df[df["Course"] == course]

st.write(filtered)

# -----------------------
# Pie chart
# -----------------------
st.header("Students per Course")

course_counts = df["Course"].value_counts()

st.pyplot(course_counts.plot.pie(autopct="%1.1f%%").get_figure())