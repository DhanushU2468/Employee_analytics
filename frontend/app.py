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
