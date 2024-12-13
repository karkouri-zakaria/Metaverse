import time
import streamlit as st
from backend.database import Database
import sqlite3

class Auth:
    def __init__(self, db_name):
        self.db = Database(db_name)

    def register(self, username, password, confirm_password):
        if password != confirm_password:
            st.error('Passwords do not match!')
        else:
            try:
                self.db.add_user(username, password)
                st.success('User registered successfully!')
            except sqlite3.IntegrityError:
                st.error('Username already exists!')

    def login(self, username, password):
        user = self.db.get_user(username)
        if user and self.db.verify_password(user[1], password):
            st.session_state['logged_in'] = True
            st.session_state['user_id'] = user[0]
            st.session_state['username'] = username
            st.success(f'Welcome, {username}!, You have successfully logged in!')
            time.sleep(1)
            st.rerun()
        else:
            st.error('Invalid username or password!')
