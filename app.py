import os
import snowflake.connector
from flask import Flask, request, render_template, redirect, flash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")

# --- Snowflake credentials ---
SNOWFLAKE_ACCOUNT   = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_USER      = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_PASSWORD  = os.getenv("SNOWFLAKE_PASSWORD")
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")
SNOWFLAKE_DATABASE  = os.getenv("SNOWFLAKE_DATABASE")
SNOWFLAKE_SCHEMA    = os.getenv("SNOWFLAKE_SCHEMA")
SNOWFLAKE_ROLE      = os.getenv("SNOWFLAKE_ROLE")

def sf_connect():
    conn = snowflake.connector.connect(
        user=SNOWFLAKE_USER,
        password=SNOWFLAKE_PASSWORD,
        account=SNOWFLAKE_ACCOUNT,
        warehouse=SNOWFLAKE_WAREHOUSE,
        database=SNOWFLAKE_DATABASE,
        schema=SNOWFLAKE_SCHEMA,
        role=SNOWFLAKE_ROLE,
        autocommit=False,  # we do explicit commit
    )
    return conn

def insert_application(email, purpose, prompts):
    """Insert signup record into HLEE3088_DB.PUBLIC.APPLICATION and log context."""
    conn = sf_connect()
    cs = conn.cursor()
    try:
        # Log context to Flask console
        cs.execute("SELECT CURRENT_ROLE(), CURRENT_DATABASE(), CURRENT_SCHEMA()")
        role, db, schema = cs.fetchone()
        print(f"[Snowflake] Context -> ROLE={role}, DB={db}, SCHEMA={schema}")

        cs.execute("""
            CREATE TABLE IF NOT EXISTS HLEE3088_DB.PUBLIC.APPLICATION (
                EMAIL STRING,
                PURPOSE STRING,
                PROMPTS_PER_DAY NUMBER,
                INSERTED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
            )
        """)

        print(f"[Insert] email={email} prompts={prompts} purpose={purpose[:60]}{'...' if len(purpose)>60 else ''}")
        cs.execute(
            """
            INSERT INTO HLEE3088_DB.PUBLIC.APPLICATION
            (EMAIL, PURPOSE, PROMPTS_PER_DAY)
            VALUES (%s, %s, %s)
            """,
            (email, purpose, int(prompts)),
        )
        print(f"[Insert] rowcount={cs.rowcount}")

        # Verify one row visible immediately
        cs.execute("""
            SELECT EMAIL, PURPOSE, PROMPTS_PER_DAY, INSERTED_AT
            FROM HLEE3088_DB.PUBLIC.APPLICATION
            ORDER BY INSERTED_AT DESC
            LIMIT 1
        """)
        print(f"[Verify last row] {cs.fetchone()}")

        conn.commit()
    finally:
        cs.close()
        conn.close()

def fetch_recent(limit=20):
    """Fetch recent signups for /admin view."""
    conn = sf_connect()
    cs = conn.cursor()
    try:
        cs.execute("""
            SELECT EMAIL, PURPOSE, PROMPTS_PER_DAY, INSERTED_AT
            FROM HLEE3088_DB.PUBLIC.APPLICATION
            ORDER BY INSERTED_AT DESC
            LIMIT %s
        """, (limit,))
        rows = cs.fetchall()
        return rows
    finally:
        cs.close()
        conn.close()

@app.route("/", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email   = request.form.get("email", "").strip()
        purpose = request.form.get("purpose", "").strip()
        prompts = request.form.get("prompts", "").strip()

        if not email or "@" not in email:
            flash("❌ Please enter a valid email.", "error")
            return render_template("index.html")
        if not purpose:
            flash("❌ Purpose cannot be empty.", "error")
            return render_template("index.html")
        if not prompts.isdigit():
            flash("❌ Prompts must be a number.", "error")
            return render_template("index.html")

        try:
            insert_application(email, purpose, prompts)
            flash("✅ Saved to Snowflake (APPLICATION).", "success")
        except Exception as e:
            print(f"[Snowflake Error] {e}")
            flash(f"⚠️ Error saving to Snowflake: {e}", "error")

        return redirect("/")

    return render_template("index.html")

@app.route("/admin")
def admin():
    try:
        rows = fetch_recent(25)
        # quick, inline table
        html = ["<h2 style='font-family: sans-serif'>Recent Signups</h2>",
                "<table border='1' cellpadding='6' cellspacing='0' style='font-family: sans-serif; background:#fff'>",
                "<tr><th>Email</th><th>Purpose</th><th>Prompts/day</th><th>Inserted</th></tr>"]
        for r in rows:
            email, purpose, prompts, ts = r
            html.append(f"<tr><td>{email}</td><td>{purpose}</td><td>{prompts}</td><td>{ts}</td></tr>")
        html.append("</table>")
        html.append("<p style='font-family: sans-serif'><a href='/'>Back</a></p>")
        return "\n".join(html)
    except Exception as e:
        return f"<pre>Error fetching rows: {e}</pre>", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
