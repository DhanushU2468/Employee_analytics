from backend.dal.base_manager import BaseManager


class WarehouseSyncManager(BaseManager):
    """Synchronize new source records into the analytical tables without stored procedures."""

    def sync_incremental(self):
        with self.db.get_cursor(db_key="olap", dictionary=False) as cursor:
            cursor.execute(
                """
                INSERT IGNORE INTO Dim_Department (DepartmentID_BK, DepartmentName)
                SELECT DepartmentID, DepartmentName FROM departments;
                """
            )
            department_count = cursor.rowcount

            cursor.execute(
                """
                INSERT IGNORE INTO Dim_Project (ProjectID_BK, ProjectName, Budget, Status)
                SELECT ProjectID, ProjectName, Budget, Status FROM projects;
                """
            )
            project_count = cursor.rowcount

            cursor.execute(
                """
                INSERT INTO Dim_Employee (
                    EmployeeID_BK, FirstName, LastName, Email, Age, Gender,
                    EducationField, DistanceFromHome, MonthlyIncome,
                    DepartmentName, RoleName, JobLevel,
                    EffectiveStartDate, EffectiveEndDate, IsCurrent
                )
                SELECT
                    e.EmployeeID, e.FirstName, e.LastName, e.Email, e.Age, e.Gender,
                    e.EducationField, e.DistanceFromHome, e.MonthlyIncome,
                    d.DepartmentName, r.RoleName, r.JobLevel,
                    e.HireDate, '9999-12-31', TRUE
                FROM employees e
                JOIN departments d ON e.DepartmentID = d.DepartmentID
                JOIN jobroles r ON e.JobRoleID = r.JobRoleID
                WHERE NOT EXISTS (
                    SELECT 1 FROM Dim_Employee de
                    WHERE de.EmployeeID_BK = e.EmployeeID
                );
                """
            )
            employee_count = cursor.rowcount

            cursor.execute(
                """
                INSERT IGNORE INTO Dim_Date (
                    DateKey, FullDate, Year, Quarter, Month, MonthName, Day,
                    DayOfWeek, IsWeekend
                )
                SELECT DISTINCT
                    YEAR(ReviewDate) * 10000 + MONTH(ReviewDate) * 100 + DAY(ReviewDate),
                    ReviewDate, YEAR(ReviewDate), QUARTER(ReviewDate),
                    MONTH(ReviewDate), MONTHNAME(ReviewDate), DAY(ReviewDate),
                    DAYNAME(ReviewDate),
                    IF(DAYOFWEEK(ReviewDate) IN (1, 7), TRUE, FALSE)
                FROM performancereviews;
                """
            )
            date_count = cursor.rowcount

            cursor.execute(
                """
                INSERT INTO Fact_PerformanceReviews (
                    ReviewID_BK, EmployeeSK, DepartmentSK, ProjectSK, DateKey,
                    PerformanceRating, JobSatisfaction, EnvironmentSatisfaction,
                    WorkLifeBalance, RelationshipSatisfaction,
                    MonthlyIncomeSnapshot, AllocationPercentageSnapshot
                )
                SELECT
                    pr.ReviewID, de.EmployeeSK, dd.DepartmentSK, dp.ProjectSK,
                    YEAR(pr.ReviewDate) * 10000 + MONTH(pr.ReviewDate) * 100
                        + DAY(pr.ReviewDate),
                    pr.PerformanceRating, pr.JobSatisfaction,
                    pr.EnvironmentSatisfaction, pr.WorkLifeBalance,
                    pr.RelationshipSatisfaction, de.MonthlyIncome,
                    COALESCE(ep.AllocationPercentage, 0)
                FROM performancereviews pr
                JOIN Dim_Employee de
                    ON pr.EmployeeID = de.EmployeeID_BK AND de.IsCurrent = TRUE
                JOIN employees e ON pr.EmployeeID = e.EmployeeID
                JOIN Dim_Department dd ON e.DepartmentID = dd.DepartmentID_BK
                LEFT JOIN (
                    SELECT EmployeeID, MIN(ProjectID) AS ProjectID,
                           MAX(AllocationPercentage) AS AllocationPercentage
                    FROM employeeprojects
                    GROUP BY EmployeeID
                ) ep ON pr.EmployeeID = ep.EmployeeID
                LEFT JOIN Dim_Project dp ON ep.ProjectID = dp.ProjectID_BK
                WHERE NOT EXISTS (
                    SELECT 1 FROM Fact_PerformanceReviews f
                    WHERE f.ReviewID_BK = pr.ReviewID
                );
                """
            )
            fact_count = cursor.rowcount

        return {
            "departments": department_count,
            "projects": project_count,
            "employees": employee_count,
            "dates": date_count,
            "reviews": fact_count,
        }
