"""
File Search Module - Fuzzy file finder with indexing
Robust implementation with Path usage
"""

import os
import sqlite3
import re
from pathlib import Path
from typing import List, Dict, Optional

from fuzzywuzzy import fuzz, process


class FileIndexer:
    """Manages file index for fast searching"""
    
    def __init__(self, db_path: str, scan_directory: str, extensions: list):
        self.db_path = Path(db_path)
        self.scan_directory = Path(scan_directory)
        self.extensions = [ext.lower() for ext in extensions]
        
        # Ensure parent exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(str(self.db_path))
        self._init_db()
    
    def _init_db(self):
        """Initialize database"""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY,
                filename TEXT NOT NULL,
                filepath TEXT UNIQUE NOT NULL,
                file_number INTEGER,
                size_bytes INTEGER,
                modified_time TEXT
            )
        ''')
        self.conn.commit()
    
    def build_index(self) -> int:
        """Scan directory and build index"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM files")
        
        count = 0
        ext_tuple = tuple(self.extensions)
        
        for root, _, files in os.walk(self.scan_directory):
            root_path = Path(root)
            for filename in files:
                ext = Path(filename).suffix.lower()
                if ext in ext_tuple:
                    filepath = root_path / filename
                    
                    try:
                        stat = filepath.stat()
                        file_number = self._extract_number(filename)
                        
                        cursor.execute('''
                            INSERT OR REPLACE INTO files 
                            (filename, filepath, file_number, size_bytes, modified_time)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (
                            filename,
                            str(filepath),
                            file_number,
                            stat.st_size,
                            filepath.stat().st_mtime
                        ))
                        count += 1
                    except Exception as e:
                        # Skip files we can't access
                        continue
        
        self.conn.commit()
        return count
    
    def _extract_number(self, filename: str) -> Optional[int]:
        """Extract first number from filename"""
        numbers = re.findall(r'\d+', filename)
        return int(numbers[0]) if numbers else None
    
    def search_by_number(self, number: int) -> List[Dict]:
        """Search by file number (exact match)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT filename, filepath, size_bytes, file_number
            FROM files WHERE file_number = ?
        ''', (number,))
        
        return [
            {
                'filename': row[0],
                'filepath': row[1],
                'size_bytes': row[2],
                'file_number': row[3]
            }
            for row in cursor.fetchall()
        ]
    
    def search_fuzzy(self, query: str, threshold: int = 60, limit: int = 10) -> List[Dict]:
        """Fuzzy search files"""
        query_lower = query.lower()
        cursor = self.conn.cursor()
        cursor.execute('SELECT filename, filepath, size_bytes FROM files')
        files = cursor.fetchall()
        
        if not files:
            return []
        
        filenames = [f[0] for f in files]
        
        matches = process.extract(
            query_lower, 
            filenames, 
            scorer=fuzz.token_set_ratio, 
            limit=limit * 2
        )
        
        results = []
        seen = set()
        
        for filename, score, _ in matches:
            if score < threshold:
                continue
            
            for f in files:
                if f[0] == filename and filename not in seen:
                    seen.add(filename)
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
    
    def get_all_files(self) -> List[Dict]:
        """Get all indexed files"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT filename, filepath, size_bytes FROM files')
        
        return [
            {
                'filename': row[0],
                'filepath': row[1],
                'size_bytes': row[2]
            }
            for row in cursor.fetchall()
        ]
    
    def close(self):
        """Close database"""
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


def search_files(query: str, indexer: FileIndexer, threshold: int = 60, max_results: int = 10) -> List[Dict]:
    """Main search - tries number first, then fuzzy"""
    # Try to parse as number first
    try:
        number = int(query)
        number_results = indexer.search_by_number(number)
        if number_results:
            return number_results
    except ValueError:
        pass
    
    # Fuzzy search
    return indexer.search_fuzzy(query, threshold=threshold, limit=max_results)
