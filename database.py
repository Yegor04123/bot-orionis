import sqlite3
import datetime
from dataclasses import dataclass
from typing import Optional, List, Tuple


@dataclass
class Application:
    user_id: int
    username: str
    minecraft_nickname: str
    age: int
    experience: str
    has_microphone: str
    motivation: str
    plans: str
    agreed_rules: bool
    filled_manually: bool
    status: str
    created_at: str
    processed_at: Optional[str] = None
    processed_by: Optional[int] = None
    application_id: Optional[int] = None


class Database:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            minecraft_nickname TEXT NOT NULL,
            age INTEGER NOT NULL,
            experience TEXT NOT NULL,
            has_microphone TEXT NOT NULL,
            motivation TEXT NOT NULL,
            plans TEXT NOT NULL,
            agreed_rules BOOLEAN NOT NULL,
            filled_manually BOOLEAN NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            processed_at TEXT,
            processed_by INTEGER
        )
        ''')
        self.conn.commit()

    def create_application(self, application: Application) -> int:
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO applications (
            user_id, username, minecraft_nickname, age, experience, 
            has_microphone, motivation, plans, agreed_rules, filled_manually, 
            status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            application.user_id, application.username, application.minecraft_nickname,
            application.age, application.experience, application.has_microphone,
            application.motivation, application.plans, application.agreed_rules,
            application.filled_manually, application.status, application.created_at
        ))
        self.conn.commit()
        return cursor.lastrowid

    def get_active_application_by_user_id(self, user_id: int) -> Optional[Application]:
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT * FROM applications 
        WHERE user_id = ? AND status = 'pending'
        ''', (user_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return Application(
            application_id=row['id'],
            user_id=row['user_id'],
            username=row['username'],
            minecraft_nickname=row['minecraft_nickname'],
            age=row['age'],
            experience=row['experience'],
            has_microphone=row['has_microphone'],
            motivation=row['motivation'],
            plans=row['plans'],
            agreed_rules=bool(row['agreed_rules']),
            filled_manually=bool(row['filled_manually']),
            status=row['status'],
            created_at=row['created_at'],
            processed_at=row['processed_at'],
            processed_by=row['processed_by']
        )

    def get_application_by_id(self, application_id: int) -> Optional[Application]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM applications WHERE id = ?', (application_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return Application(
            application_id=row['id'],
            user_id=row['user_id'],
            username=row['username'],
            minecraft_nickname=row['minecraft_nickname'],
            age=row['age'],
            experience=row['experience'],
            has_microphone=row['has_microphone'],
            motivation=row['motivation'],
            plans=row['plans'],
            agreed_rules=bool(row['agreed_rules']),
            filled_manually=bool(row['filled_manually']),
            status=row['status'],
            created_at=row['created_at'],
            processed_at=row['processed_at'],
            processed_by=row['processed_by']
        )

    def update_application_status(self, application_id: int, status: str, processed_by: int) -> None:
        cursor = self.conn.cursor()
        now = datetime.datetime.now().isoformat()
        cursor.execute('''
        UPDATE applications 
        SET status = ?, processed_at = ?, processed_by = ? 
        WHERE id = ?
        ''', (status, now, processed_by, application_id))
        self.conn.commit()

    def can_submit_new_application(self, user_id: int) -> Tuple[bool, Optional[str]]:
        cursor = self.conn.cursor()

        # Check if user has a pending application
        cursor.execute('''
        SELECT id FROM applications 
        WHERE user_id = ? AND status = 'pending'
        ''', (user_id,))

        if cursor.fetchone():
            return False, "У вас уже есть активная заявка на рассмотрении."

        # Check if user has been rejected recently
        cursor.execute('''
        SELECT processed_at FROM applications 
        WHERE user_id = ? AND status = 'rejected' 
        ORDER BY processed_at DESC LIMIT 1
        ''', (user_id,))

        last_rejection = cursor.fetchone()

        if last_rejection:
            rejection_date = datetime.datetime.fromisoformat(last_rejection[0])
            cooldown_end = rejection_date + datetime.timedelta(days=14)

            if cooldown_end > datetime.datetime.now():
                days_left = (cooldown_end - datetime.datetime.now()).days + 1
                return False, f"Вы можете подать новую заявку через {days_left} дней."

        return True, None

    def close(self):
        self.conn.close()