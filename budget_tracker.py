import streamlit as st
import pandas as pd
import json
from datetime import datetime
import plotly.graph_objects as go

class BudgetTracker:
    def __init__(self):
        st.set_page_config(page_title="מעקב תקציב", layout="wide")
        
        # Add CSS for RTL support
        st.markdown("""
            <style>
                .stApp {
                    direction: rtl;
                }
                .stButton button {
                    direction: rtl;
                }
                .stSelectbox select {
                    direction: rtl;
                }
                .stTextInput input {
                    direction: rtl;
                }
                .stNumberInput input {
                    direction: rtl;
                }
            </style>
        """, unsafe_allow_html=True)
        
        if 'current_budgets' not in st.session_state:
            st.session_state.current_budgets = {}
        if 'categories' not in st.session_state:
            st.session_state.categories = []
        if 'spending_data' not in st.session_state:
            st.session_state.spending_data = {}
        if 'years' not in st.session_state:
            st.session_state.years = []
        if 'active_tab' not in st.session_state:
            st.session_state.active_tab = "analysis"

        self.templates_file = "budget_templates.json"
        self.load_templates_from_file()
        self.excluded_categories = {
            'הכנסות לא תזרימיות',
            'הוצאות לא תזרימיות',
            'הכנסות קבועות',
            'הכנסות משתנות'
        }
        
        # Try to load default template if exists
        default_template = next((name for name in self.templates.keys() 
                               if name.lower() == "default"), None)
        if default_template:
            self.load_template(default_template)
            
        self.run()

    def load_templates_from_file(self):
        try:
            with open(self.templates_file, 'r', encoding='utf-8') as f:
                self.templates = json.load(f)
        except FileNotFoundError:
            self.templates = {}
            self.save_templates_to_file()

    def save_templates_to_file(self):
        with open(self.templates_file, 'w', encoding='utf-8') as f:
            json.dump(self.templates, f, ensure_ascii=False, indent=2)

    def save_template(self, name):
        self.templates[name] = st.session_state.current_budgets.copy()
        self.save_templates_to_file()
        st.success(f"תבנית '{name}' נשמרה בהצלחה!")

    def load_template(self, name):
        if name in self.templates:
            st.session_state.current_budgets = self.templates[name].copy()
            st.success(f"תבנית '{name}' נטענה בהצלחה!")

    def delete_template(self, name):
        if name in self.templates:
            del self.templates[name]
            self.save_templates_to_file()
            st.success(f"תבנית '{name}' נמחקה בהצלחה!")

    def process_file(self, uploaded_file):
        try:
            df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
            df['year'] = df['שייך לתזרים חודש'].str[:4]
            years = sorted(df['year'].unique())
            st.session_state.years = years
            
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
            st.error(f"שגיאה בעיבוד הקובץ: {str(e)}")
            return False

    def calculate_year_progress(self):
        now = datetime.now()
        start_of_year = datetime(now.year, 1, 1)
        progress = (now - start_of_year).total_seconds() / (365.25 * 24 * 60 * 60)
        return min(progress, 1.0)

    def display_budget_setup(self):
        st.header("הגדרת תקציב")
        
        st.subheader("ניהול תבניות")
        col1, col2 = st.columns(2)
        
        with col1:
            template_name = st.text_input("שם התבנית")
            if st.button("שמור תבנית") and template_name:
                self.save_template(template_name)

        with col2:
            if self.templates:
                template_to_load = st.selectbox("בחר תבנית", list(self.templates.keys()))
                col2_1, col2_2 = st.columns(2)
                with col2_1:
                    if st.button("טען תבנית"):
                        self.load_template(template_to_load)
                with col2_2:
                    if st.button("מחק תבנית", type="secondary"):
                        self.delete_template(template_to_load)
            else:
                st.info("אין תבניות שמורות")

        st.subheader("תקציב לפי קטגוריה")
        for category in st.session_state.categories:
            st.session_state.current_budgets[category] = st.number_input(
                category,
                value=float(st.session_state.current_budgets.get(category, 0)),
                key=f"budget_{category}"
            )

    def display_analysis(self, selected_year):
        st.header(f"ניתוח תקציב לשנת {selected_year}")
        
        year_progress = self.calculate_year_progress()
        current_month = datetime.now().month

        def create_progress_bar(spent_percent, year_progress_percent):
            return f"""
                <div dir="rtl" style="position: relative; width: 100%; height: 20px; background-color: #e2e8f0; border-radius: 9999px; overflow: hidden;">
                    <div style="position: absolute; right: 0; width: {min(spent_percent, 100)}%; height: 100%; 
                        background-color: {get_progress_color(spent_percent, year_progress_percent)}; 
                        border-radius: 9999px; transform-origin: right;">
                    </div>
                    <div style="position: absolute; top: 0; right: {year_progress_percent}%; 
                        width: 2px; height: 100%; background-color: black;">
                    </div>
                </div>
            """

        def get_progress_color(spent_percent, expected_percent):
            if spent_percent > expected_percent * 1.1:
                return "#ef4444"  # red for over budget
            elif spent_percent < expected_percent * 0.9:
                return "#eab308"  # yellow for under spending
            else:
                return "#22c55e"  # green for on track

        progress_col1, progress_col2 = st.columns([3, 1])
        with progress_col1:
            st.progress(year_progress)
        with progress_col2:
            st.write(f"{year_progress*100:.1f}% מהשנה הושלם")
        
        spending_data = st.session_state.spending_data.get(selected_year, {})
        
        over_budget, on_track, under_spending = st.columns(3)
        
        with over_budget:
            st.subheader("🔴 חריגה")
        with on_track:
            st.subheader("🟢 בכיוון הנכון")
        with under_spending:
            st.subheader("🟡 תת ניצול")

        def is_category_active(category, budget, spent):
            return budget > 0 or spent > 0

        for category in st.session_state.categories:
            budget = abs(st.session_state.current_budgets.get(category, 0))
            spent = abs(spending_data.get(category, 0))

            if not is_category_active(category, budget, spent):
                continue

            expected_spend = budget * year_progress
            
            if budget > 0:
                spent_percent = (spent / budget) * 100
            else:
                spent_percent = 100 if spent > 0 else 0
            
            year_progress_percent = year_progress * 100
            
            if budget == 0:
                if spent > 0:
                    container = over_budget
                else:
                    container = on_track
            else:
                if spent > expected_spend * 1.1:
                    container = over_budget
                elif spent < expected_spend * 0.9:
                    container = under_spending
                else:
                    container = on_track
            
            with container:
                with st.expander(f"{category}", expanded=True):
                    st.markdown(create_progress_bar(spent_percent, year_progress_percent), unsafe_allow_html=True)
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("תקציב", f"₪{budget:,.0f}")
                        st.metric("הוצאה", f"₪{spent:,.0f}")
                    with col2:
                        st.metric("צפוי", f"₪{expected_spend:,.0f}")
                        if budget > 0:
                            remainder = expected_spend - spent
                            if abs(remainder) > 0:
                                if remainder < 0:
                                    st.metric("חריגה", f"₪{abs(remainder):,.0f}", delta_color="inverse")
                                else:
                                    st.metric("פער חיובי", f"₪{remainder:,.0f}")
                        elif spent > 0:
                            st.metric("חריגה", f"₪{spent:,.0f}", delta_color="inverse")
                    
                    if current_month > 1:
                        monthly_avg = spent / current_month
                        st.write(f"ממוצע חודשי: ₪{monthly_avg:,.0f}")
                        yearly_projection = monthly_avg * 12
                        if budget > 0:
                            if yearly_projection > budget:
                                st.warning(f"תחזית שנתית: ₪{yearly_projection:,.0f} (מעל התקציב)")
                            else:
                                st.info(f"תחזית שנתית: ₪{yearly_projection:,.0f} (במסגרת התקציב)")
                        else:
                            st.warning(f"תחזית שנתית: ₪{yearly_projection:,.0f} (ללא תקציב)")

    def run(self):
        st.title("מעקב תקציב")
        
        if not st.session_state.categories:
            uploaded_file = st.file_uploader("העלה קובץ CSV של עסקאות", type=['csv'])
            if uploaded_file and self.process_file(uploaded_file):
                st.success("הקובץ עובד בהצלחה!")
        
        if st.session_state.categories:
            tab2, tab1 = st.tabs(["ניתוח", "הגדרת תקציב"])
            
            with tab1:
                self.display_budget_setup()
            
            with tab2:
                if st.session_state.years:
                    selected_year = st.selectbox(
                        "בחר שנה",
                        st.session_state.years,
                        index=len(st.session_state.years)-1
                    )
                    self.display_analysis(selected_year)

if __name__ == "__main__":
    BudgetTracker()