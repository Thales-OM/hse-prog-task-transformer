from typing import List
from lxml import etree
from bs4 import Tag
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