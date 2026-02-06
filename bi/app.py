import os
import time
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, text

st.set_page_config(page_title="DataFoundry BI", layout="wide")

DB_URL = os.environ.get("BI_DATABASE_URL")
ADMIN_USER = os.environ.get("BI_ADMIN_USERNAME", "admin")
ADMIN_PASS = os.environ.get("BI_ADMIN_PASSWORD", "admin")

engine = create_engine(DB_URL, pool_pre_ping=True)


def init_metadata():
    with engine.begin() as conn:
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS bi_saved_queries (
              id SERIAL PRIMARY KEY,
              name TEXT NOT NULL,
              sql TEXT NOT NULL,
              created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """
        ))
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS bi_dashboards (
              id SERIAL PRIMARY KEY,
              name TEXT NOT NULL,
              description TEXT,
              created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """
        ))
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS bi_dashboard_items (
              id SERIAL PRIMARY KEY,
              dashboard_id INTEGER NOT NULL REFERENCES bi_dashboards(id) ON DELETE CASCADE,
              query_id INTEGER NOT NULL REFERENCES bi_saved_queries(id) ON DELETE CASCADE,
              title TEXT NOT NULL,
              viz_type TEXT NOT NULL DEFAULT 'table'
            );
            """
        ))


def login():
    st.title("DataFoundry BI")
    st.subheader("Sign in")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Sign in"):
        if username == ADMIN_USER and password == ADMIN_PASS:
            st.session_state["logged_in"] = True
            st.rerun()
        else:
            st.error("Invalid credentials")


def run_query(sql: str):
    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn)
    return df


def sidebar():
    st.sidebar.title("DataFoundry BI")
    page = st.sidebar.radio("Navigate", ["SQL Lab", "Saved Queries", "Dashboards"])
    if st.sidebar.button("Sign out"):
        st.session_state["logged_in"] = False
        st.rerun()
    return page


def sql_lab():
    st.header("SQL Lab")
    sql = st.text_area("SQL", height=200, value="SELECT * FROM analytics.nyc_taxi_yellow_tripdata LIMIT 100;")
    cols = st.columns(3)
    run = cols[0].button("Run")
    save = cols[1].button("Save Query")
    name = cols[2].text_input("Save as", value="My Query")

    if run:
        with st.spinner("Running query..."):
            try:
                df = run_query(sql)
                st.session_state["last_df"] = df
                st.success(f"Returned {len(df)} rows")
            except Exception as e:
                st.error(str(e))

    if save:
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO bi_saved_queries (name, sql) VALUES (:name, :sql)"),
                {"name": name, "sql": sql},
            )
        st.success("Saved")

    df = st.session_state.get("last_df")
    if df is not None:
        st.dataframe(df, use_container_width=True)
        st.subheader("Quick Chart")
        chart_type = st.selectbox("Chart type", ["table", "line", "bar"])
        if chart_type == "table":
            st.dataframe(df, use_container_width=True)
        else:
            x_col = st.selectbox("X", list(df.columns))
            y_col = st.selectbox("Y", list(df.columns))
            if chart_type == "line":
                fig = px.line(df, x=x_col, y=y_col)
            else:
                fig = px.bar(df, x=x_col, y=y_col)
            st.plotly_chart(fig, use_container_width=True)


def saved_queries():
    st.header("Saved Queries")
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT id, name, created_at FROM bi_saved_queries ORDER BY created_at DESC")).fetchall()
    if not rows:
        st.info("No saved queries yet")
        return
    for row in rows:
        st.write(f"**{row[1]}** — {row[2]}")
        if st.button(f"Run {row[0]}"):
            with engine.connect() as conn:
                sql = conn.execute(text("SELECT sql FROM bi_saved_queries WHERE id=:id"), {"id": row[0]}).scalar()
            df = run_query(sql)
            st.dataframe(df, use_container_width=True)


def dashboards():
    st.header("Dashboards")
    with engine.connect() as conn:
        dashboards = conn.execute(text("SELECT id, name, description FROM bi_dashboards ORDER BY created_at DESC")).fetchall()

    with st.expander("Create Dashboard"):
        name = st.text_input("Name", key="dash_name")
        desc = st.text_area("Description", key="dash_desc")
        if st.button("Create", key="dash_create"):
            with engine.begin() as conn:
                conn.execute(
                    text("INSERT INTO bi_dashboards (name, description) VALUES (:n, :d)"),
                    {"n": name, "d": desc},
                )
            st.success("Created")
            st.rerun()

    if not dashboards:
        st.info("No dashboards yet")
        return

    for dash in dashboards:
        st.subheader(dash[1])
        if dash[2]:
            st.caption(dash[2])
        with engine.connect() as conn:
            items = conn.execute(
                text(
                    """
                    SELECT i.id, i.title, i.viz_type, q.sql
                    FROM bi_dashboard_items i
                    JOIN bi_saved_queries q ON q.id = i.query_id
                    WHERE i.dashboard_id = :did
                    """
                ),
                {"did": dash[0]},
            ).fetchall()

        with st.expander("Add Item"):
            with engine.connect() as conn:
                queries = conn.execute(text("SELECT id, name FROM bi_saved_queries ORDER BY created_at DESC")).fetchall()
            if queries:
                qmap = {f"{q[1]} (#{q[0]})": q[0] for q in queries}
                q_label = st.selectbox("Query", list(qmap.keys()), key=f"q_{dash[0]}")
                title = st.text_input("Title", key=f"t_{dash[0]}")
                viz = st.selectbox("Viz", ["table", "line", "bar"], key=f"v_{dash[0]}")
                if st.button("Add", key=f"add_{dash[0]}"):
                    with engine.begin() as conn:
                        conn.execute(
                            text(
                                "INSERT INTO bi_dashboard_items (dashboard_id, query_id, title, viz_type) VALUES (:d, :q, :t, :v)"
                            ),
                            {"d": dash[0], "q": qmap[q_label], "t": title or q_label, "v": viz},
                        )
                    st.success("Added")
                    st.rerun()
            else:
                st.info("Save a query first")

        for item in items:
            st.markdown(f"### {item[1]}")
            df = run_query(item[3])
            if item[2] == "table":
                st.dataframe(df, use_container_width=True)
            elif item[2] == "line" and len(df.columns) >= 2:
                fig = px.line(df, x=df.columns[0], y=df.columns[1])
                st.plotly_chart(fig, use_container_width=True)
            elif item[2] == "bar" and len(df.columns) >= 2:
                fig = px.bar(df, x=df.columns[0], y=df.columns[1])
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.dataframe(df, use_container_width=True)


init_metadata()

if not st.session_state.get("logged_in"):
    login()
    st.stop()

page = sidebar()

if page == "SQL Lab":
    sql_lab()
elif page == "Saved Queries":
    saved_queries()
else:
    dashboards()
