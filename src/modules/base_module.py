from PyQt5.QtWidgets import QWidget
from abc import ABC, abstractmethod


class PDFModule(ABC):
    """Base class for all PDF modules"""

    @abstractmethod
    def get_name(self) -> str:
        """Return the name of the module"""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Return the description of the module"""
        pass

    @abstractmethod
    def get_widget(self) -> QWidget:
        """Return the main widget of the module"""
        pass
