#!/usr/bin/env python3
"""
Content Processor Module

This module handles the processing and chunking of repository content for embedding.
It provides functionality to:
1. Classify repository files by type
2. Process different file types (code, documentation, configuration)
3. Extract logical chunks with appropriate metadata
4. Prepare content for embedding

It implements a hierarchical logging system for debugging and monitoring the
content processing pipeline.
"""

import os
import re
import logging
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union, Any, Generator
import ast
import tokenize
from io import StringIO
from collections import defaultdict

# Setup module logger
logger = logging.getLogger("content_processor")
logger.propagate = False
logger.setLevel(logging.DEBUG)

# Create console handler if not already present
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

# Define file type constants
FILE_TYPE_CODE = "code"
FILE_TYPE_DOCUMENTATION = "documentation"
FILE_TYPE_CONFIGURATION = "configuration"
FILE_TYPE_UNKNOWN = "unknown"

# Define code language constants
LANG_PYTHON = "python"
LANG_JAVASCRIPT = "javascript"
LANG_TYPESCRIPT = "typescript"
LANG_JAVA = "java"
LANG_GO = "go"
LANG_RUBY = "ruby"
LANG_RUST = "rust"
LANG_CPP = "cpp"
LANG_CSHARP = "csharp"
LANG_UNKNOWN = "unknown"

from tree_sitter import Language, Parser

# Build Tree-sitter language library only once
TREE_SITTER_JAVA_PATH = os.path.join(os.path.dirname(__file__), 'tree_sitter_languages', 'tree-sitter-java')
TREE_SITTER_LIB_PATH = os.path.join(os.path.dirname(__file__), 'tree-sitter-java-libs.so')
if not os.path.exists(TREE_SITTER_LIB_PATH):
    Language.build_library(
        TREE_SITTER_LIB_PATH,
        [TREE_SITTER_JAVA_PATH]
    )

JAVA_LANGUAGE = Language(TREE_SITTER_LIB_PATH, 'java')
JAVA_PARSER = Parser()
JAVA_PARSER.set_language(JAVA_LANGUAGE)
GO_LANGUAGE = Language(TREE_SITTER_LIB_PATH, "go")


class SyntaxErrorTracker:
    """Tracks syntax errors across different file types during repository processing."""

    def __init__(self):
        self.errors = []
        self.error_count = 0

    def add_error(self, file_path, language, error_msg, line_number, function_name, metadata=None):
        """
        Record a syntax error.

        Args:
            file_path: Path to the file with the error
            language: Programming language of the file
            error_msg: Error message or description
            line_number: Line number where the error occurred (optional)
            function_name: Function or class name containing the error (optional)
        """
        self.errors.append({
            'file_path': file_path,
            'language': language,
            'error_msg': error_msg,
            'line_number': line_number,
            'function_name': function_name,
            "metadata": metadata
        })
        self.error_count += 1

    def has_errors(self):
        """Check if any syntax errors were found."""
        return self.error_count > 0

    def get_errors(self):
        """Get all recorded syntax errors."""
        return self.errors

    def get_error_count(self):
        """Get the total number of syntax errors."""
        return self.error_count

    def generate_report(self):
        """Generate a formatted report of all syntax errors."""
        if not self.has_errors():
            return {
                "has_syntax_errors": False,
                "error_count": 0,
                "summary": "No syntax errors were detected in the codebase.",
                "errors": []
            }

        # Group errors by language
        errors_by_language = {}
        for error in self.errors:
            lang = error['language']
            if lang not in errors_by_language:
                errors_by_language[lang] = []
            errors_by_language[lang].append(error)

        # Create summary
        languages_with_errors = list(errors_by_language.keys())
        error_summary = f"Found {self.error_count} syntax errors across {len(languages_with_errors)} languages: {', '.join(languages_with_errors)}"

        return {
            "has_syntax_errors": True,
            "error_count": self.error_count,
            "summary": error_summary,
            "errors": self.errors,
            "errors_by_language": errors_by_language
        }


class ContentChunk:
    """Represents a chunk of content with metadata for embedding."""

    def __init__(
        self,
        content: str,
        file_path: str,
        chunk_type: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        language: Optional[str] = None,
        parent: Optional[str] = None,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a content chunk.

        Args:
            content: The text content of the chunk
            file_path: Path to the source file, relative to repository root
            chunk_type: Type of content (code, documentation, configuration)
            start_line: Starting line number in the source file (optional)
            end_line: Ending line number in the source file (optional)
            language: Programming language or format (optional)
            parent: Name of parent entity (e.g., class name for a method) (optional)
            name: Name of the chunk entity (e.g., function name) (optional)
            metadata: Additional metadata as key-value pairs (optional)
        """
        self.content = content
        self.file_path = file_path
        self.chunk_type = chunk_type
        self.start_line = start_line
        self.end_line = end_line
        self.language = language
        self.parent = parent
        self.name = name
        self.metadata = metadata or {}

        # Calculate token count (simple approximation)
        self.token_count = len(content.split())

    def __repr__(self) -> str:
        """String representation of the chunk."""
        return (f"ContentChunk(file='{self.file_path}', "
                f"type='{self.chunk_type}', "
                f"lines={self.start_line}-{self.end_line}, "
                f"name='{self.name}', "
                f"tokens={self.token_count})")

    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk to dictionary for serialization."""
        return {
            "content": self.content,
            "file_path": self.file_path,
            "chunk_type": self.chunk_type,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "language": self.language,
            "parent": self.parent,
            "name": self.name,
            "token_count": self.token_count,
            "metadata": self.metadata
        }


class ContentProcessor:
    """
    Processes repository content for embedding.
    Handles file classification, content extraction, and chunking.
    """

    def __init__(self, repo_path: str, log_level: int = logging.INFO):
        """
        Initialize the content processor.

        Args:
            repo_path: Path to the repository root
            log_level: Logging level for this processor instance
        """
        self.repo_path = repo_path
        self.chunks = []
        # Initialize the syntax error tracker
        self.error_tracker = SyntaxErrorTracker()

        # Setup processor-specific logger
        self.logger = logging.getLogger(f"content_processor.{os.path.basename(repo_path)}")
        self.logger.setLevel(log_level)

        # Create file handler for this repository
        log_dir = os.path.join(os.path.dirname(repo_path), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"{os.path.basename(repo_path)}_processing.log")

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        self.logger.info(f"Initialized content processor for {repo_path}")

        # Stats tracking
        self.stats = {
            "files_processed": 0,
            "chunks_created": 0,
            "files_by_type": defaultdict(int),
            "chunks_by_type": defaultdict(int),
            "processing_time": 0,
            "errors": 0
        }

    def classify_file(self, file_path: str) -> Tuple[str, Optional[str]]:
        """
        Classify a file based on its extension and content.

        Args:
            file_path: Path to the file, relative to repository root

        Returns:
            Tuple of (file_type, language)
        """
        start_time = time.time()
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        # Initialize with unknown types
        file_type = FILE_TYPE_UNKNOWN
        language = LANG_UNKNOWN

        # Check documentation files
        if ext in ['.md', '.rst', '.txt', '.docx', '.pdf']:
            file_type = FILE_TYPE_DOCUMENTATION
            language = ext[1:]  # Use extension without the dot

        # Check configuration files
        elif ext in ['.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf']:
            file_type = FILE_TYPE_CONFIGURATION
            language = ext[1:]  # Use extension without the dot

        # Check various code files
        elif ext in ['.py']:
            file_type = FILE_TYPE_CODE
            language = LANG_PYTHON
        elif ext in ['.js']:
            file_type = FILE_TYPE_CODE
            language = LANG_JAVASCRIPT
        elif ext in ['.ts', '.tsx']:
            file_type = FILE_TYPE_CODE
            language = LANG_TYPESCRIPT
        elif ext in ['.java']:
            file_type = FILE_TYPE_CODE
            language = LANG_JAVA
        elif ext in ['.go']:
            file_type = FILE_TYPE_CODE
            language = LANG_GO
        elif ext in ['.rb']:
            file_type = FILE_TYPE_CODE
            language = LANG_RUBY
        elif ext in ['.rs']:
            file_type = FILE_TYPE_CODE
            language = LANG_RUST
        elif ext in ['.cpp', '.cc', '.cxx', '.c', '.h', '.hpp']:
            file_type = FILE_TYPE_CODE
            language = LANG_CPP
        elif ext in ['.cs']:
            file_type = FILE_TYPE_CODE
            language = LANG_CSHARP

        # Special cases by filename
        filename = os.path.basename(file_path)
        if filename in ['Dockerfile']:
            file_type = FILE_TYPE_CONFIGURATION
            language = 'dockerfile'
        elif filename in ['.gitignore', '.dockerignore']:
            file_type = FILE_TYPE_CONFIGURATION
            language = 'ignore'
        elif filename in ['Makefile', 'makefile']:
            file_type = FILE_TYPE_CONFIGURATION
            language = 'makefile'

        # Special case for GitHub workflow files
        if '.github/workflows' in file_path and ext in ['.yml', '.yaml']:
            file_type = FILE_TYPE_CONFIGURATION
            language = 'github_workflow'

        # Special case for package definition files
        if filename in ['package.json', 'package-lock.json', 'yarn.lock']:
            file_type = FILE_TYPE_CONFIGURATION
            language = 'npm'
        elif filename in ['requirements.txt', 'Pipfile', 'Pipfile.lock', 'pyproject.toml', 'setup.py']:
            file_type = FILE_TYPE_CONFIGURATION
            language = 'python_package'

        # Special case for GitHub-specific files
        if '.github/' in file_path:
            file_type = FILE_TYPE_CONFIGURATION
            language = 'github'

        elapsed = time.time() - start_time
        self.logger.debug(f"Classified {file_path} as {file_type}/{language} in {elapsed:.4f}s")

        return file_type, language

    def process_file(self, file_path: str) -> List[ContentChunk]:
        """
        Process a file and create content chunks.

        Args:
            file_path: Path to the file, relative to repository root

        Returns:
            List of ContentChunk objects
        """
        start_time = time.time()
        abs_path = os.path.join(self.repo_path, file_path)

        # Skip if file doesn't exist
        if not os.path.exists(abs_path):
            self.logger.warning(f"File does not exist: {abs_path}")
            return []

        # Skip directories
        if os.path.isdir(abs_path):
            self.logger.debug(f"Skipping directory: {abs_path}")
            return []

        try:
            # Read file content
            with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Classify file
            file_type, language = self.classify_file(file_path)

            # Process based on file type
            if file_type == FILE_TYPE_CODE:
                chunks = self._process_code_file(file_path, content, language)
            elif file_type == FILE_TYPE_DOCUMENTATION:
                chunks = self._process_documentation_file(file_path, content, language)
            elif file_type == FILE_TYPE_CONFIGURATION:
                chunks = self._process_configuration_file(file_path, content, language)
            else:
                # For unknown types, create a single chunk
                self.logger.info(f"Processing unknown file type: {file_path}")
                chunks = [ContentChunk(
                    content=content,
                    file_path=file_path,
                    chunk_type=FILE_TYPE_UNKNOWN,
                    language=language
                )]

            # Update stats safely
            self.stats["files_processed"] += 1
            self.stats["files_by_type"][file_type] += 1

            if chunks:
                self.stats["chunks_created"] += len(chunks)
                self.stats["chunks_by_type"][file_type] += len(chunks)
                elapsed = time.time() - start_time
                self.logger.info(
                f"Processed {file_path} ({file_type}/{language}): "
                f"created {len(chunks)} chunks in {elapsed:.4f}s"
            )
            else:
                self.logger.warning(f"No chunks returned for file: {file_path}")




            return chunks

        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {e}", exc_info=True)
            self.stats["errors"] += 1
            return []

    def _process_code_file(self, file_path: str, content: str, language: str) -> List[ContentChunk]:
        """
        Process a code file and create code chunks.

        Args:
            file_path: Path to the file
            content: File content
            language: Programming language

        Returns:
            List of ContentChunk objects
        """
        chunks = []

        # Use language-specific processing
        if language == LANG_PYTHON:
            chunks = self._process_python_code(file_path, content)
        elif language == LANG_JAVA:
            chunks = self._process_java_code(file_path, content)
        elif language == LANG_GO:
            chunks = self._process_go_code(file_path, content)
        else:
            # For other languages, use generic chunking
            self.logger.debug(f"Using generic chunking for {language} file: {file_path}")
            chunks = self._chunk_by_size(
                content, file_path, FILE_TYPE_CODE, language,
                chunk_size=1500, overlap=200
            )

        return chunks

    def _process_python_code(self, file_path: str, content: str) -> List[ContentChunk]:
        """
        Process Python code file using AST.

        Args:
            file_path: Path to the file
            content: File content

        Returns:
            List of ContentChunk objects
        """
        chunks = []

        try:
            # Parse the Python code into an AST
            tree = ast.parse(content)

            # Track line numbers for AST nodes
            line_numbers = {}
            for node in ast.walk(tree):
                if hasattr(node, 'lineno'):
                    line_numbers[node] = (
                        getattr(node, 'lineno', None),
                        getattr(node, 'end_lineno', None)
                    )

            # Process classes
            for cls_node in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
                cls_name = cls_node.name
                cls_start, cls_end = line_numbers.get(cls_node, (None, None))
                if cls_start and cls_end:
                    # Extract class definition and docstring
                    cls_lines = content.splitlines()[cls_start-1:cls_end]
                    cls_content = '\n'.join(cls_lines)

                    # Create chunk for the class
                    cls_chunk = ContentChunk(
                        content=cls_content,
                        file_path=file_path,
                        chunk_type=FILE_TYPE_CODE,
                        start_line=cls_start,
                        end_line=cls_end,
                        language=LANG_PYTHON,
                        name=cls_name,
                        metadata={"type": "class"}
                    )
                    chunks.append(cls_chunk)

                    # Process methods within the class
                    for method_node in [n for n in cls_node.body if isinstance(n, ast.FunctionDef)]:
                        method_name = method_node.name
                        method_start, method_end = line_numbers.get(method_node, (None, None))
                        if method_start and method_end:
                            # Extract method definition
                            method_lines = content.splitlines()[method_start-1:method_end]
                            method_content = '\n'.join(method_lines)

                            # Create chunk for the method
                            method_chunk = ContentChunk(
                                content=method_content,
                                file_path=file_path,
                                chunk_type=FILE_TYPE_CODE,
                                start_line=method_start,
                                end_line=method_end,
                                language=LANG_PYTHON,
                                parent=cls_name,
                                name=method_name,
                                metadata={"type": "method"}
                            )
                            chunks.append(method_chunk)

            # Process standalone functions
            for func_node in [n for n in tree.body if isinstance(n, ast.FunctionDef)]:
                func_name = func_node.name
                func_start, func_end = line_numbers.get(func_node, (None, None))
                if func_start and func_end:
                    # Extract function definition
                    func_lines = content.splitlines()[func_start-1:func_end]
                    func_content = '\n'.join(func_lines)

                    # Create chunk for the function
                    func_chunk = ContentChunk(
                        content=func_content,
                        file_path=file_path,
                        chunk_type=FILE_TYPE_CODE,
                        start_line=func_start,
                        end_line=func_end,
                        language=LANG_PYTHON,
                        name=func_name,
                        metadata={"type": "function"}
                    )
                    chunks.append(func_chunk)

            # If no chunks were created (e.g., file with only imports or constants),
            # create a single chunk for the entire file
            if not chunks:
                self.logger.debug(f"No classes or functions found in {file_path}, using whole file")
                chunks = [ContentChunk(
                    content=content,
                    file_path=file_path,
                    chunk_type=FILE_TYPE_CODE,
                    language=LANG_PYTHON,
                    metadata={"type": "whole_file"}
                )]

            return chunks

        except SyntaxError as e:
            # Handle Python syntax errors
            self.logger.warning(f"Syntax error in Python file {file_path}: {e}")
            # Track the error
            self.error_tracker.add_error(
                file_path=file_path,
                language=LANG_PYTHON,
                error_msg=str(e),
                line_number=getattr(e, 'lineno', None)

            )
            # Fall back to generic chunking
            return self._chunk_by_size(
                content, file_path, FILE_TYPE_CODE, LANG_PYTHON,
                chunk_size=1500, overlap=200
            )

        except Exception as e:
            self.logger.error(f"Error processing Python file {file_path}: {e}", exc_info=True)
            # Fall back to generic chunking
            return self._chunk_by_size(
                content, file_path, FILE_TYPE_CODE, LANG_PYTHON,
                chunk_size=1500, overlap=200
            )

    def _process_class_node(self, class_node, file_path, content):
        local_chunks = []
        def get_node_text(node):
            return content[node.start_byte:node.end_byte]

        def get_line_range(node):
            return node.start_point[0] + 1, node.end_point[0] + 1

        class_text = get_node_text(class_node)
        start, end = get_line_range(class_node)
        class_name_node = class_node.child_by_field_name("name")
        class_name = get_node_text(class_name_node) if class_name_node else "UnknownClass"

        local_chunks.append(ContentChunk(
            content=class_text,
            file_path=file_path,
            chunk_type=FILE_TYPE_CODE,
            start_line=start,
            end_line=end,
            language="java",
            name=class_name,
            metadata={"type": "class"}
        ))

        for child in class_node.children:
            if child.type == "method_declaration":
                method_text = get_node_text(child)
                method_name_node = child.child_by_field_name("name")
                method_name = get_node_text(method_name_node) if method_name_node else "UnknownMethod"
                m_start, m_end = get_line_range(child)

                local_chunks.append(ContentChunk(
                    content=method_text,
                    file_path=file_path,
                    chunk_type=FILE_TYPE_CODE,
                    start_line=m_start,
                    end_line=m_end,
                    language="java",
                    parent=class_name,
                    name=method_name,
                    metadata={"type": "method"}
                ))

        return local_chunks

    def _process_go_code(self, file_path, content):
        try:
            parser = Parser()
            parser.set_language(GO_LANGUAGE)
            tree = parser.parse(bytes(content, "utf8"))
            root = tree.root_node

            # Check if tree-sitter encountered errors during parsing
            if root.has_error:
                # Track the error but continue processing
                self.error_tracker.add_error(
                    file_path=file_path,
                    language=LANG_GO,
                    error_msg="Go syntax error detected by tree-sitter"
                )
                self.logger.warning(f"Syntax error in Go file {file_path}")

            chunks = []

            def extract_chunks(node):
                if node.type in ["function_declaration", "method_declaration", "type_declaration", "struct_type"]:
                    code = content[node.start_byte:node.end_byte]
                    name_node = node.child_by_field_name("name")
                    name = name_node.text.decode() if name_node else "unnamed"
                    chunks.append({
                        "file_path": file_path,
                        "language": "go",
                        "name": name,
                        "type": node.type,
                        "start_line": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                        "content": code.strip()
                    })
                for child in node.children:
                    extract_chunks(child)

            extract_chunks(root)
            return chunks

        except Exception as e:
            self.logger.error(f"Error processing Go file {file_path}: {e}", exc_info=True)
            self.error_tracker.add_error(
                file_path=file_path,
                language=LANG_GO,
                error_msg=f"Failed to parse: {str(e)}"
            )
            return []  # Return empty list on failure

    def _process_java_code(self, file_path: str, content: str) -> List[ContentChunk]:
        """Process Java file using Tree-sitter to extract classes and methods."""
        chunks = []
        try:
            tree = JAVA_PARSER.parse(bytes(content, "utf8"))
            root = tree.root_node

            # Check if tree-sitter encountered errors during parsing
            if root.has_error:
                # Find all error nodes
                error_nodes = []

                def find_error_nodes(node):
                    if node.has_error or node.is_missing or node.type == "ERROR":
                        error_nodes.append(node)
                    for child in node.children:
                        find_error_nodes(child)

                find_error_nodes(root)

                for error_node in error_nodes:
                    # Get line and column info
                    line_num = error_node.start_point[0] + 1
                    col_num = error_node.start_point[1] + 1

                    # Get context (3 lines before and after)
                    lines = content.splitlines()
                    start_line = max(0, line_num - 4)
                    end_line = min(len(lines), line_num + 3)
                    context_lines = lines[start_line:end_line]
                    context = "\n".join(context_lines)

                    # Determine error type
                    error_type = "Unknown"
                    if error_node.type == "ERROR":
                        error_type = "Syntax Error"
                    elif error_node.is_missing:
                        error_type = "Missing Element"

                    # Determine containing element
                    containing_element = "Unknown"
                    parent = error_node.parent
                    while parent and parent != root:
                        if parent.type in ["class_declaration", "method_declaration", "field_declaration"]:
                            containing_element = parent.type
                            break
                        parent = parent.parent

                    # Add detailed error
                    self.error_tracker.add_error(
                        file_path=file_path,
                        language=LANG_JAVA,
                        error_msg=f"{error_type} in {containing_element}",
                        line_number=line_num,
                        function_name=containing_element,
                        metadata={
                            "column": col_num,
                            "context": context,
                            "error_node_type": error_node.type,
                            "containing_element": containing_element
                        }
                    )

                    self.logger.warning(f"Syntax error in Java file {file_path} at line {line_num}, column {col_num}")

                # If no specific error nodes found, add a generic error
                if not error_nodes:
                    self.error_tracker.add_error(
                        file_path=file_path,
                        language=LANG_JAVA,
                        error_msg="Java syntax error detected by tree-sitter"
                    )
                    self.logger.warning(f"Syntax error in Java file {file_path}")
                    
                def get_node_text(node):
                    return content[node.start_byte:node.end_byte]

                def get_line_range(node):
                    return node.start_point[0] + 1, node.end_point[0] + 1

                def find_classes_and_methods(node):
                    for child in node.children:
                        if child.type == "class_declaration":
                            class_chunks = self._process_class_node(child, file_path, content)
                            chunks.extend(class_chunks)
                        else:
                            find_classes_and_methods(child)

                find_classes_and_methods(root)
                return chunks
        except Exception as e:
            self.logger.error(f"Error processing Java file {file_path}: {e}", exc_info=True)
            self.error_tracker.add_error(
                file_path=file_path,
                language=LANG_JAVA,
                error_msg=f"Failed to parse: {str(e)}"
            )
            # Fall back to generic chunking
            return self._chunk_by_size(
                content, file_path, FILE_TYPE_CODE, LANG_JAVA,
                chunk_size=1500, overlap=200
            )

    def _process_documentation_file(self, file_path: str, content: str, language: str) -> List[ContentChunk]:
        """
        Process a documentation file.

        Args:
            file_path: Path to the file
            content: File content
            language: Documentation format (e.g., md, rst)

        Returns:
            List of ContentChunk objects
        """
        chunks = []

        if language == 'md':
            # For Markdown, try to chunk by headings
            chunks = self._chunk_markdown_by_heading(file_path, content)
        else:
            # For other documentation formats, use generic chunking
            chunks = self._chunk_by_size(
                content, file_path, FILE_TYPE_DOCUMENTATION, language,
                chunk_size=1500, overlap=250
            )

        return chunks

    def _chunk_markdown_by_heading(self, file_path: str, content: str) -> List[ContentChunk]:
        """
        Chunk Markdown content by headings.

        Args:
            file_path: Path to the file
            content: Markdown content

        Returns:
            List of ContentChunk objects
        """
        chunks = []

        # Find all headings and their positions
        heading_pattern = re.compile(r'^(#{1,6})\s+(.+?)$', re.MULTILINE)
        headings = list(heading_pattern.finditer(content))

        # If no headings found, use generic chunking
        if not headings:
            self.logger.debug(f"No headings found in Markdown file {file_path}, using size-based chunking")
            return self._chunk_by_size(
                content, file_path, FILE_TYPE_DOCUMENTATION, 'md',
                chunk_size=1500, overlap=250
            )

        # Process content between headings
        for i, match in enumerate(headings):
            heading = match.group(0)
            heading_level = len(match.group(1))  # Number of # characters
            heading_text = match.group(2).strip()
            start_pos = match.start()

            # Determine end position (next heading or end of file)
            if i < len(headings) - 1:
                end_pos = headings[i + 1].start()
            else:
                end_pos = len(content)

            # Extract section content
            section_content = content[start_pos:end_pos]

            # Calculate approximate line numbers (not exact)
            start_line = content[:start_pos].count('\n') + 1
            end_line = start_line + section_content.count('\n')

            # Create chunk for this section
            chunk = ContentChunk(
                content=section_content,
                file_path=file_path,
                chunk_type=FILE_TYPE_DOCUMENTATION,
                start_line=start_line,
                end_line=end_line,
                language='md',
                name=heading_text,
                metadata={
                    "type": "markdown_section",
                    "heading_level": heading_level
                }
            )
            chunks.append(chunk)

        # If the first heading doesn't start at the beginning of the file,
        # add a chunk for the content before the first heading
        if headings and headings[0].start() > 0:
            prefix_content = content[:headings[0].start()]
            if prefix_content.strip():  # Only if there's non-whitespace content
                chunk = ContentChunk(
                    content=prefix_content,
                    file_path=file_path,
                    chunk_type=FILE_TYPE_DOCUMENTATION,
                    start_line=1,
                    end_line=prefix_content.count('\n') + 1,
                    language='md',
                    name="Introduction",
                    metadata={"type": "markdown_intro"}
                )
                chunks.insert(0, chunk)  # Insert at the beginning

        return chunks

    def _process_configuration_file(self, file_path: str, content: str, language: str) -> List[ContentChunk]:
        """
        Process a configuration file.

        Args:
            file_path: Path to the file
            content: File content
            language: Configuration format (e.g., json, yaml)

        Returns:
            List of ContentChunk objects
        """
        # For most configuration files, keep as a single chunk
        chunk = ContentChunk(
            content=content,
            file_path=file_path,
            chunk_type=FILE_TYPE_CONFIGURATION,
            language=language,
            metadata={"type": language}
        )

        return [chunk]

    def _chunk_by_size(
        self, content: str, file_path: str, chunk_type: str, language: str,
        chunk_size: int = 1500, overlap: int = 200
    ) -> List[ContentChunk]:
        """
        Chunk content by size with overlapping windows.

        Args:
            content: Text content to chunk
            file_path: Path to the source file
            chunk_type: Type of content
            language: Language or format
            chunk_size: Target chunk size in characters
            overlap: Overlap between chunks in characters

        Returns:
            List of ContentChunk objects
        """
        chunks = []
        lines = content.splitlines()

        if not lines:
            return chunks

        chunk_text = []
        chunk_length = 0
        chunk_start_line = 1

        for i, line in enumerate(lines, 1):
            chunk_text.append(line)
            chunk_length += len(line) + 1  # +1 for the newline

            # If we've reached the target chunk size, create a chunk
            if chunk_length >= chunk_size:
                chunk_content = '\n'.join(chunk_text)
                chunk = ContentChunk(
                    content=chunk_content,
                    file_path=file_path,
                    chunk_type=chunk_type,
                    start_line=chunk_start_line,
                    end_line=i,
                    language=language,
                    metadata={"type": "size_based_chunk"}
                )
                chunks.append(chunk)

                # Calculate overlap for next chunk
                overlap_lines = []
                overlap_length = 0

                # Add lines from the end of the current chunk until we reach the overlap size
                for overlap_line in reversed(chunk_text):
                    if overlap_length + len(overlap_line) + 1 > overlap:
                        break
                    overlap_lines.insert(0, overlap_line)
                    overlap_length += len(overlap_line) + 1

                # Start the next chunk with the overlap
                chunk_text = overlap_lines
                chunk_length = overlap_length
                chunk_start_line = i - len(overlap_lines) + 1

        # Add any remaining content as a final chunk
        if chunk_text:
            final_chunk = ContentChunk(
                content='\n'.join(chunk_text),
                file_path=file_path,
                chunk_type=chunk_type,
                start_line=chunk_start_line,
                end_line=len(lines),
                language=language,
                metadata={"type": "size_based_chunk"}
            )
            chunks.append(final_chunk)

        return chunks

    def process_repository(self, exclude_dirs: Optional[List[str]] = None) -> List[ContentChunk]:
        """
        Process the entire repository.

        Args:
            exclude_dirs: List of directories to exclude (relative to repo root)

        Returns:
            List of all ContentChunk objects
        """
        self.logger.info(f"Starting repository processing: {self.repo_path}")
        start_time = time.time()

        all_chunks = []
        exclude_dirs = exclude_dirs or ['.git', 'node_modules', 'venv', 'env', '.env', 'build', 'dist']
        exclude_dirs = [os.path.normpath(d) for d in exclude_dirs]

        # Convert exclude_dirs to absolute paths for easier comparison
        exclude_abs = [os.path.join(self.repo_path, d) for d in exclude_dirs]

        # Walk through all repository files
        for root, dirs, files in os.walk(self.repo_path):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if os.path.join(root, d) not in exclude_abs]

            # Process each file
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, self.repo_path)

                # Process the file
                chunks = self.process_file(rel_path)
                if chunks:
                    all_chunks.extend(chunks)
                else:
                    self.logger.warning(f"Skipping extension: no chunks for a file.")

        # Update final statistics
        elapsed = time.time() - start_time
        self.stats["processing_time"] = elapsed

        self.logger.info(
            f"Repository processing complete: {len(all_chunks)} chunks created from "
            f"{self.stats['files_processed']} files in {elapsed:.2f}s"
        )

        # Log detailed statistics
        self.logger.info(f"Files by type: {dict(self.stats['files_by_type'])}")
        self.logger.info(f"Chunks by type: {dict(self.stats['chunks_by_type'])}")
        self.logger.info(f"Processing errors: {self.stats['errors']}")

        return all_chunks

    def get_syntax_error_report(self):
        """Get a report of all syntax errors encountered during processing."""
        return self.error_tracker.generate_report()

    def save_chunks(self, output_dir: str) -> str:
        """
        Save all chunks to a JSON file.

        Args:
            output_dir: Directory to save chunks in

        Returns:
            Path to the saved file
        """
        os.makedirs(output_dir, exist_ok=True)

        # Create filename based on repository name
        repo_name = os.path.basename(self.repo_path)
        output_file = os.path.join(output_dir, f"{repo_name}_chunks.json")

        # Convert chunks to dictionaries
        chunks_data = [chunk.to_dict() for chunk in self.chunks]

        # Save to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "repository": repo_name,
                "stats": self.stats,
                "chunks": chunks_data
            }, f, indent=2)

        self.logger.info(f"Saved {len(self.chunks)} chunks to {output_file}")
        return output_file


# Example usage
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Process repository content for embedding")
    parser.add_argument("--repo-path", required=True, help="Path to the repository")
    parser.add_argument("--output-dir", default="./data", help="Directory to save chunks")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Logging level")

    args = parser.parse_args()

    # Set log level
    log_level = getattr(logging, args.log_level)

    # Process the repository
    processor = ContentProcessor(args.repo_path, log_level=log_level)
    chunks = processor.process_repository()
    processor.chunks = chunks

    # Get syntax error report
    syntax_error_report = processor.get_syntax_error_report()
    print(f"Syntax Error Report: {syntax_error_report['summary'] if syntax_error_report['has_syntax_errors'] else 'No syntax errors found'}")

    # Save chunks to file
    output_file = processor.save_chunks(args.output_dir)
    print(f"Chunks saved to {output_file}")