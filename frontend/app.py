import os
import sys
import importlib
from datetime import date
from decimal import Decimal
import plotly.graph_objects as go
import streamlit as st

# Ensure project root is on PYTHONPATH
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Force reload backend modules if already cached in long-running processes (e.g. Streamlit Cloud)
for mod_name in list(sys.modules.keys()):
    if mod_name.startswith("backend."):
        try:
            importlib.reload(sys.modules[mod_name])
        except Exception:
            pass

from backend.db.db_manager import DatabaseConnection
from backend.dal.employee_manager import EmployeeManager
from backend.dal.project_manager import ProjectManager
from backend.dal.analytics_manager import AnalyticsManager
from backend.dal.warehouse_sync_manager import WarehouseSyncManager
from backend.models.entities import Employee

# Page Configuration (No emojis)
st.set_page_config(
    page_title="Enterprise HR Analytics Portal",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
css_path = os.path.join(os.path.dirname(__file__), "styles", "custom.css")
if os.path.exists(css_path):
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def get_managers():
    db = DatabaseConnection()
    return EmployeeManager(db), ProjectManager(db), AnalyticsManager(db), db


emp_mgr, proj_mgr, analytics_mgr, db_conn = get_managers()


def format_table_value(col, val):
    """Format table cell values cleanly."""
    if val is None:
        return ""
    if "Income" in col or "Salary" in col or "Budget" in col:
        try:
            return f"${float(val):,.2f}"
        except (ValueError, TypeError):
            return str(val)
    if "Percentage" in col:
        try:
            return f"{float(val):.1f}%"
        except (ValueError, TypeError):
            return str(val)
    if isinstance(val, (float, Decimal)):
        return f"{float(val):.2f}"
    return str(val)


def has_data(val):
    """Safely check if val (list, dict, or DataFrame) contains any records."""
    if val is None:
        return False
    if hasattr(val, "empty"):
        return not val.empty
    try:
        return len(val) > 0
    except TypeError:
        return bool(val)


def ensure_records(data):
    """Ensure data is a list of dicts, converting DataFrame or None safely."""
    if data is None:
        return []
    if hasattr(data, "to_dict"):
        return data.to_dict(orient="records")
    if isinstance(data, list):
        return data
    return list(data)


def render_html_table(rows, columns=None):
    """Render a clean, responsive HTML table without requiring pyarrow/pandas."""
    records = ensure_records(rows)
    if not records:
        st.info("No records found.")
        return
    if not columns:
        columns = list(records[0].keys())

    html = ['<div style="overflow-x:auto; margin-bottom: 1.2rem;"><table style="width:100%; border-collapse: collapse; font-size: 0.88rem; text-align: left; font-family: sans-serif;">']
    html.append('<thead><tr style="background-color: #F1F5F9; border-bottom: 2px solid #CBD5E1;">')
    for col in columns:
        html.append(f'<th style="padding: 10px 12px; font-weight: 600; color: #1E293B;">{col}</th>')
    html.append('</tr></thead><tbody>')

    for i, row in enumerate(records):
        bg = "#FFFFFF" if i % 2 == 0 else "#F8FAFC"
        html.append(f'<tr style="background-color: {bg}; border-bottom: 1px solid #E2E8F0;">')
        for col in columns:
            raw_val = row.get(col, "")
            formatted_val = format_table_value(col, raw_val)
            html.append(f'<td style="padding: 8px 12px; color: #334155;">{formatted_val}</td>')
        html.append('</tr>')

    html.append('</tbody></table></div>')
    st.markdown("".join(html), unsafe_allow_html=True)


def render_plotly_chart(fig):
    """Render Plotly figure cleanly avoiding Streamlit deprecation warnings."""
    try:
        st.plotly_chart(fig, width="stretch")
    except TypeError:
        st.plotly_chart(fig, use_container_width=True)


# ------------------------------------------------------------------------------
# SIDEBAR NAVIGATION (Replaces top tabs; connection status removed)
# ------------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Enterprise HR Portal")
    st.caption("Operational and analytics tables on TiDB")
    st.markdown("---")

    st.markdown("#### Navigation")
    selected_page = st.radio(
        "Navigation Menu",
        ["HR Data Entry", "Employee Directory", "Executive Dashboard"],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown("#### Data Maintenance")
    if st.button("Run Warehouse Incremental Sync", use_container_width=True):
        try:
            sync_counts = WarehouseSyncManager(db_conn).sync_incremental()
            st.toast("Warehouse synchronized successfully!")
            st.caption(f"New warehouse records: {sync_counts}")
        except Exception as e:
            st.error(f"Sync failed: {e}")

# ------------------------------------------------------------------------------
# MAIN APPLICATION INTERFACE
# ------------------------------------------------------------------------------
st.markdown('<div class="main-header">Enterprise HR Analytics & Data Warehouse System</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Object-Oriented Middleware | SCD Type 2 Warehouse | Executive Dashboards</div>', unsafe_allow_html=True)

# Cache reference data for dropdowns
departments = emp_mgr.get_all_departments()
job_roles = emp_mgr.get_all_job_roles()
dept_options = {d.department_name: d.department_id for d in departments}
role_options = {f"{r.role_name} (Level {r.job_level})": r.job_role_id for r in job_roles}

# ==============================================================================
# MODULE 1: HR DATA ENTRY (OLTP INTERACTION)
# ==============================================================================
if selected_page == "HR Data Entry":
    st.markdown("### Workforce Operations and Data Entry")
    st.info("Decoupled Architecture: Forms securely write to the OLTP database via the Python DAL. Career changes automatically trigger SCD Type 2 versioning in the OLAP Data Warehouse.")

    entry_sub1, entry_sub2, entry_sub3, entry_sub4 = st.tabs([
        "Onboard Employee",
        "Update Department & Role (SCD Type 2)",
        "Create Project & Assign Staff",
        "Submit Performance Review"
    ])

    # 1. Onboard Employee
    with entry_sub1:
        st.markdown("#### Onboard New Employee")
        with st.form("form_onboard", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            with col_a:
                fn = st.text_input("First Name", placeholder="Jane")
                ln = st.text_input("Last Name", placeholder="Doe")
                email = st.text_input("Corporate Email", placeholder="jane.doe@company.com")
                age = st.number_input("Age", min_value=18, max_value=75, value=29)
                gender = st.selectbox("Gender", ["Female", "Male", "Non-Binary", "Other"])
                marital_status = st.selectbox("Marital Status", ["Single", "Married", "Divorced"])

            with col_b:
                dist = st.number_input("Distance From Home (km)", min_value=1, max_value=150, value=12)
                edu = st.selectbox("Education Field", ["Life Sciences", "Medical", "Marketing", "Technical Degree", "Human Resources", "Other"])
                sel_dept = st.selectbox("Department", list(dept_options.keys()))
                sel_role = st.selectbox("Job Role", list(role_options.keys()))
                salary = st.number_input("Monthly Income ($)", min_value=1000.0, max_value=100000.0, value=5200.0, step=250.0)
                hire_date = st.date_input("Hire Date", value=date.today())

            submit_onboard = st.form_submit_button("Onboard Employee", use_container_width=True)
            if submit_onboard:
                if not fn or not ln or not email:
                    st.error("Please fill out all required name and email fields.")
                else:
                    try:
                        new_emp = Employee(
                            employee_id=None,
                            first_name=fn.strip(),
                            last_name=ln.strip(),
                            email=email.strip().lower(),
                            age=int(age),
                            gender=gender,
                            marital_status=marital_status,
                            distance_from_home=int(dist),
                            education_field=edu,
                            monthly_income=float(salary),
                            hire_date=hire_date,
                            is_active=True,
                            department_id=dept_options[sel_dept],
                            job_role_id=role_options[sel_role]
                        )
                        assigned_id = emp_mgr.onboard_employee(new_emp)
                        st.success(f"Employee {fn} {ln} onboarded with EmployeeID: {assigned_id}. Synchronized into OLAP Dim_Employee as Active Record.")
                    except Exception as e:
                        st.error(f"Onboarding failed: {e}")

    # 2. Update Employee Department / Role (SCD Type 2 Trigger)
    with entry_sub2:
        st.markdown("#### Update Employee Department, Role or Salary (SCD Type 2)")
        st.caption("Updating an employee department or salary triggers an SCD Type 2 update in the Data Warehouse (retires old row with EffectiveEndDate = TODAY, opens new row with EffectiveStartDate = TODAY).")

        emp_search_id = st.number_input("Enter EmployeeID", min_value=1, value=1, step=1)
        target_emp = emp_mgr.get_employee_by_id(emp_search_id)

        if target_emp:
            st.markdown(f"**Selected Employee:** `{target_emp.full_name}` | **Email:** `{target_emp.email}`")
            col_c1, col_c2, col_c3 = st.columns(3)
            with col_c1:
                st.metric("Current Department", target_emp.department_name or "N/A")
            with col_c2:
                st.metric("Current Role", f"{target_emp.role_name} (Level {target_emp.job_level})")
            with col_c3:
                st.metric("Current Monthly Salary", f"${target_emp.monthly_income:,.2f}")

            with st.form("form_update_career"):
                col_u1, col_u2, col_u3 = st.columns(3)
                with col_u1:
                    new_dept_name = st.selectbox("New Department", list(dept_options.keys()))
                with col_u2:
                    new_role_name = st.selectbox("New Job Role", list(role_options.keys()))
                with col_u3:
                    new_salary = st.number_input("New Monthly Income ($)", min_value=1000.0, max_value=150000.0, value=float(target_emp.monthly_income * 1.15), step=500.0)

                submit_update = st.form_submit_button("Apply Update (Triggers SCD Type 2)", use_container_width=True)
                if submit_update:
                    try:
                        emp_mgr.update_employee_career(
                            employee_id=emp_search_id,
                            new_department_id=dept_options[new_dept_name],
                            new_job_role_id=role_options[new_role_name],
                            new_salary=float(new_salary)
                        )
                        st.success(f"Updated career details for {target_emp.full_name}. SCD Type 2 version created in Dim_Employee.")
                    except Exception as e:
                        st.error(f"Update failed: {e}")

            # Instant SCD Type 2 Audit Trail
            st.markdown("##### SCD Type 2 Historical Audit Trail for this Employee")
            journey = ensure_records(analytics_mgr.get_employee_career_journey(emp_search_id))
            if has_data(journey):
                render_html_table(journey, ["EmployeeSK", "FullName", "DepartmentName", "RoleName", "MonthlyIncome", "EffectiveStartDate", "EffectiveEndDate", "RoleStatus", "DaysInRole"])
        else:
            st.warning(f"Employee with ID {emp_search_id} not found.")

    # 3. Create Project & Assign Staff
    with entry_sub3:
        st.markdown("#### Projects and Resource Allocation")
        col_proj1, col_proj2 = st.columns(2)

        with col_proj1:
            st.markdown("##### Create New Project")
            with st.form("form_create_project", clear_on_submit=True):
                p_name = st.text_input("Project Name", placeholder="Cloud Data Migration")
                p_budget = st.number_input("Project Budget ($)", min_value=10000.0, max_value=5000000.0, value=250000.0, step=10000.0)
                p_status = st.selectbox("Status", ["Active", "Planning", "Completed"])
                submit_proj = st.form_submit_button("Register Project", use_container_width=True)

                if submit_proj:
                    if not p_name:
                        st.error("Project name is required.")
                    else:
                        try:
                            pid = proj_mgr.create_project(p_name, float(p_budget), p_status)
                            st.success(f"Project '{p_name}' created with ID: {pid}")
                        except Exception as e:
                            st.error(f"Project creation failed: {e}")

        with col_proj2:
            st.markdown("##### Assign Employee to Project")
            all_projs = proj_mgr.get_all_projects()
            proj_dict = {f"[{p.project_id}] {p.project_name} (${p.budget:,.0f})": p.project_id for p in all_projs[:50]}

            with st.form("form_assign_staff"):
                alloc_emp_id = st.number_input("EmployeeID", min_value=1, value=1, step=1)
                sel_proj = st.selectbox("Select Project", list(proj_dict.keys()) if proj_dict else ["No Projects"])
                alloc_pct = st.slider("Allocation Percentage (%)", min_value=10, max_value=100, value=50, step=5)
                submit_alloc = st.form_submit_button("Assign Resource", use_container_width=True)

                if submit_alloc and proj_dict:
                    try:
                        proj_mgr.assign_employee_to_project(
                            employee_id=int(alloc_emp_id),
                            project_id=proj_dict[sel_proj],
                            allocation_percentage=int(alloc_pct)
                        )
                        st.success(f"Assigned Employee #{alloc_emp_id} to project at {alloc_pct}% allocation.")
                    except Exception as e:
                        st.error(f"Allocation failed: {e}")

    # 4. Submit Performance Review
    with entry_sub4:
        st.markdown("#### Submit Performance Review")
        st.caption("Writes to OLTP performancereviews and synchronizes to OLAP Fact_PerformanceReviews.")

        with st.form("form_submit_review", clear_on_submit=True):
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                rev_emp_id = st.number_input("EmployeeID", min_value=1, value=1, step=1)
                rev_date = st.date_input("Review Date", value=date.today())
                perf_rating = st.slider("Performance Rating (1-5)", min_value=1, max_value=5, value=4)
                job_sat = st.slider("Job Satisfaction (1-4)", min_value=1, max_value=4, value=3)

            with col_r2:
                env_sat = st.slider("Environment Satisfaction (1-4)", min_value=1, max_value=4, value=3)
                wlb = st.slider("Work-Life Balance (1-4)", min_value=1, max_value=4, value=3)
                rel_sat = st.slider("Relationship Satisfaction (1-4)", min_value=1, max_value=4, value=4)

            submit_rev = st.form_submit_button("Submit Review", use_container_width=True)
            if submit_rev:
                try:
                    rev_id = analytics_mgr.submit_performance_review(
                        employee_id=int(rev_emp_id),
                        review_date=rev_date,
                        performance_rating=int(perf_rating),
                        job_satisfaction=int(job_sat),
                        environment_satisfaction=int(env_sat),
                        work_life_balance=int(wlb),
                        relationship_satisfaction=int(rel_sat)
                    )
                    st.success(f"Performance Review #{rev_id} recorded in OLTP and synchronized into Data Warehouse Fact table.")
                except Exception as e:
                    st.error(f"Review submission failed: {e}")

# ==============================================================================
# MODULE 2: ACTIVE EMPLOYEE DIRECTORY (OLTP OPERATIONAL READ)
# ==============================================================================
elif selected_page == "Employee Directory":
    st.markdown("### Active Employee Directory (OLTP Live Stream)")
    st.caption("Live data stream fetching active employees from the operational employees table via Python DAL.")

    col_s1, col_s2, col_s3 = st.columns([2, 1, 1])
    with col_s1:
        search_query = st.text_input("Search by Name or Email", placeholder="Filter by name or email...")
    with col_s2:
        dept_list = ["All Departments"] + [d.department_name for d in departments]
        selected_dept = st.selectbox("Department Filter", dept_list)
        dept_filter_id = dept_options.get(selected_dept) if selected_dept != "All Departments" else None
    with col_s3:
        page_size = st.selectbox("Page Size", [25, 50, 100], index=1)

    total_matching = emp_mgr.count_active_employees(search=search_query, department_id=dept_filter_id)
    total_pages = max(1, (total_matching + page_size - 1) // page_size)

    col_pg1, col_pg2 = st.columns([1, 4])
    with col_pg1:
        page_num = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1)
    with col_pg2:
        st.markdown(f"<br><small style='color: #64748B;'>Showing page {page_num} of {total_pages:,} ({total_matching:,} active employees matching)</small>", unsafe_allow_html=True)

    offset = (page_num - 1) * page_size
    active_employees = emp_mgr.get_active_employees(limit=page_size, offset=offset, search=search_query, department_id=dept_filter_id)

    if active_employees:
        table_rows = [
            {
                "ID": e.employee_id,
                "Name": e.full_name,
                "Email": e.email,
                "Department": e.department_name,
                "Role": e.role_name,
                "Level": e.job_level,
                "Monthly Salary": e.monthly_income,
                "Hire Date": str(e.hire_date)
            }
            for e in active_employees
        ]
        render_html_table(table_rows, ["ID", "Name", "Email", "Department", "Role", "Level", "Monthly Salary", "Hire Date"])

        st.markdown("---")
        st.markdown("#### Inspect Employee Profile & SCD Type 2 Timeline")
        inspect_id = st.number_input("Select EmployeeID to Inspect", min_value=1, value=active_employees[0].employee_id, step=1)
        inspected_emp = emp_mgr.get_employee_by_id(inspect_id)

        if inspected_emp:
            col_prof1, col_prof2 = st.columns([1, 2])
            with col_prof1:
                st.markdown(f"##### Profile: {inspected_emp.full_name}")
                st.write(f"**Email:** `{inspected_emp.email}`")
                st.write(f"**Department:** {inspected_emp.department_name}")
                st.write(f"**Role:** {inspected_emp.role_name} (Level {inspected_emp.job_level})")
                st.write(f"**Monthly Salary:** ${inspected_emp.monthly_income:,.2f}")
                st.write(f"**Education:** {inspected_emp.education_field}")
                st.write(f"**Distance to Office:** {inspected_emp.distance_from_home} km")
                st.write(f"**Hire Date:** {inspected_emp.hire_date}")

                allocations = proj_mgr.get_employee_allocations(inspect_id)
                st.markdown("##### Project Allocations")
                if allocations:
                    for a in allocations:
                        st.write(f"- **{a.project_name}**: `{a.allocation_percentage}%`")
                else:
                    st.caption("No project assignments recorded.")

            with col_prof2:
                st.markdown("##### SCD Type 2 Historical Career Journey (Data Warehouse)")
                career_history = ensure_records(analytics_mgr.get_employee_career_journey(inspect_id))
                if has_data(career_history):
                    render_html_table(career_history, ["EmployeeSK", "DepartmentName", "RoleName", "MonthlyIncome", "EffectiveStartDate", "EffectiveEndDate", "RoleStatus", "DaysInRole"])
                else:
                    st.caption("No historical records found.")
    else:
        st.warning("No employees match the selected criteria.")

# ==============================================================================
# MODULE 3: EXECUTIVE DASHBOARD (OLAP INTERACTION)
# ==============================================================================
elif selected_page == "Executive Dashboard":
    st.markdown("### Executive Analytics Dashboard")
    st.caption("Fetches analytical metrics from the Star Schema using database-level aggregations and Window Functions.")

    kpis = analytics_mgr.get_executive_kpis()
    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
    with col_m1:
        st.metric("Active Headcount", f"{kpis.get('active_headcount', 0):,}")
    with col_m2:
        st.metric("SCD Type 2 Historical Snapshots", f"{kpis.get('historical_versions', 0):,}")
    with col_m3:
        st.metric("Avg Performance Rating", f"{kpis.get('avg_performance', 0)} / 5.0")
    with col_m4:
        st.metric("Avg Work-Life Balance", f"{kpis.get('avg_work_life_balance', 0)} / 4.0")
    with col_m5:
        st.metric("Total Project Budget", f"${kpis.get('total_project_budget', 0):,.0f}")

    st.markdown("---")

    # --------------------------------------------------------------------------
    # 1. Year-over-Year Performance Trends
    # --------------------------------------------------------------------------
    st.markdown("#### 1. Year-over-Year (YoY) Performance Trends")
    yoy_data = ensure_records(analytics_mgr.get_yoy_performance_trends())
    if has_data(yoy_data):
        dept_names = sorted(list(set(r["DepartmentName"] for r in yoy_data)))
        fig_yoy = go.Figure()
        for dept in dept_names:
            dept_rows = [r for r in yoy_data if r["DepartmentName"] == dept]
            dept_rows.sort(key=lambda x: x["Year"])
            fig_yoy.add_trace(go.Scatter(
                x=[r["Year"] for r in dept_rows],
                y=[r["AvgPerformanceRating"] for r in dept_rows],
                mode="lines+markers",
                name=dept
            ))
        fig_yoy.update_layout(
            title="Year-over-Year Average Performance Rating by Department",
            xaxis_title="Calendar Year",
            yaxis_title="Average Performance Rating",
            hovermode="x unified",
            margin=dict(l=40, r=40, t=50, b=40)
        )
        render_plotly_chart(fig_yoy)

    st.markdown("---")

    # --------------------------------------------------------------------------
    # 2. Top-Performing Employees by Department (Strictly 3 per Department)
    # --------------------------------------------------------------------------
    st.markdown("#### 2. Top Performing Employees by Department")
    st.caption("Displaying strictly the top 3 performing employees per department ranked by SQL Window Functions.")
    top_performers = ensure_records(analytics_mgr.get_top_performers_by_department(limit_per_dept=3))
    if has_data(top_performers):
        render_html_table(
            top_performers,
            ["DepartmentRank", "FullName", "DepartmentName", "RoleName", "JobLevel", "MonthlyIncome", "AvgPerformanceRating", "AvgJobSatisfaction"]
        )
    else:
        st.info("No top performers data available.")

    st.markdown("---")

    # --------------------------------------------------------------------------
    # 3. Employee Attrition Risk Analysis (NEW FEATURE)
    # --------------------------------------------------------------------------
    st.markdown("#### 3. Employee Attrition Risk Analysis")
    st.caption("Identifies burnout indicators and flight risks based on Job Satisfaction, Work-Life Balance, and Environment Satisfaction.")

    risk_kpis = analytics_mgr.get_attrition_kpis()
    col_r1, col_r2, col_r3, col_r4, col_r5 = st.columns(5)
    with col_r1:
        st.metric("Total Evaluated Employees", f"{risk_kpis.get('total_evaluations', 0):,}")
    with col_r2:
        st.metric("High Burnout Risk", f"{risk_kpis.get('high_risk_count', 0):,}")
    with col_r3:
        st.metric("Medium Risk", f"{risk_kpis.get('medium_risk_count', 0):,}")
    with col_r4:
        st.metric("Low Risk (Stable)", f"{risk_kpis.get('low_risk_count', 0):,}")
    with col_r5:
        st.metric("High Risk Percentage", f"{risk_kpis.get('high_risk_percentage', 0)}%")

    dept_risk = ensure_records(analytics_mgr.get_department_attrition_risk())
    if has_data(dept_risk):
        col_risk_chart, col_risk_summary = st.columns([3, 2])
        with col_risk_chart:
            fig_risk = go.Figure()
            fig_risk.add_trace(go.Bar(
                name="High Risk (Burnout)",
                x=[r["DepartmentName"] for r in dept_risk],
                y=[float(r["HighRiskCount"]) for r in dept_risk],
                marker_color="#DC2626"
            ))
            fig_risk.add_trace(go.Bar(
                name="Medium Risk",
                x=[r["DepartmentName"] for r in dept_risk],
                y=[float(r["MediumRiskCount"]) for r in dept_risk],
                marker_color="#F59E0B"
            ))
            fig_risk.add_trace(go.Bar(
                name="Low Risk",
                x=[r["DepartmentName"] for r in dept_risk],
                y=[float(r["LowRiskCount"]) for r in dept_risk],
                marker_color="#10B981"
            ))
            fig_risk.update_layout(
                barmode="stack",
                title="Attrition & Burnout Risk Distribution by Department",
                xaxis_title="Department",
                yaxis_title="Employee Count",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            render_plotly_chart(fig_risk)

        with col_risk_summary:
            st.markdown("##### Department Risk Summary")
            render_html_table(
                dept_risk,
                ["DepartmentName", "TotalEvaluations", "HighRiskPercentage", "AvgJobSatisfaction", "AvgWorkLifeBalance"]
            )

    st.markdown("##### Employees at Critical Flight Risk (Lowest Satisfaction & Work-Life Balance)")
    high_risk_emps = ensure_records(analytics_mgr.get_high_risk_employees(limit=10))
    if has_data(high_risk_emps):
        render_html_table(
            high_risk_emps,
            ["EmployeeID", "FullName", "DepartmentName", "RoleName", "MonthlyIncome", "DistanceFromHome", "PerformanceRating", "JobSatisfaction", "WorkLifeBalance", "EnvironmentSatisfaction"]
        )

    st.markdown("---")

    # --------------------------------------------------------------------------
    # 4. Project Bottleneck & Resource Allocation Analysis (NEW FEATURE)
    # --------------------------------------------------------------------------
    st.markdown("#### 4. Project Bottleneck & Resource Allocation Analysis")
    st.caption("Analyzes resource contention, overallocated staff (>100% capacity), and project delivery bottlenecks.")

    # Talent Bottlenecks: Overallocated Staff
    st.markdown("##### Resource Overallocation Bottlenecks (Talent Strained > 100%)")
    overallocated_staff = ensure_records(proj_mgr.get_overallocated_employees(limit=10))
    if has_data(overallocated_staff):
        render_html_table(
            overallocated_staff,
            ["EmployeeID", "FullName", "DepartmentName", "ProjectCount", "TotalAllocationPercentage"]
        )
    else:
        st.info("No overallocated resources found.")

    # Project Portfolio Bottlenecks
    st.markdown("##### Project Portfolio Capacity & Workload Pressure")
    project_bottlenecks = ensure_records(analytics_mgr.get_project_bottlenecks(status="Active"))
    if has_data(project_bottlenecks):
        top_projects = project_bottlenecks[:12]
        fig_proj_bot = go.Figure()
        fig_proj_bot.add_trace(go.Bar(
            name="Budget ($)",
            x=[p["ProjectName"] for p in top_projects],
            y=[float(p["Budget"]) for p in top_projects],
            yaxis="y",
            marker_color="#3B82F6"
        ))
        fig_proj_bot.add_trace(go.Scatter(
            name="Avg Staff Allocation (%)",
            x=[p["ProjectName"] for p in top_projects],
            y=[float(p["AvgAllocationPercentage"] or 0) for p in top_projects],
            yaxis="y2",
            mode="lines+markers",
            line=dict(color="#EF4444", width=3)
        ))
        fig_proj_bot.update_layout(
            title="Active Projects: Budget vs. Team Allocation Load",
            xaxis=dict(title="Project Name", tickangle=35),
            yaxis=dict(title="Budget ($)"),
            yaxis2=dict(
                title="Avg Allocation (%)",
                overlaying="y",
                side="right",
                range=[0, 100]
            ),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=50, b=100)
        )
        render_plotly_chart(fig_proj_bot)

        st.markdown("##### Active Projects Bottleneck Status Table")
        render_html_table(
            top_projects,
            ["ProjectName", "Budget", "LoggedReviews", "AvgAllocationPercentage", "AvgTeamWorkLifeBalance", "BottleneckRisk"]
        )
