A **data warehouse** is a **consolidated/integrated view of corporate data** drawn from **disparate operational data sources** and supported by a range of **end-user access tools** capable of supporting simple to highly complex queries for **decision making**.

## Attributes and Characteristics of a Data Warehouse

The data held within a data warehouse is described by four main attributes:

* **Subject-oriented:** The warehouse is organized around the major **subjects** of the organization (like customers, products, and sales), not the major application areas (like stock control or customer invoicing). This is intended to store data for decision support, rather than application-oriented data.
* **Integrated:** The data comes from different organization-wide application systems. Source data is often inconsistent (using different data types or formats), so the integrated data source must be made **consistent** to present a unified view to users.
* **Time-variant:** The data is accurate and valid only at some specific point in time or over some time interval.
* **Nonvolatile:** The data is not updated in real time; instead, it is **refreshed** from operational systems on a regular basis. New data is always added as a **supplement** to the database, rather than replacing existing data.

## Purpose of the Data Warehouse

The **principal purpose** of data warehousing is to **provide information to business users for strategic decision making**.

Historically, organizations focused their investment on **online transaction processing (OLTP) systems** (transaction systems) that automate business processes. However, operational systems were **never primarily designed to support business decision making**. The data warehouse was conceived as the solution to meet the requirements of a system specifically capable of supporting decision making, receiving its necessary data from those multiple operational sources.

## Data Warehouse and Decision Support Systems (DSS)

Yes, the enterprise data warehouse (EDW) is fundamentally part of a data-driven Decision Support System (DSS).

* **Why?** The entire concept of the data warehouse was established to provide the integrated, analytical, and historical data required to support high-level **decision making**. It serves as the single, reliable source of knowledge necessary to turn archives of data into actionable insights.

## Decision Support Technologies Used

The end-user access tools used to interact with the data warehouse—which is the analytical component of a DSS—typically include:

* **Reporting and Query Tools**
* **Application Development Tools**
* **Executive Information System (EIS) Tools**
* **Online Analytical Processing (OLAP) Tools** 
* **Data Mining Tools**

## Major Benefit of the Data Warehouse

The major benefit of the enterprise data warehouse (EDW) is that it provides a **single integrated/consolidated view of the organization’s data**.

* **Why?** A typical organization may have **numerous operational systems** with data definitions that are often **overlapping and sometimes contradictory** (e.g., different data types for the same field). The data warehouse solves this **inconsistency** by drawing from these disparate operational sources and making the source data **consistent** to present a unified, trustworthy view of the data to the users, thereby enabling accurate strategic decision-making.
