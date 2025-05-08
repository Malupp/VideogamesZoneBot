import sqlite3
from typing import List, Dict, Optional
from utils.logger import setup_logger
from datetime import datetime, timedelta
import os
import json

logger = setup_logger()


class Database:
    def __init__(self, db_path: str = 'database/bot.db'):
        """Inizializza il database e crea le tabelle necessarie"""
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self.initialize_db()

    def get_connection(self) -> sqlite3.Connection:
        """Restituisce una connessione al database"""
        return sqlite3.connect(self.db_path)

    def initialize_db(self) -> None:
        """Crea le tabelle del database se non esistono"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Tabella utenti
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    joined_date TEXT,
                    last_activity TEXT,
                    preferences TEXT,
                    marked_for_removal INTEGER DEFAULT 0
                )
                ''')

                # Tabella iscrizioni
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS subscriptions (
                    user_id INTEGER,
                    category TEXT,
                    subscribed_date TEXT,
                    PRIMARY KEY (user_id, category),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
                ''')

                # Tabella statistiche
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS news_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    category TEXT,
                    subscribers_count INTEGER,
                    sent_count INTEGER
                )
                ''')

                # Tabella statistiche utenti
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_stats (
                    user_id INTEGER PRIMARY KEY,
                    news_received INTEGER DEFAULT 0,
                    news_read INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
                ''')

                conn.commit()
                logger.info("Database initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise

    def add_user(self, user_id: int, username: Optional[str] = None,
                 first_name: Optional[str] = None, last_name: Optional[str] = None) -> bool:
        """Aggiunge un nuovo utente al database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Verifica se l'utente esiste già
                cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
                if cursor.fetchone():
                    cursor.execute(
                        "UPDATE users SET last_activity = ?, username = ?, first_name = ?, last_name = ? WHERE user_id = ?",
                        (datetime.now().isoformat(), username, first_name, last_name, user_id)
                    )
                    return False

                # Aggiunge il nuovo utente
                cursor.execute(
                    "INSERT INTO users (user_id, username, first_name, last_name, joined_date, last_activity, preferences) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (user_id, username, first_name, last_name,
                     datetime.now().isoformat(), datetime.now().isoformat(), '{}')
                )

                # Aggiunge le statistiche
                cursor.execute(
                    "INSERT INTO user_stats (user_id) VALUES (?)",
                    (user_id,)
                )

                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Error adding user {user_id}: {e}")
            return False

    def update_user_activity(self, user_id: int) -> bool:
        """Aggiorna la data dell'ultima attività dell'utente"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET last_activity = ?, marked_for_removal = 0 WHERE user_id = ?",
                    (datetime.now().isoformat(), user_id)
                )
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating activity for user {user_id}: {e}")
            return False

    def subscribe(self, user_id: int, category: str) -> bool:
        """Iscrive un utente a una categoria"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR IGNORE INTO subscriptions (user_id, category, subscribed_date) "
                    "VALUES (?, ?, ?)",
                    (user_id, category, datetime.now().isoformat())
                )
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error subscribing user {user_id} to {category}: {e}")
            return False

    def unsubscribe(self, user_id: int, category: str) -> bool:
        """Disiscrive un utente da una categoria"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM subscriptions WHERE user_id = ? AND category = ?",
                    (user_id, category)
                )
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error unsubscribing user {user_id} from {category}: {e}")
            return False

    def get_subscribers(self, category: str) -> Dict[int, Dict]:
        """Restituisce tutti gli iscritti a una categoria con le loro preferenze"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT u.user_id, u.preferences 
                    FROM users u
                    JOIN subscriptions s ON u.user_id = s.user_id
                    WHERE s.category = ? AND u.marked_for_removal = 0
                """, (category,))

                return {
                    row['user_id']: json.loads(row['preferences']) if row['preferences'] else {}
                    for row in cursor.fetchall()
                }
        except Exception as e:
            logger.error(f"Error getting subscribers for {category}: {e}")
            return {}

    def get_user_categories(self, user_id: int) -> List[str]:
        """Restituisce le categorie a cui è iscritto un utente"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT category FROM subscriptions WHERE user_id = ?",
                    (user_id,)
                )
                return [row['category'] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting categories for user {user_id}: {e}")
            return []

    def update_user_preferences(self, user_id: int, preferences: Dict) -> bool:
        """Aggiorna le preferenze di un utente"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Ottieni le preferenze esistenti
                cursor.execute("SELECT preferences FROM users WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()

                if not row:
                    return False

                # Unisci le nuove preferenze con quelle esistenti
                existing_prefs = json.loads(row['preferences']) if row['preferences'] else {}
                existing_prefs.update(preferences)

                # Aggiorna il database
                cursor.execute(
                    "UPDATE users SET preferences = ? WHERE user_id = ?",
                    (json.dumps(existing_prefs), user_id)
                )
                return True

        except Exception as e:
            logger.error(f"Error updating preferences for user {user_id}: {e}")
            return False

    def get_user_preferences(self, user_id: int) -> Dict:
        """Restituisce le preferenze di un utente"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT preferences FROM users WHERE user_id = ?",
                    (user_id,)
                )
                row = cursor.fetchone()
                return json.loads(row['preferences']) if row and row['preferences'] else {}
        except Exception as e:
            logger.error(f"Error getting preferences for user {user_id}: {e}")
            return {}

    def log_news_sent(self, category: str, sent_count: int) -> None:
        """Registra le statistiche di invio delle notizie"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Conta gli iscritti
                cursor.execute(
                    "SELECT COUNT(*) as count FROM subscriptions WHERE category = ?",
                    (category,)
                )
                subscribers_count = cursor.fetchone()['count']

                # Registra l'invio
                cursor.execute(
                    "INSERT INTO news_stats (date, category, subscribers_count, sent_count) "
                    "VALUES (?, ?, ?, ?)",
                    (datetime.now().isoformat(), category, subscribers_count, sent_count)
                )
        except Exception as e:
            logger.error(f"Error logging news stats for {category}: {e}")

    def increment_news_sent(self, user_id: int) -> None:
        """Incrementa il contatore delle notizie inviate a un utente"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE user_stats SET news_received = news_received + 1 "
                    "WHERE user_id = ?",
                    (user_id,)
                )
        except Exception as e:
            logger.error(f"Error incrementing news count for user {user_id}: {e}")

    def get_inactive_users(self, days: int = 60) -> List[int]:
        """Restituisce gli ID degli utenti inattivi"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
                cursor.execute(
                    "SELECT user_id FROM users "
                    "WHERE last_activity < ? AND marked_for_removal = 0",
                    (cutoff_date,)
                )
                return [row['user_id'] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting inactive users: {e}")
            return []

    def mark_for_removal(self, user_id: int) -> None:
        """Segna un utente per la rimozione"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET marked_for_removal = 1 WHERE user_id = ?",
                    (user_id,)
                )
        except Exception as e:
            logger.error(f"Error marking user {user_id} for removal: {e}")

    def remove_user(self, user_id: int) -> None:
        """Rimuove completamente un utente dal database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Rimuovi da tutte le tabelle
                cursor.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
                cursor.execute("DELETE FROM user_stats WHERE user_id = ?", (user_id,))
                cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))

        except Exception as e:
            logger.error(f"Error removing user {user_id}: {e}")

    def get_stats(self) -> Dict:
        """Restituisce le statistiche generali del bot"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                stats = {
                    'total_users': 0,
                    'total_news_sent': 0,
                    'last_update': datetime.now().isoformat()
                }

                # Conta utenti totali
                cursor.execute("SELECT COUNT(*) as count FROM users")
                row = cursor.fetchone()
                if row:
                    stats['total_users'] = row['count']

                # Conta notizie inviate totali
                cursor.execute("SELECT SUM(sent_count) as total FROM news_stats")
                row = cursor.fetchone()
                if row and row['total']:
                    stats['total_news_sent'] = row['total']

                return stats

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                'total_users': 0,
                'total_news_sent': 0,
                'last_update': datetime.now().isoformat()
            }