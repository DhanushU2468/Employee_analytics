from typing import List, Optional
from backend.dal.base_manager import BaseManager
from backend.models.entities import Project, EmployeeProject


class ProjectManager(BaseManager):
    """
    Handles CRUD operations on OLTP Projects and EmployeeProject allocations,
    and syncs project dimensions to the OLAP Data Warehouse.
    """

    def create_project(self, project_name: str, budget: float, status: str = "Active") -> int:
        """Create a new project in OLTP and reflect it into Dim_Project in OLAP."""
        # 1. Insert into OLTP
        query_oltp = """
            INSERT INTO projects (ProjectName, Budget, Status)
            VALUES (%s, %s, %s);
        """
        project_id = self.execute_insert(query_oltp, (project_name, budget, status), db_key="oltp")

        # 2. Reflect into OLAP
        query_olap = """
            INSERT INTO Dim_Project (ProjectID, ProjectName, Budget, Status)
            VALUES (%s, %s, %s, %s);
        """
        self.execute_query(query_olap, (project_id, project_name, budget, status), db_key="olap", fetch="none")

        return project_id

    def assign_employee_to_project(
        self,
        employee_id: int,
        project_id: int,
        allocation_percentage: int
    ) -> int:
        """Assign an employee to a project with allocation percentage."""
        query = """
            INSERT INTO employeeprojects (EmployeeID, ProjectID, AllocationPercentage)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE AllocationPercentage = VALUES(AllocationPercentage);
        """
        return self.execute_insert(query, (employee_id, project_id, allocation_percentage), db_key="oltp")

    def get_all_projects(self, status: Optional[str] = None) -> List[Project]:
        """Fetch all projects."""
        if status:
            query = "SELECT ProjectID, ProjectName, Budget, Status FROM projects WHERE Status = %s ORDER BY ProjectID DESC;"
            rows = self.execute_query(query, (status,), db_key="oltp", fetch="all")
        else:
            query = "SELECT ProjectID, ProjectName, Budget, Status FROM projects ORDER BY ProjectID DESC;"
            rows = self.execute_query(query, db_key="oltp", fetch="all")

        return [
            Project(
                project_id=r["ProjectID"],
                project_name=r["ProjectName"],
                budget=float(r["Budget"]) if r["Budget"] is not None else 0.0,
                status=r["Status"]
            )
            for r in rows
        ]

    def get_employee_allocations(self, employee_id: int) -> List[EmployeeProject]:
        """Fetch all project assignments for an employee."""
        query = """
            SELECT 
                ep.AllocationID, ep.EmployeeID, ep.ProjectID, ep.AllocationPercentage,
                p.ProjectName
            FROM employeeprojects ep
            JOIN projects p ON ep.ProjectID = p.ProjectID
            WHERE ep.EmployeeID = %s;
        """
        rows = self.execute_query(query, (employee_id,), db_key="oltp", fetch="all")
        return [
            EmployeeProject(
                allocation_id=r["AllocationID"],
                employee_id=r["EmployeeID"],
                project_id=r["ProjectID"],
                allocation_percentage=r["AllocationPercentage"],
                project_name=r["ProjectName"]
            )
            for r in rows
        ]

    def get_overallocated_employees(self, limit: int = 15) -> List[dict]:
        """Fetch employees whose cumulative project allocation percentage exceeds 100%."""
        query = """
            SELECT 
                ep.EmployeeID,
                CONCAT(e.FirstName, ' ', e.LastName) AS FullName,
                d.DepartmentName,
                COUNT(ep.ProjectID) AS ProjectCount,
                SUM(ep.AllocationPercentage) AS TotalAllocationPercentage
            FROM employeeprojects ep
            JOIN employees e ON ep.EmployeeID = e.EmployeeID
            LEFT JOIN departments d ON e.DepartmentID = d.DepartmentID
            GROUP BY ep.EmployeeID, e.FirstName, e.LastName, d.DepartmentName
            HAVING TotalAllocationPercentage > 100
            ORDER BY TotalAllocationPercentage DESC
            LIMIT %s;
        """
        rows = self.execute_query(query, (limit,), db_key="oltp", fetch="all")
        return rows or []


