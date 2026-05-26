"""
File-based SQLite database initialization for access control threat demonstration.
"""
import sqlite3
import json
import time
from pathlib import Path
import os
from typing import Optional

# Database file path
_db_dir = os.path.dirname(os.path.abspath(__file__))
DB_FILE_PATH = os.path.join(_db_dir, "databasefile.sqlite")




def init_database(db_path: str = None) -> sqlite3.Connection:
    """
    Initialize file-based SQLite database with access control schema.
    
    Args:
        db_path: Database path (default: DB_FILE_PATH)
    
    Returns:
        SQLite connection object with read/write access
    """
    if db_path is None:
        db_path = DB_FILE_PATH

    # Use absolute path    
    db_path = os.path.abspath(db_path)
    
    # Clean up any existing database files to start fresh
    _cleanup_db_files(db_path)

    # Ensure directory is writeable BEFORE creating the file
    _ensure_db_permissions(db_path)

    # Use URI mode with create/write access
    db_uri = f"file:{db_path}?mode=rwc"

    try:
        conn = sqlite3.connect(db_uri, timeout=10.0, uri=True, check_same_thread=False)
    except Exception as e:
            conn = sqlite3.connect(db_path, timeout=10.0, check_same_thread=False)
        
    
    # Connect to database with timeout for multi-process access
    conn.row_factory = sqlite3.Row  # Enable column access by name

    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("PRAGMA synchronous=OFF")
    
    
    cursor = conn.cursor()
    
    # Drop existing tables if they exist (for clean initialization)
    cursor.executescript("""
        DROP TABLE IF EXISTS door_passkeys;
        DROP TABLE IF EXISTS doors;
        DROP TABLE IF EXISTS users;
    """)
    
    # Create tables
    cursor.executescript("""
        -- Users table (Name, Role, Passkey)
        CREATE TABLE IF NOT EXISTS users (
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            passkey TEXT NOT NULL PRIMARY KEY
        );
        
        -- Doors table
        CREATE TABLE IF NOT EXISTS doors (
            door_code TEXT NOT NULL PRIMARY KEY,
            description TEXT
        );
        
        -- Door-PassKey mapping (which passkeys open which doors)
        CREATE TABLE IF NOT EXISTS door_passkeys (
            door_code TEXT NOT NULL,
            passkey TEXT NOT NULL,
            FOREIGN KEY (door_code) REFERENCES doors(door_code),
            PRIMARY KEY (door_code, passkey)
        );
    """)
    
    # Insert initial data
    # Users (5 distinct users)
    cursor.executemany(
        "INSERT OR IGNORE INTO users (name, role, passkey) VALUES (?, ?, ?)",
        [
            ('Bjorn', 'CEO', 'P578655'),
            ('Amit', 'Researcher', 'P370425'),
            ('Sarah', 'Manager', 'P123456'),
            ('John', 'Developer', 'P789012'),
            ('Emma', 'Security', 'P345678')
        ]
    )
    
    # Doors
    cursor.executemany(
        "INSERT OR IGNORE INTO doors (door_code, description) VALUES (?, ?)",
        [
            ('A', 'Main Office'),
            ('B', 'Server Room'),
            ('C', 'Storage'),
            ('D', 'Lab'),
            ('E', 'Archive')
        ]
    )
    
    
    cursor.executemany(
        "INSERT OR IGNORE INTO door_passkeys (door_code, passkey) VALUES (?, ?)",
        [
            ('A', 'P578655'),  # Door A (main office) accepts Bjorn's passkey
            ('D', 'P578655'),  # Door D (lab) accepts Bjorn's passkey
            ('A', 'P123456')   # Door A also accepts Sarah's passkey
        ]
    )
    
    
    cursor.executemany(
        "INSERT OR IGNORE INTO door_passkeys (door_code, passkey) VALUES (?, ?)",
        [
            ('B', 'P370425'),  # Door B accepts Amit's passkey
            ('B', 'P789012')  # Door B also accepts John's passkey
        ]
    )
    

    cursor.execute(
        "INSERT OR IGNORE INTO door_passkeys (door_code, passkey) VALUES (?, ?)",
        ('C', 'P345678') # Door C accepts Emma's passkey
    )
    

    cursor.executemany(
        "INSERT OR IGNORE INTO door_passkeys (door_code, passkey) VALUES (?, ?)",
        [
            ('D', 'P123456'),  # Door D accepts Sarah's passkey
            ('D', 'P789012')  # Door D also accepts John's passkey
        ]
    )
    
    # Door E opens with P345678 (Emma)
    cursor.execute(
        "INSERT OR IGNORE INTO door_passkeys (door_code, passkey) VALUES (?, ?)",
        ('E', 'P345678')
    )
    
    conn.commit()
    return conn


# Global file-based database connection (initialized on module import)
_db_conn: Optional[sqlite3.Connection] = None
# Track file modification time to detect resets
_db_file_mtime: Optional[float] = None


def _ensure_db_permissions(db_path: str):
    """
    Aggressively ensure database file and directory have write permissions.
    CRITICAL: This must be called EVERY time we access the database.
    """
    # Use absolute path
    db_path = os.path.abspath(db_path)
    db_dir = os.path.dirname(db_path)
    
    # Ensure directory exists and is VERY permissive
    try:
        os.makedirs(db_dir, exist_ok=True)
        # Make directory writable by everyone
        os.chmod(db_dir, 0o777)
    except Exception as e:
        print(f"Error setting directory permissions on {db_dir}: {e}")
    
    # If file exists, make it writable
    if os.path.exists(db_path):
        try:
            os.chmod(db_path, 0o666)  # Read/write for all
        except Exception as e:
            print(f"Error setting file permissions on {db_path}: {e}")
            # Try to get current permissions for debugging
            try:
                import stat
                file_stat = os.stat(db_path)
                print(f"Current file mode: {oct(file_stat.st_mode)}")
                print(f"File owner UID: {file_stat.st_uid}, current UID: {os.getuid()}")
            except Exception:
                pass


def get_shared_db() -> sqlite3.Connection:
    """
    Get shared file-based database connection with read/write access.
    Automatically detects if database file has been reset and reconnects.
    """
    global _db_conn, _db_file_mtime
    
    # Use absolute path
    db_path = os.path.abspath(DB_FILE_PATH)
    
    # ALWAYS ensure permissions first
    _ensure_db_permissions(db_path)
    
    # Check if database file exists and get its modification time
    file_mtime = None
    if os.path.exists(db_path):
        try:
            file_mtime = os.path.getmtime(db_path)
        except Exception:
            pass
    
    # Check if connection exists and is still valid AND writable
    # Also check if file has been reset (newer modification time or file doesn't match)
    if _db_conn is not None:
        # Check if file was reset (different modification time)
        file_was_reset = False
        
        if file_mtime is not None and _db_file_mtime is not None:
            # File exists and we have a tracked time - check if it changed
            if abs(file_mtime - _db_file_mtime) > 0.05:  # File was modified/recreated (50ms tolerance)
                file_was_reset = True
                print(f"Database file reset detected (mtime changed from {_db_file_mtime} to {file_mtime})")
        elif file_mtime is None and _db_file_mtime is not None:
            # File was deleted (reset happened, file is being recreated)
            file_was_reset = True
            print("Database file deleted - reset detected")
        elif file_mtime is not None and _db_file_mtime is None:
            # File exists but we didn't track it before (first access or after reset)
            # Always reconnect in this case to ensure we have the latest file
            file_was_reset = True
            print("First database access or post-reset - reconnecting to ensure fresh state")
        elif file_mtime is None and _db_file_mtime is None:
            # No file exists and we haven't tracked it - this is first time
            pass  # Not a reset, just initial state
        
        if file_was_reset:
            # File was reset, close old connection
            try:
                _db_conn.close()
            except Exception:
                pass
            _db_conn = None
            _db_file_mtime = None
            print("Database file reset detected - reconnecting...")
        else:
            # File wasn't reset, check if connection is still valid and writable
            try:
                # Test if connection is writable
                _db_conn.execute("BEGIN IMMEDIATE")
                _db_conn.execute("COMMIT")
            except (sqlite3.OperationalError, sqlite3.ProgrammingError) as e:
                # Connection is invalid or read-only - treat as reset needed
                print(f"Connection invalid/writable check failed: {e} - reconnecting...")
                try:
                    _db_conn.close()
                except Exception:
                    pass
                _db_conn = None
                _db_file_mtime = None
    
    if _db_conn is None:
        # Ensure permissions again (in case file was just created)
        _ensure_db_permissions(db_path)
        
        # If database file doesn't exist, initialize it
        if not os.path.exists(db_path):
            _db_conn = init_database(db_path)
            # Track file modification time
            try:
                _db_file_mtime = os.path.getmtime(db_path)
            except Exception:
                _db_file_mtime = None
        else:
            # File exists - use URI mode with explicit write access
            # This ensures SQLite opens in write mode
            db_uri = f"file:{db_path}?mode=rw"
            
            try:
                _db_conn = sqlite3.connect(db_uri, timeout=10.0, uri=True, check_same_thread=False)
            except sqlite3.OperationalError as e:
                if "unable to open" in str(e).lower() or "readonly" in str(e).lower():
                    # Try regular mode as fallback
                    print(f"URI mode failed, trying regular mode: {e}")
                    _ensure_db_permissions(db_path)  # Fix permissions again
                    _db_conn = sqlite3.connect(db_path, timeout=10.0, check_same_thread=False)
                else:
                    raise
            
            _db_conn.row_factory = sqlite3.Row
            
            try:
                # Set journal mode
                _db_conn.execute("PRAGMA journal_mode=DELETE")
                _db_conn.execute("PRAGMA synchronous=NORMAL")
                
                # Test write with immediate transaction
                _db_conn.execute("BEGIN IMMEDIATE")
                _db_conn.execute("COMMIT")
                
            except sqlite3.OperationalError as e:
                if "readonly" in str(e).lower():
                    print(f"Database is read-only! Attempting to fix...")
                    # Close and try to fix
                    try:
                        _db_conn.close()
                    except Exception:
                        pass
                    _db_conn = None
                    
                    # Aggressively fix permissions
                    _ensure_db_permissions(db_path)
                    
                    # Remove and recreate database
                    try:
                        os.remove(db_path)
                    except Exception:
                        pass
                    
                    # Reinitialize
                    _db_conn = init_database(db_path)
                else:
                    raise
            
            # Track file modification time after successful connection
            try:
                _db_file_mtime = os.path.getmtime(db_path)
            except Exception:
                _db_file_mtime = None
    
    return _db_conn


def reset_shared_db():
    """
    Reset shared file-based database connection to original state.
    This deletes and recreates the database file, which will cause
    other processes to detect the reset and reconnect.
    
    Returns:
        New database connection with fresh initial data
    """
    global _db_conn, _db_file_mtime
    
    db_path = os.path.abspath(DB_FILE_PATH)
    
    # Close existing connection in this process
    if _db_conn is not None:
        try:
            _db_conn.close()
        except Exception:
            pass
        _db_conn = None
    _db_file_mtime = None
    
    # Ensure directory permissions
    _ensure_db_permissions(db_path)
    
    # Aggressively clean up ALL database files
    _cleanup_db_files(db_path)
    
    # Small delay to ensure file system sync across processes
    time.sleep(0.1)
    
    # Recreate database with fresh initial data
    _db_conn = init_database(db_path)
    
    # Force file system sync by syncing the connection
    try:
        if _db_conn is not None:
            _db_conn.commit()  # Ensure all data is written
            # Force SQLite to sync to disk
            _db_conn.execute("PRAGMA synchronous=FULL")
            _db_conn.execute("PRAGMA synchronous=NORMAL")  # Reset to normal
    except Exception:
        pass
    
    # Track new file modification time
    try:
        _db_file_mtime = os.path.getmtime(db_path)
    except Exception:
        _db_file_mtime = None
    
    # Additional small delay to ensure other processes can see the new file
    time.sleep(0.05)
    
    print(f"Database reset complete. File mtime: {_db_file_mtime}")
    return _db_conn


def _cleanup_db_files(db_path: str):
    """
    Clean up database file and related SQLite files (journal, WAL, SHM).
    Ensures all files are completely removed to allow a clean reset.
    
    Args:
        db_path: Database file path
    """
    db_path = os.path.abspath(db_path)
    
    # Remove SQLite journal and WAL files first (these might lock the main file)
    for suffix in ['-journal', '-wal', '-shm']:
        journal_path = db_path + suffix
        if os.path.exists(journal_path):
            try:
                # Try multiple times in case file is locked
                for attempt in range(3):
                    try:
                        os.chmod(journal_path, 0o666)  # Make writable
                        os.remove(journal_path)
                        break
                    except Exception:
                        if attempt < 2:
                            time.sleep(0.05)
                        else:
                            raise
            except Exception as e:
                print(f"Warning: Could not remove {journal_path}: {e}")
    
    # Remove main database file
    if os.path.exists(db_path):
        try:
            # Try multiple times in case file is locked
            for attempt in range(3):
                try:
                    os.chmod(db_path, 0o666)  # Make writable before removing
                    os.remove(db_path)
                    break
                except Exception:
                    if attempt < 2:
                        time.sleep(0.05)
                    else:
                        raise
        except Exception as e:
            print(f"Warning: Could not remove database file {db_path}: {e}")
    
    # Small delay to ensure file system has processed the deletions
    time.sleep(0.05)



if __name__ == "__main__":
    # Test database initialization
    conn = init_database(DB_FILE_PATH)
    cursor = conn.cursor()
    
    # Test queries
    print("=== Users ===")
    cursor.execute("SELECT * FROM users")
    for row in cursor.fetchall():
        print(dict(row))
    
    print("\n=== Doors ===")
    cursor.execute("SELECT * FROM doors")
    for row in cursor.fetchall():
        print(dict(row))
    
    print("\n=== Door Access (Who can open Door A?) ===")
    cursor.execute("""
        SELECT DISTINCT u.name, u.role, u.passkey
        FROM users u
        JOIN door_passkeys dp ON u.passkey = dp.passkey
        JOIN doors d ON dp.door_id = d.id
        WHERE d.door_code = 'A'
    """)
    for row in cursor.fetchall():
        print(dict(row))
    
    conn.close()

