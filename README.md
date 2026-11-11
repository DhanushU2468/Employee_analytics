# Enterprise Employee Analytics & Data Warehouse System

An end-to-end HR data portal and analytical warehouse built with **Streamlit**, **TiDB Cloud**, and **Python**. Separates operational and analytical workloads into distinct table sets within a single database. Supports **Slowly Changing Dimensions (SCD Type 2)** and an Object-Oriented Python middleware.

---

## Live Deployment (Streamlit Cloud)

This project is configured for one-click deployment on **Streamlit Cloud**.

### Deploy Steps

1. **Push this repo to GitHub** (public or private).
2. Go to [share.streamlit.io](https://share.streamlit.io) and click **"New app"**.
3. Select your repo, branch, and set the **Main file path** to:
   ```
   frontend/app.py
   ```
4. In the **Advanced settings → Secrets** section, paste the contents of your `.streamlit/secrets.toml`:
   ```toml
   [mysql]
   host = "gateway01.ap-northeast-1.prod.aws.tidbcloud.com"
   port = 4000
   user = "2XEWYAy31U7rGmd.root"
   password = "TyOCJcQpSsDL3lBT"
   database = "employee_analytics"
   ssl_enabled = true
   ssl_verify_cert = true
   ssl_ca = "isrgrootx1.pem"
   pool_size = 3
   ```
5. Click **Deploy**. Streamlit Cloud installs dependencies from `requirements.txt` automatically.

> **Note:** The `isrgrootx1.pem` file (ISRG Root X1 CA certificate) is bundled in the repo root and required for TLS connections to TiDB Cloud.

---

## System Architecture

```
[TiDB Cloud – employee_analytics database]
    ├── [OLTP tables] (3NF Relational)
    │     ├── departments & jobroles (Lookups)
    │     ├── employees (Core Entity)
    │     ├── projects & employeeprojects (Bridge)
    │     └── performancereviews (Transactions)
    │
    └── [OLAP tables] (Star Schema)
          ├── Dim_Employee (SCD Type 2 Temporal)
          ├── Dim_Department, Dim_Project, Dim_Date
          └── Fact_PerformanceReviews (Measures)
                    │
                    ▼
          [Object-Oriented Middleware / DAL]
            ├── DatabaseConnection (Singleton Pool)
            ├── EmployeeManager, ProjectManager
            └── AnalyticsManager
                    │
                    ▼
          [Streamlit Web App: frontend/app.py]
            ├── Module 1: HR Data Entry & SCD2 Trigger
            ├── Module 2: Operational Employee Directory
            └── Module 3: Executive OLAP Dashboard (Plotly)
```

---

## Key Features

### 1. Logical OLTP/OLAP Separation
- **OLTP tables**: Strict 3NF normalization optimized for transactional reads/writes and referential integrity.
- **OLAP tables**: A dimensional Star Schema for analytical window queries, YoY reporting, and executive metrics.

### 2. Slowly Changing Dimensions (SCD Type 2)
Preserves complete historical audit trails when an employee undergoes a promotion, department transfer, or salary revision.

### 3. Object-Oriented Python Middleware & DAL
- **Singleton Connection Pool**: TLS certificate verification with TiDB Cloud.
- **Encapsulated Entity Models**: Type-safe domain models for `Employee`, `Project`, `PerformanceReview`, and `Department`.
- **Parameterized Queries**: Defending against SQL injection with automated transaction management.

### 4. Advanced SQL Analytics
- **Window Functions**: Top performers per department via `ROW_NUMBER()`.
- **Year-over-Year Trends**: CTEs with `LAG()` for performance trajectories.
- **Employee Attrition Risk Analysis**: Multi-factor burnout model.
- **Project Bottleneck Detection**: Resource overallocation and budget utilization.

---

## Repository Structure

```plaintext
Employee_Analytics_portal/
├── .streamlit/
│   ├── config.toml                    # Streamlit theme configuration
│   └── secrets.toml.example           # Template for TiDB credentials
├── backend/
│   ├── db/
│   │   ├── config.py                  # Settings loader with SSL CA resolution
│   │   └── db_manager.py              # Singleton connection pool & context managers
│   ├── models/
│   │   └── entities.py                # OOP Entity classes
│   └── dal/
│       ├── base_manager.py            # Base DAL with transaction management
│       ├── employee_manager.py        # OLTP CRUD & SCD Type 2
│       ├── warehouse_sync_manager.py  # Incremental warehouse sync
│       ├── project_manager.py         # Project & allocation management
│       └── analytics_manager.py       # OLAP Star Schema & View execution
├── frontend/
│   ├── app.py                         # Streamlit web application
│   └── styles/
│       └── custom.css                 # Enterprise CSS styling
├── isrgrootx1.pem                     # ISRG Root X1 CA cert (TiDB Cloud TLS)
├── requirements.txt                   # Production dependencies
└── README.md
```

---

## Local Development

### Prerequisites
- Python 3.10+
- The `employee_analytics` database already provisioned on TiDB Cloud

### Setup
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in your TiDB credentials.

### Run Locally
```bash
python -m streamlit run frontend/app.py
```
Open your browser at `http://localhost:8501`.

---

## Streamlit Application Modules

### Module 1: HR Data Entry & Workforce Operations (OLTP)
- **Onboard New Employee** – writes to OLTP and initializes OLAP Dim_Employee.
- **Update Department & Role (SCD Type 2)** – live SCD Type 2 versioning.
- **Project & Resource Allocation** – create projects and assign staff.
- **Submit Performance Review** – updates OLTP and appends to OLAP Fact table.

### Module 2: Active Employee Directory (OLTP Operational Read)
- Real-time search & pagination with department filters.
- Detailed profile inspector with SCD Type 2 career history.

### Module 3: Executive Analytics Dashboard (OLAP Interaction)
- KPI summary cards, YoY performance trends (Plotly), top performers table.
- Employee attrition risk analysis and project bottleneck detection.
