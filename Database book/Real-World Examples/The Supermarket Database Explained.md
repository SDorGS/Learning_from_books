# The Supermarket Database


# LOGIC 1 — Foundational Axioms (the axioms that ground everything)


## Axiom 1: Uniqueness (Barcode/UPC)

**Claim (informal):** Every distinct physical product has a unique identifier (UPC), and the system must be able to identify a product record unambiguously by that identifier.

### I will unpack that into primitives:

1. **Unique identifier domain**: There exists a domain `UPC` (string of digits) and a bijection between *product instances* in the product master and UPC values.
2. **Uniqueness invariant**: ∀ two `Products` rows p1, p2: if `p1.UPC = p2.UPC` then `p1` and `p2` are the same row. (No two product rows share the same UPC.)
3. **Referential identity**: Any referencing table (Inventory, Transactions) that refers to a UPC must refer to an existing product (foreign-key relationship).

### Database translation (how we enforce it in SQL)

* `Products.UPC` is declared `PRIMARY KEY` or at least `UNIQUE NOT NULL`.
* `Inventory.UPC` and `Transactions.UPC` use `FOREIGN KEY (...) REFERENCES Products(UPC)`.

I note: **Uniqueness is not enough** if data is corrupted outside transactions; we need DB-level constraints and backups.

## Axiom 2: Inventory Integrity

**Claim (informal):** For each unit sold, the recorded stock count must decrease by exactly one, with no failure or lag that results in an inconsistent state.

### Unpacking:

1. **Atomic decrement property**: A single completed sale operation must cause a corresponding decrement of exactly 1 in `Inventory.StockQuantity` for that UPC and a corresponding entry in `Transactions`.
2. **No double-count / no lost decrement**: Concurrency or crashes must not cause the system to apply the decrement 0 times (lost update) or >1 times (double decrement for single sale).
3. **Eventual reflectivity**: If payment completes, the inventory and transaction records must commit consistently (the system must not reflect payment without decrement or decrement without record of payment).
4. **No phantom units**: Stock counts must be non-negative if the business forbids negative inventory (or the system must track backorders separately).

### Database translation

* Wrap the inventory decrement and transaction insert in a **single ACID transaction**.
* Use a **CHECK** or application logic to prevent `StockQuantity < 0` (if business rule forbids negative).

---

# LOGIC 3 — Perspectival Easing: Transaction Flow (how things look at the point-of-sale and how the system eases between axioms and applied rules)

You told me Logic 3 comes *before* Logic 2 in the narrative: user sees Logic 3 (the scan, immediate feedback), Logic 3 observes the constraints of Logic 1 and eases transition to Logic 2. I’ll adopt that ordering:

1. **User action (scan barcode)**: The cashier scans a UPC. From the cashier’s perspective, they expect instant price retrieval, and near-instant success/failure feedback for the sale. They don’t see the internal DB steps.
2. **POS system (client)**: Issues a read (SELECT) to fetch product details; prepares to initiate the sale.
3. **DB transaction begins**: POS opens a transaction; executes read, update, insert inside it.
4. **User receives success/failure**: the POS commits or aborts and shows the result.

I will show the full low-level sequence (messages, DB locks, logs) — that’s the real “easing” between axioms and constraints.

---

# From theory to SQL — full schema with every reasonable constraint

I will present the schema I’ll use for the rest of the explanation. I deliberately include constraints (PK, FK, UNIQUE, NOT NULL, CHECK) and helpful indexes.

```sql
-- PRODUCTS: master list; UPC is authoritative
CREATE TABLE Products (
  UPC VARCHAR(14) NOT NULL PRIMARY KEY,     -- Axiom 1
  ProductName VARCHAR(255) NOT NULL,
  RetailPrice DECIMAL(10,2) NOT NULL CHECK (RetailPrice >= 0),
  CategoryID INT,
  SupplierID INT,
  CreatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- INVENTORY: current physical stock counts
CREATE TABLE Inventory (
  InventoryID INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  UPC VARCHAR(14) NOT NULL,
  StockQuantity INT NOT NULL CHECK (StockQuantity >= 0),
  LastRestockDate DATETIME,
  CONSTRAINT fk_inv_prod FOREIGN KEY (UPC) REFERENCES Products(UPC)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,
  UNIQUE (UPC)     -- There is exactly one inventory row per UPC in this design
);

-- TRANSACTIONS: immutable audit of sales
CREATE TABLE Transactions (
  TransactionID BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  UPC VARCHAR(14) NOT NULL,
  SalePrice DECIMAL(10,2) NOT NULL CHECK (SalePrice >= 0),
  Quantity INT NOT NULL CHECK (Quantity > 0),
  SaleTime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CashierID INT,
  PaymentStatus ENUM('PENDING','COMPLETED','FAILED') NOT NULL DEFAULT 'PENDING',
  CONSTRAINT fk_trans_prod FOREIGN KEY (UPC) REFERENCES Products(UPC)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
);
```

**I chose** `UNIQUE (UPC)` on Inventory to force the one-row-per-product invariant. I use `CHECK (StockQuantity >= 0)` to enforce non-negative inventory at the DB level, but I’ll discuss concurrency and how to avoid transient violations.

---

# The atomic sale: SQL and exact engine-level steps

I will now unblackbox the “sale” operation. I’ll show:

1. Application-level call (pseudocode / stored-procedure usage).
2. Exact SQL inside a transaction.
3. The DB engine’s internal steps (locks, logs, buffer, undo/redo, MVCC behavior) for each statement.
4. How ACID properties are satisfied.

## A – High-level application call (POS)

I will call the stored procedure `Execute_Sale(UPC, Quantity, CashierID)`.

### POS pseudocode

```python
def execute_sale(upc, qty, cashier_id):
    # 1. read product and price
    product = db.query("SELECT UPC, ProductName, RetailPrice FROM Products WHERE UPC = %s", upc)
    if not product:
        return {"success": False, "reason": "unknown_upc"}

    # 2. call stored proc (atomic work happens in DB)
    result = db.callproc("Execute_Sale", [upc, qty, cashier_id])
    return result
```

**I’m sending the heavy lifting to the DB** so the engine ensures atomicity, locking, crash-safety, and logging.

## B – Stored procedure + transaction (MySQL / pseudo-PL)

I will write a MySQL-style stored procedure that does everything in one transaction, with explicit checks and error handling. I’ll show the SQL then step-by-step engine internals.

```sql
DELIMITER $$

CREATE PROCEDURE Execute_Sale(
    IN p_upc VARCHAR(14),
    IN p_qty INT,
    IN p_cashier INT
)
BEGIN
  DECLARE v_price DECIMAL(10,2);
  DECLARE v_stock INT;

  -- Start a transaction
  START TRANSACTION;

  -- Step 1: read current price and stock
  SELECT RetailPrice INTO v_price FROM Products WHERE UPC = p_upc FOR SHARE;  -- or use SELECT ... LOCK IN SHARE MODE
  IF v_price IS NULL THEN
    ROLLBACK;
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Product not found';
  END IF;

  SELECT StockQuantity INTO v_stock FROM Inventory WHERE UPC = p_upc FOR UPDATE;
  IF v_stock IS NULL THEN
    ROLLBACK;
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Inventory row missing';
  END IF;

  -- Business rule: cannot sell more than stock (simple example)
  IF v_stock < p_qty THEN
    ROLLBACK;
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Insufficient stock';
  END IF;

  -- Step 2: update inventory (atomic decrement)
  UPDATE Inventory
    SET StockQuantity = StockQuantity - p_qty,
        LastRestockDate = LastRestockDate
    WHERE UPC = p_upc;

  -- Step 3: insert transaction record (audit)
  INSERT INTO Transactions (UPC, SalePrice, Quantity, CashierID, SaleTime, PaymentStatus)
  VALUES (p_upc, v_price, p_qty, p_cashier, NOW(), 'COMPLETED');

  -- Optional verification: ensure inventory remained non-negative (defensive)
  SELECT StockQuantity INTO v_stock FROM Inventory WHERE UPC = p_upc;
  IF v_stock < 0 THEN
    ROLLBACK;
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Negative stock after update – abort';
  END IF;

  COMMIT;
END$$

DELIMITER ;
```

### Why `FOR UPDATE` / `FOR SHARE`?

* `SELECT ... FOR UPDATE` acquires an exclusive lock (or necessary MVCC protection) on the Inventory row to prevent concurrent updates that would cause lost updates. This ensures the subsequent `UPDATE` is logically consistent in presence of concurrent transactions.
* `SELECT ... FOR SHARE` (or `LOCK IN SHARE MODE`) for `Products` prevents concurrent schema-level changes to product data while still allowing reads.

---

## C – Engine-level internal trace — every step, precisely

I will now follow a **single execution** of `Execute_Sale('737628064502', 1, 17)`. I’ll name the transaction `T1`, and I’ll also show a concurrent transaction `T2` that tries to sell the same UPC at the same time to illustrate isolation and locking.

### 1. T1: `START TRANSACTION;`

* DB: creates a transaction context structure `txn_T1`.
* Engine sets `txn_T1` status to active.
* No locks yet; undo/redo logs reserved in memory for this txn.

### 2. T1: `SELECT RetailPrice ... FOR SHARE;`

* Because it’s a read-of-master-data, engine:

  * If using MVCC (e.g. InnoDB): reads the current consistent snapshot version of `Products` (snapshot visibility determined by transaction isolation level). No exclusive lock needed; `FOR SHARE` may record a predicate lock or intend-share depending on engine. InnoDB supports shared locks for `LOCK IN SHARE MODE`.
  * Returns `v_price`.
* From my perspective, this is instantaneous logically, but the DB may read pages into the buffer pool from disk if not cached.

### 3. T1: `SELECT StockQuantity INTO v_stock FROM Inventory WHERE UPC = p_upc FOR UPDATE;`

* Engine locates the `Inventory` index record for UPC (unique index lookup).
* **Lock acquisition**:

  * In a pessimistic locking model, engine acquires an **exclusive (X) lock** on the matched row(s) — meaning no other transaction can modify that row until `COMMIT/ROLLBACK`.
  * In an MVCC model, `SELECT ... FOR UPDATE` still prevents conflicting updates by taking X locks (or marking row as locked in the transaction).
* Engine reads `v_stock` and keeps the lock held in `txn_T1`.

### 4. Concurrent T2 attempts same `SELECT ... FOR UPDATE` at the same time

* T2 will attempt to acquire X lock on the same row. Since T1 already holds X, T2 will **block** (wait) until T1 commits or rolls back, or until T2’s wait timeout occurs.
* This blocking enforces **serializability of the concurrent updates**. I note: blocking vs. non-blocking depends on engine—some use optimistic MVCC and detect conflicts at commit.

### 5. T1 performs `IF v_stock < p_qty THEN ...` check

* If `v_stock` < `p_qty`, T1 rolls back and releases locks.

### 6. T1 executes `UPDATE Inventory SET StockQuantity = StockQuantity - p_qty WHERE UPC = p_upc;`

* Engine modifies the row in its **buffer pool** (memory):

  * It creates an **undo record** describing the previous value (for potential rollback) and records the new value to page.
  * It appends a **redo log entry** to the transaction’s in-memory redo buffer (to be flushed later to the redo log).
  * The in-memory page is marked dirty. The row remains locked by T1.
* At this point, other transactions (like T2) are still blocked from updating that row.

### 7. T1 executes `INSERT INTO Transactions (...)`

* Engine inserts the new row into the `Transactions` clustered/index page (or appends to the table structure).
* Undo record created for this insert (so it can be undone on rollback). Redo entry appended.

### 8. Optional verification and final `COMMIT`

* `COMMIT` triggers engine to:

  * Flush redo log entries to durable storage (the log file / redo log) — **this is the point of durability guarantee** for committed transactions. The exact moment depends on `innodb_flush_log_at_trx_commit` (MySQL detail) but the principle is that commit requires the redo to be safely on disk to prevent lost commits after a crash.
  * Release locks held by `txn_T1`.
  * Mark undo logs as no longer needed by T1 (they are kept for MVCC snapshot visibility until older snapshots are gone and purge occurs).
* Once commit returns success, the POS can inform the cashier: “Sale completed.”

### If crash happens before `COMMIT`

* If the DB process or machine crashes after T1 updated the buffer pool but before the redo log is flushed to disk and the transaction committed, on restart:

  * The REDO/UNDO system uses the on-disk redo log to **replay committed transactions** and **undo** uncommitted changes. Because commit did not persist the redo, the engine will **rollback** the partial changes using undos — this prevents inconsistencies.
  * In other words, either the update+insert completed (commit reached durable log) or the system rolled it back — atomicity preserved.

### Why `StockQuantity = StockQuantity - p_qty` as an atomic update is safe here

* Because we locked the Inventory row for update before reading and updating, concurrent transactions cannot interleave and cause lost updates.
* The engine’s undo/redo logging ensures that the update is durable only if the transaction commits; otherwise, rollback restores previous state.

---

# ACID, revisited in machine terms (I will expand each property and map to the steps above)

## Atomicity (A)

* **Definition**: The set of operations in a transaction either all occur or none do.
* **Mechanism**: Undo log + transaction boundaries.
* **Step-by-step**:

  * When T1 begins, any changes create undo records describing the previous versions of rows.
  * If T1 commits, the DB ensures redo log contains entries to reapply the changes if needed after a crash, and then undos can be discarded/purged later.
  * If T1 aborts, the DB applies undo records to restore the old state.
* **Why this matters**: If power cuts out after `INSERT` but before `UPDATE` (or vice versa), the DB will either completely rollback or appear to have both, depending on commit state — though the stored procedure seeks to do both before commit.

## Consistency (C)

* **Definition**: The transaction moves database from one valid state to another valid state, respecting constraints (foreign keys, CHECKs, triggers).
* **Mechanism**:

  * Schema-level checks (FK, CHECK) are evaluated during DML; violation causes acceptance failure and rollback.
  * Application-level logic (e.g., do not allow `StockQuantity < 0`) must be reflected in the DB schema (CHECK) or enforced by transactional code.
* **Caveat**: DB-level constraints are the last guard; application-level checks can still cause inconsistencies if not enforced in DB constraints or a transaction.

## Isolation (I)

* **Definition**: Concurrent transactions must not interfere; the system must behave as if transactions executed serially (for serializable isolation) or in a permissible weaker model for performance.
* **Mechanisms**:

  * **Pessimistic locking**: `SELECT FOR UPDATE` acquires locks preventing others from mutating rows.
  * **MVCC**: Each transaction reads a consistent snapshot while writers create new versions; conflicts detected at commit.
* **Isolation levels and anomalies**:

  * **READ UNCOMMITTED**: dirty reads allowed.
  * **READ COMMITTED**: avoids dirty reads, but non-repeatable reads/phantoms possible.
  * **REPEATABLE READ**: InnoDB default; prevents non-repeatable reads; phantoms are more nuanced.
  * **SERIALIZABLE**: strictest; can add locks and prevent phantoms.
* **For the supermarket**: I **prefer** `REPEATABLE READ` or `SERIALIZABLE` for inventory updates; but `FOR UPDATE` locking plus the stored procedure ensures safe inventory decrements even at lower isolation levels because we explicitly lock the rows we modify.

## Durability (D)

* **Definition**: Once a transaction commits, its effects survive crashes.
* **Mechanisms**:

  * Write-ahead logging (WAL): changes are written to a redo log persisted before acknowledging commit.
  * Engine configuration (fsync behavior) controls exact flush semantics.
* **Tradeoffs**:

  * Aggressive fsync on commit gives strongest guarantee but at I/O cost.
  * Delayed flush risks losing recently committed transactions on crash.

---

# Concurrency anomalies and how to prevent them — full unblackboxing

I will enumerate possible problematic interleavings and how the stored-procedure/locking pattern prevents them. I will give small stepwise examples of how anomalies can happen *without* appropriate locks and how our pattern prevents them.

## Problem: Lost update

* **Scenario**: T1 reads Stock=10, T2 reads Stock=10. T1 sets Stock=9 and commits. T2 sets Stock=9 and commits — net change: -1 instead of -2.
* **Without locks**: both read then write based on old value — lost update.
* **With `SELECT ... FOR UPDATE` and row lock**:

  * T1 obtains X lock, T2 blocks when trying to `FOR UPDATE`. T1 updates to 9, commits, releases lock, then T2 runs, re-reads stock (now 9), updates to 8. No lost update.

I will explicitly trace the read-modify-write sequence to show the correct outcome.

## Problem: Dirty read / phantom / inconsistent read

* Dirty read: reading uncommitted changes from another txn. Avoid with READ COMMITTED or better.
* Phantom: inserts match a predicate that a repeatable read earlier didn't see. Inventory with unique UPC typically prevents phantoms for same UPC, but range locks or secondary indices can matter if using `SELECT ... WHERE StockQuantity > 0`.
* **Solution**: Use `FOR UPDATE` for rows you will examine and update; use appropriate isolation level for reads.

---

# Edge cases, failures and recovery — exhaustive list, and how we handle them

I will list every realistic failure mode and state how the system behaves and how to mitigate.

## 1. POS crashes after payment accepted but before DB call

* **Symptom**: Customer paid; DB never gets the transaction.
* **Mitigation**: Payment and DB commit should be coordinated or payment gateway callback should be used. Use idempotency tokens so repeated retries do not create duplicate transactions.

## 2. DB crashes after inventory update but before transaction insert

* **Mechanism**: If `COMMIT` not reached, the redo log lacks the commit entry; on restart, undo runs and state rolls back — inventory not decremented.
* **Potential business issue**: Customer paid but sale not recorded because the POS thought commit succeeded before actually seeing it.
* **Mitigation**:

  * Ensure POS waits for DB commit confirmation before printing receipt.
  * Use two-phase commit between payment processor and DB, or implement a careful retry/compensating process: if payment succeeded but DB didn't persist, create a compensating transaction (refund or manual reconciliation).

## 3. Concurrency causing negative stock (race without locks)

* **Prevention**: locks (FOR UPDATE) and `CHECK (StockQuantity >= 0)` to catch anomalies if they slip in.

## 4. Partial commit in distributed setting (multiple databases)

* **Problem**: If sale updates Inventory on one shard and Transactions on another, they may not commit atomically.
* **Mitigation**: Use a distributed transaction protocol (2PC), or design for eventual consistency with an idempotent event-driven pipeline and compensating transactions. 2PC has availability costs.

## 5. Network partition between POS and DB

* **Behavior**: POS may be uncertain whether commit succeeded.
* **Mitigation**: POS should block until commit or adopt asynchronous design with reconciliation. Use unique sale identifiers and idempotent operations so retries are safe.

## 6. Hardware failure causing redo log to be lost (corruption)

* **Mitigation**: use mirrored/replicated storage, and a reliable backup and replication pipeline.

---

# Analytics and aggregation — how transactional data becomes analytics-ready and why it’s safe

You showed `SELECT SUM(SalePrice) FROM Transactions WHERE DATE(SaleTime) = CURDATE();`. I will show the exact concerns and propose robust solutions.

## Issues and solutions

1. **Realtime correctness**: If transactions are in flight, should aggregate include them?

   * **If you need exact real-time:** run query in the same DB with appropriate isolation to include committed transactions only. InnoDB `READ COMMITTED` returns committed rows.
   * **If eventual consistency is acceptable:** read from read-replica (lag may cause slight undercounts).
2. **Performance**: aggregating over millions of rows can be slow.

   * **Solution**: maintain a derived aggregate table (daily_sales) updated transactionally (e.g., within same transaction or by transactional outbox) or use materialized views / OLAP ETL.
3. **Precision**: ensure DECIMAL arithmetic used (not FLOAT) to avoid rounding errors.
4. **Auditability**: keep immutable `Transactions` and never update them except for allowed corrections with audit trail.

### Example: transactional per-sale increment to daily aggregate (safe)

```sql
-- table for fast daily total
CREATE TABLE DailyRevenue (
  Day DATE PRIMARY KEY,
  TotalRevenue DECIMAL(15,2) NOT NULL DEFAULT 0
);

-- Within Execute_Sale transaction, after INSERT:
UPDATE DailyRevenue SET TotalRevenue = TotalRevenue + v_price * p_qty
WHERE Day = CURRENT_DATE();

-- or INSERT ... ON DUPLICATE KEY UPDATE ... to create the row if missing
```

**Note**: Doing this inside the same transaction keeps consistency but increases contention on DailyRevenue row (serialization hotspot). For high throughput you may prefer event-streaming (Kafka) and an aggregator.

---

# Tests, invariants, and proofs — how to be sure the axioms hold

I’ll produce test cases you can run and how to reason about them.

## Unit test 1 — Single sale, happy path

* Setup: Inventory.StockQuantity = 10
* Action: Execute_Sale(upc, 1)
* Expected: Inventory.StockQuantity = 9; a Transaction row exists with `Quantity=1` and `SalePrice=RetailPrice`.

## Unit test 2 — concurrent sales: T1 and T2 both sell 1 unit from stock 1

* Setup: Stock = 1
* Spawn T1 and T2 calling `Execute_Sale(upc, 1)` concurrently.
* Expected outcome: One completes (Stock becomes 0), the other fails with `Insufficient stock` (or blocks and then fails).
* **Why**: lock prevents both from decrementing to negative or double-selling.

## Unit test 3 — crash during transaction

* Setup: In test harness, simulate crash after inventory `UPDATE` but before `INSERT` and before commit.
* Expected: after restart, no decrement persisted (atomicity) and no transaction row exists.
* **How to test**: Use an engine with crash simulation tools or stop the DB process mid-transaction.

## Proof sketch of inventory invariant (informal)

Given:

* `Inventory` has exactly one row per UPC.
* Updates happen only inside transactions that lock the row (`FOR UPDATE`), and commit steps flush redo before acknowledging.
* No external process updates the same row without lock.

Then:

* Any committed transaction that decremented Stock did so with exclusive possession of the row at the time of update, and the DB serialized these updates, so final stock equals initial minus sum of committed decrements. This is a direct mapping of serial execution.

I’m explicit that this proof relies on the engine correctly implementing locking and WAL.

---

# Schema evolution, migrations, and safe changes — how to change the black boxes without violating axioms

I will show how to add columns or change constraints while preserving invariants.

## Example: converting the inventory to allow negative stock (backorders)

* New business rule: allow `StockQuantity` negative for backorders.
* Steps:

  1. Create new column `AvailableQuantity` or `BackorderAllowed` flag to avoid immediate change.
  2. Migrate logic: change stored procedure to check `if not BackorderAllowed and Stock < qty then abort`.
  3. Once app and tests validated, alter `CHECK (StockQuantity >= 0)` to remove the check.

I **never recommend** removing FK/NOT NULL/CHECKs before ensuring code paths are ready, because temporarily relaxing constraints can allow inconsistent data.

---

# Advanced considerations — scaling, distributed inventory, eventual consistency

Your supermarket may be local (single DB) or distributed across stores. I will cover both.

## Single-node / single DB (simpler)

* Use the pattern above. Pros: strong consistency, simple.
* Cons: throughput limit at DB, single point of failure.

## Multi-store common inventory (distributed)

* If multiple locations share inventory numbers centrally, you face latency and availability tradeoffs.
* Design options:

  1. **Centralized DB** — all stores query central DB; simple consistency, network latency.
  2. **Local caches + central reconciliation** — allow local sells, reconcile later (eventual consistency). Must accept occasional oversells and implement compensation.
  3. **Partition by UPC ranges** — shard inventory across nodes; requires routing.
  4. **Distributed transactions** (2PC) — ensure atomic multi-node commit; costly and availability-weak under partitions.

### Two-Phase Commit (2PC) sketch

* Coordinator tells participants to prepare (they write a prepare record, flush redo to disk), then the coordinator issues commit. This ensures atomic commit across nodes, but if coordinator fails during commit phase, participants block waiting — availability concern.

### Idempotency and event-sourcing alternative

* Use an event log (append-only) of `SaleAttempt` events; consumers compute inventory. Use idempotent event processing and snapshots. This design is resilient and scales, but you give up immediate strong consistency (inventory counts are eventually consistent).

---

# Observability, monitoring, and alerting — how to know your invariants are holding

I will list metrics and checks I would put into production.

1. **Inventory vs. expected baseline**: periodic reconciliation between physical counts and DB counts (cycle counts).
2. **Transaction-per-second** and **lock-wait times**: if lock waits spike, contention problem.
3. **Rollback ratio**: aborted transactions vs. total — high value indicates business or coding issues.
4. **Replication lag** (if you have replicas): ensure analytic queries do not read stale data that confuse reporting.
5. **Daily sales totals** compared to payment processor logs — detect missing/incomplete writes.
6. **Deadlock count**: increase indicates concurrency design issues.

---

# Hardening: additional DB-level defenses I add to "never violate inventory integrity"

I will present a stronger, more defensive stored procedure and DB features.

## 1. Use optimistic check when high concurrency but short critical section

* If locking is too costly, read stock, attempt `UPDATE Inventory SET StockQuantity = StockQuantity - p_qty WHERE UPC = p_upc AND StockQuantity >= p_qty;` and check affected row count. If 0 rows affected, abort (another txn beat you or insufficient stock). This avoids explicit `SELECT FOR UPDATE` but relies on row-level atomic `UPDATE ... WHERE` semantics.

## 2. Use `INSERT` audit + compensation for eventual consistency systems

* Append event to `SalesEvents` (immutable), and let an aggregator consume events to update Inventory. The aggregator must be idempotent and durable.

## 3. Implement an *outbox* pattern for cross-system reliability

* When you need to call a payment processor AND persist a transaction, write a record to `Outbox` in the same DB transaction; a separate reliable worker reads outbox and sends to external systems. This ensures the external calls are consistent with DB commits.

---

# Full worked example with precise SQL alternatives and tradeoffs

I will show three precise approaches to perform a sale, explain step-by-step engine behavior, and recommend when to use each.

## Approach A — Pessimistic lock (my earlier stored procedure) — recommended for moderate throughput, high correctness

* `START TRANSACTION; SELECT StockQuantity ... FOR UPDATE; UPDATE ...; INSERT ...; COMMIT;`
* **Engine actions**: locks row(s), writes undo/redo, flush redo on commit.
* **Pros**: correctness, simple reasoning.
* **Cons**: contention if many sells of same UPC at same time.

## Approach B — Atomic conditional update (no explicit SELECT lock)

```sql
START TRANSACTION;
SELECT RetailPrice INTO v_price FROM Products WHERE UPC = p_upc;
-- atomic conditional update
UPDATE Inventory SET StockQuantity = StockQuantity - p_qty WHERE UPC = p_upc AND StockQuantity >= p_qty;
IF ROW_COUNT() = 0 THEN
  ROLLBACK; SIGNAL 'Insufficient stock';
END IF;
-- insert transaction
INSERT INTO Transactions (...);
COMMIT;
```

* **Why it works**: `UPDATE ... WHERE ...` executes atomically at the row level; the affected-rows test tells you if the update succeeded or another txn beat you.
* **Pros**: less locking contention for the read path.
* **Cons**: still susceptible to race if you need `v_price` to match the exact time of sale (but we read price before update).

## Approach C — Event-sourced / asynchronous (Recommendation only if you accept eventual consistency)

* Append immutable event to `SalesEvents`.
* Worker consumes and updates `Inventory`.
* **Pros**: scalable, easy to audit.
* **Cons**: inventory not immediate, possible oversell until reconciliation.

---

# Formalized invariants and short mathematical reasoning

I’ll write invariants as formulas and show how transaction serializability preserves them.

Let `Stock0(UPC)` be starting stock, and let `D = {d1,d2,...dn}` be a set of decrements (each dj ∈ ℕ). Each committed transaction corresponds to a decrement of some dj items.

**Invariant**: `Stock_final(UPC) = Stock0(UPC) - Σ_{committed transactions} dj`

**Argument**:

* Each committed transaction executes an atomic update that changes `Stock` by `-dj`. Because of serializability (or because we lock the row), all committed updates are equivalent to some serial ordering of transactions; hence final stock is initial minus sum of decrements in that serial order. The DB ensures serializability of conflicting updates via locking or MVCC conflict detection; thus invariant holds.

**Assumptions**: all updates path that modify `Stock` are either inside properly serialized transactions or enforced by constraints. If an external system (manual DB edits) modifies `Stock` outside transactions or bypasses constraints, invariants may be broken.

---

# Reconciliation and human workflows (because real stores have humans and errors)

Even with machine guarantees, humans make mistakes. I will outline safe operational policies and example procedures for reconciliation:

1. **End-of-day reconciliation**:

   * SKU-by-SKU compare `db_stock` vs `physical_count`.
   * Differences logged into `InventoryAdjustments` with reason and user who adjusted.
2. **Manual correction UI**:

   * Allow an adjustment transaction that updates `Inventory` and inserts an audit row; require supervisor sign-off for large adjustments.
3. **Compensation pattern**:

   * For payment-system mismatches, log a `PaymentMismatch` and create a workflow for operator to reconcile.

---

# Documentation / teaching-style TL;DR (but I will not skip details as you demanded)

I will summarize the actionable design choices with a terse checklist (this is still part of the exhaustive explanation, presented as a quick reference):

* **DB schema**: `Products(UPC PK)`, `Inventory(UPC FK UNIQUE, StockQuantity CHECK >=0)`, `Transactions (immutable)`.
* **Atomic sale**: perform `UPDATE Inventory` and `INSERT Transactions` inside a single DB transaction. Use row locking or atomic conditional update to avoid races.
* **Use DECIMAL for monetary values**: prevents floating-point rounding issues.
* **Durability**: set DB to flush redo logs at commit for strong durability; accept performance cost or mitigate with replication.
* **Concurrency**: for high contention SKUs (e.g. limited items), consider queuing or sharding.
* **Scalability**: for very high throughput, use event-sourcing and eventual consistency with idempotent processors and reconciliation mechanisms.
* **Monitoring**: watch lock waits, rollback ratio, replication lag, and daily reconciliation mismatches.
* **Human processes**: provide audit trails, adjustment records, and supervisor approval.

---

# Practical appendix — complete example session with interleaving and expected outcomes

I’ll provide a step-by-step example where two cashiers race to buy the last banana — I will show SQL and the engine events.

### Initial state

* Inventory(UPC='737628064502', StockQuantity=1)

### Two concurrent attempts: T1 and T2

**T1**: START TRANSACTION
**T2**: START TRANSACTION

**T1**: SELECT StockQuantity FROM Inventory WHERE UPC='...' FOR UPDATE;  — obtains X lock, reads Stock=1
**T2**: SELECT StockQuantity FROM Inventory WHERE UPC='...' FOR UPDATE;  — blocked

**T1**: UPDATE Inventory SET StockQuantity = StockQuantity - 1 WHERE UPC='...'; — sets Stock=0
**T1**: INSERT Transactions (... Quantity=1 ...)
**T1**: COMMIT  — flushes redo log for T1, releases lock

**T2** unblocks, resumes:
**T2**: SELECT StockQuantity returns Stock=0
**T2**: v_stock < p_qty -> ROLLBACK -> SIGNAL Insufficient stock

**Outcome**: only one transaction committed; invariant holds.

---

# Closing — what I would implement for production (my concrete recommendation)

If you asked me to implement a robust supermarket backend, I would do:

1. **Schema** as above (Products PK, Inventory UNIQUE UPC, Transactions immutable).
2. **Stored Procedure** `Execute_Sale` implementing `SELECT ... FOR UPDATE`, conditional `UPDATE` (safe variant), `INSERT Transactions`, `COMMIT`, with robust SIGNALs for errors.
3. **Outbox pattern** for external interactions (payment processors), so the DB commit contains the event that the payment worker can pick up. This prevents split-brain between payment and DB writes.
4. **Monitoring** (lock waits, rollbacks, replication lag).
5. **Reconciliation** jobs and human workflows.
6. **Testing harness** for crash simulation and concurrency testing (simulate interleavings and verify invariants).
7. **Documented operational playbooks** for failures (e.g., what to do if DB crashes mid-sale and customers are uncertain).

