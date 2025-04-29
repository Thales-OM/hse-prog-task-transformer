from fastapi import Depends, Request
from typing import List, Callable, Optional
from lxml import etree
import re
from bs4 import Tag, BeautifulSoup
from typing import Any
from psycopg2.extensions import cursor, connection
from src.config import settings
from src.logger import LoggerFactory
from src.exceptions import InvalidXMLException


logger = LoggerFactory.getLogger(__name__)


def validate_xml(data: str) -> None:
    parser = etree.XMLParser(
        no_network=True, resolve_entities=False
    )  # Disable external entities for security

    try:
        # Attempt to parse the XML string
        etree.fromstring(data.encode(), parser)
        return
    except etree.XMLSyntaxError as e:
        raise InvalidXMLException(f"Invalid XML syntax:\n{e}")


def safe_deep_find(
    element: Tag, names: List[str], default: Any = None, recursive: bool = True
) -> Any:
    current_element = element
    for name in names:
        current_element = current_element.find(name=name, recursive=recursive)
        if current_element is None:
            return default
    return current_element


def get_connection_id(connection: connection) -> int:
    """Function to avoid collision with id parameter name"""
    return id(connection)


def code_md_to_html(text):
    # Regular expression to find code blocks with the pattern ```lang:python
    code_block_pattern = r"```lang:\w+;;(.*?)```"

    def replace_code_block(match):
        # Extract the code block content
        code_content = match.group(1).strip()

        # Create the HTML code block
        html_code_block = (
            f"<pre><code class='language-python'>\n{code_content}\n</code></pre>"
        )
        return html_code_block

    # Replace all code blocks in the text
    converted_text = re.sub(
        code_block_pattern, replace_code_block, text, flags=re.DOTALL
    )

    return converted_text


def clean_html_tags(text: str) -> str:
    """Remove all HTML tags from the given text using BeautifulSoup."""
    soup = BeautifulSoup(text, "html.parser")
    clean_text = soup.get_text()  # Extract text without HTML tags
    return clean_text.strip()  # Remove leading and trailing whitespace


def wrap_code_in_html(text: str) -> str:
    html_code_block = f"<pre><code class='language-python'>\n{text}\n</code></pre>"
    return html_code_block


def form_to_key(text):
    """
    Replace all newline escape symbols with actual newlines.

    Args:
    text (str): The input string containing newline escape symbols.

    Returns:
    str: The modified string with actual newlines.
    """
    return text.replace("\\n", "\n")


def get_request_ip(request: Request) -> str:
    client_ip = request.headers.get("X-Envoy-External-Address")
    if client_ip is None:
        client_ip = request.client.host
    return client_ip


def replace_and_append_options(text):
    # Define the regex pattern to find the specified format
    pattern = r"{:MCS:=(.*?)}"
    
    # Search for the pattern in the text
    match = re.search(pattern, text)
    
    if match:
        contents = match.group(1)  # Get the contents inside the braces
        # Split the contents by [int]~ or just ~
        options = re.split(r'\s*\[-?\d+\]?~\s*', contents)
        # Replace the original match with <choose option>
        replacement = "<Выберите вариант>"
        # Create the options string
        options_str = "<pre>" + "Варианты ответа:" + "\n  - " + "\n  - ".join(options) + "</pre>"
        
        # Replace the first occurrence of the pattern in the text
        new_text = text.replace(match.group(0), replacement)
        # Append the options string at the end of the original text
        new_text += "\n" + options_str + "\n"
        
        return new_text
    else:
        # If no match is found, return the original text
        return text
