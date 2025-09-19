# frontend.py

import streamlit as st
import backend as db
from datetime import date
import pandas as pd

st.set_page_config(page_title="Performance Management System", layout="wide")
st.title("🤝 Performance Management System")

# Ensure tables exist
db.create_tables()

# Simulate user authentication
st.sidebar.header("User Selection")
roles = ['Manager', 'Employee']
selected_role = st.sidebar.radio("Select your role:", roles)
st.session_state['selected_role'] = selected_role

if selected_role == 'Manager':
    users_df = db.get_users_by_role('Manager')
else:
    users_df = db.get_users_by_role('Employee')

if users_df.empty:
    st.sidebar.warning("No users found. Please create some in your database.")
else:
    selected_user_name = st.sidebar.selectbox("Select your name:", users_df['name'])
    st.session_state['user_id'] = users_df[users_df['name'] == selected_user_name]['user_id'].iloc[0]
    st.session_state['user_name'] = selected_user_name

# Main app content based on role
if st.session_state.get('user_id'):
    st.sidebar.markdown("---")
    st.sidebar.info(f"Logged in as: **{st.session_state['user_name']}** ({st.session_state['selected_role']})")

    if st.session_state['selected_role'] == 'Manager':
        st.header("Manager Dashboard")
        st.info("Set goals, review tasks, and provide feedback for your team.")

        # --- Tasks Awaiting Review (NEW SECTION) ---
        st.subheader("Tasks Awaiting Your Approval")
        pending_tasks_df = db.get_pending_tasks_for_manager(st.session_state['user_id'])
        if not pending_tasks_df.empty:
            st.warning(f"You have **{len(pending_tasks_df)}** tasks pending approval.")
            for _, task_row in pending_tasks_df.iterrows():
                with st.container(border=True):
                    st.write(f"**Task:** {task_row['task_description']}")
                    st.write(f"**Goal:** {task_row['goal_description']}")
                    st.write(f"**Employee:** {task_row['employee_name']}")
                    col_approve, col_reject = st.columns(2)
                    with col_approve:
                        if st.button("Approve", key=f"approve_{task_row['task_id']}"):
                            if db.update_task_status(task_row['task_id'], 'Approved'):
                                st.success("Task approved!")
                                st.rerun()
                            else:
                                st.error("Failed to approve task.")
                    with col_reject:
                        if st.button("Reject", key=f"reject_{task_row['task_id']}"):
                            if db.update_task_status(task_row['task_id'], 'Rejected'):
                                st.success("Task rejected!")
                                st.rerun()
                            else:
                                st.error("Failed to reject task.")
        else:
            st.info("No tasks are currently pending your approval.")

        st.markdown("---")
        # --- Goal Setting (CREATE) ---
        st.subheader("Set a New Goal")
        employees_df = db.get_users_by_role('Employee')
        if not employees_df.empty:
            with st.form("new_goal_form"):
                employee_name = st.selectbox("Select Employee:", employees_df['name'])
                employee_id = employees_df[employees_df['name'] == employee_name]['user_id'].iloc[0]
                description = st.text_area("Goal Description:")
                due_date = st.date_input("Due Date:", min_value=date.today())
                submitted = st.form_submit_button("Set Goal")
                if submitted:
                    goal_id = db.create_goal(int(employee_id), int(st.session_state['user_id']), description, due_date)
                    if goal_id:
                        st.success(f"Goal set successfully for {employee_name}!")
                        st.rerun()
                    else:
                        st.error("Failed to set goal.")
        else:
            st.warning("No employees found. Please add an employee to your database.")

        st.markdown("---")
        # --- Goal & Task Management (READ & UPDATE) ---
        st.subheader("Review Team Goals & Tasks")
        # CHANGE MADE HERE: Use get_manager_goals instead of get_employee_goals
        goals_df = db.get_manager_goals(st.session_state['user_id'])
        if not goals_df.empty:
            for _, goal_row in goals_df.iterrows():
                with st.expander(f"Goal for {goal_row['employee_name']}: {goal_row['goal_description']} (Due: {goal_row['due_date']})"):
                    st.write(f"**Status:** {goal_row['status']}")
                    
                    st.markdown("#### Tasks Logged")
                    tasks_df = db.get_tasks_for_goal(goal_row['goal_id'])
                    if not tasks_df.empty:
                        st.dataframe(tasks_df, use_container_width=True)
                    else:
                        st.info("No tasks have been logged for this goal yet.")

                    # --- Feedback (CREATE) ---
                    st.markdown("#### Provide Feedback")
                    feedback_text = st.text_area("Your feedback:", key=f"feedback_{goal_row['goal_id']}")
                    if st.button("Submit Feedback", key=f"submit_feedback_{goal_row['goal_id']}"):
                        if db.create_feedback(goal_row['goal_id'], st.session_state['user_id'], feedback_text):
                            st.success("Feedback submitted successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to submit feedback.")

                    # --- Goal Status Update (UPDATE) ---
                    st.markdown("#### Update Goal Status")
                    new_status = st.selectbox("Update status:", ['Draft', 'In Progress', 'Completed', 'Cancelled'], index=['Draft', 'In Progress', 'Completed', 'Cancelled'].index(goal_row['status']), key=f"status_{goal_row['goal_id']}")
                    if st.button("Update Status", key=f"update_status_{goal_row['goal_id']}"):
                        if db.update_goal_status(goal_row['goal_id'], new_status):
                            st.success(f"Goal status updated to '{new_status}'!")
                            st.rerun()
                        else:
                            st.error("Failed to update status.")
        else:
            st.info("You have not set any goals for your team yet.")

    elif st.session_state['selected_role'] == 'Employee':
        st.header("Employee Dashboard")
        st.info("View your goals, log your progress, and see feedback.")

        # --- View Goals & Log Tasks (READ & CREATE) ---
        st.subheader("My Current Goals")
        goals_df = db.get_employee_goals(st.session_state['user_id'])
        if not goals_df.empty:
            for _, goal_row in goals_df.iterrows():
                with st.expander(f"Goal: {goal_row['description']} (Due: {goal_row['due_date']})"):
                    st.write(f"**Status:** {goal_row['status']}")
                    st.write(f"**Assigned By:** {goal_row['manager_name']}")

                    # --- Log Tasks (CREATE) ---
                    st.markdown("##### Log a New Task")
                    task_description = st.text_input("Task you completed:", key=f"task_desc_{goal_row['goal_id']}")
                    if st.button("Log Task", key=f"log_task_{goal_row['goal_id']}"):
                        if task_description:
                            if db.create_task(goal_row['goal_id'], task_description):
                                st.success("Task logged successfully! Waiting for manager approval.")
                                st.rerun()
                            else:
                                st.error("Failed to log task.")
                        else:
                            st.warning("Please provide a task description.")

                    # --- View Tasks (READ) ---
                    st.markdown("##### My Tasks")
                    tasks_df = db.get_tasks_for_goal(goal_row['goal_id'])
                    if not tasks_df.empty:
                        st.dataframe(tasks_df, use_container_width=True)
                    else:
                        st.info("No tasks logged yet.")
                    
                    # --- View Feedback (READ) ---
                    st.markdown("##### Manager Feedback")
                    feedback_df = db.get_feedback_for_goal(goal_row['goal_id'])
                    if not feedback_df.empty:
                        for _, feedback_row in feedback_df.iterrows():
                            st.write(f"**{feedback_row['manager_name']}** on {feedback_row['created_at'].strftime('%Y-%m-%d')}:")
                            st.info(feedback_row['feedback_text'])
                    else:
                        st.info("No feedback has been provided for this goal yet.")
        else:
            st.info("You currently have no goals assigned.")

    # --- Performance History (REPORTING) ---
    st.markdown("---")
    st.header("Performance History Report")
    st.info("View your comprehensive performance history including all goals, tasks, and feedback.")
    history_df = db.get_employee_performance_history(st.session_state['user_id'])
    if not history_df.empty:
        st.dataframe(history_df, use_container_width=True)
    else:
        st.warning("No performance history found.")