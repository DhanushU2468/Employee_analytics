
CREATE DATABASE IF NOT EXISTS hr_enterprise_oltp;
USE hr_enterprise_oltp;

-- TABLE 1: Departments 

CREATE TABLE IF NOT EXISTS Departments (
    DepartmentID INT AUTO_INCREMENT PRIMARY KEY,
    DepartmentName VARCHAR(100) NOT NULL UNIQUE
);

-- TABLE 2: JobRoles 

CREATE TABLE IF NOT EXISTS JobRoles (
    JobRoleID INT AUTO_INCREMENT PRIMARY KEY,
    RoleName VARCHAR(100) NOT NULL,
    JobLevel INT NOT NULL
);

-- TABLE 3: Employees 

CREATE TABLE IF NOT EXISTS Employees (
    EmployeeID INT PRIMARY KEY, -- Maps directly to IBM EmployeeNumber
    FirstName VARCHAR(50) NOT NULL,
    LastName VARCHAR(50) NOT NULL,
    Email VARCHAR(100) NOT NULL UNIQUE,
    Age INT,
    Gender VARCHAR(20),
    MaritalStatus VARCHAR(50),
    DistanceFromHome INT,
    EducationField VARCHAR(100),
    MonthlyIncome DECIMAL(10, 2),
    HireDate DATE NOT NULL,
    IsActive BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Foreign Keys
    DepartmentID INT,
    JobRoleID INT,
    FOREIGN KEY (DepartmentID) REFERENCES Departments(DepartmentID),
    FOREIGN KEY (JobRoleID) REFERENCES JobRoles(JobRoleID)
);

-- TABLE 4: PerformanceReviews

CREATE TABLE IF NOT EXISTS PerformanceReviews (
    ReviewID INT AUTO_INCREMENT PRIMARY KEY,
    EmployeeID INT NOT NULL,
    ReviewDate DATE NOT NULL,
    PerformanceRating INT CHECK(PerformanceRating BETWEEN 1 AND 5),
    JobSatisfaction INT CHECK(JobSatisfaction BETWEEN 1 AND 4),
    EnvironmentSatisfaction INT CHECK(EnvironmentSatisfaction BETWEEN 1 AND 4),
    WorkLifeBalance INT CHECK(WorkLifeBalance BETWEEN 1 AND 4),
    RelationshipSatisfaction INT CHECK(RelationshipSatisfaction BETWEEN 1 AND 4),
    
    -- Foreign Key
    FOREIGN KEY (EmployeeID) REFERENCES Employees(EmployeeID) ON DELETE CASCADE
);

-- TABLE 5A: Projects

CREATE TABLE IF NOT EXISTS Projects (
    ProjectID INT AUTO_INCREMENT PRIMARY KEY,
    ProjectName VARCHAR(100) NOT NULL,
    Budget DECIMAL(15, 2),
    Status VARCHAR(50) DEFAULT 'Active'
);


-- TABLE 5B: EmployeeProjects 

CREATE TABLE IF NOT EXISTS EmployeeProjects (
    AllocationID INT AUTO_INCREMENT PRIMARY KEY,
    EmployeeID INT NOT NULL,
    ProjectID INT NOT NULL,
    AllocationPercentage INT CHECK(AllocationPercentage BETWEEN 1 AND 100),
    
    -- Foreign Keys
    FOREIGN KEY (EmployeeID) REFERENCES Employees(EmployeeID) ON DELETE CASCADE,
    FOREIGN KEY (ProjectID) REFERENCES Projects(ProjectID) ON DELETE CASCADE
);



-- 1. historic_employees 

CREATE TABLE IF NOT EXISTS historic_employees (
    EmployeeID INT, 
    FirstName VARCHAR(50) NOT NULL,
    LastName VARCHAR(50) NOT NULL,
    Email VARCHAR(100) NOT NULL, 
    Age INT,
    Gender VARCHAR(20),
    MaritalStatus VARCHAR(50),
    DistanceFromHome INT,
    EducationField VARCHAR(100),
    MonthlyIncome DECIMAL(10, 2),
    HireDate DATE NOT NULL,
    IsActive BOOLEAN NOT NULL DEFAULT TRUE,
    DepartmentID INT,
    JobRoleID INT
);


-- 2. historic_employee_projects 

CREATE TABLE IF NOT EXISTS historic_employee_projects (
    AllocationID INT,
    EmployeeID INT NOT NULL,
    ProjectID INT NOT NULL,
    AllocationPercentage INT CHECK(AllocationPercentage BETWEEN 1 AND 100)
);

