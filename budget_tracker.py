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
        
        # Calculate year progress
        year_progress = self.calculate_year_progress()
        current_month = datetime.now().month
        
        # Display year progress bar
        st.subheader("Year Progress")
        progress_col1, progress_col2 = st.columns([3, 1])
        with progress_col1:
            st.progress(year_progress)
        with progress_col2:
            st.write(f"{year_progress*100:.1f}% of year completed")
        
        # Get spending data for selected year
        spending_data = st.session_state.spending_data.get(selected_year, {})
        
        # Create three columns for different status categories
        over_budget, on_track, under_spending = st.columns(3)
        
        with over_budget:
            st.subheader("🔴 Over Budget")
        with on_track:
            st.subheader("🟢 On Track")
        with under_spending:
            st.subheader("🟡 Under Spending")
        
        # Analyze each category
        for category in st.session_state.categories:
            budget = abs(st.session_state.current_budgets.get(category, 0))
            spent = abs(spending_data.get(category, 0))
            expected_spend = budget * year_progress
            
            # Handle percentage calculation
            if budget > 0:
                spent_percent = (spent / budget) * 100
            else:
                # If budget is 0, we'll treat any spending as over budget
                spent_percent = 100 if spent > 0 else 0
            
            expected_percent = year_progress * 100
            
            # Determine category status
            if budget == 0:
                if spent > 0:
                    container = over_budget
                    status = "Unbudgeted Spending"
                else:
                    container = on_track
                    status = "No Budget / No Spending"
            else:
                if spent > expected_spend * 1.1:  # Over budget (>10% over expected)
                    container = over_budget
                    status = "Over Budget"
                elif spent < expected_spend * 0.9:  # Under spending (<90% of expected)
                    container = under_spending
                    status = "Under Spending"
                else:  # On track (within 10% of expected)
                    container = on_track
                    status = "On Track"
            
            with container:
                with st.expander(f"{category}", expanded=True):
                    # Budget progress bar (cap at 100% for zero budgets)
                    st.progress(min(spent_percent/100, 1.0))
                    
                    # Key metrics
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Budget", f"₪{budget:,.0f}")
                        st.metric("Spent", f"₪{spent:,.0f}")
                    with col2:
                        st.metric("Expected", f"₪{expected_spend:,.0f}")
                        if budget > 0:  # Only show over/under for non-zero budgets
                            remainder = expected_spend - spent
                            if abs(remainder) > 0:
                                if remainder < 0:
                                    st.metric("Over by", f"₪{abs(remainder):,.0f}", delta_color="inverse")
                                else:
                                    st.metric("Under by", f"₪{remainder:,.0f}")
                        elif spent > 0:  # For zero budget with spending
                            st.metric("Over by", f"₪{spent:,.0f}", delta_color="inverse")
                    
                    # Monthly average (only show projection if there's a budget)
                    if current_month > 1:
                        monthly_avg = spent / current_month
                        st.write(f"Monthly average: ₪{monthly_avg:,.0f}")
                        if budget > 0:
                            yearly_projection = monthly_avg * 12
                            if yearly_projection > budget:
                                st.warning(f"Yearly projection: ₪{yearly_projection:,.0f} (Over budget)")
                            else:
                                st.info(f"Yearly projection: ₪{yearly_projection:,.0f} (Within budget)")
                        else:
                            yearly_projection = monthly_avg * 12
                            st.warning(f"Yearly projection: ₪{yearly_projection:,.0f} (No budget set)")

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