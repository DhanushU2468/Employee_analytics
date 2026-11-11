from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Department:
    department_id: int
    department_name: str

    def to_dict(self):
        return {
            "department_id": self.department_id,
            "department_name": self.department_name,
        }


@dataclass
class JobRole:
    job_role_id: int
    role_name: str
    job_level: int

    def to_dict(self):
        return {
            "job_role_id": self.job_role_id,
            "role_name": self.role_name,
            "job_level": self.job_level,
        }


@dataclass
class Employee:
    employee_id: Optional[int]
    first_name: str
    last_name: str
    email: str
    age: int
    gender: str
    marital_status: str
    distance_from_home: int
    education_field: str
    monthly_income: float
    hire_date: date
    is_active: bool = True
    department_id: Optional[int] = None
    job_role_id: Optional[int] = None
    department_name: Optional[str] = None
    role_name: Optional[str] = None
    job_level: Optional[int] = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def to_dict(self):
        return {
            "employee_id": self.employee_id,
            "full_name": self.full_name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "age": self.age,
            "gender": self.gender,
            "marital_status": self.marital_status,
            "distance_from_home": self.distance_from_home,
            "education_field": self.education_field,
            "monthly_income": self.monthly_income,
            "hire_date": str(self.hire_date),
            "is_active": self.is_active,
            "department_id": self.department_id,
            "job_role_id": self.job_role_id,
            "department_name": self.department_name,
            "role_name": self.role_name,
            "job_level": self.job_level,
        }


@dataclass
class Project:
    project_id: Optional[int]
    project_name: str
    budget: float
    status: str = "Active"

    def to_dict(self):
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "budget": self.budget,
            "status": self.status,
        }


@dataclass
class EmployeeProject:
    allocation_id: Optional[int]
    employee_id: int
    project_id: int
    allocation_percentage: int
    project_name: Optional[str] = None

    def to_dict(self):
        return {
            "allocation_id": self.allocation_id,
            "employee_id": self.employee_id,
            "project_id": self.project_id,
            "allocation_percentage": self.allocation_percentage,
            "project_name": self.project_name,
        }


@dataclass
class PerformanceReview:
    review_id: Optional[int]
    employee_id: int
    review_date: date
    performance_rating: int
    job_satisfaction: int
    environment_satisfaction: int
    work_life_balance: int
    relationship_satisfaction: int

    def to_dict(self):
        return {
            "review_id": self.review_id,
            "employee_id": self.employee_id,
            "review_date": str(self.review_date),
            "performance_rating": self.performance_rating,
            "job_satisfaction": self.job_satisfaction,
            "environment_satisfaction": self.environment_satisfaction,
            "work_life_balance": self.work_life_balance,
            "relationship_satisfaction": self.relationship_satisfaction,
        }

