# Updated app/services/code_validator.py
# Adds CodeCompletenessValidator.validate_completeness that returns a dict with keys:
# - is_complete (bool)
# - completeness_score (float 0..1)
# - issues (list of strings)
# - warnings (list of strings)
# - language (optional)

from typing import List, Dict, Any
import re
import ast
import logging

logger = logging.getLogger(__name__)

TRUNCATION_MARKERS = [
    '...',
    '# ... rest of code',
    '# ... kode lainnya',
    '# rest of the code',
    '// ... rest of code',
    '// ... kode lainnya',
    '/* ... */',
    '<!-- ... -->',
    '[truncated]',
    '[continued]',
    '[TRUNCATED]',
    '[CONTINUED]',
    '# dan seterusnya',
    '// dan seterusnya',
    '# ... (rest omitted)',
    '// ... (rest omitted)',
]

INCOMPLETE_PATTERNS = [
    r'(def\s+\w+\([^)]*\):)\s*\.\.\.', # Python function with ...
    r'(function\s+\w+\([^)]*\))\s*\{?\s*\.\.\.', # JS function with ...
]


class CodeCompletenessValidator:
    """Validator to detect truncation, incomplete functions/classes and compute a completeness_score."""

    @staticmethod
    def _detect_truncation_markers(content: str) -> List[str]:
        found = []
        low = content.lower()
        for m in TRUNCATION_MARKERS:
            if m.lower() in low:
                found.append(m)
        return found

    @staticmethod
    def _detect_incomplete_patterns(content: str) -> List[str]:
        issues = []
        for pat in INCOMPLETE_PATTERNS:
            if re.search(pat, content, flags=re.MULTILINE):
                issues.append(f"pattern: {pat}")
        return issues

    @staticmethod
    def _language_from_filename(filename: str) -> str:
        if filename.endswith('.py'):
            return 'python'
        if filename.endswith(('.js', '.jsx', '.ts', '.tsx')):
            return 'javascript'
        if filename.endswith(('.html', '.htm')):
            return 'html'
        if filename.endswith(('.css', '.scss')):
            return 'css'
        return 'unknown'

    @staticmethod
    def _validate_python_ast(content: str) -> List[str]:
        issues = []
        try:
            ast.parse(content)
        except SyntaxError as e:
            issues.append(f"SyntaxError: {e}")
        except Exception as e:
            issues.append(f"AST parse error: {e}")
        return issues

    @staticmethod
    def validate_completeness(content: str, filename: str = "code.py") -> Dict[str, Any]:
        """
        Return a dictionary with keys:
        - is_complete: bool
        - completeness_score: float (0..1)
        - issues: list[str]
        - warnings: list[str]
        - language: str
        """
        if not isinstance(content, str) or not content.strip():
            return {
                'is_complete': False,
                'completeness_score': 0.0,
                'issues': ['empty content'],
                'warnings': [],
                'language': CodeCompletenessValidator._language_from_filename(filename)
            }

        issues = []
        warnings = []

        # Detect truncation markers
        truncs = CodeCompletenessValidator._detect_truncation_markers(content)
        if truncs:
            issues.append(f"truncation_markers: {', '.join(truncs)}")

        # Detect incomplete patterns
        incp = CodeCompletenessValidator._detect_incomplete_patterns(content)
        if incp:
            issues.extend(incp)

        # Language specific checks
        language = CodeCompletenessValidator._language_from_filename(filename)
        if language == 'python':
            py_issues = CodeCompletenessValidator._validate_python_ast(content)
            if py_issues:
                issues.extend(py_issues)
        else:
            # For other languages, at minimum check braces balance for JS/CSS/HTML as heuristic
            if language == 'javascript':
                # simple heuristic for unmatched braces
                open_braces = content.count('{')
                close_braces = content.count('}')
                if open_braces != close_braces:
                    issues.append('unmatched_braces')

        # compute completeness_score heuristically
        base_score = 1.0
        # penalize by issues found
        if issues:
            # Each issue reduces score; cap minimum at 0.0
            penalty = min(0.9, 0.2 + 0.15 * len(issues))
            base_score -= penalty
        else:
            # small penalty if file is very short
            if len(content) < 50:
                warnings.append('very_short_file')
                base_score -= 0.1

        # Normalize
        completeness_score = max(0.0, round(base_score, 3))
        is_complete = completeness_score >= getattr(__import__('app.core.config', fromlist=['settings']).settings, 'COMPLETENESS_THRESHOLD', 0.95)

        return {
            'is_complete': is_complete,
            'completeness_score': completeness_score,
            'issues': issues,
            'warnings': warnings,
            'language': language
        }


# Expose for imports
__all__ = ['CodeCompletenessValidator']