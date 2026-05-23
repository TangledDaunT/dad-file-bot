"""
File Search Module - Fuzzy file finder with indexing
"""

import os
import json
import sqlite3
from pathlib import Path
from fuzzywuzzy import fuzz, process
from datetime import datetime


class FileIndexer:
    """Manages file index for fast searching"""
    
    def __init__(self, db_path: str, scan_directory: str, extensions: list):
        self.db_path = db_path
        self.scan_directory = Path(scan_directory)
        self.extensions = extensions
        self.conn = sqlite3.connect(db_path)
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database"""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY,
                filename TEXT NOT NULL,
                filepath TEXT UNIQUE NOT NULL,
                file_number INTEGER,
                size_bytes INTEGER,
                modified_time TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()
    
    def build_index(self) -> int:
        """Scan directory and build file index. Returns count of indexed files."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM files")
        
        count = 0
        ext_tuple = tuple(ext.lower() for ext in self.extensions)
        
        for root, _, files in os.walk(self.scan_directory):
            for filename in files:
                ext = Path(filename).suffix.lower()
                if ext in ext_tuple:
                    filepath = os.path.join(root, filename)
                    stat = os.stat(filepath)
                    
                    # Try to extract file number from filename
                    file_number = self._extract_number(filename)
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO files 
                        (filename, filepath, file_number, size_bytes, modified_time)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        filename,
                        filepath,
                        file_number,
                        stat.st_size,
                        datetime.fromtimestamp(stat.st_mtime).isoformat()
                    ))
                    count += 1
        
        self.conn.commit()
        return count
    
    def _extract_number(self, filename: str) -> int | None:
        """Try to extract a number from filename for exact number matching"""
        import re
        numbers = re.findall(r'\d+', filename)
        if numbers:
            return int(numbers[0])
        return None
    
    def search_by_number(self, number: int) -> list[dict]:
        """Search files by number (exact match)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT filename, filepath, size_bytes, file_number
            FROM files WHERE file_number = ?
        ''', (number,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'filename': row[0],
                'filepath': row[1],
                'size_bytes': row[2],
                'file_number': row[3]
            })
        return results
    
    def search_fuzzy(self, query: str, threshold: int = 60, limit: int = 10) -> list[dict]:
        """Fuzzy search files by name"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT filename, filepath, size_bytes FROM files')
        files = cursor.fetchall()
        
        if not files:
            return []
        
        # Extract just filenames for fuzzy matching
        filenames = [f[0] for f in files]
        
        # Perform fuzzy matching
        matches = process.extract(query, filenames, scorer=fuzz.token_set_ratio, limit=limit * 2)
        
        results = []
        seen_files = set()
        
        for filename, score, _ in matches:
            if score < threshold:
                continue
                
            # Find full file record
            for f in files:
                if f[0] == filename and filename not in seen_files:
                    seen_files.add(filename)
                    results.append({
                        'filename': f[0],
                        'filepath': f[1],
                        'size_bytes': f[2],
                        'score': score
                    })
                    break
            
            if len(results) >= limit:
                break
        
        return results
    
    def get_all_files(self) -> list[dict]:
        """Get all indexed files"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT filename, filepath, size_bytes FROM files')
        
        return [
            {'filename': row[0], 'filepath': row[1], 'size_bytes': row[2]}
            for row in cursor.fetchall()
        ]
    
    def close(self):
        """Close database connection"""
        self.conn.close()


def format_file_size(bytes_size: int) -> str:
    """Format bytes to human readable"""
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f} KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size / (1024 * 1024):.1f} MB"
    else:
        return f"{bytes_size / (1024 * 1024 * 1024):.1f} GB"


def search_files(query: str, indexer: FileIndexer, threshold: int = 60, max_results: int = 10) -> list[dict]:
    """
    Main search function - tries number search first, then fuzzy
    """
    # Try to parse as number first
    try:
        number = int(query)
        number_results = indexer.search_by_number(number)
        if number_results:
            return number_results
    except ValueError:
        pass
    
    # Fall back to fuzzy search
    return indexer.search_fuzzy(query, threshold=threshold, limit=max_results)
