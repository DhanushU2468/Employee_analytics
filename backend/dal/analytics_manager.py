from datetime import date
from typing import List, Dict, Any, Optional

try:
    import pandas as pd
except Exception:
    pd = None

from backend.dal.base_manager import BaseManager
from backend.models.entities import PerformanceReview


def _wrap_dataframe(rows):
    """Return a pandas DataFrame if pandas is functional, otherwise return list of dicts."""
    if pd is not None:
        try:
            return pd.DataFrame(rows)
        except Exception:
            pass
    return rows


class AnalyticsManager(BaseManager):
    """
    Connects to the analytical tables in the configured database to power
    interactive executive dashboards, window functions, and YoY reporting.
    """

    def get_executive_kpis(self) -> Dict[str, Any]:
        """Aggregate high-level executive KPIs from the OLAP Star Schema."""
        query = """
            SELECT 
                (SELECT COUNT(*) FROM Dim_Employee WHERE IsCurrent = TRUE) AS active_headcount,
                (SELECT COUNT(*) FROM Dim_Employee WHERE IsCurrent = FALSE) AS historical_versions,
                (SELECT ROUND(AVG(PerformanceRating), 2) FROM Fact_PerformanceReviews) AS avg_performance,
                (SELECT ROUND(AVG(WorkLifeBalance), 2) FROM Fact_PerformanceReviews) AS avg_work_life_balance,
                (SELECT ROUND(AVG(JobSatisfaction), 2) FROM Fact_PerformanceReviews) AS avg_job_satisfaction,
                (SELECT COUNT(*) FROM Dim_Project WHERE Status = 'Active') AS active_projects,
                (SELECT ROUND(SUM(Budget), 2) FROM Dim_Project) AS total_project_budget,
                (SELECT ROUND(AVG(MonthlyIncome), 2) FROM Dim_Employee WHERE IsCurrent = TRUE) AS avg_monthly_salary;
        """
        row = self.execute_query(query, db_key="olap", fetch="one")
        return row or {}

    def get_top_performers_by_department(self, limit_per_dept: int = 5) -> pd.DataFrame:
        """
        Query top-performing employees ranked via DENSE_RANK() OVER (PARTITION BY DepartmentName...).
        """
        query = """
            SELECT 
                DepartmentName,
                DepartmentRank,
                FullName,
                RoleName,
                JobLevel,
                MonthlyIncome,
                AvgPerformanceRating,
                AvgJobSatisfaction
            FROM vw_department_top_performers
            WHERE DepartmentRank <= %s
            ORDER BY DepartmentName, DepartmentRank;
        """
        rows = self.execute_query(query, (limit_per_dept,), db_key="olap", fetch="all")
        return _wrap_dataframe(rows)

    def get_yoy_performance_trends(self) -> pd.DataFrame:
        """Fetch YoY performance, satisfaction, and rating delta metrics."""
        query = """
            SELECT 
                Year,
                DepartmentName,
                TotalReviews,
                AvgPerformanceRating,
                PrevYearAvgRating,
                YoY_Rating_Delta,
                AvgJobSatisfaction,
                AvgWorkLifeBalance,
                AvgMonthlyIncome
            FROM vw_yoy_performance_trends
            ORDER BY Year ASC, DepartmentName ASC;
        """
        rows = self.execute_query(query, db_key="olap", fetch="all")
        return _wrap_dataframe(rows)

    def get_salary_vs_performance_correlation(self) -> pd.DataFrame:
        """Fetch compensation vs performance distribution by department and role."""
        query = """
            SELECT 
                DepartmentName,
                RoleName,
                JobLevel,
                ActiveHeadcount,
                AvgMonthlyIncome,
                MinMonthlyIncome,
                MaxMonthlyIncome,
                AvgPerformanceRating,
                AvgJobSatisfaction,
                AvgWorkLifeBalance
            FROM vw_salary_vs_performance_correlation
            ORDER BY DepartmentName, JobLevel;
        """
        rows = self.execute_query(query, db_key="olap", fetch="all")
        return _wrap_dataframe(rows)

    def get_project_bottlenecks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch project resource allocation, performance density, and bottleneck risk status."""
        if status:
            query = """
                SELECT 
                    ProjectSK,
                    ProjectID_BK,
                    ProjectName,
                    Budget,
                    Status,
                    LoggedReviews,
                    AvgAllocationPercentage,
                    AvgProjectPerformance,
                    AvgTeamWorkLifeBalance,
                    BottleneckRisk
                FROM vw_project_resource_bottlenecks
                WHERE Status = %s
                ORDER BY Budget DESC;
            """
            rows = self.execute_query(query, (status,), db_key="olap", fetch="all")
        else:
            query = """
                SELECT 
                    ProjectSK,
                    ProjectID_BK,
                    ProjectName,
                    Budget,
                    Status,
                    LoggedReviews,
                    AvgAllocationPercentage,
                    AvgProjectPerformance,
                    AvgTeamWorkLifeBalance,
                    BottleneckRisk
                FROM vw_project_resource_bottlenecks
                ORDER BY Budget DESC;
            """
            rows = self.execute_query(query, db_key="olap", fetch="all")
        return _wrap_dataframe(rows)

    def get_attrition_kpis(self) -> Dict[str, Any]:
        """Fetch overall employee burnout and attrition risk statistics from Fact_PerformanceReviews."""
        query = """
            SELECT 
                COUNT(*) AS total_evaluations,
                SUM(CASE WHEN JobSatisfaction <= 2 AND WorkLifeBalance <= 2 THEN 1 ELSE 0 END) AS high_risk_count,
                SUM(CASE WHEN (JobSatisfaction <= 2 OR WorkLifeBalance <= 2) AND NOT (JobSatisfaction <= 2 AND WorkLifeBalance <= 2) THEN 1 ELSE 0 END) AS medium_risk_count,
                SUM(CASE WHEN JobSatisfaction > 2 AND WorkLifeBalance > 2 THEN 1 ELSE 0 END) AS low_risk_count,
                ROUND(SUM(CASE WHEN JobSatisfaction <= 2 AND WorkLifeBalance <= 2 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS high_risk_percentage,
                ROUND(AVG(JobSatisfaction), 2) AS avg_job_satisfaction,
                ROUND(AVG(WorkLifeBalance), 2) AS avg_work_life_balance
            FROM Fact_PerformanceReviews;
        """
        row = self.execute_query(query, db_key="olap", fetch="one")
        return row or {}

    def get_department_attrition_risk(self) -> List[Dict[str, Any]]:
        """Fetch department-level breakdown of attrition and burnout risk."""
        query = """
            SELECT 
                DepartmentName,
                TotalEvaluations,
                HighRiskCount,
                MediumRiskCount,
                LowRiskCount,
                AvgJobSatisfaction,
                AvgWorkLifeBalance,
                AvgEnvironmentSatisfaction,
                HighRiskPercentage
            FROM vw_department_attrition_risk
            ORDER BY HighRiskPercentage DESC;
        """
        rows = self.execute_query(query, db_key="olap", fetch="all")
        return _wrap_dataframe(rows)

    def get_high_risk_employees(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Fetch employees exhibiting severe burnout and attrition risk factors."""
        query = """
            SELECT 
                e.EmployeeID AS EmployeeID,
                CONCAT(e.FirstName, ' ', e.LastName) AS FullName,
                e.DepartmentName,
                e.RoleName,
                e.MonthlyIncome,
                e.DistanceFromHome,
                f.PerformanceRating,
                f.JobSatisfaction,
                f.WorkLifeBalance,
                f.EnvironmentSatisfaction
            FROM Fact_PerformanceReviews f
            JOIN Dim_Employee e ON f.EmployeeKey = e.EmployeeKey
            WHERE e.IsCurrent = TRUE
              AND f.JobSatisfaction = 1
              AND f.WorkLifeBalance = 1
            ORDER BY e.MonthlyIncome ASC
            LIMIT %s;
        """
        rows = self.execute_query(query, (limit,), db_key="olap", fetch="all")
        return _wrap_dataframe(rows)

    def get_employee_career_journey(self, employee_id: int) -> pd.DataFrame:
        """
        Retrieve the full SCD Type 2 career journey (promotions, department changes, raises)
        for a specific employee.
        """
        query = """
            SELECT 
                EmployeeSK,
                EmployeeID_BK,
                FullName,
                Email,
                DepartmentName,
                RoleName,
                JobLevel,
                MonthlyIncome,
                EffectiveStartDate,
                EffectiveEndDate,
                IsCurrent,
                RoleStatus,
                DaysInRole
            FROM vw_employee_career_journey
            WHERE EmployeeID_BK = %s
            ORDER BY EffectiveStartDate ASC;
        """
        rows = self.execute_query(query, (employee_id,), db_key="olap", fetch="all")
        return _wrap_dataframe(rows)

    def submit_performance_review(
        self,
        employee_id: int,
        review_date: date,
        performance_rating: int,
        job_satisfaction: int,
        environment_satisfaction: int,
        work_life_balance: int,
        relationship_satisfaction: int
    ) -> int:
        """
        Submit a performance review into OLTP and automatically append to OLAP Fact_PerformanceReviews.
        """
        # 1. Insert into OLTP
        query_oltp = """
            INSERT INTO performancereviews (
                EmployeeID, ReviewDate, PerformanceRating, JobSatisfaction,
                EnvironmentSatisfaction, WorkLifeBalance, RelationshipSatisfaction
            ) VALUES (%s, %s, %s, %s, %s, %s, %s);
        """
        params_oltp = (
            employee_id, review_date, performance_rating, job_satisfaction,
            environment_satisfaction, work_life_balance, relationship_satisfaction
        )
        review_id = self.execute_insert(query_oltp, params_oltp, db_key="oltp")

        # 2. Look up Dimension Keys in OLAP
        lookup_emp = self.execute_query(
            "SELECT EmployeeKey, MonthlyIncome FROM Dim_Employee WHERE EmployeeID = %s AND IsCurrent = TRUE;",
            (employee_id,),
            db_key="olap",
            fetch="one"
        )
        emp_sk = lookup_emp["EmployeeKey"] if lookup_emp else None
        salary = lookup_emp["MonthlyIncome"] if lookup_emp else 0.0

        lookup_dept = self.execute_query(
            """
            SELECT dd.DepartmentKey 
            FROM employees e
            JOIN Dim_Department dd ON e.DepartmentID = dd.DepartmentID
            WHERE e.EmployeeID = %s;
            """,
            (employee_id,),
            db_key="olap",
            fetch="one"
        )
        dept_sk = lookup_dept["DepartmentKey"] if lookup_dept else 1

        lookup_proj = self.execute_query(
            """
            SELECT dp.ProjectKey, ep.AllocationPercentage
            FROM employeeprojects ep
            JOIN Dim_Project dp ON ep.ProjectID = dp.ProjectID
            WHERE ep.EmployeeID = %s
            LIMIT 1;
            """,
            (employee_id,),
            db_key="olap",
            fetch="one"
        )
        proj_sk = lookup_proj["ProjectKey"] if lookup_proj else None
        allocation = lookup_proj["AllocationPercentage"] if lookup_proj else 0

        date_key = review_date.year * 10000 + review_date.month * 100 + review_date.day

        # 3. Insert into Fact_PerformanceReviews
        if emp_sk:
            query_fact = """
                INSERT INTO Fact_PerformanceReviews (
                    ReviewID, EmployeeKey, DepartmentKey, ProjectKey, DateKey,
                    PerformanceRating, JobSatisfaction, EnvironmentSatisfaction,
                    WorkLifeBalance, RelationshipSatisfaction,
                    MonthlyIncomeSnapshot, AllocationPercentageSnapshot
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """
            params_fact = (
                review_id, emp_sk, dept_sk, proj_sk, date_key,
                performance_rating, job_satisfaction, environment_satisfaction,
                work_life_balance, relationship_satisfaction,
                salary, allocation
            )
            self.execute_query(query_fact, params_fact, db_key="olap", fetch="none")

        return review_id
