# -*- coding: utf-8 -*-
import os
from qgis.core import QgsVectorLayer

def plugin_dir() -> str:
    """Zwraca katalog bieżącej wtyczki (tam powinna być ikona icon.png)."""
    return os.path.dirname(os.path.abspath(__file__))

def ensure_output_string(path: str) -> str:
    """
    Zwraca prawidłowy identyfikator wyjścia Processing.
    Jeśli użytkownik nie podał rozszerzenia – domyślnie Shapefile (.shp).
    """
    if not path:
        return 'memory:'
    p = path.strip()
    root, ext = os.path.splitext(p)
    if not ext:
        # domyślnie .shp (Shapefile)
        p = p + '.shp'
    return p

def infer_layer_name_from_source(src: str) -> str:
    """
    Wywnioskuj nazwę warstwy z:
    - ścieżki do pliku (np. C:/data/wydz_lin_agreg.shp -> 'wydz_lin_agreg')
    - parametru warstwy w źródle OGR (np. gpkg|layername=foo -> 'foo')
    """
    name_from_param = None
    if '|' in src:
        # np. "C:/data/out.gpkg|layername=foo"
        parts = src.split('|')
        for p in parts[1:]:
            if p.lower().startswith('layername='):
                name_from_param = p.split('=', 1)[1]
                break
        base = parts[0]
    else:
        base = src
    base_name = os.path.splitext(os.path.basename(base))[0]
    return name_from_param or base_name

def load_vector_if_exists(path: str, name: str | None) -> QgsVectorLayer:
    """
    Jeśli 'path' wskazuje na plik, wczytaj warstwę jako OGR.
    - Jeśli name=None, użyj nazwy pochodzącej z pliku/parametru "layername=" (dla GPKG).
    - Ignoruje ścieżki 'memory:'.
    """
    if not path or path.lower().startswith('memory:'):
        return None

    # Dla ścieżek z parametrami OGR (np. gpkg|layername=foo) sprawdź tylko część plikową
    file_part = path.split('|')[0]
    if not os.path.exists(file_part):
        # dla nieistniejących plików i tak spróbujemy – OGR może wskazać złożone źródło
        pass

    display_name = name if name else infer_layer_name_from_source(path)
    lyr = QgsVectorLayer(path, display_name if display_name else 'warstwa', 'ogr')
    if lyr and lyr.isValid():
        # wymuś nazwę jeszcze raz na wszelki wypadek (niektóre providery potrafią ją nadpisać)
        if display_name:
            lyr.setName(display_name)
        return lyr
    return None