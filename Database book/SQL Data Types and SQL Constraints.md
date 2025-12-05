# **SQL Data Types and SQL Constraints**

# **1. SQL Data Types**

SQL Data Types define the *fundamental nature* of data stored in a database column. They determine:

* What values are permitted
* How values are stored internally
* What operations can be performed
* What constraints logically follow from the type

## **2.1 Conceptual Foundations of Data Types**

### **2.1.1 Definition and Logical Role**

**Data types** impose a *domain of allowable values*. This domain ensures correctness, optimizes performance, and enables predictable behavior for operations.

### **2.1.2 Theoretical Underpinnings**

Data types originate from:

* **Type Theory** (mathematical logic): ensuring expressions are well‑formed
* **Domain Theory**: mapping conceptual entities to storage representations
* **Information Theory**: optimizing data encoding and retrieval

### **2.1.3 Historical Development**

* Early relational databases (1970s, E. F. Codd) used minimal atomic types.
* As applications expanded (GIS, analytics, multimedia), databases introduced richer types such as **JSON**, **GEOMETRY**, and **BLOBs**.

# **3. Classification of SQL Data Types**

SQL Data Types fall into **four major categories**, each with distinct properties, principles, and sub-variants.

## **3.1 Numeric Data Types**

### **3.1.1 Purpose and Properties**

Used to store numbers—supporting mathematical computation, indexing, sorting, and aggregations.

**Key Properties**:

* Precision
* Range
* Storage size
* Signed vs unsigned

### **3.1.2 Subcategories**

#### **A. Integer Types**

* **INT**, **TINYINT**, **SMALLINT**, **MEDIUMINT**, **BIGINT**
* Stored using fixed bytes; no fractional part.

**Principle**: Binary integer representation.

**Why they work this way**: The discrete nature of integers aligns with binary storage, enabling fast arithmetic.

**Variants/Purpose**:

* TINYINT for flags or status codes
* BIGINT for high-range counters

#### **B. Fixed-Point Types**

* **DECIMAL(p, s)**

**Principle**: Numeric representation using scaled integers.

**Why**: Ensures *exact precision*, crucial in finance.

#### **C. Floating-Point Types**

* **FLOAT**, **DOUBLE**

**Principle**: IEEE-754 fractional binary representation.

**Behavior**: Fast computations but subject to rounding errors.

**Practical Relevance**: Scientific calculations.

## **3.2 String Data Types**

### **3.2.1 Purpose and Properties**

Store sequences of characters or binary content.

**Key Properties**:

* Length (fixed vs variable)
* Character encoding
* Collation (sorting rules)

### **3.2.2 Subcategories and Variants**

#### **A. Character Strings**

* **CHAR(n)**: Fixed length
* **VARCHAR(n)**: Variable length

**Principle**: Memory allocation strategy (fixed vs dynamic).

**Why**: CHAR improves performance for uniform-length fields; VARCHAR minimizes storage overhead.

#### **B. Large Text Types**

* **TEXT**, **TINYTEXT**, **MEDIUMTEXT**, **LONGTEXT**

Used for large documents, logs, descriptions.

#### **C. Binary Types**

* **BLOB**, **MEDIUMBLOB**, **LONGBLOB**

**Principle**: Byte-level storage; no collation.

**Why**: Arbitrary data (images, PDFs) cannot be interpreted as text.

## **3.3 Date and Time Data Types**

### **3.3.1 Purpose and Properties**

Track temporal information.

**Key Properties**:

* Time zone behavior
* Precision
* Range

### **3.3.2 Main Variants**

* **DATE**: stores year-month-day
* **TIME**: hours-minutes-seconds
* **DATETIME**: combined
* **TIMESTAMP**: UTC-based epoch time
* **YEAR**

**Principle**: Timekeeping and chronological ordering.

**Why**: Consistent temporal representation enables accurate time-based computations.

**Historical Relevance**: Unix timestamp emerged in early OS design; databases later adopted similar concepts.

## **3.4 Spatial and Specialized Types**

### **3.4.1 GEOMETRY**

Stores spatial objects (points, polygons) using geometric principles.

**Applications**: Mapping, GPS systems.

### **3.4.2 JSON**

Stores hierarchical structured data.

**Principle**: Semi-structured document storage.

**Why**: Increasing need for flexible schemas.

### **3.4.3 ENUM**

Stores predefined list values.

**Principle**: Domain restriction.

**Why**: Enforces controlled vocabularies.

# **4. SQL Constraints**

SQL Constraints define rules governing:

* Data validity
* Relationship integrity
* Structural consistency

They operate *logically on top of* data types.

## **4.1 Theoretical Basis of Constraints**

### **4.1.1 Relation Model Foundations**

Constraints stem from:

* **Predicate logic**: constraints express truth conditions
* **Set theory**: tables represent sets of tuples
* **Integrity rules**: ensure database remains semantically correct

### **4.1.2 Categories of Constraints**

1. **Key Constraints**
2. **Existence Constraints**
3. **Value Constraints**
4. **Referential Constraints**

# **5. Classification of SQL Constraints**

## **5.1 Key Constraints**

Guarantee uniqueness and identity.

### **5.1.1 PRIMARY KEY**

**Properties**:

* Unique
* Not Null
* Identifies each row

**Principle**: Entity integrity.

### **5.1.2 UNIQUE**

Allows NULL but enforces uniqueness otherwise.

**Principle**: Candidate key constraint.

### **5.1.3 FOREIGN KEY**

Links to another table's primary key.

**Principle**: Referential integrity.

**Variants**:

* Composite foreign keys
* Self-referencing keys

## **5.2 Existence Constraints**

### **5.2.1 NOT NULL**

Prevents missing values.

**Principle**: Mandatory attributes.

### **5.2.2 NULL**

Allows absence of value.

**Theoretical Basis**: Three-valued logic (true/false/unknown).

## **5.3 Value Constraints**

### **5.3.1 DEFAULT**

Automatically substitutes a value.

**Application**: timestamps, status flags.

### **5.3.2 CHECK**

Ensures logical rule is satisfied.

**Examples**:

* CHECK (age >= 0)
* CHECK (rating BETWEEN 1 AND 10)

### **5.3.3 AUTO_INCREMENT**

Sequential value generation.

**Relevance**: Primary keys, log identifiers.

## **5.4 Referential Actions (Foreign Key Behaviors)**

### **5.4.1 ON DELETE / ON UPDATE RULES**

**CASCADE**: Propagate changes.

**SET NULL**: Remove reference.

**RESTRICT/NO ACTION**: Block change.

**SET DEFAULT**: Reassign fallback value.

# **6. Practical Applications**

### **6.1 In Real Database Designs**

* Numeric types: financial computations, counters
* String types: user input, metadata
* Date/time: logging, auditing
* JSON: flexible configs
* FOREIGN KEY constraints: multi-table transactions

# **7. Expert Practices and Observations**

### **7.1 Consultation With Experts**

Database architects emphasize:

* Using smallest appropriate data type (performance)
* Avoiding misuse of VARCHAR for numeric data
* Ensuring constraints reflect business rules

### **7.2 Observational Patterns**

Real-world systems reveal:

* Many performance issues arise from improper type selection
* Constraints prevent subtle long-term data corruption

# **8. Conclusion**

This document provides a deeply detailed, precise, logically structured exploration of SQL Data Types and Constraints, intended to support advanced understanding, conceptual clarity, and professional mastery.
