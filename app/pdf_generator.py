import os
import time
from datetime import datetime
from weasyprint import HTML
from logging_config import get_logger

logger = get_logger("pdf_generator")

OUTPUT_DIR = "output_reports"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_pdf_from_llm_response(repo_name: str, role: str, llm_text: str) -> str:
    """
    Wrap the LLM response in HTML and export as a PDF file.
    Returns the path to the saved PDF.
    """
    timestamp = int(time.time())
    file_name = f"{repo_name}_{role}_report_{timestamp}.pdf"
    file_path = os.path.join(OUTPUT_DIR, file_name)

    html_template = f"""
    <html>
    <head>
        <meta charset='utf-8'>
        <style>
            body {{ font-family: sans-serif; padding: 2em; line-height: 1.5; }}
            h1, h2, h3 {{ color: #2c3e50; }}
            pre {{ background: #f4f4f4; padding: 1em; border-radius: 5px; overflow-x: auto; }}
            hr {{ margin: 2em 0; }}
        </style>
    </head>
    <body>
        <h1>Repository Analysis Report</h1>
        <h2>Project: {repo_name}</h2>
        <h3>Role: {role.title()}</h3>
        <p><em>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em></p>
        <hr>
        <pre>{llm_text}</pre>
    </body>
    </html>
    """

    try:
        HTML(string=html_template).write_pdf(file_path)
        logger.info(f"✅ PDF saved to: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"❌ Failed to generate PDF: {e}")
        return ""
