# Query Catalog

These SQL files are reviewable query contracts. The planner emits only a
`query_id` and typed parameters; execution is delegated to the existing
ClickHouse client, which owns connection, parameter binding, and table access.
Keeping the contracts in the repository makes every supported analysis
capability visible and testable instead of allowing the model to invent SQL.

The application currently uses `clickhouse-driver` over native TCP. Configure
`CLICKHOUSE_PORT=9000` and `CLICKHOUSE_DATABASE=net_measure`; port 8123 is the
ClickHouse HTTP interface and is not used by `src/clickhouse/client.py`.
