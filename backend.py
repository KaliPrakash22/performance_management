# backend.py

import psycopg2
import pandas as pd
from datetime import date
from typing import List, Dict, Any
import streamlit as st

# Database credentials (replace with your PostgreSQL details)
DB_HOST = "localhost"
DB_NAME = "pms"
DB_USER = "postgres"
DB_PASSWORD = "KaliNew"

def get_db_connection():
    """Establishes and returns a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return conn
    except psycopg2.OperationalError as e:
        st.error(f"Error connecting to database: {e}")
        return None

def create_tables():
    """Creates all necessary tables for the application."""
    conn = get_db_connection()
    if not conn: return
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (user_id SERIAL PRIMARY KEY, name VARCHAR(255) NOT NULL, role VARCHAR(50) NOT NULL, manager_id INTEGER REFERENCES users(user_id));
            CREATE TABLE IF NOT EXISTS goals (goal_id SERIAL PRIMARY KEY, employee_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE, manager_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE, description TEXT NOT NULL, due_date DATE NOT NULL, status VARCHAR(50) NOT NULL DEFAULT 'Draft', created_at TIMESTAMPTZ DEFAULT NOW());
            CREATE TABLE IF NOT EXISTS tasks (task_id SERIAL PRIMARY KEY, goal_id INTEGER REFERENCES goals(goal_id) ON DELETE CASCADE, description TEXT NOT NULL, status VARCHAR(50) NOT NULL DEFAULT 'Pending Approval', created_at TIMESTAMPTZ DEFAULT NOW());
            CREATE TABLE IF NOT EXISTS feedback (feedback_id SERIAL PRIMARY KEY, goal_id INTEGER REFERENCES goals(goal_id) ON DELETE CASCADE, manager_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE, feedback_text TEXT NOT NULL, created_at TIMESTAMPTZ DEFAULT NOW());
        """)
        conn.commit()
    except (Exception, psycopg2.Error) as error:
        conn.rollback()
        print(f"Error creating tables: {error}")
    finally:
        if conn: cur.close(); conn.close()

# --- CRUD Operations ---

# Users
def get_users_by_role(role: str):
    conn = get_db_connection()
    if not conn: return pd.DataFrame()
    df = pd.read_sql_query("SELECT user_id, name FROM users WHERE role = %s ORDER BY name;", conn, params=(role,))
    conn.close()
    return df

# Goals
def create_goal(employee_id: int, manager_id: int, description: str, due_date: date):
    conn = get_db_connection()
    if not conn: return None
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO goals (employee_id, manager_id, description, due_date) VALUES (%s, %s, %s, %s) RETURNING goal_id;", (employee_id, manager_id, description, due_date))
        goal_id = cur.fetchone()[0]
        conn.commit()
        return goal_id
    except (Exception, psycopg2.Error) as error:
        conn.rollback()
        print(f"Error creating goal: {error}")
        return None
    finally:
        if conn: cur.close(); conn.close()

def update_goal_status(goal_id: int, status: str):
    conn = get_db_connection()
    if not conn: return False
    cur = conn.cursor()
    try:
        cur.execute("UPDATE goals SET status = %s WHERE goal_id = %s;", (status, goal_id))
        conn.commit()
        return True
    except (Exception, psycopg2.Error) as error:
        conn.rollback()
        print(f"Error updating goal status: {error}")
        return False
    finally:
        if conn: cur.close(); conn.close()

def get_employee_goals(employee_id: int):
    conn = get_db_connection()
    if not conn: return pd.DataFrame()
    query = """
    SELECT
        g.goal_id,
        g.description,
        g.due_date,
        g.status,
        m.name AS manager_name
    FROM goals g
    JOIN users m ON g.manager_id = m.user_id
    WHERE g.employee_id = %s
    ORDER BY g.due_date;
    """
    # Fix: Convert the numpy.int64 to a standard Python int
    df = pd.read_sql_query(query, conn, params=(int(employee_id),))
    conn.close()
    return df

def get_manager_goals(manager_id: int):
    """
    Retrieves all goals assigned by a specific manager.
    Includes employee name for context.
    """
    conn = get_db_connection()
    if not conn: return pd.DataFrame()
    query = """
    SELECT
        g.goal_id,
        g.description AS goal_description,
        g.due_date,
        g.status,
        e.name AS employee_name
    FROM goals g
    JOIN users e ON g.employee_id = e.user_id
    WHERE g.manager_id = %s
    ORDER BY g.due_date;
    """
    df = pd.read_sql_query(query, conn, params=(int(manager_id),))
    conn.close()
    return df

# Tasks
def create_task(goal_id: int, description: str):
    conn = get_db_connection()
    if not conn: return None
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO tasks (goal_id, description) VALUES (%s, %s) RETURNING task_id;", (goal_id, description))
        task_id = cur.fetchone()[0]
        conn.commit()
        return task_id
    except (Exception, psycopg2.Error) as error:
        conn.rollback()
        print(f"Error creating task: {error}")
        return None
    finally:
        if conn: cur.close(); conn.close()

def get_tasks_for_goal(goal_id: int):
    conn = get_db_connection()
    if not conn: return pd.DataFrame()
    df = pd.read_sql_query("SELECT task_id, description, status FROM tasks WHERE goal_id = %s ORDER BY created_at;", conn, params=(goal_id,))
    conn.close()
    return df

def get_pending_tasks_for_manager(manager_id: int):
    """
    Retrieves all tasks for a manager's team that are 'Pending Approval'.
    """
    conn = get_db_connection()
    if not conn: return pd.DataFrame()
    query = """
    SELECT
        t.task_id,
        t.description AS task_description,
        g.description AS goal_description,
        e.name AS employee_name
    FROM tasks t
    JOIN goals g ON t.goal_id = g.goal_id
    JOIN users e ON g.employee_id = e.user_id
    WHERE t.status = 'Pending Approval' AND g.manager_id = %s
    ORDER BY g.due_date;
    """
    df = pd.read_sql_query(query, conn, params=(int(manager_id),))
    conn.close()
    return df

def update_task_status(task_id: int, status: str):
    conn = get_db_connection()
    if not conn: return False
    cur = conn.cursor()
    try:
        cur.execute("UPDATE tasks SET status = %s WHERE task_id = %s;", (status, task_id))
        conn.commit()
        return True
    except (Exception, psycopg2.Error) as error:
        conn.rollback()
        print(f"Error updating task status: {error}")
        return False
    finally:
        if conn: cur.close(); conn.close()

# Feedback
def create_feedback(goal_id: int, manager_id: int, feedback_text: str):
    conn = get_db_connection()
    if not conn: return False
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO feedback (goal_id, manager_id, feedback_text) VALUES (%s, %s, %s);", (goal_id, manager_id, feedback_text))
        conn.commit()
        return True
    except (Exception, psycopg2.Error) as error:
        conn.rollback()
        print(f"Error creating feedback: {error}")
        return False
    finally:
        if conn: cur.close(); conn.close()

def get_feedback_for_goal(goal_id: int):
    conn = get_db_connection()
    if not conn: return pd.DataFrame()
    query = """
    SELECT
        f.feedback_text,
        u.name AS manager_name,
        f.created_at
    FROM feedback f
    JOIN users u ON f.manager_id = u.user_id
    WHERE f.goal_id = %s
    ORDER BY f.created_at DESC;
    """
    df = pd.read_sql_query(query, conn, params=(goal_id,))
    conn.close()
    return df

# Reporting
def get_employee_performance_history(employee_id: int):
    conn = get_db_connection()
    if not conn: return pd.DataFrame()
    query = """
    SELECT
        g.goal_id,
        g.description AS goal_description,
        g.due_date,
        g.status AS goal_status,
        string_agg(t.description, ' | ') AS task_descriptions,
        string_agg(f.feedback_text, ' | ') AS feedback_history
    FROM goals g
    LEFT JOIN tasks t ON g.goal_id = t.goal_id
    LEFT JOIN feedback f ON g.goal_id = f.goal_id
    WHERE g.employee_id = %s
    GROUP BY g.goal_id
    ORDER BY g.due_date;
    """
    df = pd.read_sql_query(query, conn, params=(int(employee_id),))
    conn.close()
    return df