# Problem Statement – HTTP and the GET Method Task

## Objective

Build a small web system that demonstrates how a browser (client) and a server communicate through HTTP.

The system should follow the basic structure of web communication:

* A **client sends a request**
* A **server sends back a response**

Each request should use one of the standard HTTP methods — such as `GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`, `TRACE`, or `CONNECT` — and target a specific resource identified by a **URI** or **URL**.

## Focus: The GET Method

The primary focus of this task is the `GET` method:

* It **retrieves information** without modifying data on the server.
* It is **read-only** and **idempotent**, meaning multiple identical requests produce the same result without side effects.

## Additional Methods

Optionally, you may also support:

* `POST` — to create new data
* `PUT` — to update existing data
* `DELETE` — to remove data

Each server response **must include correct HTTP headers**, such as `Content-Type`, and adhere to HTTP protocol safety rules.

## Requirements

* The **server** should be written in **Python**.
* The server must maintain a simple internal store (e.g., an **in-memory dictionary**) to act as shared state.
* The **client** should:

  * Send HTTP requests to the server.
  * Display responses instantly, **without reloading the page**.
