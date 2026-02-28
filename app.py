import streamlit as st
import mysql.connector
import hashlib
import re
from datetime import datetime
import pandas as pd

# MySQL configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Rohit@123',
    'database': 'hospital_db'
}

# Constant passkey for all users
CONSTANT_PASSKEY = "PASS12"

# Function to connect to MySQL
def get_db_connection():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as err:
        st.error(f"Error connecting to database: {err}")
        return None

# Initialize database and tables
def init_db():
    conn = get_db_connection()
    if not conn:
        return
    cursor = conn.cursor()
    
    # Updated users table with passkey, security_question, and security_answer
    # Set a default constant passkey
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(64) NOT NULL,
            passkey VARCHAR(6) NOT NULL DEFAULT 'PASS123',
            security_question VARCHAR(255) NOT NULL,
            security_answer VARCHAR(255) NOT NULL
        )
    ''')

    # Create patients table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            patient_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            age INT NOT NULL,
            gender ENUM('Male', 'Female', 'Other') NOT NULL,
            contact VARCHAR(15),
            admission_date DATETIME
        )
    ''')

    # Create doctors table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS doctors (
            doctor_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            specialty VARCHAR(100) NOT NULL,
            contact VARCHAR(15)
        )
    ''')

    # Create beds table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS beds (
            bed_id INT AUTO_INCREMENT PRIMARY KEY,
            ward VARCHAR(50) NOT NULL,
            status ENUM('available', 'occupied', 'maintenance') NOT NULL,
            last_cleaned DATETIME
        )
    ''')

    # Create assignments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assignments (
            assignment_id INT AUTO_INCREMENT PRIMARY KEY,
            patient_id INT,
            bed_id INT,
            doctor_id INT,
            assignment_date DATETIME,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
            FOREIGN KEY (bed_id) REFERENCES beds(bed_id),
            FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id)
        )
    ''')

    conn.commit()
    cursor.close()
    conn.close()

# Hash password using SHA-256
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Validate username as an email
def validate_email(username):
    email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(email_pattern, username))

# Login function with passkey validation
def login(username, password, passkey):
    conn = get_db_connection()
    if not conn:
        return None
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
    user = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if user and user['password_hash'] == hash_password(password) and user['passkey'] == passkey:
        return user
    return None

# Register function with constant passkey
def register(name, username, password, security_question, security_answer):
    if not name or not username or not password or not security_question or not security_answer:
        return False, "All fields are required"
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not validate_email(username):
        return False, "Username must be a valid email address (e.g., user@example.com)"
    
    password_hash = hash_password(password)
    passkey = CONSTANT_PASSKEY  # Use the constant passkey
    
    conn = get_db_connection()
    if not conn:
        return False, "Database connection failed"
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO users (name, username, password_hash, passkey, security_question, security_answer)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (name, username, password_hash, passkey, security_question, security_answer))
        conn.commit()
        return True, "Account created successfully! Please use the passkey PASS123 to log in."
    except mysql.connector.Error as err:
        return False, f"Error: {err}"
    finally:
        cursor.close()
        conn.close()

# Password reset function
def reset_password(username, security_answer, new_password):
    if len(new_password) < 8:
        return False, "New password must be at least 8 characters long"
    
    conn = get_db_connection()
    if not conn:
        return False, "Database connection failed"
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT security_answer FROM users WHERE username = %s', (username,))
    user = cursor.fetchone()
    
    if not user:
        cursor.close()
        conn.close()
        return False, "User not found"
    
    if user['security_answer'].lower() != security_answer.lower():
        cursor.close()
        conn.close()
        return False, "Incorrect security answer"
    
    try:
        new_password_hash = hash_password(new_password)
        cursor.execute('UPDATE users SET password_hash = %s WHERE username = %s', (new_password_hash, username))
        conn.commit()
        cursor.close()
        conn.close()
        return True, "Password reset successfully"
    except mysql.connector.Error as err:
        cursor.close()
        conn.close()
        return False, f"Error: {err}"

# Get security question for a user
def get_security_question(username):
    conn = get_db_connection()
    if not conn:
        return None
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT security_question FROM users WHERE username = %s', (username,))
    user = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return user['security_question'] if user else None

# Add patient
def add_patient(name, age, gender, contact):
    if not name or not age or not gender:
        return False, "Name, age, and gender are required"
    
    try:
        age = int(age)
        if age <= 0:
            raise ValueError
    except ValueError:
        return False, "Age must be a positive number"
    
    if gender not in ['Male', 'Female', 'Other']:
        return False, "Gender must be Male, Female, or Other"
    
    conn = get_db_connection()
    if not conn:
        return False, "Database connection failed"
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO patients (name, age, gender, contact, admission_date)
            VALUES (%s, %s, %s, %s, NOW())
        ''', (name, age, gender, contact or None))
        conn.commit()
        return True, "Patient added successfully"
    except mysql.connector.Error as err:
        return False, f"Error: {err}"
    finally:
        cursor.close()
        conn.close()

# Delete patient
def delete_patient(patient_id):
    conn = get_db_connection()
    if not conn:
        return False, "Database connection failed"
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM patients WHERE patient_id = %s', (patient_id,))
        if cursor.rowcount == 0:
            return False, "Patient not found"
        conn.commit()
        return True, "Patient deleted successfully"
    except mysql.connector.Error as err:
        return False, f"Error: {err}"
    finally:
        cursor.close()
        conn.close()

# Get patients
def get_patients():
    conn = get_db_connection()
    if not conn:
        return []
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM patients')
    patients = cursor.fetchall()
    cursor.close()
    conn.close()
    return patients

# Add doctor
def add_doctor(name, specialty, contact):
    if not name or not specialty:
        return False, "Name and specialty are required"
    
    conn = get_db_connection()
    if not conn:
        return False, "Database connection failed"
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO doctors (name, specialty, contact)
            VALUES (%s, %s, %s)
        ''', (name, specialty, contact or None))
        conn.commit()
        return True, "Doctor added successfully"
    except mysql.connector.Error as err:
        return False, f"Error: {err}"
    finally:
        cursor.close()
        conn.close()

# Delete doctor
def delete_doctor(doctor_id):
    conn = get_db_connection()
    if not conn:
        return False, "Database connection failed"
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM doctors WHERE doctor_id = %s', (doctor_id,))
        if cursor.rowcount == 0:
            return False, "Doctor not found"
        conn.commit()
        return True, "Doctor deleted successfully"
    except mysql.connector.Error as err:
        return False, f"Error: {err}"
    finally:
        cursor.close()
        conn.close()

# Get doctors
def get_doctors():
    conn = get_db_connection()
    if not conn:
        return []
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM doctors')
    doctors = cursor.fetchall()
    cursor.close()
    conn.close()
    return doctors

# Add bed
def add_bed(ward, status):
    if not ward or not status:
        return False, "Ward and status are required"
    
    if status not in ['available', 'occupied', 'maintenance']:
        return False, "Status must be available, occupied, or maintenance"
    
    conn = get_db_connection()
    if not conn:
        return False, "Database connection failed"
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO beds (ward, status, last_cleaned)
            VALUES (%s, %s, NOW())
        ''', (ward, status))
        conn.commit()
        return True, "Bed added successfully"
    except mysql.connector.Error as err:
        return False, f"Error: {err}"
    finally:
        cursor.close()
        conn.close()

# Delete bed
def delete_bed(bed_id):
    conn = get_db_connection()
    if not conn:
        return False, "Database connection failed"
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM beds WHERE bed_id = %s', (bed_id,))
        if cursor.rowcount == 0:
            return False, "Bed not found"
        conn.commit()
        return True, "Bed deleted successfully"
    except mysql.connector.Error as err:
        return False, f"Error: {err}"
    finally:
        cursor.close()
        conn.close()

# Get beds
def get_beds():
    conn = get_db_connection()
    if not conn:
        return []
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM beds')
    beds = cursor.fetchall()
    cursor.close()
    conn.close()
    return beds

# Get available beds
def get_available_beds():
    conn = get_db_connection()
    if not conn:
        return []
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM beds WHERE status = "available"')
    beds = cursor.fetchall()
    cursor.close()
    conn.close()
    return beds

# Create assignment
def create_assignment(patient_id, bed_id, doctor_id):
    if not patient_id or not bed_id or not doctor_id:
        return False, "Please select a patient, bed, and doctor"
    
    conn = get_db_connection()
    if not conn:
        return False, "Database connection failed"
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute('SELECT status FROM beds WHERE bed_id = %s', (bed_id,))
        bed = cursor.fetchone()
        if not bed or bed['status'] != 'available':
            return False, "Selected bed is not available"
        
        cursor.execute('''
            INSERT INTO assignments (patient_id, bed_id, doctor_id, assignment_date)
            VALUES (%s, %s, %s, NOW())
        ''', (patient_id, bed_id, doctor_id))
        
        cursor.execute('UPDATE beds SET status = "occupied" WHERE bed_id = %s', (bed_id,))
        
        conn.commit()
        return True, "Assignment created successfully"
    except mysql.connector.Error as err:
        return False, f"Error: {err}"
    finally:
        cursor.close()
        conn.close()

# Delete assignment
def delete_assignment(assignment_id):
    conn = get_db_connection()
    if not conn:
        return False, "Database connection failed"
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT bed_id FROM assignments WHERE assignment_id = %s', (assignment_id,))
        result = cursor.fetchone()
        if not result:
            return False, "Assignment not found"
        
        bed_id = result[0]
        
        cursor.execute('DELETE FROM assignments WHERE assignment_id = %s', (assignment_id,))
        cursor.execute('UPDATE beds SET status = "available" WHERE bed_id = %s', (bed_id,))
        
        conn.commit()
        return True, "Assignment deleted successfully"
    except mysql.connector.Error as err:
        return False, f"Error: {err}"
    finally:
        cursor.close()
        conn.close()

# Get assignments
def get_assignments():
    conn = get_db_connection()
    if not conn:
        return []
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT a.assignment_id, p.name as patient_name, b.bed_id, b.ward, d.name as doctor_name, a.assignment_date
        FROM assignments a
        JOIN patients p ON a.patient_id = p.patient_id
        JOIN beds b ON a.bed_id = b.bed_id
        JOIN doctors d ON a.doctor_id = d.doctor_id
    ''')
    assignments = cursor.fetchall()
    cursor.close()
    conn.close()
    return assignments

# Search function
def search_data(search_type, search_term):
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()
    cursor = conn.cursor(dictionary=True)
    
    if search_type == "Patient":
        cursor.execute('SELECT patient_id, name, age, gender, contact, admission_date FROM patients WHERE name LIKE %s', (f'%{search_term}%',))
        results = cursor.fetchall()
        df = pd.DataFrame(results)
    elif search_type == "Doctor":
        cursor.execute('SELECT doctor_id, name, specialty, contact FROM doctors WHERE specialty LIKE %s OR name LIKE %s', 
                      (f'%{search_term}%', f'%{search_term}%'))
        results = cursor.fetchall()
        df = pd.DataFrame(results)
    elif search_type == "Bed":
        cursor.execute('SELECT bed_id, ward, status, last_cleaned FROM beds WHERE ward LIKE %s OR status = %s', 
                      (f'%{search_term}%', search_term))
        results = cursor.fetchall()
        df = pd.DataFrame(results)
    else:
        df = pd.DataFrame()
    
    cursor.close()
    conn.close()
    return df

# Main Streamlit app
def main():
    init_db()
    
    # Initialize session state
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'page' not in st.session_state:
        st.session_state.page = 'login'
    if 'riddle_passed' not in st.session_state:
        st.session_state.riddle_passed = False
    if 'forgot_password' not in st.session_state:
        st.session_state.forgot_password = False

    # Custom CSS (preserving existing styling)
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');

        body {
            font-family: 'Roboto', sans-serif;
            background: #ADD8E6;
        }
        .main {
            background: #FFFFFF;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            max-width: 1200px;
            margin: auto;
        }
        .stSidebar {
            background: linear-gradient(180deg, #4dabf7 0%, #74c0fc 100%);
            color: white;
            border-radius: 10px;
        }
        .stSidebar .sidebar-content {
            padding: 20px;
        }
        .stSidebar h2 {
            color: white;
            font-size: 24px;
            margin-bottom: 20px;
        }
        .stSidebar select {
            background: rgba(255, 255, 255, 0.1);
            color: white;
            border: none;
            border-radius: 5px;
            padding: 10px;
        }
        .stSidebar select option {
            background: #4dabf7;
            color: white;
        }
        .stButton>button {
            background: #007BFF;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 12px 20px;
            font-size: 16px;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            background: #0056b3;
            transform: scale(1.05);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        }
        .stTextInput>input, .stNumberInput>input, .stSelectbox>div>select {
            background: #FFFFFF;
            border: 2px solid #ced4da;
            border-radius: 8px;
            padding: 10px;
            font-size: 16px;
        }
        .stTextInput>input:focus, .stNumberInput>input:focus, .stSelectbox>div>select:focus {
            border-color: #007BFF;
            box-shadow: 0 0 5px rgba(0, 123, 255, 0.5);
        }
        h1, h2, h3 {
            color: #343a40;
            font-weight: 700;
        }
        .stDataFrame {
            border: 1px solid #dee2e6;
            border-radius: 8px;
            overflow: hidden;
        }
        .stDataFrame table {
            width: 100%;
            border-collapse: collapse;
        }
        .stDataFrame tr:nth-child(even) {
            background: #f8f9fa;
        }
        .stDataFrame tr:hover {
            background: #e9ecef;
        }
        .stDataFrame th, .stDataFrame td {
            padding: 12px;
            text-align: left;
        }
        .stSuccess, .stError, .stWarning {
            border-radius: 8px;
            padding: 15px;
            animation: fadeIn 0.5s ease-in;
        }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        .form-container {
            max-width: 500px;
            margin: 50px auto;
            padding: 20px;
            text-align: center;
        }
        .sidebar-option::before {
            content: "➡️ ";
            margin-right: 5px;
        }
        </style>
    """, unsafe_allow_html=True)

    # Riddle for authentication
    riddle = "I speak without a mouth and hear without ears. I have no body, but I come alive with the wind. What am I?"
    correct_answer = "echo"

    # Security questions options
    security_questions = [
        "What was the name of your first pet?",
        "What is your mother's maiden name?",
        "What was the name of your elementary school?",
        "What is your favorite book?"
    ]

    # Login page with riddle and passkey
    if st.session_state.page == 'login' and not st.session_state.user:
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.title("Hospital Bed Management System")
        
        if not st.session_state.forgot_password:
            # Riddle authentication step
            if not st.session_state.riddle_passed:
                st.markdown("<h2>Solve the Riddle</h2>", unsafe_allow_html=True)
                st.write(riddle)
                riddle_answer = st.text_input("Your Answer", placeholder="Enter the answer to the riddle")
                if st.button("Submit Answer"):
                    if riddle_answer.lower() == correct_answer.lower():
                        st.session_state.riddle_passed = True
                        st.success("Correct! Proceed to login.")
                        st.rerun()
                    else:
                        st.error("Incorrect answer. Try again.")
            else:
                # Login form after passing riddle
                st.markdown("<h2>Login</h2>", unsafe_allow_html=True)
                st.markdown(
                    "<p style='color: #343a40; font-size: 16px;'>Use the passkey: <strong>PASS12</strong></p>",
                    unsafe_allow_html=True
                )
                
                with st.form("login_form"):
                    username = st.text_input("Email", placeholder="Enter your email (e.g., user@example.com)")
                    password = st.text_input("Password", type="password", placeholder="Enter your password")
                    passkey = st.text_input("Passkey", placeholder="Enter the passkey (PASS12)")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        login_button = st.form_submit_button("Login")
                    with col2:
                        register_button = st.form_submit_button("Go to Register")
                    with col3:
                        forgot_button = st.form_submit_button("Forgot Password")
                    
                    if login_button:
                        if not validate_email(username):
                            st.error("Please enter a valid email address")
                        else:
                            user = login(username, password, passkey)
                            if user:
                                st.session_state.user = user
                                st.session_state.page = 'main'
                                st.session_state.riddle_passed = False  # Reset for next login
                                st.success("Login successful!")
                                st.rerun()
                            else:
                                st.error("Invalid email, password, or passkey")
                    
                    if register_button:
                        st.session_state.page = 'register'
                        st.session_state.riddle_passed = False
                        st.rerun()
                    
                    if forgot_button:
                        st.session_state.forgot_password = True
                        st.rerun()
        
        else:
            # Forgot Password flow
            st.markdown("<h2>Reset Password</h2>", unsafe_allow_html=True)
            username = st.text_input("Email", placeholder="Enter your email (e.g., user@example.com)", key="reset_email")
            
            if username:
                security_question = get_security_question(username)
                if security_question:
                    st.write(f"Security Question: {security_question}")
                    security_answer = st.text_input("Your Answer", placeholder="Enter your answer")
                    new_password = st.text_input("New Password", type="password", placeholder="Enter new password")
                    
                    if st.button("Reset Password"):
                        success, message = reset_password(username, security_answer, new_password)
                        if success:
                            st.success(message)
                            st.session_state.forgot_password = False
                            st.session_state.riddle_passed = False
                            st.rerun()
                        else:
                            st.error(message)
                else:
                    st.error("User not found")
            
            if st.button("Back to Login"):
                st.session_state.forgot_password = False
                st.session_state.riddle_passed = False
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Register page with security question and constant passkey
    elif st.session_state.page == 'register' and not st.session_state.user:
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.title("Hospital Bed Management System")
        st.markdown("<h2>Create New Account</h2>", unsafe_allow_html=True)
        
        with st.form("register_form"):
            name = st.text_input("Full Name", placeholder="Enter your full name")
            username = st.text_input("Email", placeholder="Enter your email (e.g., user@example.com)")
            password = st.text_input("Password (minimum 8 characters)", type="password", placeholder="Enter your password")
            security_question = st.selectbox("Security Question", security_questions)
            security_answer = st.text_input("Security Answer", placeholder="Enter your answer")
            col1, col2 = st.columns(2)
            with col1:
                register_button = st.form_submit_button("Register")
            with col2:
                login_button = st.form_submit_button("Back to Login")
            
            if register_button:
                success, message = register(name, username, password, security_question, security_answer)
                if success:
                    # Display success message without redirecting immediately
                    st.markdown(
                        f"""
                        <div style='background-color: #28a745; color: white; padding: 15px; border-radius: 8px; text-align: center; font-size: 18px;'>
                            {message}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    # Add a button to proceed to login
                    if st.button("Continue to Login"):
                        st.session_state.page = 'login'
                        st.rerun()
                else:
                    st.error(f"Registration failed: {message}")
            
            if login_button:
                st.session_state.page = 'login'
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Main app
    elif st.session_state.user:
        st.sidebar.markdown(f"<h2>Welcome, {st.session_state.user['name']}</h2>", unsafe_allow_html=True)
        page = st.sidebar.selectbox("Navigate", 
                                   ["Dashboard", "Patients", "Doctors", "Beds", "Assignments", "Search", "Logout"],
                                   format_func=lambda x: f"{x}")
        
        if page == "Logout":
            st.session_state.user = None
            st.session_state.page = 'login'
            st.session_state.riddle_passed = False
            st.success("Logged out successfully")
            st.rerun()
        
        elif page == "Dashboard":
            st.title("Dashboard")
            st.markdown("### Overview")
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute('SELECT COUNT(*) as count FROM patients')
                patient_count = cursor.fetchone()['count']
                cursor.execute('SELECT COUNT(*) as count FROM doctors')
                doctor_count = cursor.fetchone()['count']
                cursor.execute('SELECT COUNT(*) as count FROM beds')
                bed_count = cursor.fetchone()['count']
                cursor.execute('SELECT COUNT(*) as count FROM beds WHERE status = "available"')
                available_bed_count = cursor.fetchone()['count']
                cursor.execute('SELECT COUNT(*) as count FROM assignments')
                assignment_count = cursor.fetchone()['count']
                cursor.close()
                conn.close()
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Patients", patient_count)
                col2.metric("Total Doctors", doctor_count)
                col3.metric("Total Beds", bed_count)
                col1.metric("Available Beds", available_bed_count)
                col2.metric("Assignments", assignment_count)
        
        elif page == "Patients":
            st.title("Manage Patients")
            
            with st.form("add_patient_form"):
                st.subheader("Add New Patient")
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("Name", placeholder="Enter patient name")
                    gender = st.selectbox("Gender", ["Male", "Female", "Other"], key="patient_gender")
                with col2:
                    age = st.number_input("Age", min_value=0, step=1, value=0)
                    contact = st.text_input("Contact (optional)", placeholder="Enter contact number")
                submit = st.form_submit_button("Add Patient")
                
                if submit:
                    success, message = add_patient(name, age, gender, contact)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
            
            st.subheader("Patients List")
            patients = get_patients()
            if patients:
                df = pd.DataFrame(patients)
                df = df[['patient_id', 'name', 'age', 'gender', 'contact', 'admission_date']]
                df.columns = ['ID', 'Name', 'Age', 'Gender', 'Contact', 'Admission Date']
                st.dataframe(df, use_container_width=True)
                
                st.subheader("Delete Patient")
                patient_id = st.number_input("Enter Patient ID to delete", min_value=1, step=1, key="delete_patient")
                if st.button("Delete Patient"):
                    success, message = delete_patient(patient_id)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.write("No patients found")
        
        elif page == "Doctors":
            st.title("Manage Doctors")
            
            with st.form("add_doctor_form"):
                st.subheader("Add New Doctor")
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("Name", placeholder="Enter doctor name")
                with col2:
                    specialty = st.text_input("Specialty", placeholder="Enter specialty")
                contact = st.text_input("Contact (optional)", placeholder="Enter contact number")
                submit = st.form_submit_button("Add Doctor")
                
                if submit:
                    success, message = add_doctor(name, specialty, contact)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
            
            st.subheader("Doctors List")
            doctors = get_doctors()
            if doctors:
                df = pd.DataFrame(doctors)
                df = df[['doctor_id', 'name', 'specialty', 'contact']]
                df.columns = ['ID', 'Name', 'Specialty', 'Contact']
                st.dataframe(df, use_container_width=True)
                
                st.subheader("Delete Doctor")
                doctor_id = st.number_input("Enter Doctor ID to delete", min_value=1, step=1, key="delete_doctor")
                if st.button("Delete Doctor"):
                    success, message = delete_doctor(doctor_id)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.write("No doctors found")
        
        elif page == "Beds":
            st.title("Manage Beds")
            
            with st.form("add_bed_form"):
                st.subheader("Add New Bed")
                col1, col2 = st.columns(2)
                with col1:
                    ward = st.text_input("Ward", placeholder="Enter ward name")
                with col2:
                    status = st.selectbox("Status", ["available", "occupied", "maintenance"], key="bed_status")
                submit = st.form_submit_button("Add Bed")
                
                if submit:
                    success, message = add_bed(ward, status)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
            
            st.subheader("Beds List")
            beds = get_beds()
            if beds:
                df = pd.DataFrame(beds)
                df = df[['bed_id', 'ward', 'status', 'last_cleaned']]
                df.columns = ['ID', 'Ward', 'Status', 'Last Cleaned']
                st.dataframe(df, use_container_width=True)
                
                st.subheader("Delete Bed")
                bed_id = st.number_input("Enter Bed ID to delete", min_value=1, step=1, key="delete_bed")
                if st.button("Delete Bed"):
                    success, message = delete_bed(bed_id)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.write("No beds found")
        
        elif page == "Assignments":
            st.title("Manage Assignments")
            
            with st.form("add_assignment_form"):
                st.subheader("Create New Assignment")
                patients = get_patients()
                beds = get_available_beds()
                doctors = get_doctors()
                
                patient_options = {f"{p['name']} (ID: {p['patient_id']})": p['patient_id'] for p in patients}
                bed_options = {f"{b['ward']} (ID: {b['bed_id']})": b['bed_id'] for b in beds}
                doctor_options = {f"{d['name']} (ID: {d['doctor_id']})": d['doctor_id'] for d in doctors}
                
                col1, col2 = st.columns(2)
                with col1:
                    patient = st.selectbox("Patient", list(patient_options.keys()) if patient_options else ["No patients available"], 
                                          key="assign_patient")
                    doctor = st.selectbox("Doctor", list(doctor_options.keys()) if doctor_options else ["No doctors available"], 
                                         key="assign_doctor")
                with col2:
                    bed = st.selectbox("Bed", list(bed_options.keys()) if bed_options else ["No available beds"], 
                                      key="assign_bed")
                
                submit = st.form_submit_button("Create Assignment")
                
                if submit:
                    if not patient_options or not bed_options or not doctor_options:
                        st.error("Cannot create assignment: Missing patients, beds, or doctors")
                    else:
                        success, message = create_assignment(
                            patient_options[patient],
                            bed_options[bed],
                            doctor_options[doctor]
                        )
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
            
            st.subheader("Assignments List")
            assignments = get_assignments()
            if assignments:
                df = pd.DataFrame(assignments)
                df = df[['assignment_id', 'patient_name', 'bed_id', 'ward', 'doctor_name', 'assignment_date']]
                df.columns = ['ID', 'Patient', 'Bed ID', 'Ward', 'Doctor', 'Assignment Date']
                st.dataframe(df, use_container_width=True)
                
                st.subheader("Delete Assignment")
                assignment_id = st.number_input("Enter Assignment ID to delete", min_value=1, step=1, key="delete_assignment")
                if st.button("Delete Assignment"):
                    success, message = delete_assignment(assignment_id)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
            else:
                st.write("No assignments found")
        
        elif page == "Search":
            st.title("Search Data")
            
            with st.form("search_form"):
                st.subheader("Search Records")
                col1, col2 = st.columns(2)
                with col1:
                    search_type = st.selectbox("Search Type", ["Patient", "Doctor", "Bed"], key="search_type")
                with col2:
                    search_term = st.text_input("Search Term", placeholder="Enter search term", key="search_term")
                submit = st.form_submit_button("Search")
                
                if submit and search_term:
                    df = search_data(search_type, search_term)
                    if not df.empty:
                        st.subheader(f"Search Results for '{search_term}' in {search_type}")
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.warning(f"No {search_type.lower()}s found matching '{search_term}'")
                elif submit:
                    st.error("Please enter a search term")

if __name__ == "__main__":
    main()