## Simple MYSQL Commands I learnt on my Day 1

### **I. MySQL Shell & Client Commands (The "Backslash" Codes)**

*These commands control the software you are using. They do **not** use a semicolon.*

#### **1. Mode Switching (MySQL Shell specific)**

*Used when you see `MySQL JS >` or need to switch languages.*

```bash
\sql       # Switch to SQL mode or execute a single SQL statement
\js        # Switch to JavaScript mode
\py        # Switch to Python mode
```

#### **2. Connection & Session**

*Used to log in or check who you are.*

```bash
\connect root@localhost:3306   # Connect to server (Shell specific)
\status                        # (or \s) Show current user, version, and SSL status
\use daily_life                # (or \u) Set active schema (Shell specific alias)
\disconnect                    # Disconnect global session
\reconnect                     # Force a reconnection
```

#### **3. System & Interface Control**

*Used to manage the window or OS.*

```bash
\system cls    # (or \! cls) Run Windows OS command to clear screen
\system clear  # (or \! clear) Run Linux/Mac OS command to clear screen
Ctrl + L       # Keyboard shortcut to clear the terminal screen
\quit          # (or \q or \exit) Exit the program completely
\help          # (or \h or \?) Show the help menu
```

#### **4. Emergency & Buffer Control**

*Used when you are stuck in the `->` prompt.*

```bash
\c    # Clear the current input buffer (Cancel the command)
```

-----

### **II. SQL: Data Definition Language (DDL)**

*These commands build the structure. They **must** end with a semicolon `;`.*

#### **1. Database & Context**

```sql
CREATE DATABASE daily_life;    -- Create the filing cabinet
USE daily_life;                -- Enter the filing cabinet
SHOW DATABASES;                -- List all databases on the server
```

#### **2. Table Inspection**

```sql
SHOW TABLES;            -- List tables in the current database
DESCRIBE calls;         -- Show columns, types, and keys of 'calls' table
```

#### **3. Table Creation (The Blueprints)**

```sql
-- 1. Calls Table
CREATE TABLE calls (
    id INT AUTO_INCREMENT PRIMARY KEY,
    caller VARCHAR(100),
    time_of_call DATETIME,
    duration_minutes INT
);

-- 2. Messages Table (Using TEXT)
CREATE TABLE messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sender VARCHAR(100),
    message_text TEXT,
    time_received DATETIME
);

-- 3. Meals Table
CREATE TABLE meals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    meal_name VARCHAR(100),
    rating INT,
    time_eaten DATETIME
);

-- 4. Water Intake Table
CREATE TABLE water_intake (
    id INT AUTO_INCREMENT PRIMARY KEY,
    amount_ml INT,
    time_drank DATETIME
);

-- 5. Sleep Table (Advanced Constraints)
CREATE TABLE sleep (
    id INT AUTO_INCREMENT PRIMARY KEY,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    duration_hours DECIMAL(4, 2), -- Exact precision (e.g., 8.50)
    rating INT,
    bed_day DATE UNIQUE NOT NULL  -- One record per day only
);
```

-----

### **III. SQL: Data Manipulation (DML - CRUD)**

*These commands interact with the data rows.*

#### **1. Create (Insert)**

```sql
-- Standard Insert
INSERT INTO meals (meal_name, rating, time_eaten)
VALUES ("Lunch", 2, NOW());

-- Insert with specific date strings
INSERT INTO sleep (start_time, end_time, duration_hours, rating, bed_day)
VALUES ('2025-12-03 23:00:00', '2025-12-04 07:00:00', 8.00, 9, '2025-12-04');
```

#### **2. Read (Select)**

```sql
-- Select All
SELECT * FROM meals;

-- Select Specific Columns
SELECT caller, duration_minutes FROM calls;

-- Select with Filter (WHERE)
SELECT * FROM meals WHERE rating < 5;
```

#### **3. Update**

```sql
UPDATE tasks SET is_completed = 1 WHERE task_id = 1;
```

#### **4. Delete**

```sql
DELETE FROM tasks WHERE task_id = 5;
```

-----

### **IV. SQL: Analytics & Logic (DQL)**

*Advanced querying tools.*

#### **1. Aggregation Functions**

```sql
SELECT COUNT(*) FROM calls;        -- Count total rows
SELECT SUM(amount_ml) FROM water_intake; -- Add up values
```

#### **2. Date & Time Functions**

```sql
NOW()               -- Get current date and time
CURDATE()           -- Get current date only
DATE(time_column)   -- Extract just the date part from a datetime
```

#### **3. The Relational Join**

```sql
-- Combine Calls and Sleep data based on the date
SELECT
    C.caller,
    S.rating AS sleep_rating
FROM
    calls C
INNER JOIN
    sleep S ON DATE(C.time_of_call) = S.bed_day
WHERE
    S.rating <= 5;
```
