import streamlit as st
import sqlite3
import pandas as pd
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import re

# --- Configuration ---
DB_NAME = "users.db"
# IMPORTANT: Replace with your actual Gmail address and App Password
SENDER_EMAIL = "hmuktanandg@gmail.com"  # <--- REPLACE THIS WITH YOUR GMAIL ADDRESS
SENDER_PASSWORD = "mqjdzdktaxqbtief"  # <--- REPLACE THIS WITH YOUR GMAIL APP PASSWORD

# --- Database Functions ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone_number TEXT,
            is_email_verified BOOLEAN DEFAULT FALSE,
            instagram_handle TEXT,
            followers_count INTEGER,
            following_count INTEGER,
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_user(name, email, phone_number=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (name, email, phone_number) VALUES (?, ?, ?)",
                  (name, email, phone_number))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        st.error("This email is already registered.")
        return False
    finally:
        conn.close()

def update_email_verification_status(email, status):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET is_email_verified = ? WHERE email = ?", (status, email))
    conn.commit()
    conn.close()

def update_instagram_details(email, insta_handle, followers, following):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET instagram_handle = ?, followers_count = ?, following_count = ? WHERE email = ?",
              (insta_handle, followers, following, email))
    conn.commit()
    conn.close()

def get_user_by_email(email):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = c.fetchone()
    conn.close()
    if user:
        columns = [description[0] for description in c.description]
        return dict(zip(columns, user))
    return None

def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM users", conn)
    conn.close()
    return df

# --- Email Functions ---
def send_otp_email(receiver_email, otp):
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = receiver_email
    msg['Subject'] = "Your OTP for Account Verification"

    body = f"""
    Hello,

    Your One-Time Password (OTP) for verifying your account is:

    **{otp}**

    This OTP is valid for 5 minutes. Please do not share this with anyone.

    Thank you,
    The App Team
    """
    msg.attach(MIMEText(body, 'html'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Failed to send OTP email. Error: {e}")
        st.warning("Please ensure you have enabled 'Less secure app access' or generated an App Password for your Gmail account if using Gmail.")
        st.warning("For Gmail, you might need to generate an App Password: go to Google Account -> Security -> App passwords.")
        return False

def send_instagram_fraud_report_email(receiver_email, insta_handle, report):
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = receiver_email
    msg['Subject'] = f"Instagram Account Analysis Report for @{insta_handle}"

    body = f"""
    Hello,

    Here is the analysis report for the Instagram account **@{insta_handle}** you registered:

    {report}

    **Important Disclaimer:**
    This analysis is based on publicly available information (which you provided) and common patterns of potentially fake accounts. It is **not a definitive declaration of fraud** but rather provides insights and potential red flags. Instagram's policies prevent direct programmatic verification of account authenticity without specific partnerships. Always exercise caution and perform your own due diligence.

    If you believe this analysis is incorrect or your account details are wrong, please re-register or contact support.

    Thank you,
    The App Team
    """
    msg.attach(MIMEText(body, 'html'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Failed to send report email. Error: {e}")
        return False

# --- OTP Generation and Validation ---
def generate_otp():
    return str(random.randint(100000, 999999))

def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def is_valid_phone(phone_number):
    return re.match(r"^\+?\d{10,15}$", phone_number)


# --- Instagram "Fraud" Analysis Heuristics ---
def analyze_instagram_account(insta_handle, followers_count, following_count):
    report_lines = []
    suspicion_score = 0

    report_lines.append(f"**Analysis for Instagram Account: @{insta_handle}**\n")
    report_lines.append("This report highlights potential red flags based on common indicators of fake or suspicious accounts, using the information you provided.")
    report_lines.append("It is not a definitive fraud detection.")

    handle_lower = insta_handle.lower().replace('@', '')

    # --- Heuristic 1: Username Pattern ---
    if re.search(r'\d{5,}', handle_lower):
        report_lines.append("- **Username Pattern (Numbers):** The handle contains a long sequence of numbers (5+ digits), which is sometimes associated with bot or auto-generated accounts. **(Medium Red Flag)**")
        suspicion_score += 30
    elif re.search(r'(_[a-z0-9]){2,}', handle_lower):
        report_lines.append("- **Username Pattern (Underscores/Random):** The handle contains patterns (e.g., multiple underscores followed by random characters) sometimes associated with bot accounts. **(Medium Red Flag)**")
        suspicion_score += 25
    elif re.search(r'[a-z]\d{2,}[a-z]', handle_lower):
        report_lines.append("- **Username Pattern (Mixed):** The handle has a mix of letters and numbers in a non-natural pattern (e.g., a123b). **(Minor Red Flag)**")
        suspicion_score += 15
    else:
        report_lines.append("- **Username Pattern:** The handle appears to be a typical human-readable username.")

    # --- Heuristic 2: Presence of certain keywords in the handle ---
    suspicious_keywords = ["free", "giveaway", "money", "crypto", "official", "fans", "gain", "follow", "likes", "cash", "promo"]
    found_keywords = [k for k in suspicious_keywords if k in handle_lower]
    if found_keywords:
        report_lines.append(f"- **Keywords in Handle:** The handle contains keywords like '{', '.join(found_keywords)}' which can sometimes be used by spam or promotional accounts. **(High Red Flag)**")
        suspicion_score += 40
    else:
        report_lines.append("- **Keywords in Handle:** No obvious suspicious keywords found in the handle.")

    # --- Heuristic 3: Handle Length ---
    if len(handle_lower) < 3 or len(handle_lower) > 25:
        report_lines.append("- **Handle Length:** The handle length is unusually short or long (Instagram allows 3-30 characters). **(Minor Red Flag)**")
        suspicion_score += 10
    else:
        report_lines.append("- **Handle Length:** Handle length is within typical Instagram limits.")

    # --- Heuristic 4: Follower/Following Ratio ---
    if followers_count is not None and following_count is not None:
        report_lines.append(f"\n- **Followers:** {followers_count:,}")
        report_lines.append(f"- **Following:** {following_count:,}")

        if following_count > 0:
            ratio = followers_count / following_count
            report_lines.append(f"- **Follower/Following Ratio (Followers : Following):** {ratio:.2f} : 1")

            # Define thresholds for suspicious ratios, with consideration for large accounts
            CELEBRITY_THRESHOLD_FOLLOWERS = 100_000 # Adjust this threshold as needed (e.g., 500k, 1M)

            if followers_count >= CELEBRITY_THRESHOLD_FOLLOWERS:
                report_lines.append("- **Ratio Analysis:** This account has a very high number of followers, indicating it may be a public figure, celebrity, or large brand. For such accounts, a significantly higher follower-to-following ratio (many followers, few following) is **normal and expected** and does not indicate fraud.")
            elif followers_count < 100 and following_count > 500:
                 report_lines.append("- **Ratio Analysis:** Very low followers compared to a very high number of accounts followed. This is a common pattern for bot accounts. **(High Red Flag)**")
                 suspicion_score += 45
            elif ratio < 0.1 and followers_count < 1000:
                report_lines.append("- **Ratio Analysis:** The account follows significantly more accounts than it has followers, especially for a relatively small follower base. This can be a sign of aggressive 'follow-for-follow' tactics or bot activity. **(Medium Red Flag)**")
                suspicion_score += 35
            elif ratio > 100 and following_count < 100:
                report_lines.append("- **Ratio Analysis:** Extremely high followers compared to very few accounts followed. For an account with fewer than 100,000 followers, this can sometimes indicate bought followers or a highly managed account without genuine reciprocal engagement. **(Minor Red Flag)**")
                suspicion_score += 20
            else:
                report_lines.append("- **Ratio Analysis:** The follower/following ratio appears relatively normal or within typical ranges for real accounts given the follower count.")
        else: # following_count is 0
            if followers_count > 0:
                if followers_count >= CELEBRITY_THRESHOLD_FOLLOWERS:
                    report_lines.append("- **Ratio Analysis:** Account has a high follower count and follows 0 accounts. This is typical for very popular public figures and celebrities. **(Normal)**")
                else:
                    report_lines.append("- **Ratio Analysis:** Account has followers but follows 0 accounts. While possible for certain niches, this is unusual for most active, non-celebrity accounts. **(Minor Red Flag)**")
                    suspicion_score += 10
            else:
                report_lines.append("- **Ratio Analysis:** No followers and no following. This could be a brand new or inactive account.")
    else:
        report_lines.append("\n- **Follower/Following Data:** Not provided. Cannot analyze ratio comprehensively.")


    # --- Determine overall verdict based on suspicion_score ---
    report_lines.append("\n--- Overall Risk Assessment ---")
    if suspicion_score >= 80:
        report_lines.append(f"**Verdict: HIGH SUSPICION OF FRAUDULENT ACTIVITY** 🚨")
        report_lines.append("Based on the provided information, this account exhibits multiple strong indicators often associated with fake, bot, or scam accounts. **Extreme caution is advised.**")
    elif 45 <= suspicion_score < 80:
        report_lines.append(f"**Verdict: MEDIUM SUSPICION** ⚠️")
        report_lines.append("This account shows several patterns that are frequently seen in suspicious or less genuine accounts. Further manual inspection is highly recommended.")
    else:
        report_lines.append(f"**Verdict: LOW SUSPICION** ✅")
        report_lines.append("Based on the provided information, this account does not trigger significant automated red flags. However, **manual verification is still crucial.**")

    report_lines.append(f"\n**(Calculated Suspicion Score: {suspicion_score}/100)**")


    # General advice (most important part, as direct checks are limited)
    report_lines.append("\n**General Advice for Spotting Fake Instagram Accounts (Manual Check):**")
    report_lines.append("Please manually check the following on the Instagram profile:")
    report_lines.append("- **Profile Picture:** Is it generic, low-quality, or a stock photo? Real accounts usually have a clear, personal profile picture.")
    report_lines.append("- **Bio:** Is it empty, spammy, contains many irrelevant emojis, or promotes suspicious links/offers? Genuine bios are usually more descriptive.")
    report_lines.append("- **Posts:** Does the account have very few posts, or are they low-quality, repetitive, or stolen content? Look for original content and a consistent posting history.")
    report_lines.append("- **Engagement:** Do the posts have genuine comments and likes, or are comments generic, repetitive, or spammy? Low engagement on many posts can be a sign of fake followers.")
    report_lines.append("- **Activity:** Is the account active, or does it seem to suddenly post a lot or very little?")
    report_lines.append("- **Account Creation Date:** Newer accounts with high activity or suspicious patterns are often red flags.")
    report_lines.append(f"Visit the profile: [https://www.instagram.com/{handle_lower}](https://www.instagram.com/{handle_lower})")

    return "\n".join(report_lines)


# --- Streamlit App ---
def main():
    init_db()
    st.set_page_config(page_title="Secure Account & Instagram Analysis", layout="centered")

    st.title("User Account Registration and Instagram Analysis")
    st.markdown("Register and verify your account via email, then check your registered Instagram handle for potential red flags.")

    if "current_stage" not in st.session_state:
        st.session_state["current_stage"] = "register"

    if st.session_state["current_stage"] == "register":
        st.header("Step 1: Register Your Details")
        with st.form("registration_form"):
            name = st.text_input("Your Name", key="reg_name_input")
            email = st.text_input("Your Email", key="reg_email_input")
            phone_number = st.text_input("Your Phone Number (Optional, e.g., +919876543210)", key="reg_phone_input")

            register_button = st.form_submit_button("Register & Send OTP")

            if register_button:
                if not name or not email:
                    st.error("Name and Email are required.")
                elif not is_valid_email(email):
                    st.error("Please enter a valid email address.")
                elif phone_number and not is_valid_phone(phone_number):
                    st.error("Please enter a valid phone number (e.g., +91XXXXXXXXXX).")
                else:
                    if add_user(name, email, phone_number):
                        otp = generate_otp()
                        st.session_state["otp"] = otp
                        st.session_state["otp_timestamp"] = time.time()
                        st.session_state["registered_email_for_otp"] = email
                        st.session_state["registered_name_for_otp"] = name

                        if send_otp_email(email, otp):
                            st.success(f"OTP sent to {email}. Please check your inbox.")
                            st.session_state["current_stage"] = "verify_otp"
                            st.rerun()
                        else:
                            pass
        st.markdown("---")
        st.subheader("Already Registered or Verified?")
        if st.button("Check/Update My Account"):
            st.session_state["current_stage"] = "check_account"
            st.rerun()

    elif st.session_state["current_stage"] == "verify_otp":
        st.header("Step 2: Verify Your Email")
        st.info(f"An OTP has been sent to **{st.session_state['registered_email_for_otp']}**. Please enter it below.")

        with st.form("otp_verification_form"):
            user_otp = st.text_input("Enter OTP", key="otp_input")
            verify_button = st.form_submit_button("Verify OTP")

            if verify_button:
                if time.time() - st.session_state.get("otp_timestamp", 0) > 300: # 5 minutes
                    st.error("OTP expired. Please re-register to get a new OTP.")
                    st.session_state["current_stage"] = "register"
                    st.rerun()
                elif user_otp == st.session_state["otp"]:
                    update_email_verification_status(st.session_state["registered_email_for_otp"], True)
                    st.session_state["current_stage"] = "registered"
                    st.session_state["user_email"] = st.session_state["registered_email_for_otp"]
                    st.success("Email verified successfully!")
                    st.rerun()
                else:
                    st.error("Invalid OTP. Please try again.")
        if st.button("Resend OTP"):
            otp = generate_otp()
            st.session_state["otp"] = otp
            st.session_state["otp_timestamp"] = time.time()
            if send_otp_email(st.session_state["registered_email_for_otp"], otp):
                st.success("New OTP sent. Please check your inbox.")
            else:
                st.error("Failed to resend OTP.")

    elif st.session_state["current_stage"] == "check_account":
        st.header("Check/Update Your Account")
        with st.form("check_account_form"):
            check_email = st.text_input("Enter your registered Email", key="check_email_input")
            check_button = st.form_submit_button("Find My Account")

            if check_button:
                user = get_user_by_email(check_email)
                if user:
                    st.session_state["user_email"] = user['email']
                    st.session_state["user_name"] = user['name']
                    st.session_state["user_phone"] = user['phone_number']
                    st.session_state["user_insta"] = user['instagram_handle']
                    st.session_state["user_followers"] = user['followers_count']
                    st.session_state["user_following"] = user['following_count']
                    st.session_state["is_verified"] = user['is_email_verified']
                    st.session_state["current_stage"] = "registered"
                    st.rerun()
                else:
                    st.error("No account found with this email. Please register first.")

    elif st.session_state["current_stage"] == "registered":
        user_email = st.session_state.get("user_email")
        user = get_user_by_email(user_email) if user_email else None

        if user:
            st.header("Your Registered Account Details")
            st.write(f"**Name:** {user['name']}")
            st.write(f"**Email:** {user['email']} {'(Verified ✅)' if user['is_email_verified'] else '(Not Verified ❌ - Check your email for OTP)'}")
            if user['phone_number']:
                st.write(f"**Phone Number:** {user['phone_number']}")
            if user['instagram_handle']:
                st.write(f"**Registered Instagram Handle:** `{user['instagram_handle']}`")
                if user['followers_count'] is not None:
                    st.write(f"**Provided Followers:** {user['followers_count']:,}")
                if user['following_count'] is not None:
                    st.write(f"**Provided Following:** {user['following_count']:,}")
                insta_url = get_instagram_url(user['instagram_handle'])
                if insta_url != "#":
                    st.markdown(f"Visit profile: [Instagram Profile]({insta_url})")
            else:
                st.info("No Instagram handle registered yet.")

            st.markdown("---")
            st.header("Step 3: Analyze Your Instagram Account")
            with st.form("instagram_analysis_form"):
                current_insta_handle = user['instagram_handle'] if user['instagram_handle'] else ""
                # FIX: Default to 0 instead of "" for number inputs
                current_followers = user['followers_count'] if user['followers_count'] is not None else 0
                current_following = user['following_count'] if user['following_count'] is not None else 0

                new_insta_handle = st.text_input(
                    "Enter or Update your Instagram Handle (e.g., @yourusername)",
                    value=current_insta_handle,
                    key="insta_handle_input"
                )
                new_followers = st.number_input(
                    "Enter Instagram Followers Count (as of your check)",
                    min_value=0,
                    value=current_followers, # This is now correctly an integer
                    step=1,
                    key="followers_input"
                )
                new_following = st.number_input(
                    "Enter Instagram Following Count (as of your check)",
                    min_value=0,
                    value=current_following, # This is now correctly an integer
                    step=1,
                    key="following_input"
                )

                # FIX: Ensure this button is inside the form
                analyze_button = st.form_submit_button("Analyze Instagram Account & Get Report")

                if analyze_button:
                    if not new_insta_handle:
                        st.error("Please enter an Instagram handle to analyze.")
                    elif not user['is_email_verified']:
                        st.error("Please verify your email first before getting an Instagram report.")
                    else:
                        # Update handle and counts in DB if new/changed
                        if (new_insta_handle != current_insta_handle or
                            new_followers != current_followers or
                            new_following != current_following):
                            update_instagram_details(user_email, new_insta_handle, new_followers, new_following)
                            st.success(f"Instagram details updated.")
                            # Fetch updated user data
                            user = get_user_by_email(user_email)

                        st.info("Analyzing Instagram account... This might take a moment.")
                        # Pass followers and following to the analysis function
                        report = analyze_instagram_account(new_insta_handle, user['followers_count'], user['following_count'])
                        st.subheader("Instagram Account Analysis Report:")
                        st.markdown(report)

                        if send_instagram_fraud_report_email(user['email'], new_insta_handle, report):
                            st.success(f"Detailed report sent to your registered email: {user['email']}.")
                        else:
                            st.error("Failed to send the report email. Please check your email settings.")


            if st.button("Go to Registration Page"):
                # Clear relevant session state variables
                keys_to_clear = ["user_email", "user_name", "user_phone",
                                 "user_insta", "user_followers", "user_following", "is_verified"]
                for key in keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]
                st.session_state["current_stage"] = "register"
                st.rerun()
        else:
            st.error("User session lost. Please go back to registration.")
            st.session_state["current_stage"] = "register"
            st.rerun()

    st.markdown("---")
    st.subheader("All Registered Users (for Admin View - In a real app, this would be secured)")
    st.dataframe(get_all_users())

def get_instagram_url(handle):
    if handle and handle.startswith('@'):
        handle = handle[1:]
    return f"https://www.instagram.com/{handle}" if handle else "#"

if __name__ == "__main__":
    main()