import json
import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
from passlib.hash import bcrypt
from sqlalchemy import create_engine, text

st.set_page_config(page_title="DataFoundry BI", layout="wide")

DB_URL = os.environ.get("BI_DATABASE_URL")
ADMIN_USER = os.environ.get("BI_ADMIN_USERNAME", "admin")
ADMIN_PASS = os.environ.get("BI_ADMIN_PASSWORD", "admin")
CACHE_TTL_SECONDS = int(os.environ.get("BI_DASHBOARD_CACHE_TTL_SECONDS", "60"))

engine = create_engine(DB_URL, pool_pre_ping=True)


def init_metadata():
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

        admin_hash = bcrypt.hash(ADMIN_PASS)
        conn.execute(
            text(
                """
                INSERT INTO bi_users (username, password_hash, role)
                VALUES (:u, :p, 'admin')
                ON CONFLICT (username) DO NOTHING
                """
            ),
            {"u": ADMIN_USER, "p": admin_hash},
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
            {"wid": default_ws_id, "uri": DB_URL},
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
            {"wid": default_ws_id, "u": ADMIN_USER},
        )


def audit(username: str, action: str, details: str = "", workspace_id: int | None = None):
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO bi_audit_log (username, action, details, workspace_id)
                VALUES (:u, :a, :d, :w)
                """
            ),
            {"u": username, "a": action, "d": details, "w": workspace_id},
        )


def get_user(username: str):
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT username, password_hash, role FROM bi_users WHERE username=:u"),
            {"u": username},
        ).fetchone()


def has_role(required: str) -> bool:
    role = st.session_state.get("role", "viewer")
    if role == "admin":
        return True
    if required == "analyst" and role in ("analyst",):
        return True
    return role == required


def list_workspaces_for_user(username: str):
    with engine.connect() as conn:
        if has_role("admin"):
            return conn.execute(text("SELECT id, name FROM bi_workspaces ORDER BY name")).fetchall()
        return conn.execute(
            text(
                """
                SELECT w.id, w.name
                FROM bi_workspaces w
                JOIN bi_workspace_users u ON u.workspace_id = w.id
                WHERE u.username = :u
                ORDER BY w.name
                """
            ),
            {"u": username},
        ).fetchall()


def list_datasources(workspace_id: int):
    with engine.connect() as conn:
        return conn.execute(
            text(
                """
                SELECT id, name, sqlalchemy_uri, is_default
                FROM bi_datasources
                WHERE workspace_id = :wid
                ORDER BY is_default DESC, name
                """
            ),
            {"wid": workspace_id},
        ).fetchall()


def get_engine_for_datasource(datasource_id: int):
    with engine.connect() as conn:
        uri = conn.execute(
            text("SELECT sqlalchemy_uri FROM bi_datasources WHERE id=:id"),
            {"id": datasource_id},
        ).scalar()
    return create_engine(uri, pool_pre_ping=True)


def run_query(sql: str, datasource_id: int):
    ds_engine = get_engine_for_datasource(datasource_id)
    with ds_engine.connect() as conn:
        df = pd.read_sql(text(sql), conn)
    return df


def get_cached_query_result(query_id: int):
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT run_at, data_json
                FROM bi_query_results
                WHERE query_id = :qid
                ORDER BY run_at DESC
                LIMIT 1
                """
            ),
            {"qid": query_id},
        ).fetchone()
    if not row:
        return None

    run_at = row[0]
    if not run_at:
        return None

    age = (datetime.utcnow() - run_at).total_seconds()
    if age > CACHE_TTL_SECONDS:
        return None

    try:
        data = json.loads(row[1]) if row[1] else []
        return pd.DataFrame(data)
    except Exception:
        return None


def set_cached_query_result(query_id: int, df: pd.DataFrame):
    data_json = df.to_json(orient="records")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO bi_query_results (query_id, run_at, row_count, data_json)
                VALUES (:qid, :run_at, :rows, :data)
                """
            ),
            {
                "qid": query_id,
                "run_at": datetime.utcnow(),
                "rows": len(df),
                "data": data_json,
            },
        )


def drag_reorder(items, key: str):
    if not items:
        return None

    safe_items = [
        {"id": str(item["id"]), "title": str(item["title"])} for item in items
    ]
    items_json = json.dumps(safe_items)

    html = f"""
    <div id="df-drag-root" style="font-family: sans-serif;">
      <style>
        .df-item {{
          padding: 8px 10px;
          margin: 6px 0;
          background: #f4f6f8;
          border: 1px solid #d9dee3;
          border-radius: 6px;
          cursor: grab;
        }}
        .df-item.dragging {{
          opacity: 0.5;
        }}
      </style>
      <div id="df-list"></div>
    </div>
    <script>
      const items = {items_json};
      const list = document.getElementById("df-list");
      function render() {{
        list.innerHTML = "";
        items.forEach(item => {{
          const div = document.createElement("div");
          div.className = "df-item";
          div.setAttribute("draggable", "true");
          div.dataset.id = item.id;
          div.textContent = item.title + " (#" + item.id + ")";
          list.appendChild(div);
        }});
        attachHandlers();
      }}
      function attachHandlers() {{
        let dragEl = null;
        document.querySelectorAll(".df-item").forEach(el => {{
          el.addEventListener("dragstart", (e) => {{
            dragEl = el;
            el.classList.add("dragging");
            e.dataTransfer.effectAllowed = "move";
          }});
          el.addEventListener("dragend", () => {{
            el.classList.remove("dragging");
          }});
          el.addEventListener("dragover", (e) => {{
            e.preventDefault();
            e.dataTransfer.dropEffect = "move";
          }});
          el.addEventListener("drop", (e) => {{
            e.preventDefault();
            if (!dragEl || dragEl === el) return;
            const nodes = Array.from(list.children);
            const dragIndex = nodes.indexOf(dragEl);
            const dropIndex = nodes.indexOf(el);
            if (dragIndex < dropIndex) {{
              list.insertBefore(dragEl, el.nextSibling);
            }} else {{
              list.insertBefore(dragEl, el);
            }}
            const order = Array.from(list.children).map(n => n.dataset.id);
            const msg = {{
              isStreamlitMessage: true,
              type: "streamlit:setComponentValue",
              value: order
            }};
            window.parent.postMessage(msg, "*");
          }});
        }});
      }}
      render();
    </script>
    """
    return components.html(html, height=300, key=key)


def login():
    st.title("DataFoundry BI")
    st.subheader("Sign in")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Sign in"):
        row = get_user(username)
        if row and bcrypt.verify(password, row[1]):
            st.session_state["logged_in"] = True
            st.session_state["username"] = row[0]
            st.session_state["role"] = row[2]
            audit(row[0], "login")
            st.rerun()
        else:
            st.error("Invalid credentials")


def sidebar():
    st.sidebar.title("DataFoundry BI")

    workspaces = list_workspaces_for_user(st.session_state["username"])
    if not workspaces:
        st.sidebar.error("No workspace access. Ask an admin to add you.")
        st.stop()

    ws_map = {name: wid for wid, name in workspaces}
    current_ws = st.session_state.get("workspace")
    if current_ws not in ws_map.values():
        st.session_state["workspace"] = list(ws_map.values())[0]

    selected_name = st.sidebar.selectbox("Workspace", list(ws_map.keys()))
    st.session_state["workspace"] = ws_map[selected_name]

    pages = ["SQL Lab", "Saved Queries", "Charts", "Dashboards", "Schedules", "Audit Logs"]
    if has_role("admin"):
        pages.extend(["Workspaces", "Datasources", "User Management"])

    page = st.sidebar.radio("Navigate", pages)
    st.sidebar.write(
        f"User: {st.session_state.get('username')} ({st.session_state.get('role')})"
    )
    if st.sidebar.button("Sign out"):
        st.session_state["logged_in"] = False
        st.rerun()
    return page


def sql_lab():
    st.header("SQL Lab")
    if not has_role("analyst") and not has_role("admin"):
        st.warning("You do not have permission to run ad-hoc SQL.")
        return

    workspace_id = st.session_state["workspace"]
    datasources = list_datasources(workspace_id)
    if not datasources:
        st.info("No datasources in this workspace.")
        return

    ds_map = {f"{row[1]}": row[0] for row in datasources}
    ds_name = st.selectbox("Datasource", list(ds_map.keys()))
    datasource_id = ds_map[ds_name]

    sql = st.text_area("SQL", height=200, value="SELECT * FROM analytics.nyc_taxi_yellow_tripdata LIMIT 100;")
    cols = st.columns(3)
    run = cols[0].button("Run")
    save = cols[1].button("Save Query")
    name = cols[2].text_input("Save as", value="My Query")

    if run:
        with st.spinner("Running query..."):
            try:
                df = run_query(sql, datasource_id)
                st.session_state["last_df"] = df
                st.success(f"Returned {len(df)} rows")
                audit(st.session_state["username"], "run_query", name, workspace_id)
            except Exception as e:
                st.error(str(e))

    if save:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO bi_saved_queries (workspace_id, datasource_id, name, sql, owner)
                    VALUES (:w, :d, :name, :sql, :owner)
                    """
                ),
                {
                    "w": workspace_id,
                    "d": datasource_id,
                    "name": name,
                    "sql": sql,
                    "owner": st.session_state["username"],
                },
            )
        audit(st.session_state["username"], "save_query", name, workspace_id)
        st.success("Saved")

    df = st.session_state.get("last_df")
    if df is not None:
        st.dataframe(df, use_container_width=True)
        st.subheader("Quick Chart")
        chart_type = st.selectbox("Chart type", ["table", "line", "bar", "area", "scatter", "pie", "metric"])
        if chart_type == "table":
            st.dataframe(df, use_container_width=True)
        elif chart_type == "metric" and len(df.columns) >= 1:
            st.metric("Metric", df.iloc[0, 0])
        else:
            x_col = st.selectbox("X", list(df.columns))
            y_col = st.selectbox("Y", list(df.columns))
            if chart_type == "line":
                fig = px.line(df, x=x_col, y=y_col)
            elif chart_type == "bar":
                fig = px.bar(df, x=x_col, y=y_col)
            elif chart_type == "area":
                fig = px.area(df, x=x_col, y=y_col)
            elif chart_type == "scatter":
                fig = px.scatter(df, x=x_col, y=y_col)
            else:
                fig = px.pie(df, names=x_col, values=y_col)
            st.plotly_chart(fig, use_container_width=True)


def saved_queries():
    st.header("Saved Queries")
    workspace_id = st.session_state["workspace"]
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, name, created_at, owner
                FROM bi_saved_queries
                WHERE workspace_id = :w
                ORDER BY created_at DESC
                """
            ),
            {"w": workspace_id},
        ).fetchall()

    if not rows:
        st.info("No saved queries yet")
        return

    for row in rows:
        st.write(f"**{row[1]}** — {row[2]} — owner: {row[3]}")
        if st.button(f"Run {row[0]}"):
            with engine.connect() as conn:
                sql = conn.execute(text("SELECT sql, datasource_id FROM bi_saved_queries WHERE id=:id"), {"id": row[0]}).fetchone()
            df = run_query(sql[0], sql[1])
            st.dataframe(df, use_container_width=True)


def charts():
    st.header("Charts")
    workspace_id = st.session_state["workspace"]

    with engine.connect() as conn:
        charts_rows = conn.execute(
            text(
                """
                SELECT id, name, viz_type, owner, created_at
                FROM bi_charts
                WHERE workspace_id = :w
                ORDER BY created_at DESC
                """
            ),
            {"w": workspace_id},
        ).fetchall()

    if has_role("analyst") or has_role("admin"):
        with st.expander("Create Chart"):
            with engine.connect() as conn:
                queries = conn.execute(
                    text(
                        """
                        SELECT id, name
                        FROM bi_saved_queries
                        WHERE workspace_id = :w
                        ORDER BY created_at DESC
                        """
                    ),
                    {"w": workspace_id},
                ).fetchall()
            if queries:
                qmap = {f"{q[1]} (#{q[0]})": q[0] for q in queries}
                q_label = st.selectbox("Query", list(qmap.keys()), key="chart_query")
                name = st.text_input("Chart name", key="chart_name")
                viz = st.selectbox("Viz", ["table", "line", "bar", "area", "scatter", "pie", "metric"], key="chart_viz")
                x_col = st.text_input("X column", key="chart_x")
                y_col = st.text_input("Y column", key="chart_y")
                color_col = st.text_input("Color column (optional)", key="chart_color")
                agg = st.selectbox("Aggregation", ["none", "sum", "avg", "min", "max"], key="chart_agg")
                if st.button("Create Chart", key="chart_create"):
                    with engine.begin() as conn:
                        conn.execute(
                            text(
                                """
                                INSERT INTO bi_charts (workspace_id, query_id, name, owner, viz_type, x_col, y_col, color_col, agg)
                                VALUES (:w, :q, :n, :o, :v, :x, :y, :c, :a)
                                """
                            ),
                            {
                                "w": workspace_id,
                                "q": qmap[q_label],
                                "n": name or q_label,
                                "o": st.session_state["username"],
                                "v": viz,
                                "x": x_col or None,
                                "y": y_col or None,
                                "c": color_col or None,
                                "a": agg,
                            },
                        )
                    audit(st.session_state["username"], "create_chart", name, workspace_id)
                    st.success("Chart created")
                    st.rerun()
            else:
                st.info("Save a query first")

    if not charts_rows:
        st.info("No charts yet")
        return

    for row in charts_rows:
        st.write(f"**{row[1]}** — {row[2]} — owner: {row[3]} — {row[4]}")
        with st.expander(f"Edit {row[1]}"):
            name = st.text_input("Name", value=row[1], key=f"cname_{row[0]}")
            viz = st.selectbox(
                "Viz", ["table", "line", "bar", "area", "scatter", "pie", "metric"],
                index=["table", "line", "bar", "area", "scatter", "pie", "metric"].index(row[2]),
                key=f"cviz_{row[0]}"
            )
            x_col = st.text_input("X column", key=f"cx_{row[0]}")
            y_col = st.text_input("Y column", key=f"cy_{row[0]}")
            if st.button("Save", key=f"csave_{row[0]}"):
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            """
                            UPDATE bi_charts
                            SET name=:n, viz_type=:v, x_col=:x, y_col=:y
                            WHERE id=:id
                            """
                        ),
                        {"n": name, "v": viz, "x": x_col or None, "y": y_col or None, "id": row[0]},
                    )
                audit(st.session_state["username"], "edit_chart", name, workspace_id)
                st.success("Updated")
                st.rerun()
            if st.button("Delete", key=f"cdel_{row[0]}"):
                with engine.begin() as conn:
                    conn.execute(text("DELETE FROM bi_charts WHERE id=:id"), {"id": row[0]})
                audit(st.session_state["username"], "delete_chart", row[1], workspace_id)
                st.success("Deleted")
                st.rerun()


def apply_filters(df: pd.DataFrame, filters):
    if df is None or not filters:
        return df

    for f in filters:
        col = f.get("column")
        op = f.get("operator")
        val = f.get("value")
        if col not in df.columns:
            continue
        if op == "contains" and isinstance(val, str):
            df = df[df[col].astype(str).str.contains(val, case=False, na=False)]
        elif op == "equals":
            df = df[df[col] == val]
        elif op == "gte":
            df = df[df[col] >= val]
        elif op == "lte":
            df = df[df[col] <= val]
    return df


def render_chart(df: pd.DataFrame, viz_type: str, x_col: str | None, y_col: str | None):
    if df is None:
        return
    if viz_type == "table":
        st.dataframe(df, use_container_width=True)
        return
    if viz_type == "metric":
        if len(df.columns) >= 1:
            st.metric("Metric", df.iloc[0, 0])
        else:
            st.info("No data")
        return

    if x_col not in df.columns or y_col not in df.columns:
        st.dataframe(df, use_container_width=True)
        return

    if viz_type == "line":
        fig = px.line(df, x=x_col, y=y_col)
    elif viz_type == "bar":
        fig = px.bar(df, x=x_col, y=y_col)
    elif viz_type == "area":
        fig = px.area(df, x=x_col, y=y_col)
    elif viz_type == "scatter":
        fig = px.scatter(df, x=x_col, y=y_col)
    else:
        fig = px.pie(df, names=x_col, values=y_col)
    st.plotly_chart(fig, use_container_width=True)


def dashboards():
    st.header("Dashboards")
    workspace_id = st.session_state["workspace"]
    with engine.connect() as conn:
        dashboards_rows = conn.execute(
            text(
                """
                SELECT id, name, description, owner, filters_json
                FROM bi_dashboards
                WHERE workspace_id = :w
                ORDER BY created_at DESC
                """
            ),
            {"w": workspace_id},
        ).fetchall()

    if has_role("analyst") or has_role("admin"):
        with st.expander("Create Dashboard"):
            name = st.text_input("Name", key="dash_name")
            desc = st.text_area("Description", key="dash_desc")
            if st.button("Create", key="dash_create"):
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            """
                            INSERT INTO bi_dashboards (workspace_id, name, description, owner)
                            VALUES (:w, :n, :d, :o)
                            """
                        ),
                        {"w": workspace_id, "n": name, "d": desc, "o": st.session_state["username"]},
                    )
                audit(st.session_state["username"], "create_dashboard", name, workspace_id)
                st.success("Created")
                st.rerun()

    if not dashboards_rows:
        st.info("No dashboards yet")
        return

    for dash in dashboards_rows:
        dash_id = dash[0]
        st.subheader(dash[1])
        if dash[2]:
            st.caption(dash[2])

        filters = []
        if dash[4]:
            try:
                filters = json.loads(dash[4])
            except Exception:
                filters = []

        with engine.connect() as conn:
            items = conn.execute(
                text(
                    """
                    SELECT i.id, i.title, i.order_index, i.width, i.height,
                           c.viz_type, c.x_col, c.y_col, c.query_id,
                           q.sql, q.datasource_id
                    FROM bi_dashboard_items i
                    LEFT JOIN bi_charts c ON c.id = i.chart_id
                    LEFT JOIN bi_saved_queries q ON q.id = c.query_id OR q.id = i.query_id
                    WHERE i.dashboard_id = :did
                    ORDER BY i.order_index ASC, i.id ASC
                    """
                ),
                {"did": dash_id},
            ).fetchall()

        if has_role("analyst") or has_role("admin"):
            with st.expander("Builder"):
                with engine.connect() as conn:
                    chart_rows = conn.execute(
                        text(
                            """
                            SELECT id, name FROM bi_charts
                            WHERE workspace_id = :w
                            ORDER BY created_at DESC
                            """
                        ),
                        {"w": workspace_id},
                    ).fetchall()
                if chart_rows:
                    c_map = {f"{c[1]} (#{c[0]})": c[0] for c in chart_rows}
                    c_label = st.selectbox("Chart", list(c_map.keys()), key=f"chart_{dash_id}")
                    title = st.text_input("Title", key=f"title_{dash_id}")
                    order_index = st.number_input("Order", min_value=0, max_value=1000, value=0, key=f"order_{dash_id}")
                    width = st.number_input("Width (1-12)", min_value=1, max_value=12, value=6, key=f"width_{dash_id}")
                    height = st.number_input("Height (rows)", min_value=1, max_value=12, value=6, key=f"height_{dash_id}")
                    if st.button("Add Item", key=f"add_{dash_id}"):
                        with engine.begin() as conn:
                            conn.execute(
                                text(
                                    """
                                    INSERT INTO bi_dashboard_items (dashboard_id, chart_id, title, order_index, width, height)
                                    VALUES (:d, :c, :t, :o, :w, :h)
                                    """
                                ),
                                {
                                    "d": dash_id,
                                    "c": c_map[c_label],
                                    "t": title or c_label,
                                    "o": order_index,
                                    "w": width,
                                    "h": height,
                                },
                            )
                        audit(st.session_state["username"], "add_dashboard_item", title, workspace_id)
                        st.success("Added")
                        st.rerun()
                else:
                    st.info("Create a chart first")

                st.markdown("**Dashboard Filters**")
                col = st.text_input("Column", key=f"fcol_{dash_id}")
                op = st.selectbox("Operator", ["contains", "equals", "gte", "lte"], key=f"fop_{dash_id}")
                val = st.text_input("Value", key=f"fval_{dash_id}")
                if st.button("Add Filter", key=f"fadd_{dash_id}"):
                    filters.append({"column": col, "operator": op, "value": val})
                    with engine.begin() as conn:
                        conn.execute(
                            text("UPDATE bi_dashboards SET filters_json=:f WHERE id=:id"),
                            {"f": json.dumps(filters), "id": dash_id},
                        )
                    st.success("Filter added")
                    st.rerun()

                st.markdown("**Drag & Drop Order**")
                order_ids = drag_reorder(
                    [{"id": item[0], "title": item[1]} for item in items],
                    key=f"drag_{dash_id}",
                )
                if order_ids:
                    with engine.begin() as conn:
                        for idx, item_id in enumerate(order_ids):
                            conn.execute(
                                text(
                                    "UPDATE bi_dashboard_items SET order_index=:o WHERE id=:id"
                                ),
                                {"o": idx, "id": int(item_id)},
                            )
                    st.success("Order updated")
                    st.rerun()

                st.markdown("**Layout (size + edit)**")
                for item in items:
                    with st.container():
                        st.write(f"Item #{item[0]} — {item[1]}")
                        new_title = st.text_input("Title", value=item[1], key=f"it_title_{item[0]}")
                        new_order = st.number_input("Order", min_value=0, max_value=1000, value=item[2], key=f"it_order_{item[0]}")
                        new_width = st.number_input("Width (1-12)", min_value=1, max_value=12, value=item[3], key=f"it_width_{item[0]}")
                        new_height = st.number_input("Height (rows)", min_value=1, max_value=12, value=item[4], key=f"it_height_{item[0]}")
                        cols = st.columns(2)
                        if cols[0].button("Update", key=f"it_up_{item[0]}"):
                            with engine.begin() as conn:
                                conn.execute(
                                    text(
                                        """
                                        UPDATE bi_dashboard_items
                                        SET title=:t, order_index=:o, width=:w, height=:h
                                        WHERE id=:id
                                        """
                                    ),
                                    {"t": new_title, "o": new_order, "w": new_width, "h": new_height, "id": item[0]},
                                )
                            st.success("Updated")
                            st.rerun()
                        if cols[1].button("Remove", key=f"it_rm_{item[0]}"):
                            with engine.begin() as conn:
                                conn.execute(text("DELETE FROM bi_dashboard_items WHERE id=:id"), {"id": item[0]})
                            st.success("Removed")
                            st.rerun()

        if not items:
            st.info("No items yet")
            continue

        row_cols = []
        current_width = 0
        rows = []
        for item in items:
            width = max(1, min(12, item[3]))
            if current_width + width > 12:
                rows.append(row_cols)
                row_cols = []
                current_width = 0
            row_cols.append(item)
            current_width += width
        if row_cols:
            rows.append(row_cols)

        for row in rows:
            cols = st.columns([max(1, min(12, r[3])) for r in row])
            for idx, item in enumerate(row):
                title = item[1]
                viz_type = item[5] or "table"
                x_col = item[6]
                y_col = item[7]
                query_id = item[8]
                sql = item[9]
                datasource_id = item[10]
                with cols[idx]:
                    st.markdown(f"### {title}")
                    df = get_cached_query_result(query_id) if query_id else None
                    if df is None and sql:
                        df = run_query(sql, datasource_id)
                        if query_id:
                            set_cached_query_result(query_id, df)
                    df = apply_filters(df, filters)
                    render_chart(df, viz_type, x_col, y_col)


def schedules():
    st.header("Schedules")
    workspace_id = st.session_state["workspace"]
    with engine.connect() as conn:
        schedules_rows = conn.execute(
            text(
                """
                SELECT s.id, s.name, s.interval_minutes, s.enabled, s.last_run, s.next_run, q.name
                FROM bi_schedules s
                JOIN bi_saved_queries q ON q.id = s.query_id
                WHERE q.workspace_id = :w
                ORDER BY s.id DESC
                """
            ),
            {"w": workspace_id},
        ).fetchall()

    if has_role("analyst") or has_role("admin"):
        with st.expander("Create Schedule"):
            with engine.connect() as conn:
                queries = conn.execute(
                    text(
                        """
                        SELECT id, name
                        FROM bi_saved_queries
                        WHERE workspace_id = :w
                        ORDER BY created_at DESC
                        """
                    ),
                    {"w": workspace_id},
                ).fetchall()
            if queries:
                qmap = {f"{q[1]} (#{q[0]})": q[0] for q in queries}
                q_label = st.selectbox("Query", list(qmap.keys()), key="sched_query")
                name = st.text_input("Name", key="sched_name")
                interval = st.number_input("Interval (minutes)", min_value=5, max_value=1440, value=60)
                if st.button("Create", key="sched_create"):
                    with engine.begin() as conn:
                        conn.execute(
                            text(
                                """
                                INSERT INTO bi_schedules (query_id, name, interval_minutes, enabled, next_run)
                                VALUES (:qid, :n, :i, TRUE, :nr)
                                """
                            ),
                            {"qid": qmap[q_label], "n": name, "i": interval, "nr": datetime.utcnow()},
                        )
                    audit(st.session_state["username"], "create_schedule", name, workspace_id)
                    st.success("Created")
                    st.rerun()
            else:
                st.info("Save a query first")

    if not schedules_rows:
        st.info("No schedules yet")
        return

    for s in schedules_rows:
        st.write(f"**{s[1]}** — every {s[2]} min — query: {s[6]}")
        st.caption(f"Last run: {s[4]} | Next run: {s[5]} | Enabled: {s[3]}")


def audit_logs():
    st.header("Audit Logs")
    if not has_role("admin"):
        st.warning("Admin only")
        return
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT username, action, details, workspace_id, created_at
                FROM bi_audit_log
                ORDER BY created_at DESC
                LIMIT 500
                """
            )
        ).fetchall()
    if rows:
        df = pd.DataFrame(rows, columns=["user", "action", "details", "workspace", "time"])
        st.dataframe(df, use_container_width=True)


def workspaces_admin():
    st.header("Workspaces")
    if not has_role("admin"):
        st.warning("Admin only")
        return

    with engine.connect() as conn:
        ws_rows = conn.execute(text("SELECT id, name, created_at FROM bi_workspaces ORDER BY name")).fetchall()
    st.dataframe(pd.DataFrame(ws_rows, columns=["id", "name", "created_at"]))

    with st.expander("Create Workspace"):
        name = st.text_input("Workspace name")
        if st.button("Create Workspace"):
            with engine.begin() as conn:
                conn.execute(text("INSERT INTO bi_workspaces (name) VALUES (:n)"), {"n": name})
            audit(st.session_state["username"], "create_workspace", name)
            st.success("Created")
            st.rerun()

    with st.expander("Add Member"):
        ws_map = {w[1]: w[0] for w in ws_rows}
        ws_name = st.selectbox("Workspace", list(ws_map.keys()))
        username = st.text_input("Username to add")
        if st.button("Add Member"):
            with engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO bi_workspace_users (workspace_id, username)
                        SELECT :w, :u
                        WHERE NOT EXISTS (
                          SELECT 1 FROM bi_workspace_users WHERE workspace_id = :w AND username = :u
                        )
                        """
                    ),
                    {"w": ws_map[ws_name], "u": username},
                )
            audit(st.session_state["username"], "add_workspace_member", f"{ws_name}:{username}")
            st.success("Member added")


def datasources_admin():
    st.header("Datasources")
    if not has_role("admin"):
        st.warning("Admin only")
        return

    with engine.connect() as conn:
        ws_rows = conn.execute(text("SELECT id, name FROM bi_workspaces ORDER BY name")).fetchall()
    ws_map = {w[1]: w[0] for w in ws_rows}
    if not ws_map:
        st.info("Create a workspace first")
        return

    with st.expander("Create Datasource"):
        ws_name = st.selectbox("Workspace", list(ws_map.keys()))
        name = st.text_input("Datasource name")
        uri = st.text_input("SQLAlchemy URI", value=DB_URL)
        is_default = st.checkbox("Set as default")
        if st.button("Create Datasource"):
            with engine.begin() as conn:
                if is_default:
                    conn.execute(
                        text("UPDATE bi_datasources SET is_default=FALSE WHERE workspace_id=:w"),
                        {"w": ws_map[ws_name]},
                    )
                conn.execute(
                    text(
                        """
                        INSERT INTO bi_datasources (workspace_id, name, sqlalchemy_uri, is_default)
                        VALUES (:w, :n, :u, :d)
                        """
                    ),
                    {"w": ws_map[ws_name], "n": name, "u": uri, "d": is_default},
                )
            audit(st.session_state["username"], "create_datasource", name)
            st.success("Datasource created")
            st.rerun()

    with engine.connect() as conn:
        ds_rows = conn.execute(
            text(
                """
                SELECT d.id, w.name, d.name, d.is_default, d.created_at
                FROM bi_datasources d
                JOIN bi_workspaces w ON w.id = d.workspace_id
                ORDER BY w.name, d.name
                """
            )
        ).fetchall()
    st.dataframe(pd.DataFrame(ds_rows, columns=["id", "workspace", "name", "default", "created_at"]))


def user_management():
    st.header("User Management")
    if not has_role("admin"):
        st.warning("Admin only")
        return

    with engine.connect() as conn:
        users = conn.execute(text("SELECT username, role, created_at FROM bi_users ORDER BY created_at DESC")).fetchall()
    st.dataframe(pd.DataFrame(users, columns=["username", "role", "created_at"]))

    with st.expander("Create User"):
        username = st.text_input("Username", key="new_user")
        password = st.text_input("Password", type="password", key="new_pass")
        role = st.selectbox("Role", ["admin", "analyst", "viewer"], key="new_role")
        if st.button("Create User"):
            with engine.begin() as conn:
                conn.execute(
                    text("INSERT INTO bi_users (username, password_hash, role) VALUES (:u, :p, :r)"),
                    {"u": username, "p": bcrypt.hash(password), "r": role},
                )
            audit(st.session_state["username"], "create_user", username)
            st.success("User created")
            st.rerun()


init_metadata()

if not st.session_state.get("logged_in"):
    login()
    st.stop()

page = sidebar()

if page == "SQL Lab":
    sql_lab()
elif page == "Saved Queries":
    saved_queries()
elif page == "Charts":
    charts()
elif page == "Dashboards":
    dashboards()
elif page == "Schedules":
    schedules()
elif page == "Audit Logs":
    audit_logs()
elif page == "Workspaces":
    workspaces_admin()
elif page == "Datasources":
    datasources_admin()
else:
    user_management()
