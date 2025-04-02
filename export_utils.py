import streamlit as st
import pandas as pd
import json

def export_tasks_to_csv(tasks):
    try:
        df = pd.DataFrame(tasks)
        csv = df.to_csv(index=False)
        return csv
    except Exception as e:
        st.error(f"Error exporting to CSV: {str(e)}")
        return None

def export_tasks_to_json(tasks):
    try:
        return json.dumps(tasks, indent=2)
    except Exception as e:
        st.error(f"Error exporting to JSON: {str(e)}")
        return None
