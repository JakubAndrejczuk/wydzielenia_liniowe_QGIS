# -*- coding: utf-8 -*-
"""
Wydz_liniowe_auto – lekki wrapper uruchamiany z natywnego dialogu Processing.
Użytkownik wskazuje:
  - warstwę formularza (wydzielenia_nr_wew z BO),
  - folder SLMN z danymi wejściowymi,
a wtyczka sama wyszukuje wymagane pliki i wywołuje bazowy model: lmn:wydz_liniowe.
"""

import os
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingContext,
    QgsProcessingMultiStepFeedback,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterFile,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterVectorDestination,
    QgsProcessingParameterDefinition,
)

import processing
from .utils import plugin_dir  # ścieżka do folderu wtyczki


# Pliki wymagane w folderze SLMN – zgodnie z parametrami bazowego modelu
REQUIRED_FILES = {
    'a_kom_adbf':     'a_kom_a.dbf',
    'a_line_adbf':    'a_line_a.dbf',
    'a_kom_linshp':   'a_kom_lin.shp',
    'a_line_linshp':  'a_line_lin.shp',
    'a_oddz_polshp':  'a_oddz_pol.shp',
}


def _opis_html() -> str:
    """
    Czyta plik Opis.txt z katalogu wtyczki i zwraca prosty HTML
    do wyświetlenia po prawej stronie natywnego dialogu Processing.
    Bez żadnego nagłówka nad treścią.
    """
    try:
        path = os.path.join(plugin_dir(), 'Opis.txt')
        with open(path, 'r', encoding='utf-8') as f:
            txt = f.read().strip()
        body = '<br>'.join(txt.splitlines())
        return f'<div style="white-space:normal">{body}</div>'
    except Exception:
        return ('<div>Wtyczka „Wydzielenia liniowe”. '
                'Umieść plik <code>Opis.txt</code> w folderze wtyczki, aby tutaj pojawiła się treść opisu.</div>')


class Wydz_liniowe_auto(QgsProcessingAlgorithm):

    def name(self):
        return 'wydz_liniowe_auto'

    def displayName(self):
        return 'Wydzielenia liniowe'

    def group(self):
        return 'LMN'

    def groupId(self):
        return 'LMN'

    def createInstance(self):
        return Wydz_liniowe_auto()

    # ------ opis w prawym panelu natywnego dialogu ------
    def shortHelpString(self) -> str:
        return _opis_html()
    # -----------------------------------------------------

    # ---- Parametry dialogu Processing ----
    def initAlgorithm(self, config=None):
        # 1) Warstwa formularza
        self.addParameter(QgsProcessingParameterVectorLayer(
            'wydzielenia_nr_wew_formularz_z_bo',
            'wydzielenia_nr_wew (formularz z BO)',
            types=[QgsProcessing.TypeVector],
            defaultValue=None
        ))

        # 2) Folder SLMN
        self.addParameter(QgsProcessingParameterFile(
            'slmn_folder',
            'Folder z warstwami SLMN',
            behavior=QgsProcessingParameterFile.Folder
        ))

        # 3) WYJŚCIE GŁÓWNE: wydz_lin_agreg (destination – obowiązkowe)
        self.addParameter(QgsProcessingParameterVectorDestination(
            'Wydz_lin_agreg', 'wydz_lin_agreg'
        ))

        # 4) WYJŚCIE DODATKOWE: wydz_lin_seg (TERAZ obowiązkowe – bez [opcjonalne])
        p_seg = QgsProcessingParameterFeatureSink(
            'Wydz_lin_seg', 'wydz_lin_seg',
            type=QgsProcessing.TypeVectorAnyGeometry,
            createByDefault=True, defaultValue=None
        )
        # UWAGA: brak FlagOptional, żeby w GUI nie pojawiał się dopisek [opcjonalne]
        self.addParameter(p_seg)

    # ---- Logika ----
    def processAlgorithm(self, parameters, context: QgsProcessingContext, model_feedback):
        feedback = QgsProcessingMultiStepFeedback(1, model_feedback)

        folder = self.parameterAsString(parameters, 'slmn_folder', context).strip()
        if not folder or not os.path.isdir(folder):
            raise QgsProcessingException('Wskaż istniejący katalog w parametrze „Folder z warstwami SLMN”.')

        # Sprawdź wymagane pliki
        missing = []
        resolved_paths = {}
        for param_name, expected_file in REQUIRED_FILES.items():
            full_path = os.path.join(folder, expected_file)
            if not os.path.exists(full_path):
                missing.append(expected_file)
            else:
                resolved_paths[param_name] = full_path

        if missing:
            raise QgsProcessingException(
                'Brakujące pliki w folderze SLMN:\n  - ' + '\n  - '.join(missing)
            )

        # Złóż parametry dla algorytmu bazowego (z modelera)
        inner_params = {
            'wydzielenia_nr_wew_formularz_z_bo': parameters['wydzielenia_nr_wew_formularz_z_bo'],
            **resolved_paths,
            'Wydz_lin_agreg': parameters.get('Wydz_lin_agreg'),  # VectorDestination
            'Wydz_lin_seg': parameters.get('Wydz_lin_seg'),
        }

        # Uruchom bazowy algorytm (zarejestrowany jako lmn:wydz_liniowe)
        results = processing.run(
            'lmn:wydz_liniowe',
            inner_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True
        )

        return {
            'Wydz_lin_agreg': results.get('Wydz_lin_agreg'),
            'Wydz_lin_seg': results.get('Wydz_lin_seg')
        }
