from typing import List
from lxml import etree
import re
import markdown
from bs4 import Tag, BeautifulSoup
from typing import Any
from psycopg2.extensions import cursor, connection
from src.config import settings
from src.logger import LoggerFactory
from src.exceptions import InvalidXMLException


logger = LoggerFactory.getLogger(__name__)


def validate_xml(data: str) -> None:
    parser = etree.XMLParser(no_network=True, resolve_entities=False)  # Disable external entities for security
    
    try:
        # Attempt to parse the XML string
        etree.fromstring(data.encode(), parser)
        return
    except etree.XMLSyntaxError as e:
        raise InvalidXMLException(f"Invalid XML syntax:\n{e}")


def safe_deep_find(element: Tag, names: List[str], default: Any = None, recursive: bool = True) -> Any:
    current_element = element
    for name in names:
        current_element = current_element.find(name=name, recursive=recursive)
        if current_element is None:
            return default
    return current_element


def get_connection_id(connection: connection) -> int:
    """Function to avoid collision with id parameter name"""
    return id(connection)


def render_md_to_html(text: str) -> str:
    """Convert Markdown to HTML while preserving existing html tags"""
    escaped_text = escape_html(text)
     
    # Convert Markdown to HTML
    markdown_html = markdown.markdown(escaped_text)
        
    # Return the final rendered HTML
    return markdown_html


def escape_html(text: str) -> str:
    # Escape HTML tags to prevent them from being rendered
    return re.sub(r'&', '&amp;', re.sub(r'<', '&lt;', re.sub(r'>', '&gt;', text)))


def convert_code_blocks_to_html(text):
    # Regular expression to find code blocks with the pattern ```lang:python
    code_block_pattern = r'```lang:\w+;;(.*?)```'
    
    def replace_code_block(match):
        # Extract the code block content
        code_content = match.group(1).strip()
        
        # Split the content into lines based on line number indicators
        lines = re.split(r'\s*\[\d+\]\s*', code_content)
        
        # Remove any empty lines that may result from splitting
        cleaned_lines = [line.strip() for line in lines if line.strip()]
        
        # Join the cleaned lines into a single string
        cleaned_code = '\n'.join(cleaned_lines)
        
        # Create the HTML code block
        html_code_block = f"<pre><code class='language-python'>\n{cleaned_code}\n</code></pre>"
        return html_code_block

    # Replace all code blocks in the text
    converted_text = re.sub(code_block_pattern, replace_code_block, text, flags=re.DOTALL)
    
    return converted_text


def clean_html_tags(text: str) -> str:
    """Remove all HTML tags from the given text using BeautifulSoup."""
    soup = BeautifulSoup(text, "html.parser")
    clean_text = soup.get_text()  # Extract text without HTML tags
    return clean_text.strip()  # Remove leading and trailing whitespace
