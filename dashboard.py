import streamlit as st
import requests

st.set_page_config(page_title="Log Analyzer", layout="wide")

BACKEND_URL = "http://localhost:8000"

st.title("AI Log Analyzer")
