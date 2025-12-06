# Logic 1: The Foundation — The Mechanics of the Pipe

Before we can argue about *how* to lock data, I must understand the machinery that allows me to touch the data at all. I see lines of code like `new SqlConnection` and `BeginTransaction`. These are not magic spells; they are heavy, mechanical operations.

### The Connection (`SqlConnection`)
> `var conn = new SqlConnection(cs);`
> `conn.Open();`

**What is this?**
I am creating a bridge. The `cs` (Connection String) is not just a string; it is a coordinate system. It contains an IP address (a location in the world), a Port (a specific door on that machine), and credentials (the key to the door).

**The Deep Reality:**
When I say `conn.Open()`, I am triggering a **TCP/IP Handshake**.
1.  My computer sends a `SYN` (Synchronize) packet to the database server. "Are you there?"
2.  The server replies `SYN-ACK`. "I am here, and I hear you."
3.  My computer sends `ACK`. "Good. We are connected."

This represents a **stateful pipe**. A physical pathway of electricity and light is now reserved for my conversation. If the internet blinks, this object dies.

### The Transaction (`BeginTransaction`)
> `var tran = conn.BeginTransaction();`

**Why do I need this?**
By default, databases are "autocommit." If I run a command, it happens immediately and permanently. But here, I have a sequence of events.
1.  Check stock.
2.  Decide if I can buy.
3.  Take stock away.

If the power fails after step 2 but before step 3, I have decided to buy, but I haven't taken the stock. The world is broken.

**The "ACID" Postulate:**
`BeginTransaction` creates a "sandbox." Everything I do inside this scope is **Atomic**.
* **Atomicity:** From the Greek *atomos* (uncuttable). It means either *all* of these lines happen, or *none* of them happen.
* The database engine creates a log entry: "User X has started a story. Do not write the ending to the permanent record (the disk) until User X says `Commit`."

### The Command (`SqlCommand`)
> `var cmd1 = new SqlCommand("SELECT...", conn, tran);`

**The Envelope:**
I am wrapping a text string (SQL) into a packet. Notice I pass `tran`. This is crucial. I am telling the database: "This command belongs to the sandbox I created earlier. Do not execute this in the public space; execute it in my private transaction context."

**The Parameter (`@id`):**
> `cmd1.Parameters.AddWithValue("@id", productId);`

**Why not just stick the ID in the string?**
If I wrote `"SELECT ... WHERE ProductId=" + productId`, I am sending raw text. If `productId` is `1 OR 1=1`, I have just allowed a hacker to read my entire database (SQL Injection).
By using `Parameters`, I am sending the data *separately* from the code. The database engine treats `@id` as a literal value, never as executable code. It is the difference between handing someone a note that says "slap me" and handing someone a note that says "read the phrase 'slap me'".

---

# Logic 3: The Pre-cursor — The Crisis of "Togetherness"

Now that I understand the tools (Connection, Transaction, Command), I must ask: **Why is the code below so complicated? Why can't I just read the stock and subtract 1?**

I need to visualize the enemy. The enemy is **Concurrency**.

Imagine two users, **Alice** and **Bob**.
The database has 1 iPhone left in stock (`Stock = 1`).

**The Naive Timeline (If we didn't use the logic in your code):**

1.  **Alice** reads the database. She sees `Stock = 1`.
2.  **Bob** reads the database. He *also* sees `Stock = 1` (because Alice hasn't bought it yet).
3.  **Alice** calculates: $1 - 1 = 0$. She sends `UPDATE Stock = 0`.
4.  **Bob** calculates: $1 - 1 = 0$. He sends `UPDATE Stock = 0`.

**The Result:** Two people bought the phone. We sold 2 phones, but we only had 1. This is a **Race Condition**.

I need a diagram to visualize this fracturing of time.



This is the problem both the "Optimistic" and "Pessimistic" blocks of code are trying to solve. They are trying to force a single-file line in a multi-lane world.

---

# Logic 2: Constraint Satisfaction — The Two Paths

Now I enter the specific logic used to solve the Crisis of Togetherness (Logic 3) using the Tools (Logic 1).

## Path A: The Optimistic Approach
*(First block of code)*

**The Philosophy:** "I trust that people rarely fight over the same item. I will let everyone read freely, but I will double-check before I write."

This is like a library with no checkout counter. You take the book, but before you leave the building, a scanner checks if anyone else took the "soul" of the book while you were holding it.

### Step 1: The Setup with a "Version"
> `SELECT Stock, Version FROM Inventory...`

I am not just reading the `Stock`. I am reading a `Version`.
* **What is a Version?** It is a "truth marker." It could be a number (1, 2, 3) or a random UUID.
* **Current State:** Alice reads `Stock = 5`, `Version = 100`.

### Step 2: The Logic Gap
> `if (stock < qty) throw new Exception();`

I do my thinking here. This takes time (microseconds or milliseconds). During this time, Bob might slip in and change the stock.

### Step 3: The Conditioned Update (The Genius Move)
> `UPDATE Inventory SET Stock = Stock - @q WHERE ProductId=@id AND Version=@v`

This is the most critical line in the optimistic block.
I am saying to the database:
"Update this row... **BUT ONLY IF** the Version is still the number I memorized earlier (`@v`)."

**Let's trace the logic:**
1.  Alice memorized `Version = 100`.
2.  While Alice was thinking, Bob bought an item. Bob updated the row and incremented the Version to `101`.
3.  Alice finally sends her update: `UPDATE ... WHERE Version = 100`.
4.  The Database looks at the row. It sees `Version = 101`.
5.  Does `101 == 100`? **No.**
6.  The Database **skips the update**. It touches 0 rows.

### Step 4: The Detection
> `int rows = cmd2.ExecuteNonQuery();`
> `if (rows == 0) throw new Exception("Optimistic concurrency conflict.");`

I asked the database to make a change. The database told me, "I changed 0 rows."
**Why?** Because the `WHERE` clause failed.
**Conclusion:** Someone changed the data under my feet. I cannot proceed. I must fail or try again.



[Image of optimistic concurrency control flow]


---

## Path B: The Pessimistic Approach
*(Second block of code)*

**The Philosophy:** "I trust no one. The moment I look at an item, I am putting my hand on it. No one else can touch it until I am done."

This is like a one-person bathroom. When I go in, I lock the door. No one else can enter until I leave.

### Step 1: The "Locked" Read
> `SELECT Stock FROM Inventory WITH (UPDLOCK, ROWLOCK)`

This is the aggressive move.
* **ROWLOCK:** "I am only locking this specific row (Product 42), not the whole table."
* **UPDLOCK (Update Lock):** "I am reading this now, but I intend to change it later."

**The Consequence:**
If Alice runs this line, she places a "flag" in the database memory on that row.
If Bob tries to run the same line 1 millisecond later, the database stops Bob. Bob's code simply **pauses**. He waits. And waits. And waits.

### Step 2: The Safety Bubble
> `if (stock < qty) throw new Exception();`
> `UPDATE Inventory SET Stock = Stock - @q ...`

Because I have the lock, I am the **God of this Row**.
I know for a fact that `Stock` cannot change between my Read and my Update. Bob is stuck waiting outside the door.
I do not need to check a `Version`. I do not need a `WHERE` clause checking the state. I own the state.

### Step 3: The Release
> `tran.Commit();`

The moment I commit, the transaction ends. The lock is dissolved.
Bob, who was waiting, is now allowed to enter. He reads the *new* value immediately.


---

Nice — I’ll unblackbox everything and give a full, rigorous, ground-up explanation and production-ready guidance for **both** your optimistic and pessimistic flows. I’ll speak in the first person (“I …”) to mirror your requested voice, but I will **not** reveal internal chain-of-thought — instead you’ll get explicit, testable reasoning, code, and concrete scenarios.

I’ll cover:

1. Precise definitions and DB schema assumptions.
2. Line-by-line unblackboxing of **optimistic** code: exact effects, failure modes, fixes.
3. Line-by-line unblackboxing of **pessimistic** code: exact effects, failure modes, fixes.
4. Concrete concurrent timelines showing races, outcomes, and how each pattern behaves.
5. Strong, production-ready implementations for both patterns (C# + SQL) with robust parameter typing, error handling, and retry/rollback behavior.
6. Recommendations, metrics to monitor, and test cases you can run.

---

# 0 — Foundations: definitions and schema (ground-up)

I’ll start from postulates (simple, explicit assumptions). Every later claim depends on these being true.

## Postulates (explicit assumptions)

1. The database is Microsoft SQL Server.
2. The `Inventory` row exists for the `ProductId` used (we will show how to handle missing rows).
3. The `Stock` column is an integer representing available items (no fractional items).
4. Concurrency must prevent selling more stock than exists (no negative stock).
5. We can modify schema (add constraints/indexes) if helpful.
6. Application is C# using ADO.NET (`SqlConnection`, `SqlCommand`) — code must properly Dispose resources.

## Minimal recommended schema (explicit)

I recommend this schema to make concurrency safe and efficient:

```sql
CREATE TABLE Inventory (
    ProductId INT PRIMARY KEY,
    Stock INT NOT NULL CHECK (Stock >= 0),
    Version BIGINT NOT NULL,          -- or use rowversion
    -- Or if using SQL Server rowversion instead:
    -- Version ROWVERSION NOT NULL
    CONSTRAINT CK_Stock_NonNegative CHECK (Stock >= 0)
);

CREATE INDEX IX_Inventory_Version ON Inventory(Version);
```

Notes:

* `CHECK (Stock >= 0)` enforces DB-level nonnegativity — good defense-in-depth.
* `Version` can be:

  * a `BIGINT` you increment on every update (explicit version).
  * or a `rowversion` column (`binary(8)`, auto-updated by SQL Server). If you use `rowversion`, handle it as `byte[]` in .NET.
* Using `rowversion` is convenient (auto-updated), but comparing `rowversion` requires `binary` parameter type.

---

# 1 — Unblackboxing the **optimistic** flow (line-by-line)

Original code (condensed):

```csharp
var conn = new SqlConnection(cs);
conn.Open();
var tran = conn.BeginTransaction();

// 1. Read data + version (NO LOCKING)
var cmd1 = new SqlCommand("SELECT Stock, Version FROM Inventory WHERE ProductId=@id", conn, tran);
cmd1.Parameters.AddWithValue("@id", productId);
var r = cmd1.ExecuteReader();
r.Read();
int stock = (int)r["Stock"];
var version = r["Version"];
r.Close();

// 2. Business logic check
if (stock < qty) throw new Exception();

// 3. Update attempts to verify nobody else changed the row
var cmd2 = new SqlCommand(
    @"UPDATE Inventory
      SET Stock = Stock - @q
      WHERE ProductId=@id AND Version=@v",
    conn, tran);
cmd2.Parameters.AddWithValue("@q", qty);
cmd2.Parameters.AddWithValue("@id", productId);
cmd2.Parameters.AddWithValue("@v", version);

// 4. OCC conflict detection
int rows = cmd2.ExecuteNonQuery();
if (rows == 0)
    throw new Exception("Optimistic concurrency conflict.");

tran.Commit();
```

I’ll unblackbox each line/operation and show what it does, why, and its failure modes.

---

## 1.1 Connection and transaction

```csharp
var conn = new SqlConnection(cs);
conn.Open();
var tran = conn.BeginTransaction();
```

* `new SqlConnection(cs)` creates a client-side object describing how to reach the server.
* `conn.Open()` acquires a physical connection from the pool (or creates one), establishes a session with the DB.
* `BeginTransaction()` starts a DB transaction associated with that session. All commands issued while referencing `tran` participate in the same transaction context.
* **Important**: the transaction isolation level defaults to the server/database setting (often `READ COMMITTED`). That determines whether your `SELECT` sees committed or uncommitted rows and whether it takes shared locks.

**Consequences**:

* Transaction keeps resources (locks) alive until `Commit()` or `Rollback()`. Long transactions increase lock retention and risk deadlocks/lock escalation.
* You must `Dispose()` `conn` and `tran` properly to free pooled connections.

---

## 1.2 Read (no explicit locking)

```csharp
var cmd1 = new SqlCommand("SELECT Stock, Version FROM Inventory WHERE ProductId=@id", conn, tran);
cmd1.Parameters.AddWithValue("@id", productId);
var r = cmd1.ExecuteReader();
r.Read();
int stock = (int)r["Stock"];
var version = r["Version"];
r.Close();
```

What happens on the DB:

* SQL Server compiles the query plan and executes it.
* Under `READ COMMITTED`, the `SELECT` uses shared locks briefly (or uses read-committed snapshot if the DB has snapshot isolation enabled). There is **no** explicit locking hint (e.g. `NOLOCK`), so default lock behavior applies.
* You get a snapshot of the **committed** state at the time each row is read (unless snapshot isolation is enabled, which gives a consistent snapshot for the transaction).

Risks:

* Between this SELECT and later UPDATE, other transactions may change the same row.
* Your `version` must be typed and passed back exactly to `UPDATE`. If `Version` is `rowversion` (binary), using `AddWithValue` may pass the wrong type — prefer explicitly typed `SqlParameter`.

Edge cases you must handle:

* `r.Read()` can return `false` (no row) → code should handle "product not found".
* `Stock` might be `DBNull` if DB allows null — code needs to check or make DB forbid null.

---

## 1.3 Business logic check

```csharp
if (stock < qty) throw new Exception();
```

Interpretation:

* I make a decision in application code: if stock is insufficient, abort.
* This is **optimistic**: I assume `stock` is still valid when I attempt the update; if not, I'll detect conflict in the `UPDATE` clause.

Important nuance:

* Between this check and the `UPDATE`, the DB row may have changed; so check failure might actually be detected later and must be handled (retry, inform user, etc).

---

## 1.4 Conditional UPDATE (OCC verification)

```csharp
var cmd2 = new SqlCommand(
  @"UPDATE Inventory
    SET Stock = Stock - @q
    WHERE ProductId=@id AND Version=@v",
  conn, tran);
cmd2.Parameters.AddWithValue("@q", qty);
cmd2.Parameters.AddWithValue("@id", productId);
cmd2.Parameters.AddWithValue("@v", version);
int rows = cmd2.ExecuteNonQuery();
if (rows == 0) throw new Exception("Optimistic concurrency conflict.");
tran.Commit();
```

What this does:

* The `UPDATE` will affect the row only if the row still has the same `Version` value you read earlier.
* `ExecuteNonQuery()` returns affected row count:

  * `1` → success. You subtracted stock and (if you manage it) incremented the version.
  * `0` → either row missing or version changed → concurrency conflict (someone else updated row).
* `tran.Commit()` persists the update.

Important omissions/risk:

* **No version increment**: If you use a numeric `Version` column, the `UPDATE` must increment it, otherwise subsequent reads won't reflect a new version and optimistic checks later break. If `Version` is SQL `rowversion`, SQL Server updates it automatically.
* The `UPDATE` does not check `Stock >= qty`. If multiple concurrent updates slip through, you might get negative stock if you make the wrong combination of checks. To be safe, include `AND Stock >= @q` in `WHERE`.
* `AddWithValue("@v", version)` may bind incorrectly if `version` is `byte[]`. Use explicit `SqlParameter` with `SqlDbType.Binary` or `Timestamp`.

**Safer conditional UPDATE**:

```sql
UPDATE Inventory
SET Stock = Stock - @q,
    Version = Version + 1
WHERE ProductId = @id
  AND Version = @v
  AND Stock >= @q;
```

Now `rows == 1` => success; `rows == 0` => either insufficient stock or version conflict or no row.

---

## 1.5 Transaction boundaries & retries

* On conflict (`rows == 0`), your code throws and never retries. Typical optimistic pattern: **retry** a few times (exponential backoff), or re-read and present updated values to caller.
* Keep transactions as short as possible: do the `SELECT` and `UPDATE` quickly. Holding user think-time inside transaction is bad.

---

# 2 — Unblackboxing the **pessimistic** flow

Original snippet (condensed and reformatted):

```csharp
using (var conn = new SqlConnection(cs)) {
  conn.Open();
  using (var tran = conn.BeginTransaction()) {
    try {
      var cmd1 = new SqlCommand(
        "SELECT Stock FROM Inventory WITH (UPDLOCK, ROWLOCK) WHERE ProductId=@id",
        conn, tran);
      cmd1.Parameters.AddWithValue("@id", productId);
      int stock = (int)cmd1.ExecuteScalar();
      if (stock < qty) throw new Exception();
      var cmd2 = new SqlCommand(
        "UPDATE Inventory SET Stock = Stock - @q WHERE ProductId=@id",
        conn, tran);
      cmd2.Parameters.AddWithValue("@q", qty);
      cmd2.Parameters.AddWithValue("@id", productId);
      cmd2.ExecuteNonQuery();
      tran.Commit();
    } catch {
      tran.Rollback();
    }
  }
}
```

I’ll unblackbox each element.

---

## 2.1 The `WITH (UPDLOCK, ROWLOCK)` hint

What it instructs SQL Server:

* `UPDLOCK`: take an **update lock** on matching rows for the duration of the transaction. An update lock prevents other transactions from taking another update or exclusive lock that would lead to a write-write conflict. It allows shared locks to be converted to exclusive later without deadlock when this transaction proceeds to an `UPDATE`.
* `ROWLOCK`: prefer row-level locking (instead of page- or table-level). This reduces concurrency loss (fewer rows locked), but SQL Server may still escalate locks if many rows/locks exist or system decides to.

How this pattern works:

1. `SELECT ... WITH (UPDLOCK, ROWLOCK)` — you read stock and acquire an update lock on the row(s). That lock prevents other transactions that also request update/insert/delete from modifying the row until you commit the transaction.
2. You do the check in-app. Because you hold the update lock, no other transaction can concurrently update this row — you have serializing behavior for that row.
3. `UPDATE` executes and converts the update lock to exclusive lock and then commits; other waiting transactions proceed in turn.

Important semantics:

* This is **pessimistic locking**: you pay the price of locking during the decision-making window, which may block others.
* Deadlocks are still possible (e.g., transaction A locks row1 then tries to update row2; B locks row2 then tries to update row1). Deadlocks must be handled by retry after catching deadlock exception.

---

## 2.2 `ExecuteScalar()` and conversion

* `ExecuteScalar()` returns a single value (first column of first row). Casting `(int)cmd1.ExecuteScalar()` can throw if the row doesn’t exist (returns `null`) or if the DB type is not directly `int`.
* Verify `ExecuteScalar()` returned non-null.

---

## 2.3 Transaction lifetime & blocking

* While the transaction is active (between `SELECT` and `Commit()`), you hold locks preventing concurrent conflicting updates.
* If this code is slow (e.g., you call external services while holding transaction), you block other transactions and reduce throughput.

---

## 2.4 Failure modes

* **Blocking**: Many clients trying to buy the same product will serialize behind each other — good for correctness but may harm throughput.
* **Deadlocks**: Possible when multiple rows/products are involved in different orders across transactions.
* **Lock escalation**: If lots of row locks accumulate, SQL Server can escalate to page or table locks — increase contention.
* **Long transactions**: risk of timeouts and blocking.

---

# 3 — Concrete concurrent timelines (show, don’t tell)

I’ll show exact state transitions for small scenarios to illustrate race behaviors. I use explicit states so you can reason mechanistically.

## Scenario A — Optimistic pattern, two clients A & B, initial `Stock = 5`, `Version = 100`, both request `qty = 3`.

Timeline:

1. A: `SELECT Stock, Version` => (5,100)
2. B: `SELECT Stock, Version` => (5,100)
3. A: checks `5 >= 3` OK.
4. B: checks `5 >= 3` OK.
5. A: `UPDATE ... WHERE Version=100 AND Stock >= 3` -> affects 1 row; sets Stock=2, Version=101.
6. B: `UPDATE ... WHERE Version=100 AND Stock >= 3` -> affects 0 rows (version mismatch).
7. B receives `rows == 0` => must handle conflict: re-read (now sees Stock=2) => fails business check -> user informed or retry aborted.

Outcome:

* Correctness: no oversell. One succeed (A), B fails gracefully if you re-read and report.

## Scenario B — Pessimistic pattern, same initial state, two clients A & B

1. A: `SELECT ... WITH(UPDLOCK, ROWLOCK)` -> reads 5, locks row for update.
2. B: `SELECT ... WITH(UPDLOCK, ROWLOCK)` -> blocks waiting for A to commit/rollback.
3. A: checks `5 >= 3` -> OK.
4. A: `UPDATE Stock = 2` -> commit -> releases lock.
5. B: then acquires lock, reads Stock=2 -> fails business check -> reports insufficient stock.

Outcome:

* Correctness: no oversell. B waited and got updated view.
* Throughput: B blocked for duration; if many threads, queuing happens.

## Scenario C — Two products or operations with cross locking (deadlock risk for pessimistic)

* A updates product X then Y
* B updates product Y then X
* Both hold UPDLOCK on first row and try to get second -> potential deadlock.

Mitigation: access resources in consistent ordering (e.g., ascending ProductId) to avoid cycles.

---

# 4 — Production-ready corrected implementations

I’ll give two robust, production-ready versions: **Optimistic** (with retries, explicit param types, proper Version handling) and **Pessimistic** (safe locking, short-held transaction, deadlock handling).

I will not expose internal chain-of-thought but will explain why lines exist.

---

## 4.1 Production optimistic implementation (C#)

Assumptions:

* `Version` is `BIGINT` that we increment on successful update.
* DB schema has `CHECK (Stock >= 0)`.

Key features:

* Use `using` to dispose objects.
* Explicit `SqlParameter` types (no `AddWithValue`).
* Conditional `UPDATE` checks both `Version` and `Stock >= @q`.
* Retry loop with limited attempts and backoff.
* On persistent conflict, re-read and return meaningful result.

```csharp
public class InventoryConcurrencyException : Exception { public InventoryConcurrencyException(string msg):base(msg){} }
public class InsufficientStockException : Exception { public InsufficientStockException(string msg):base(msg){} }

public bool TryDecrementOptimistic(int productId, int qty, string cs, int maxRetries = 3)
{
    // Validate inputs
    if (qty <= 0) throw new ArgumentException(nameof(qty));

    var attempt = 0;
    while (true)
    {
        attempt++;
        using (var conn = new SqlConnection(cs))
        {
            conn.Open();
            using (var tran = conn.BeginTransaction())
            {
                try
                {
                    // 1) Read current stock and version
                    using (var cmd = new SqlCommand("SELECT Stock, Version FROM Inventory WHERE ProductId = @id", conn, tran))
                    {
                        cmd.Parameters.Add(new SqlParameter("@id", SqlDbType.Int) { Value = productId });

                        using (var rdr = cmd.ExecuteReader(CommandBehavior.SingleRow))
                        {
                            if (!rdr.Read())
                                throw new KeyNotFoundException($"Product {productId} not found.");

                            var stock = rdr.GetInt32(0);

                            // assuming Version is BIGINT
                            var version = rdr.GetInt64(1);

                            if (stock < qty)
                                throw new InsufficientStockException($"Not enough stock. Available={stock}, Requested={qty}");

                            // 2) Try to update atomically and ensure stock non-negative and version unchanged
                            using (var updateCmd = new SqlCommand(@"
UPDATE Inventory
SET Stock = Stock - @q,
    Version = Version + 1
WHERE ProductId = @id
  AND Version = @v
  AND Stock >= @q", conn, tran))
                            {
                                updateCmd.Parameters.Add(new SqlParameter("@q", SqlDbType.Int) { Value = qty });
                                updateCmd.Parameters.Add(new SqlParameter("@id", SqlDbType.Int) { Value = productId });
                                updateCmd.Parameters.Add(new SqlParameter("@v", SqlDbType.BigInt) { Value = version });

                                var rows = updateCmd.ExecuteNonQuery();
                                if (rows == 1)
                                {
                                    tran.Commit();
                                    return true; // success
                                }
                                // rows == 0 -> conflict or insufficient stock (someone else changed it)
                                // fall through to retry logic
                            }
                        } // reader disposed
                    }
                }
                catch (InsufficientStockException)
                {
                    // business failure -> no retries
                    tran.Rollback();
                    throw;
                }
                catch (Exception ex)
                {
                    tran.Rollback();
                    // If this is a transient DB exception we may retry (e.g., deadlock)
                    if (IsTransientSqlException(ex) && attempt < maxRetries)
                    {
                        Thread.Sleep(50 * attempt); // simple backoff
                        continue;
                    }
                    throw;
                }
            } // transaction disposed
        } // connection disposed

        if (attempt >= maxRetries)
            throw new InventoryConcurrencyException("Max retries reached due to concurrent modifications.");
    }
}
```

**Notes & rationale**:

* `Version` is incremented on success. This avoids the need to rely on `rowversion` and lets you control type.
* `Stock >= @q` in WHERE prevents negative stock in a race where two updates both think stock is enough.
* On `rows==0` we retry by leaving transaction and loop: the next attempt will re-read the updated stock/version and either succeed or fail on business rule.
* Distinguish transient exceptions (deadlock, timeout) via `IsTransientSqlException` helper (check `SqlException.Number` codes like 1205 for deadlock, 4060 etc). Retry for transient errors only.
* Keep transaction short (read -> update -> commit) — do not call external services inside.

---

## 4.2 Production pessimistic implementation (C#)

Key features:

* Use `UPDLOCK, ROWLOCK` to lock only the intended row(s).
* Keep transaction minimal and fast.
* Handle deadlocks/timeouts (retry).
* Access multiple items in consistent order to avoid deadlocks.

```csharp
public bool TryDecrementPessimistic(int productId, int qty, string cs, int maxRetries = 3)
{
    if (qty <= 0) throw new ArgumentException(nameof(qty));

    int attempt = 0;
    while (true)
    {
        attempt++;
        using (var conn = new SqlConnection(cs))
        {
            conn.Open();
            using (var tran = conn.BeginTransaction())
            {
                try
                {
                    // Acquire update lock on the targeted row
                    using (var cmd = new SqlCommand(
                        "SELECT Stock FROM Inventory WITH (UPDLOCK, ROWLOCK) WHERE ProductId = @id", conn, tran))
                    {
                        cmd.Parameters.Add(new SqlParameter("@id", SqlDbType.Int) { Value = productId });
                        var result = cmd.ExecuteScalar();
                        if (result == null || result == DBNull.Value)
                            throw new KeyNotFoundException($"Product {productId} not found.");

                        var stock = Convert.ToInt32(result);
                        if (stock < qty)
                        {
                            tran.Rollback();
                            throw new InsufficientStockException($"Not enough stock. Available={stock}, Requested={qty}");
                        }

                        // We hold UPDLOCK; perform update
                        using (var upd = new SqlCommand(
                            "UPDATE Inventory SET Stock = Stock - @q WHERE ProductId = @id", conn, tran))
                        {
                            upd.Parameters.Add(new SqlParameter("@q", SqlDbType.Int) { Value = qty });
                            upd.Parameters.Add(new SqlParameter("@id", SqlDbType.Int) { Value = productId });
                            upd.ExecuteNonQuery();
                        }

                        tran.Commit();
                        return true;
                    }
                }
                catch (SqlException ex) when (IsDeadlockOrTimeout(ex) && attempt < maxRetries)
                {
                    // transient deadlock/timeout - retry
                    try { tran.Rollback(); } catch { /* ignore */ }
                    Thread.Sleep(50 * attempt);
                    continue;
                }
                catch
                {
                    try { tran.Rollback(); } catch { }
                    throw;
                }
            }
        }

        if (attempt >= maxRetries) throw new Exception("Max retries exhausted for pessimistic update.");
    }
}
```

**Notes & rationale**:

* `UPDLOCK` ensures anyone else trying to read for update will block.
* Keep the transaction short: read and immediately update.
* If you need to touch multiple rows atomically (e.g., decrement inventory for a multi-item order), **always access in consistent order** (e.g., ProductId ascending) to avoid deadlocks.
* Use proper retry/backoff for deadlocks.

---

# 5 — Parameter typing, `rowversion`, and `AddWithValue` pitfalls

* `AddWithValue` infers parameter types based on CLR types which can lead SQL Server to pick the wrong type/size causing plan cache bloat or conversion issues. Use explicit `SqlParameter` with `SqlDbType`.
* If using SQL `rowversion`, treat it as `byte[]`:

```csharp
var versionParam = new SqlParameter("@v", SqlDbType.Timestamp) { Value = versionBytes };
```

* If `Version` is `BIGINT`, use `SqlDbType.BigInt`.

---

# 6 — Deadlocks, timeouts, and transient errors — how to detect & react

* SQL Server deadlock returns SqlException with Number 1205. Timeouts have other numbers (e.g., -2).
* Detect these codes and retry with exponential backoff.
* Limit retries (e.g., 3 attempts).
* Log occurrences and monitor rate to detect hotspots.

---

# 7 — Performance, scaling & when to prefer each pattern

Quick map:

* **Optimistic concurrency** is best when:

  * Conflicts are rare (most access is independent).
  * High throughput with low contention is needed.
  * You can accept occasional retries.
  * You prefer shorter lock durations.

* **Pessimistic concurrency** is best when:

  * Conflicts are frequent and you cannot accept failed operations (e.g., certain financial operations).
  * The cost of a failed attempt is high.
  * You can accept throughput loss due to queuing.

Other considerations:

* Use optimistic with proper `WHERE Stock >= @q AND Version=@v` for correctness and fewer locks.
* Use pessimistic only when business demands serial access or when you must ensure immediate exclusive control.

---

# 8 — Monitoring & metrics

Instrument these:

* Rate of optimistic conflicts (rows==0) per minute — high rate => consider pessimistic locking or redesign.
* Average transaction duration — long durations mean more blocking.
* Deadlocks per minute — investigate queries ordering and indexing.
* Lock wait times — indicate contention hotspots.
* Query plans & missing indexes for `Inventory` queries.

---

# 9 — Unit and integration tests you must run

1. Single-threaded success tests.
2. Concurrent multi-threaded test simulating many clients buying same product:

   * For optimistic: measure successful vs conflict counts and ensure no negative stock.
   * For pessimistic: ensure queuing behavior and no negative stock.
3. Deadlock scenario test: create 2 threads updating products in opposite order; ensure retries succeed.
4. Failure simulations: force a deadlock/timeout and confirm retry/backoff works.

---

# 10 — Extra hardening & patterns

* **Idempotency tokens**: If external retries from client occur, use an idempotency key to prevent double-charging.
* **Queueing**: If throughput and ordering matter, consider putting purchase requests on a queue (e.g., service bus) and have a single consumer update inventory — removes concurrent contention at the database but moves complexity to queue consumer.
* **Optimistic + compensation**: allow temporary overcommit and reconcile later (rare).
* **Read replicas**: avoid writing via replicas — reads can be scaled out, but writes should go to master.

---

# 11 — Example SQL stored-procedure alternative (optimistic single call)

To avoid round-trip races, put the check-and-update into a single atomic stored procedure:

```sql
CREATE PROCEDURE DeductInventoryOptimistic
    @ProductId INT,
    @Qty INT,
    @ExpectedVersion BIGINT,
    @Succeeded BIT OUTPUT,
    @CurrentStock INT OUTPUT,
    @CurrentVersion BIGINT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;

    UPDATE Inventory
    SET Stock = Stock - @Qty,
        Version = Version + 1
    WHERE ProductId = @ProductId
      AND Version = @ExpectedVersion
      AND Stock >= @Qty;

    IF @@ROWCOUNT = 1
    BEGIN
        SELECT @Succeeded = 1;
        SELECT @CurrentStock = Stock, @CurrentVersion = Version FROM Inventory WHERE ProductId = @ProductId;
        RETURN 0;
    END
    ELSE
    BEGIN
        -- return current values for caller to decide
        SELECT @Succeeded = 0;
        SELECT @CurrentStock = Stock, @CurrentVersion = Version FROM Inventory WHERE ProductId = @ProductId;
        RETURN 1;
    END
END
```

Call this in one round trip; reduces interleaving risk between app check and update.

---

# 12 — Summary: concise takeaways

* **Optimistic**: fast, low locking; must have robust `UPDATE ... WHERE Version=@v AND Stock >= @q` + version increment + retry/backoff + clear user feedback. Use stored procedure for atomicity.
* **Pessimistic**: serializes using `UPDLOCK`; safe under heavy contention but reduces concurrency and can cause deadlocks; handle deadlocks and retry.
* Always use `using` / `Dispose` and explicit `SqlParameter` types; add DB constraints (CHECK(Stock>=0)).
* Monitor conflicts, deadlocks, and latency to choose the right approach.

---

If you want, I will now:

* Provide a **single-page, fully annotated code file** (C#) containing both implementations plus helper functions (`IsTransientSqlException`, logging hooks, tests), or
* Provide **step-by-step simulation tables** for specific concurrency scenarios (e.g., 3 clients, mixed qtys) in tabular form, or
* Produce **unit/integration test code** that spawns threads and asserts invariants (no negative stock, correct final stock).

Tell me **which** of those you want next and I’ll produce it immediately (I won’t ask more clarifying questions — I’ll pick a reasonable format if you don’t specify).
