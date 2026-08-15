import os
import sys
import bcrypt
import psycopg
from dotenv import load_dotenv

load_dotenv()


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def main():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL is not set in environment.")

    demo_email = "alex@recall.dev"
    demo_pass = "recall@demo123"
    hashed = hash_password(demo_pass)

    with psycopg.connect(db_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email = %s;", (demo_email,))
            row = cur.fetchone()
            if row:
                user_id = str(row[0])
                cur.execute("UPDATE users SET password_hash = %s WHERE id = %s;", (hashed, user_id))
                print(f"Updated password for demo user '{demo_email}' (ID: {user_id}).")
            else:
                cur.execute(
                    "INSERT INTO users (email, display_name, password_hash) VALUES (%s, %s, %s) RETURNING id;",
                    (demo_email, "Alex Chen", hashed),
                )
                user_id = str(cur.fetchone()[0])
                print(f"Created demo user '{demo_email}' (ID: {user_id}) with password.")

    print("DONE! Demo password seeded successfully.")


if __name__ == "__main__":
    main()
