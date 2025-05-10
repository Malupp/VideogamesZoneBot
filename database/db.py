import sqlite3
from typing import List, Dict, Optional, Any
from utils.logger import logger
from datetime import datetime, timedelta
import os
import json


class Database:
    def __init__(self, db_path: str = 'database/bot.db'):
        """Inizializza il database e crea le tabelle necessarie"""
        self.logger = logger.getChild('database')
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._initialize_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Restituisce una connessione configurata correttamente"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = lambda cursor, row: {
            col[0]: row[idx] for idx, col in enumerate(cursor.description)
        }
        return conn

    def _initialize_db(self) -> None:
        """Crea le tabelle del database se non esistono"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA foreign_keys = ON")

                # Tabella utenti
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    joined_date TEXT,
                    last_activity TEXT,
                    preferences TEXT DEFAULT '{}',
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
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
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
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
                ''')

                cursor.execute('''
                CREATE TABLE IF NOT EXISTS groups (
                    group_id INTEGER PRIMARY KEY,
                    title TEXT,
                    added_date TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    categories TEXT DEFAULT '["generale"]'
                )
                ''')

                conn.commit()
                self.logger.info("Database initialized successfully")

        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            raise

    def add_user(self, user_id: int, username: Optional[str] = None,
                 first_name: Optional[str] = None, last_name: Optional[str] = None) -> bool:
        """Aggiunge un nuovo utente al database"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, joined_date, last_activity) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, username, first_name, last_name,
                     datetime.now().isoformat(), datetime.now().isoformat())
                )

                if cursor.rowcount > 0:
                    cursor.execute(
                        "INSERT OR IGNORE INTO user_stats (user_id) VALUES (?)",
                        (user_id,)
                    )
                    conn.commit()
                    return True
                return False

        except Exception as e:
            self.logger.error(f"Error adding user {user_id}: {e}")
            return False

    def update_user_activity(self, user_id: int) -> bool:
        """Aggiorna la data dell'ultima attività dell'utente"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET last_activity = ?, marked_for_removal = 0 WHERE user_id = ?",
                    (datetime.now().isoformat(), user_id)
                )
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error updating activity for user {user_id}: {e}")
            return False

    def add_subscriber(self, chat_id: int, category: str, frequency: str = 'normal') -> bool:
        """Aggiunge un iscritto al database (funziona per utenti e gruppi)"""
        try:
            with self._get_connection() as conn:
                # Crea l'utente/gruppo se non esiste
                self.add_user(chat_id)

                # Iscrivi alla categoria
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO subscriptions (user_id, category, subscribed_date) "
                    "VALUES (?, ?, ?)",
                    (chat_id, category, datetime.now().isoformat())
                )

                # Aggiorna le preferenze
                prefs = self.get_user_preferences(chat_id) or {}
                prefs.update({'frequency': frequency})
                cursor.execute(
                    "UPDATE users SET preferences = ? WHERE user_id = ?",
                    (json.dumps(prefs), chat_id)
                )

                conn.commit()
                return True

        except Exception as e:
            self.logger.error(f"Error in add_subscriber for {chat_id}: {e}")
            return False

    def get_user_preferences(self, user_id: int) -> Dict[str, Any]:
        """Restituisce le preferenze di un utente"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT preferences FROM users WHERE user_id = ?",
                    (user_id,)
                )
                row = cursor.fetchone()
                if row and row['preferences']:
                    return json.loads(row['preferences'])
                return {}
        except Exception as e:
            self.logger.error(f"Error getting preferences for user {user_id}: {e}")
            return {}

    def get_subscribers(self, category: str) -> Dict[int, Dict]:
        """Restituisce tutti gli iscritti a una categoria con le loro preferenze"""
        try:
            with self._get_connection() as conn:
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
            self.logger.error(f"Error getting subscribers for {category}: {e}")
            return {}

    # ... (altri metodi rimangono identici ma con _get_connection invece di get_connection)
    # Assicurati di sostituire tutte le occorrenze di get_connection con _get_connection

    def cleanup_database(self):
        """Pulisce il database da record inconsistenti"""
        try:
            with self._get_connection() as conn:
                # Fix preferences vuote/nulle
                conn.execute("UPDATE users SET preferences = '{}' WHERE preferences IS NULL OR preferences = ''")
                # Rimuovi subscription senza user
                conn.execute("DELETE FROM subscriptions WHERE user_id NOT IN (SELECT user_id FROM users)")
                conn.commit()
                self.logger.info("Database cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during database cleanup: {e}")

    def add_group(self, group_id: int, title: str, categories: List[str] = None):
        """Aggiunge un nuovo gruppo al database"""
        if categories is None:
            categories = ['generale']
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO groups (group_id, title, added_date, categories) "
                    "VALUES (?, ?, ?, ?)",
                    (group_id, title, datetime.now().isoformat(), json.dumps(categories)))
                return True
        except Exception as e:
            self.logger.error(f"Error adding group {group_id}: {e}")
            return False

    def get_active_groups(self, category: str = None) -> Dict[int, Dict]:
        """Restituisce tutti i gruppi attivi, eventualmente filtrati per categoria"""
        try:
            with self._get_connection() as conn:
                query = "SELECT group_id, title, categories FROM groups WHERE is_active = 1"
                params = ()

                if category:
                    query += " AND categories LIKE ?"
                    params = (f'%"{category}"%',)

                cursor = conn.execute(query, params)
                return {
                    row['group_id']: {
                        'title': row['title'],
                        'categories': json.loads(row['categories'])
                    }
                    for row in cursor.fetchall()
                }
        except Exception as e:
            self.logger.error(f"Error getting groups: {e}")
            return {}

    def update_group_categories(self, group_id: int, categories: List[str]) -> bool:
        """Aggiorna le categorie di un gruppo"""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE groups SET categories = ? WHERE group_id = ?",
                    (json.dumps(categories), group_id)
                )
                return True
        except Exception as e:
            self.logger.error(f"Error updating group {group_id} categories: {e}")
            return False

    def unsubscribe(self, user_id: int, category: str) -> bool:
        """Disiscrive un utente/gruppo da una categoria"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM subscriptions WHERE user_id = ? AND category = ?",
                    (user_id, category)
                )
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error unsubscribing {user_id} from {category}: {e}")
            return False

    def increment_news_sent(self, user_id: int) -> bool:
        """Incrementa il contatore di notizie inviate"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE user_stats SET news_received = news_received + 1 "
                    "WHERE user_id = ?",
                    (user_id,)
                )
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error incrementing news count for {user_id}: {e}")
            return False

    def log_news_sent(self, category: str, sent_count: int) -> bool:
        """Registra l'invio di notizie nelle statistiche"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) as count FROM subscriptions WHERE category = ?",
                    (category,)
                )
                subscribers_count = cursor.fetchone()['count']

                cursor.execute(
                    "INSERT INTO news_stats (date, category, subscribers_count, sent_count) "
                    "VALUES (?, ?, ?, ?)",
                    (datetime.now().isoformat(), category, subscribers_count, sent_count)
                )
                return True
        except Exception as e:
            self.logger.error(f"Error logging news stats for {category}: {e}")
            return False

    def get_inactive_users(self, days: int = 60) -> List[int]:
        """Restituisce gli utenti inattivi"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
                cursor.execute(
                    "SELECT user_id FROM users "
                    "WHERE last_activity < ? AND marked_for_removal = 0",
                    (cutoff_date,)
                )
                return [row['user_id'] for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Error getting inactive users: {e}")
            return []

    def mark_for_removal(self, user_id: int) -> bool:
        """Segna un utente per la rimozione"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET marked_for_removal = 1 WHERE user_id = ?",
                    (user_id,)
                )
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error marking user {user_id} for removal: {e}")
            return False

    def remove_user(self, user_id: int) -> bool:
        """Rimuove completamente un utente"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
                cursor.execute("DELETE FROM user_stats WHERE user_id = ?", (user_id,))
                cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
                cursor.execute("DELETE FROM groups WHERE group_id = ?", (user_id,))
                return True
        except Exception as e:
            self.logger.error(f"Error removing user {user_id}: {e}")
            return False

    def get_user_categories(self, user_id: int) -> List[str]:
        """Restituisce le categorie a cui è iscritto un utente"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT category FROM subscriptions WHERE user_id = ?",
                    (user_id,)
                )
                return [row['category'] for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Error getting categories for user {user_id}: {e}")
            return []

    def get_subscriber_counts(self) -> Dict[str, int]:
        """Restituisce il conteggio degli iscritti per ogni categoria"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Ottieni tutte le categorie distinte
                cursor.execute("SELECT DISTINCT category FROM subscriptions")
                categories = [row['category'] for row in cursor.fetchall()]

                # Ottieni il conteggio per ogni categoria
                counts = {}
                for category in categories:
                    cursor.execute(
                        "SELECT COUNT(*) as count FROM subscriptions WHERE category = ?",
                        (category,)
                    )
                    counts[category] = cursor.fetchone()['count']

                return counts

        except Exception as e:
            self.logger.error(f"Error getting subscriber counts: {e}")
            return {}

    def get_total_subscribers(self) -> int:
        """Restituisce il numero totale di iscritti unici"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(DISTINCT user_id) as count FROM subscriptions")
                return cursor.fetchone()['count']
        except Exception as e:
            self.logger.error(f"Error getting total subscribers: {e}")
            return 0

    def get_active_subscriber_counts(self, days: int = 30) -> Dict[str, int]:
        """Restituisce il conteggio degli iscritti attivi per categoria"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT s.category, COUNT(DISTINCT s.user_id) as count 
                    FROM subscriptions s
                    JOIN users u ON s.user_id = u.user_id
                    WHERE u.last_activity >= ?
                    GROUP BY s.category
                """, (cutoff_date,))

                return {row['category']: row['count'] for row in cursor.fetchall()}

        except Exception as e:
            self.logger.error(f"Error getting active subscriber counts: {e}")
            return {}