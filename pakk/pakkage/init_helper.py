from __future__ import annotations

import os


class InitConfigOption:
    def __init__(self, key: str, value: str):
        self.key = key
        self.value = value


class InitConfigSection:
    def __init__(self, name: str | None, options: list[InitConfigOption]):
        self.name = name or "NONE"
        self.options = options


class InitHelperBase:
    @staticmethod
    def help() -> list[InitConfigSection]:
        raise NotImplementedError()
    
    @staticmethod
    def is_suitable_for_directory(directory_path: str) -> bool:
        """
        Check if this pakkage type is suitable for the given directory based on its content.
        
        Parameters
        ----------
        directory_path : str
            The path to the directory to check
            
        Returns
        -------
        bool
            True if this pakkage type is suitable for the directory, False otherwise
        """
        return False
    
    @staticmethod
    def _search_indicators(directory_path: str, indicators: list[str], max_depth: int = 2) -> bool:
        """
        Search for indicators in the directory and its subdirectories up to a specified depth.
        
        Parameters
        ----------
        directory_path : str
            The path to the directory to search
        indicators : list[str]
            List of file/directory names to search for
        max_depth : int, optional
            Maximum depth to search in subdirectories (default: 2)
            
        Returns
        -------
        bool
            True if any indicator is found, False otherwise
        """
        try:
            for root, dirs, files in os.walk(directory_path):
                # Filter out hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                # Calculate current depth
                depth = root[len(directory_path):].count(os.sep)
                if depth > max_depth:
                    continue
                
                # Check for indicators in current directory
                for indicator in indicators:
                    indicator_path = os.path.join(root, indicator)
                    if os.path.exists(indicator_path):
                        return True
        except (OSError, PermissionError):
            pass
        
        return False
    
    @staticmethod
    def _search_file_suffixes(directory_path: str, suffixes: list[str], max_depth: int = 2) -> bool:
        """
        Search for files with specific suffixes in the directory and its subdirectories.
        
        Parameters
        ----------
        directory_path : str
            The path to the directory to search
        suffixes : list[str]
            List of file suffixes to search for (e.g., ['.py', '.js'])
        max_depth : int, optional
            Maximum depth to search in subdirectories (default: 2)
            
        Returns
        -------
        bool
            True if any file with the specified suffixes is found, False otherwise
        """
        try:
            for root, dirs, files in os.walk(directory_path):
                # Filter out hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                # Calculate current depth
                depth = root[len(directory_path):].count(os.sep)
                if depth > max_depth:
                    continue
                
                # Check for files with specified suffixes
                for file in files:
                    if any(file.lower().endswith(suffix.lower()) for suffix in suffixes):
                        return True
        except (OSError, PermissionError):
            pass
        
        return False
    
    @staticmethod
    def _search_executable_files(directory_path: str, max_depth: int = 2) -> bool:
        """
        Search for executable files in the directory and its subdirectories.
        
        Parameters
        ----------
        directory_path : str
            The path to the directory to search
        max_depth : int, optional
            Maximum depth to search in subdirectories (default: 2)
            
        Returns
        -------
        bool
            True if any executable file is found, False otherwise
        """
        try:
            for root, dirs, files in os.walk(directory_path):
                # Filter out hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                # Calculate current depth
                depth = root[len(directory_path):].count(os.sep)
                if depth > max_depth:
                    continue
                
                # Check for executable files
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.isfile(file_path) and os.access(file_path, os.X_OK):
                        return True
        except (OSError, PermissionError):
            pass
        
        return False
