import os
import pandas as pd
import mysql.connector
from mysql.connector import Error


def connect_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "Swami@0320"),
        database=os.getenv("DB_NAME", "hr_enterprise_oltp")
    )


def get_data_dir():
    """Locate the data directory whether run from root, scripts folder, or elsewhere."""
    if "DATA_DIR" in os.environ and os.path.isdir(os.environ["DATA_DIR"]):
        return os.environ["DATA_DIR"]

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    candidate_root = os.path.join(project_root, "data")
    if os.path.isdir(candidate_root):
        return candidate_root

    candidate_cwd = os.path.join(os.getcwd(), "data")
    if os.path.isdir(candidate_cwd):
        return candidate_cwd

    return "data"


def resolve_file(data_dir, preferred_name, alternatives=None):
    """Find a file checking preferred name first, followed by known alternatives."""
    candidates = [preferred_name] + (alternatives or [])
    for name in candidates:
        full_path = os.path.join(data_dir, name)
        if os.path.isfile(full_path):
            return full_path
    raise FileNotFoundError(
        f"Could not find '{preferred_name}' (checked: {candidates}) in '{data_dir}' folder."
    )


def normalize_bool_col(series):
    """Convert boolean, string, or numeric representations of booleans to 1 / 0."""
    if series.dtype == object or str(series.dtype).startswith(("str", "cat")):
        return series.astype(str).str.strip().str.lower().isin(["true", "yes", "1", "t", "y"]).astype(int)
    return series.astype(bool).astype(int)


def bulk_insert(cursor, table_name, df, insert_query, chunk_size=10000):
    """Helper function to insert data in chunks to prevent memory crashes and handle NaNs."""
    df_clean = df.astype(object).where(pd.notnull(df), None)
    data_tuples = [tuple(row) for row in df_clean.to_numpy()]

    for i in range(0, len(data_tuples), chunk_size):
        chunk = data_tuples[i:i + chunk_size]
        cursor.executemany(insert_query, chunk)
    print(f"✅ Successfully injected {len(data_tuples)} rows into {table_name}.")


def inject_all_csvs():
    data_dir = get_data_dir()
    db = None
    cursor = None

    try:
        db = connect_db()
        cursor = db.cursor()
        print(f"Connected to database successfully. Reading files from '{data_dir}' folder...")

        # ==============================================================================
        # STEP 1: INJECT LOOKUP TABLES (Must go first)
        # ==============================================================================
        df_dept = pd.read_csv(resolve_file(data_dir, "departments.csv"))
        query_dept = "INSERT IGNORE INTO departments (DepartmentID, DepartmentName) VALUES (%s, %s)"
        bulk_insert(cursor, "departments", df_dept, query_dept)
        db.commit()

        df_roles = pd.read_csv(resolve_file(data_dir, "jobroles.csv"))
        query_roles = "INSERT IGNORE INTO jobroles (JobRoleID, RoleName, JobLevel) VALUES (%s, %s, %s)"
        bulk_insert(cursor, "jobroles", df_roles, query_roles)
        db.commit()

        # ==============================================================================
        # STEP 2: INJECT CORE EMPLOYEE TABLE
        # ==============================================================================
        df_emp = pd.read_csv(resolve_file(data_dir, "employees.csv"))
        df_emp["IsActive"] = normalize_bool_col(df_emp["IsActive"])

        query_emp = """
            INSERT IGNORE INTO employees 
            (EmployeeID, FirstName, LastName, Email, Age, Gender, MaritalStatus, 
             DistanceFromHome, EducationField, MonthlyIncome, HireDate, IsActive, DepartmentID, JobRoleID)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        bulk_insert(cursor, "employees", df_emp, query_emp)
        db.commit()

        # ==============================================================================
        # STEP 3: INJECT DEPENDENT TABLES (Reviews, Projects, EmployeeProjects)
        # ==============================================================================
        df_reviews = pd.read_csv(resolve_file(data_dir, "performance_reviews.csv", ["performancereviews.csv"]))
        query_reviews = """
            INSERT IGNORE INTO performancereviews 
            (ReviewID, EmployeeID, ReviewDate, PerformanceRating, JobSatisfaction, 
             EnvironmentSatisfaction, WorkLifeBalance, RelationshipSatisfaction)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        bulk_insert(cursor, "performancereviews", df_reviews, query_reviews)
        db.commit()

        df_projects = pd.read_csv(resolve_file(data_dir, "projects.csv"))
        query_projects = "INSERT IGNORE INTO projects (ProjectID, ProjectName, Budget, Status) VALUES (%s, %s, %s, %s)"
        bulk_insert(cursor, "projects", df_projects, query_projects)
        db.commit()

        df_allocations = pd.read_csv(resolve_file(data_dir, "employee_projects.csv", ["employeeprojects.csv"]))
        query_alloc = """
            INSERT IGNORE INTO employeeprojects 
            (AllocationID, EmployeeID, ProjectID, AllocationPercentage) 
            VALUES (%s, %s, %s, %s)
        """
        bulk_insert(cursor, "employeeprojects", df_allocations, query_alloc)
        db.commit()

        # ==============================================================================
        # STEP 4: INJECT HISTORIC TABLES
        # ==============================================================================

        # 4A. Historic Employees
        df_hist_emp = pd.read_csv(resolve_file(data_dir, "historic_employees.csv", ["historicemployees.csv"]))
        df_hist_emp["IsActive"] = normalize_bool_col(df_hist_emp["IsActive"])

        query_hist_emp = """
            INSERT INTO historic_employees
            (EmployeeID, FirstName, LastName, Email, Age, Gender, MaritalStatus,
             DistanceFromHome, EducationField, MonthlyIncome, HireDate, IsActive, DepartmentID, JobRoleID)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        bulk_insert(cursor, "historic_employees", df_hist_emp, query_hist_emp)
        db.commit()

        # 4B. Historic Employee Projects
        df_hist_alloc = pd.read_csv(
            resolve_file(data_dir, "historic_employee_projects.csv", ["historic_employeeprojects.csv"])
        )
        query_hist_alloc = """
            INSERT INTO historic_employee_projects
            (AllocationID, EmployeeID, ProjectID, AllocationPercentage)
            VALUES (%s, %s, %s, %s)
        """
        bulk_insert(cursor, "historic_employee_projects", df_hist_alloc, query_hist_alloc)
        db.commit()

        print("🎉 All 8 CSV files (including historic tables) injected successfully from the data folder!")

    except Error as e:
        print(f"❌ Database Error: {e}")
        if db is not None and db.is_connected():
            db.rollback()
    except FileNotFoundError as e:
        print(f"❌ File Error: {e}")
        if db is not None and db.is_connected():
            db.rollback()
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        if db is not None and db.is_connected():
            db.rollback()
    finally:
        if cursor is not None:
            cursor.close()
        if db is not None and db.is_connected():
            db.close()


if __name__ == "__main__":
    inject_all_csvs()