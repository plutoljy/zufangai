# -*- coding: utf-8 -*-
"""
工具模块
"""

from .document_parser import (
    FileTypeDetector,
    PDFParser,
    DocxParser,
    ImageOCR,
    DocumentParser,
    get_document_parser
)

__all__ = [
    'FileTypeDetector',
    'PDFParser',
    'DocxParser',
    'ImageOCR',
    'DocumentParser',
    'get_document_parser'
]
