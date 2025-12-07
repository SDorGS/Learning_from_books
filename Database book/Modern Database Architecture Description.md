## **External Level**

The three-level ANSI-SPARC database architecture exists to separate what users see, what the database stores logically, and how it is actually saved on the computer, because without this separation, any change in storage or logical structure could break all user views; the external level shows each user their own view of the “real world,” including only the entities, attributes, and relationships they need, and it can include calculated data (like age from a birth date) or different ways of showing the same data (e.g., day–month–year versus year–month–day) without knowing anything about physical storage, indexes, compression, or encryption, ensuring that users interact with data independently of how it is stored;

## **Conceptual Level**

the conceptual level is the middle layer that defines all entities, attributes, relationships, constraints, and rules in a storage-independent way, letting all external views map consistently and allowing the database administrator to change logical structures or constraints without affecting users;

## **Internal Level**

the internal level defines exactly how data is stored on disks, including file structures, record placement, indexing, compression, encryption, and how the database interacts with the operating system, giving good performance and storage efficiency while staying hidden from users and even from conceptual definitions;

## **Overall Architecture / Integration**

together, these three levels implement separation of concerns, letting user views, logical models, and physical storage evolve independently, maintain security and integrity, optimize performance, and adapt to technology or organizational changes without breaking anything, fully showing every layer, how it works, and the tradeoffs involved.


# Practical Notes

### **External Level → User-Facing API / Views**

```python
class EmployeeView:
    def __init__(self, employee_record):
        self.name = employee_record["name"]
        self.age = self.calculate_age(employee_record["dob"])
        self.hire_date = employee_record["hire_date"].strftime("%d-%m-%Y")

    @staticmethod
    def calculate_age(dob):
        from datetime import date
        today = date.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
```

* **Purpose:** Exposes exactly what your Python code or user sees. Can include derived data like age, different formats for the same data, or combined fields. Users and application code do **not** need to know how data is stored or indexed.

* **SQL Example for External View:**

```sql
CREATE VIEW PayrollView AS
SELECT 
    Name,
    DATEDIFF(YEAR, BirthDate, GETDATE()) AS Age,
    HireDate
FROM Employees;
```

---

### **Conceptual Level → Logical Model / ORM**

```python
from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Employee(Base):
    __tablename__ = 'employees'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    dob = Column(Date, nullable=False)
    department_id = Column(Integer, ForeignKey('departments.id'))
    department = relationship("Department", back_populates="employees")
```

* **Purpose:** Defines the **full logical model**: entities, relationships, attributes, and constraints. Python code can work with these objects without caring about storage details.

* **Effect in SQL/Python:** You can change database schema or constraints without breaking external views.

---

### **Internal Level → Physical Storage / Performance Layer**

* **Storage options:** `dict`, `list`, SQLite, PostgreSQL, Parquet, JSON, CSV.
* **Performance tuning:** Indexes, caching, compression, encryption.
* **Python access:** Typically hidden behind ORMs or libraries like SQLAlchemy, pandas, or file I/O.

```python
# Example: choosing storage and indexing behind the scenes
from sqlalchemy import create_engine

engine = create_engine('postgresql://user:pass@localhost/db')
# ORM code interacts with engine but doesn't handle physical placement or compression
```

---

### **Integration / Technical Mapping**

| Level      | Python / SQL Concept | Practical Use                                                                                    |
| ---------- | -------------------- | ------------------------------------------------------------------------------------------------ |
| External   | API / View           | Application code interacts with a subset of data or computed fields without knowing storage.     |
| Conceptual | ORM / Logical Model  | Maintains entities, relationships, constraints. Allows schema changes without breaking apps.     |
| Internal   | DBMS / Storage       | Handles file structures, indexes, storage optimization. Python and SQL queries remain unchanged. |

