from typing import List, Optional
from datetime import date
from backend.dal.base_manager import BaseManager
from backend.models.entities import Employee, Department, JobRole


class EmployeeManager(BaseManager):
    """
    Handles CRUD operations on OLTP Employees and enforces
    Slowly Changing Dimension (SCD) Type 2 updates in the OLAP Data Warehouse.
    """

    def get_next_employee_id(self) -> int:
        """Generate next available EmployeeID."""
        row = self.execute_query(
            "SELECT COALESCE(MAX(EmployeeID), 0) + 1 AS next_id FROM employees;",
            db_key="oltp",
            fetch="one"
        )
        return row["next_id"] if row else 1

    def onboard_employee(self, emp: Employee) -> int:
        """
        Onboard a new employee into OLTP and automatically reflect them in OLAP Dim_Employee.
        """
        if not emp.employee_id:
            emp.employee_id = self.get_next_employee_id()

        # Step 1: Insert into OLTP
        query_oltp = """
            INSERT INTO employees (
                EmployeeID, FirstName, LastName, Email, Age, Gender, MaritalStatus,
                DistanceFromHome, EducationField, MonthlyIncome, HireDate, IsActive,
                DepartmentID, JobRoleID
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        params_oltp = (
            emp.employee_id, emp.first_name, emp.last_name, emp.email,
            emp.age, emp.gender, emp.marital_status, emp.distance_from_home,
            emp.education_field, emp.monthly_income, emp.hire_date,
            1 if emp.is_active else 0, emp.department_id, emp.job_role_id
        )
        self.execute_query(query_oltp, params_oltp, db_key="oltp", fetch="none")

        # Step 2: Fetch DepartmentName & RoleName for OLAP synchronization
        dept_info = self.get_department_by_id(emp.department_id)
        role_info = self.get_job_role_by_id(emp.job_role_id)
        dept_name = dept_info.department_name if dept_info else "General"
        role_name = role_info.role_name if role_info else "Staff"
        job_level = role_info.job_level if role_info else 1

        # Step 3: Insert into OLAP Dim_Employee as Current Active Record
        query_olap = """
            INSERT INTO Dim_Employee (
                EmployeeID_BK, FirstName, LastName, Email, Age, Gender,
                EducationField, DistanceFromHome, MonthlyIncome,
                DepartmentName, RoleName, JobLevel,
                EffectiveStartDate, EffectiveEndDate, IsCurrent
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, '9999-12-31', TRUE);
        """
        params_olap = (
            emp.employee_id, emp.first_name, emp.last_name, emp.email,
            emp.age, emp.gender, emp.education_field, emp.distance_from_home,
            emp.monthly_income, dept_name, role_name, job_level, emp.hire_date
        )
        self.execute_query(query_olap, params_olap, db_key="olap", fetch="none")

        return emp.employee_id

    def update_employee_career(
        self,
        employee_id: int,
        new_department_id: int,
        new_job_role_id: int,
        new_salary: float
    ) -> bool:
        """
        Promote, transfer, or adjust salary for an employee.
        Updates the employee and its SCD Type 2 dimension row in one transaction.
        """
        with self.db.get_cursor(db_key="oltp") as cursor:
            cursor.execute(
                """
                SELECT d.DepartmentName, r.RoleName, r.JobLevel
                FROM departments d
                JOIN jobroles r ON r.JobRoleID = %s
                WHERE d.DepartmentID = %s;
                """,
                (new_job_role_id, new_department_id),
            )
            new_role = cursor.fetchone()
            if not new_role:
                raise ValueError("The selected department or job role does not exist.")

            cursor.execute(
                """
                UPDATE employees
                SET DepartmentID = %s,
                    JobRoleID = %s,
                    MonthlyIncome = %s
                WHERE EmployeeID = %s;
                """,
                (new_department_id, new_job_role_id, new_salary, employee_id),
            )
            if cursor.rowcount != 1:
                raise ValueError(f"Employee {employee_id} does not exist.")

            cursor.execute(
                """
                SELECT FirstName, LastName, Email, Age, Gender, EducationField,
                       DistanceFromHome
                FROM Dim_Employee
                WHERE EmployeeID_BK = %s AND IsCurrent = TRUE
                ORDER BY EmployeeSK DESC
                LIMIT 1;
                """,
                (employee_id,),
            )
            current = cursor.fetchone()
            if not current:
                raise RuntimeError(
                    f"Employee {employee_id} has no current Dim_Employee record."
                )

            cursor.execute(
                """
                UPDATE Dim_Employee
                SET EffectiveEndDate = CURRENT_DATE(), IsCurrent = FALSE
                WHERE EmployeeID_BK = %s AND IsCurrent = TRUE;
                """,
                (employee_id,),
            )
            cursor.execute(
                """
                INSERT INTO Dim_Employee (
                    EmployeeID_BK, FirstName, LastName, Email, Age, Gender,
                    EducationField, DistanceFromHome, MonthlyIncome,
                    DepartmentName, RoleName, JobLevel,
                    EffectiveStartDate, EffectiveEndDate, IsCurrent
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    CURRENT_DATE(), '9999-12-31', TRUE
                );
                """,
                (
                    employee_id, current["FirstName"], current["LastName"],
                    current["Email"], current["Age"], current["Gender"],
                    current["EducationField"], current["DistanceFromHome"],
                    new_salary, new_role["DepartmentName"], new_role["RoleName"],
                    new_role["JobLevel"],
                ),
            )

        return True

    def get_active_employees(
        self,
        limit: int = 50,
        offset: int = 0,
        search: str = "",
        department_id: Optional[int] = None
    ) -> List[Employee]:
        """Fetch active employees with joined Department and Role names."""
        where_clauses = ["e.IsActive = 1"]
        params = []

        if search:
            where_clauses.append("(e.FirstName LIKE %s OR e.LastName LIKE %s OR e.Email LIKE %s)")
            term = f"%{search}%"
            params.extend([term, term, term])

        if department_id:
            where_clauses.append("e.DepartmentID = %s")
            params.append(department_id)

        where_sql = " AND ".join(where_clauses)
        query = f"""
            SELECT 
                e.EmployeeID, e.FirstName, e.LastName, e.Email, e.Age, e.Gender,
                e.MaritalStatus, e.DistanceFromHome, e.EducationField, e.MonthlyIncome,
                e.HireDate, e.IsActive, e.DepartmentID, e.JobRoleID,
                d.DepartmentName, r.RoleName, r.JobLevel
            FROM employees e
            LEFT JOIN departments d ON e.DepartmentID = d.DepartmentID
            LEFT JOIN jobroles r ON e.JobRoleID = r.JobRoleID
            WHERE {where_sql}
            ORDER BY e.EmployeeID ASC
            LIMIT %s OFFSET %s;
        """
        params.extend([limit, offset])
        rows = self.execute_query(query, tuple(params), db_key="oltp", fetch="all")

        employees = []
        for r in rows:
            employees.append(Employee(
                employee_id=r["EmployeeID"],
                first_name=r["FirstName"],
                last_name=r["LastName"],
                email=r["Email"],
                age=r["Age"],
                gender=r["Gender"],
                marital_status=r["MaritalStatus"],
                distance_from_home=r["DistanceFromHome"],
                education_field=r["EducationField"],
                monthly_income=float(r["MonthlyIncome"]) if r["MonthlyIncome"] is not None else 0.0,
                hire_date=r["HireDate"],
                is_active=bool(r["IsActive"]),
                department_id=r["DepartmentID"],
                job_role_id=r["JobRoleID"],
                department_name=r.get("DepartmentName"),
                role_name=r.get("RoleName"),
                job_level=r.get("JobLevel")
            ))
        return employees

    def count_active_employees(self, search: str = "", department_id: Optional[int] = None) -> int:
        """Count total matching active employees for pagination."""
        where_clauses = ["IsActive = 1"]
        params = []
        if search:
            where_clauses.append("(FirstName LIKE %s OR LastName LIKE %s OR Email LIKE %s)")
            term = f"%{search}%"
            params.extend([term, term, term])
        if department_id:
            where_clauses.append("DepartmentID = %s")
            params.append(department_id)

        where_sql = " AND ".join(where_clauses)
        query = f"SELECT COUNT(*) AS total FROM employees WHERE {where_sql};"
        res = self.execute_query(query, tuple(params), db_key="oltp", fetch="one")
        return res["total"] if res else 0

    def get_employee_by_id(self, employee_id: int) -> Optional[Employee]:
        """Fetch a single employee by EmployeeID."""
        query = """
            SELECT 
                e.EmployeeID, e.FirstName, e.LastName, e.Email, e.Age, e.Gender,
                e.MaritalStatus, e.DistanceFromHome, e.EducationField, e.MonthlyIncome,
                e.HireDate, e.IsActive, e.DepartmentID, e.JobRoleID,
                d.DepartmentName, r.RoleName, r.JobLevel
            FROM employees e
            LEFT JOIN departments d ON e.DepartmentID = d.DepartmentID
            LEFT JOIN jobroles r ON e.JobRoleID = r.JobRoleID
            WHERE e.EmployeeID = %s;
        """
        r = self.execute_query(query, (employee_id,), db_key="oltp", fetch="one")
        if not r:
            return None
        return Employee(
            employee_id=r["EmployeeID"],
            first_name=r["FirstName"],
            last_name=r["LastName"],
            email=r["Email"],
            age=r["Age"],
            gender=r["Gender"],
            marital_status=r["MaritalStatus"],
            distance_from_home=r["DistanceFromHome"],
            education_field=r["EducationField"],
            monthly_income=float(r["MonthlyIncome"]) if r["MonthlyIncome"] is not None else 0.0,
            hire_date=r["HireDate"],
            is_active=bool(r["IsActive"]),
            department_id=r["DepartmentID"],
            job_role_id=r["JobRoleID"],
            department_name=r.get("DepartmentName"),
            role_name=r.get("RoleName"),
            job_level=r.get("JobLevel")
        )

    def get_all_departments(self) -> List[Department]:
        """Fetch all lookup departments."""
        rows = self.execute_query(
            "SELECT DepartmentID, DepartmentName FROM departments ORDER BY DepartmentName;",
            db_key="oltp",
            fetch="all"
        )
        return [Department(r["DepartmentID"], r["DepartmentName"]) for r in rows]

    def get_department_by_id(self, dept_id: int) -> Optional[Department]:
        """Fetch department by ID."""
        r = self.execute_query(
            "SELECT DepartmentID, DepartmentName FROM departments WHERE DepartmentID = %s;",
            (dept_id,),
            db_key="oltp",
            fetch="one"
        )
        return Department(r["DepartmentID"], r["DepartmentName"]) if r else None

    def get_all_job_roles(self) -> List[JobRole]:
        """Fetch all lookup job roles."""
        rows = self.execute_query(
            "SELECT JobRoleID, RoleName, JobLevel FROM jobroles ORDER BY RoleName, JobLevel;",
            db_key="oltp",
            fetch="all"
        )
        return [JobRole(r["JobRoleID"], r["RoleName"], r["JobLevel"]) for r in rows]

    def get_job_role_by_id(self, role_id: int) -> Optional[JobRole]:
        """Fetch job role by ID."""
        r = self.execute_query(
            "SELECT JobRoleID, RoleName, JobLevel FROM jobroles WHERE JobRoleID = %s;",
            (role_id,),
            db_key="oltp",
            fetch="one"
        )
        return JobRole(r["JobRoleID"], r["RoleName"], r["JobLevel"]) if r else None
