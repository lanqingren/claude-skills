#!/usr/bin/env python3
"""
Save generated math review content to a Markdown file.

Takes a title and markdown content from the skill output and saves
it as a properly named .md file in the current directory.

Example:
    python scripts/generate_review.py --title "圆的切线性质与勾股定理综合" --content "..."
"""

import argparse
import re
import sys
from pathlib import Path


def sanitize_filename(title: str) -> str:
    """
    Sanitize the title into a valid filename.

    Args:
        title: The review title to convert to filename.

    Returns:
        A sanitized filename string ending with .md
    """
    # Remove markdown formatting
    cleaned = title.strip()
    # Remove leading # markers
    cleaned = re.sub(r'^#+\s*', '', cleaned)
    # Replace invalid filename characters
    cleaned = re.sub(r'[<>:"/\\|?*]', '-', cleaned)
    # Replace newlines and extra spaces
    cleaned = re.sub(r'\s+', ' ', cleaned)
    # Trim whitespace
    cleaned = cleaned.strip()
    # Ensure it ends with .md
    if not cleaned.endswith('.md'):
        cleaned += '.md'
    return cleaned


def save_review(title: str, content: str, output_dir: str = '.') -> Path:
    """
    Save the review content to a Markdown file.

    Args:
        title: The review title, used as filename.
        content: The full markdown content to save.
        output_dir: Directory to save the file in. Defaults to current dir.

    Returns:
        Path to the saved file.

    Raises:
        ValueError: If content is empty.
        OSError: If file cannot be written.
    """
    if not content or not content.strip():
        raise ValueError("Content cannot be empty")

    filename = sanitize_filename(title)
    output_path = Path(output_dir) / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(content.strip() + '\n', encoding='utf-8')
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Save math mistake review content to a Markdown file."
    )
    parser.add_argument(
        '--title', required=True,
        help='Title for the review (used as filename)'
    )
    parser.add_argument(
        '--content', required=True,
        help='Full markdown content of the review'
    )
    parser.add_argument(
        '--output-dir', default='.',
        help='Directory to save the file (default: current directory)'
    )

    args = parser.parse_args()

    try:
        output_path = save_review(args.title, args.content, args.output_dir)
        print(f"Review saved to: {output_path}")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"Error writing file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
