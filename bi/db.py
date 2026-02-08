from __future__ import annotations

from sqlalchemy import text
from passlib.hash import bcrypt


def init_metadata(engine, admin_user: str, admin_pass: str, db_url: str) -> None:
    with engine.begin() as conn:
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS bi_users (
              id SERIAL PRIMARY KEY,
              username TEXT UNIQUE NOT NULL,
              password_hash TEXT NOT NULL,
              role TEXT NOT NULL DEFAULT 'viewer',
              created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """
        ))
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS bi_workspaces (
              id SERIAL PRIMARY KEY,
              name TEXT UNIQUE NOT NULL,
              created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """
        ))
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS bi_workspace_users (
              id SERIAL PRIMARY KEY,
              workspace_id INTEGER NOT NULL REFERENCES bi_workspaces(id) ON DELETE CASCADE,
              username TEXT NOT NULL,
              created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """
        ))
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS bi_datasources (
              id SERIAL PRIMARY KEY,
              workspace_id INTEGER NOT NULL REFERENCES bi_workspaces(id) ON DELETE CASCADE,
              name TEXT NOT NULL,
              sqlalchemy_uri TEXT NOT NULL,
              is_default BOOLEAN NOT NULL DEFAULT FALSE,
              created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """
        ))
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS bi_audit_log (
              id SERIAL PRIMARY KEY,
              username TEXT NOT NULL,
              action TEXT NOT NULL,
              details TEXT,
              workspace_id INTEGER,
              created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """
        ))
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS bi_saved_queries (
              id SERIAL PRIMARY KEY,
              workspace_id INTEGER NOT NULL REFERENCES bi_workspaces(id) ON DELETE CASCADE,
              datasource_id INTEGER NOT NULL REFERENCES bi_datasources(id) ON DELETE CASCADE,
              name TEXT NOT NULL,
              sql TEXT NOT NULL,
              owner TEXT NOT NULL,
              description TEXT,
              created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """
        ))
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS bi_charts (
              id SERIAL PRIMARY KEY,
              workspace_id INTEGER NOT NULL REFERENCES bi_workspaces(id) ON DELETE CASCADE,
              query_id INTEGER NOT NULL REFERENCES bi_saved_queries(id) ON DELETE CASCADE,
              name TEXT NOT NULL,
              description TEXT,
              owner TEXT NOT NULL,
              viz_type TEXT NOT NULL DEFAULT 'table',
              x_col TEXT,
              y_col TEXT,
              color_col TEXT,
              agg TEXT,
              options_json TEXT,
              created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """
        ))
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS bi_dashboards (
              id SERIAL PRIMARY KEY,
              workspace_id INTEGER NOT NULL REFERENCES bi_workspaces(id) ON DELETE CASCADE,
              name TEXT NOT NULL,
              description TEXT,
              owner TEXT NOT NULL,
              filters_json TEXT,
              created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """
        ))
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS bi_dashboard_items (
              id SERIAL PRIMARY KEY,
              dashboard_id INTEGER NOT NULL REFERENCES bi_dashboards(id) ON DELETE CASCADE,
              chart_id INTEGER REFERENCES bi_charts(id) ON DELETE SET NULL,
              query_id INTEGER REFERENCES bi_saved_queries(id) ON DELETE SET NULL,
              title TEXT NOT NULL,
              order_index INTEGER NOT NULL DEFAULT 0,
              width INTEGER NOT NULL DEFAULT 6,
              height INTEGER NOT NULL DEFAULT 6
            );
            """
        ))
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS bi_schedules (
              id SERIAL PRIMARY KEY,
              query_id INTEGER NOT NULL REFERENCES bi_saved_queries(id) ON DELETE CASCADE,
              name TEXT NOT NULL,
              interval_minutes INTEGER NOT NULL DEFAULT 60,
              enabled BOOLEAN NOT NULL DEFAULT TRUE,
              last_run TIMESTAMP,
              next_run TIMESTAMP
            );
            """
        ))
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS bi_query_results (
              id SERIAL PRIMARY KEY,
              query_id INTEGER NOT NULL REFERENCES bi_saved_queries(id) ON DELETE CASCADE,
              run_at TIMESTAMP NOT NULL DEFAULT NOW(),
              row_count INTEGER NOT NULL,
              data_json TEXT
            );
            """
        ))

        admin_hash = bcrypt.hash(admin_pass)
        conn.execute(
            text(
                """
                INSERT INTO bi_users (username, password_hash, role)
                VALUES (:u, :p, 'admin')
                ON CONFLICT (username) DO NOTHING
                """
            ),
            {"u": admin_user, "p": admin_hash},
        )

        conn.execute(
            text(
                """
                INSERT INTO bi_workspaces (name)
                SELECT 'Default'
                WHERE NOT EXISTS (SELECT 1 FROM bi_workspaces WHERE name='Default')
                """
            )
        )
        default_ws_id = conn.execute(
            text("SELECT id FROM bi_workspaces WHERE name='Default'")
        ).scalar()

        conn.execute(
            text(
                """
                INSERT INTO bi_datasources (workspace_id, name, sqlalchemy_uri, is_default)
                SELECT :wid, 'Warehouse', :uri, TRUE
                WHERE NOT EXISTS (
                  SELECT 1 FROM bi_datasources WHERE workspace_id = :wid AND name = 'Warehouse'
                )
                """
            ),
            {"wid": default_ws_id, "uri": db_url},
        )

        conn.execute(
            text(
                """
                INSERT INTO bi_workspace_users (workspace_id, username)
                SELECT :wid, :u
                WHERE NOT EXISTS (
                  SELECT 1 FROM bi_workspace_users WHERE workspace_id = :wid AND username = :u
                )
                """
            ),
            {"wid": default_ws_id, "u": admin_user},
        )
