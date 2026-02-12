# -*- coding: utf-8 -*-
from .plugin import WydzLiniowePlugin

def classFactory(iface):
    """
    QGIS wywołuje tę funkcję przy ładowaniu wtyczki.
    Zwraca instancję klasy implementującej interfejs wtyczki.
    """
    return WydzLiniowePlugin(iface)