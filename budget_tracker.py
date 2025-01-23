import streamlit as st
import pandas as pd
import json
from datetime import datetime
import plotly.graph_objects as go

class BudgetTracker:
    def __init__(self):
        st.set_page_config(page_title="Budget Tracker", layout="wide")
        
        if 'current_budgets' not in st.session_state:
            st.session_state.current_budgets = {}
        if 'categories' not in st.session_state:
            st.session_state.categories = []
        if 'spending_data' not in st.session_state:
            st.session_state.spending_data = {}
        if 'years' not in st.session_state:
            st.session_state.years = []
            
        self.excluded_categories = {
            'הכנסות לא תזרימיות',
            'הוצאות לא תזרימיות',
            'הכנסות קבועות',
            'הכנסות משתנות'
        }
        
        self.run()

    def process_file(self, uploaded_file):
        try:
            # Read CSV with explicit encoding
            df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
            
            # Extract years
            df['year'] = df['שייך לתזרים חודש'].str[:4]
            years = sorted(df['year'].unique())
            st.session_state.years = years
            
            # Extract categories and calculate spending
            spending_data = {}
            categories = set()
            
            for year in years:
                year_data = df[df['year'] == year]
                spending_data[year] = {}
                
                for _, row in year_data.iterrows():
                    category = row['קטגוריה בתזרים']
                    if category and category not in self.excluded_categories:
                        categories.add(category)
                        amount = float(row['סכום']) if pd.notna(row['סכום']) else 0
                        spending_data[year][category] = spending_data[year].get(category, 0) + amount
            
            st.session_state.categories = sorted(categories)
            st.session_state.spending_data = spending_data
            
            return True
            
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.write("DataFrame head:", df.head()) if 'df' in locals() else None
            st.write("DataFrame columns:", df.columns) if 'df' in locals() else None
            return False

    def calculate_year_progress(self):
        now = datetime.now()
        start_of_year = datetime(now.year, 1, 1)
        progress = (now - start_of_year).total_seconds() / (365.25 * 24 * 60 * 60)
        return min(progress, 1.0)

    def save_template(self, name):
        templates = json.loads(st.session_state.get('templates', '{}'))
        templates[name] = st.session_state.current_budgets
        st.session_state.templates = json.dumps(templates)
        st.success(f"Template '{name}' saved successfully!")

    def load_template(self, name):
        templates = json.loads(st.session_state.get('templates', '{}'))
        if name in templates:
            st.session_state.current_budgets = templates[name]
            st.success(f"Template '{name}' loaded successfully!")

    def display_budget_setup(self):
        st.header("Budget Setup")
        
        col1, col2 = st.columns(2)
        with col1:
            template_name = st.text_input("Template Name")
            if st.button("Save Template") and template_name:
                self.save_template(template_name)
        
        with col2:
            templates = json.loads(st.session_state.get('templates', '{}'))
            if templates:
                template_to_load = st.selectbox("Select Template", list(templates.keys()))
                if st.button("Load Template"):
                    self.load_template(template_to_load)

        st.subheader("Category Budgets")
        for category in st.session_state.categories:
            st.session_state.current_budgets[category] = st.number_input(
                category,
                value=float(st.session_state.current_budgets.get(category, 0)),
                key=f"budget_{category}"
            )

    def display_analysis(self, selected_year):
        st.header(f"Budget Analysis for {selected_year}")
        
        year_progress = self.calculate_year_progress()
        st.progress(year_progress)
        st.text(f"Year Progress: {year_progress*100:.1f}%")
        
        spending_data = st.session_state.spending_data.get(selected_year, {})
        
        for category in st.session_state.categories:
            budget = st.session_state.current_budgets.get(category, 0)
            spent = abs(spending_data.get(category, 0))
            expected = year_progress * budget
            
            if budget > 0:
                progress = (spent / budget) * 100
                status = "Over Budget" if spent > expected else "Within Budget"
                color = "red" if spent > expected else "green"
                
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=progress,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    gauge={
                        'axis': {'range': [0, 100]},
                        'bar': {'color': color},
                        'steps': [
                            {'range': [0, year_progress*100], 'color': "lightgray"}
                        ],
                    },
                    title={'text': f"{category}"}
                ))
                
                fig.update_layout(height=200)
                st.plotly_chart(fig, use_container_width=True)
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Budget", f"₪{budget:,.0f}")
                col2.metric("Spent", f"₪{spent:,.0f}")
                col3.metric("Status", status)
                
                if spent > expected:
                    st.warning(f"Over expected by ₪{spent-expected:,.0f}")
                
                st.divider()

    def run(self):
        st.title("Budget Tracking Application")
        
        if not st.session_state.categories:
            uploaded_file = st.file_uploader("Upload your transaction CSV file", type=['csv'])
            if uploaded_file and self.process_file(uploaded_file):
                st.success("File processed successfully!")
        
        if st.session_state.categories:
            tab1, tab2 = st.tabs(["Budget Setup", "Analysis"])
            
            with tab1:
                self.display_budget_setup()
            
            with tab2:
                if st.session_state.years:
                    selected_year = st.selectbox(
                        "Select Year",
                        st.session_state.years,
                        index=len(st.session_state.years)-1
                    )
                    self.display_analysis(selected_year)

if __name__ == "__main__":
    BudgetTracker()