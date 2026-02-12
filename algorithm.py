# -*- coding: utf-8 -*-
"""
Algorytm Processing wygenerowany z modelera i zaadaptowany do wtyczki.
"""

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingMultiStepFeedback,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterVectorDestination,
    QgsProcessingParameterDefinition,
    QgsCoordinateReferenceSystem,
)
import processing
import os

# wczytanie ścieżki katalogu wtyczki
from .utils import plugin_dir


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


class Wydz_liniowe(QgsProcessingAlgorithm):

    # ------ opis w prawym panelu natywnego dialogu ------
    def shortHelpString(self) -> str:
        return _opis_html()
    # -----------------------------------------------------

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer(
            'wydzielenia_nr_wew_formularz_z_bo',
            'wydzielenia nr wew (formularz z BO)',
            types=[QgsProcessing.TypeVector],
            defaultValue=None))

        self.addParameter(QgsProcessingParameterVectorLayer(
            'a_kom_adbf', 'a_kom_a.dbf',
            types=[QgsProcessing.TypeVector],
            defaultValue=None))

        self.addParameter(QgsProcessingParameterVectorLayer(
            'a_kom_linshp', 'a_kom_lin.shp',
            types=[QgsProcessing.TypeVector],
            defaultValue=None))

        self.addParameter(QgsProcessingParameterVectorLayer(
            'a_line_adbf', 'a_line_a.dbf',
            types=[QgsProcessing.TypeVector],
            defaultValue=None))

        self.addParameter(QgsProcessingParameterVectorLayer(
            'a_line_linshp', 'a_line_lin.shp',
            types=[QgsProcessing.TypeVector],
            defaultValue=None))

        self.addParameter(QgsProcessingParameterVectorLayer(
            'a_oddz_polshp', 'a_oddz_pol.shp',
            types=[QgsProcessing.TypeVector],
            defaultValue=None))

        # --- WYJŚCIE GŁÓWNE: wydz_lin_agreg (destination – obowiązkowe) ---
        self.addParameter(QgsProcessingParameterVectorDestination(
            'Wydz_lin_agreg', 'wydz_lin_agreg'
        ))

        # --- WYJŚCIE DODATKOWE: wydz_lin_seg (obowiązkowe – bez [opcjonalne]) ---
        p_seg = QgsProcessingParameterFeatureSink(
            'Wydz_lin_seg', 'wydz_lin_seg',
            type=QgsProcessing.TypeVectorAnyGeometry,
            createByDefault=True, defaultValue=None
        )
        self.addParameter(p_seg)

    def processAlgorithm(self, parameters, context, model_feedback):
        # 33 kroki – po agregacji: reproject do EPSG:2180 i dopiero liczenie $length
        # 31: loadlayer seg, 32: loadlayer agreg (narzucają nazwy w projekcie)
        feedback = QgsProcessingMultiStepFeedback(33, model_feedback)
        results = {}
        outputs = {}

        # 0) Zmień pola na dziesiętne
        alg_params = {
            'FIELDS_MAPPING': [
                {'alias': None, 'comment': None, 'expression': 'adr_les', 'length': 25, 'name': 'adr_les', 'precision': 0, 'sub_type': 0, 'type': 10, 'type_name': 'text'},
                {'alias': None, 'comment': None, 'expression': 'nr_wew', 'length': 10, 'name': 'nr_wew', 'precision': 0, 'sub_type': 0, 'type': 4, 'type_name': 'int8'},
                {'alias': None, 'comment': None, 'expression': 'pow', 'length': 10, 'name': 'pow', 'precision': 4, 'sub_type': 0, 'type': 6, 'type_name': 'double precision'}
            ],
            'INPUT': parameters['wydzielenia_nr_wew_formularz_z_bo'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ZmiePolaNaDziesitne'] = processing.run('native:refactorfields', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # 1) Dodaj adr_les do a_kom_a
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'FIELD': 'nr_wew',
            'FIELDS_TO_COPY': ['adr_les'],
            'FIELD_2': 'nr_wew',
            'INPUT': parameters['a_kom_adbf'],
            'INPUT_2': outputs['ZmiePolaNaDziesitne']['OUTPUT'],
            'METHOD': 1,
            'PREFIX': None,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['DodajAdr_lesDoA_kom_a'] = processing.run('native:joinattributestable', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # 2) Napraw geometrie oddz_pol
        alg_params = {
            'INPUT': parameters['a_oddz_polshp'],
            'METHOD': 1,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['NaprawGeometrieOddz_pol'] = processing.run('native:fixgeometries', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # 3) Dodaj adr_les do oddz_pol
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'FIELD': 'nr_wew',
            'FIELDS_TO_COPY': ['adr_les'],
            'FIELD_2': 'nr_wew',
            'INPUT': outputs['NaprawGeometrieOddz_pol']['OUTPUT'],
            'INPUT_2': outputs['ZmiePolaNaDziesitne']['OUTPUT'],
            'METHOD': 1,
            'PREFIX': None,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['DodajAdr_lesDoOddz_pol'] = processing.run('native:joinattributestable', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # 4) Przytnij a_kom_lin do oddz_pol
        alg_params = {
            'INPUT': parameters['a_kom_linshp'],
            'OVERLAY': outputs['NaprawGeometrieOddz_pol']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['PrzytnijA_kom_linDoOddz_pol'] = processing.run('native:clip', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # 5) Oddz_pol na oddz_lin
        alg_params = {
            'INPUT': outputs['DodajAdr_lesDoOddz_pol']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Oddz_polNaOddz_lin'] = processing.run('native:polygonstolines', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}

        # 6) Przytnij a_line_lin do oddz_pol
        alg_params = {
            'INPUT': parameters['a_line_linshp'],
            'OVERLAY': outputs['DodajAdr_lesDoOddz_pol']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['PrzytnijA_line_linDoOddz_pol'] = processing.run('native:clip', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(7)
        if feedback.isCanceled():
            return {}

        # 7) Dodaj id_oddz do a_kom_a
        alg_params = {
            'FIELD_LENGTH': 50,
            'FIELD_NAME': 'id_oddz',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 2,
            'FORMULA': '"id_kom" || trim(substr("adr_les",1,17))',
            'INPUT': outputs['DodajAdr_lesDoA_kom_a']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['DodajId_oddzDoA_kom_a'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(8)
        if feedback.isCanceled():
            return {}

        # 8) Dodaj adr_les do a_line_a
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'FIELD': 'nr_wew',
            'FIELDS_TO_COPY': ['adr_les'],
            'FIELD_2': 'nr_wew',
            'INPUT': parameters['a_line_adbf'],
            'INPUT_2': outputs['ZmiePolaNaDziesitne']['OUTPUT'],
            'METHOD': 1,
            'PREFIX': None,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['DodajAdr_lesDoA_line_a'] = processing.run('native:joinattributestable', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(9)
        if feedback.isCanceled():
            return {}

        # 9) Dodaj id_oddz do a_line_a
        alg_params = {
            'FIELD_LENGTH': 50,
            'FIELD_NAME': 'id_oddz',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 2,
            'FORMULA': '"id_lin" || trim(substr("adr_les",1,17))',
            'INPUT': outputs['DodajAdr_lesDoA_line_a']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['DodajId_oddzDoA_line_a'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(10)
        if feedback.isCanceled():
            return {}

        # 10) Podziel a_kom_lin pomocą oddz_lin
        alg_params = {
            'INPUT': outputs['PrzytnijA_kom_linDoOddz_pol']['OUTPUT'],
            'LINES': outputs['Oddz_polNaOddz_lin']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['PodzielA_kom_linPomocOddz_lin'] = processing.run('native:splitwithlines', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(11)
        if feedback.isCanceled():
            return {}

        # 11) Podziel a_line_lin pomocą oddz_lin
        alg_params = {
            'INPUT': outputs['PrzytnijA_line_linDoOddz_pol']['OUTPUT'],
            'LINES': outputs['Oddz_polNaOddz_lin']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['PodzielA_line_linPomocOddz_lin'] = processing.run('native:splitwithlines', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(12)
        if feedback.isCanceled():
            return {}

        # 12) Zmień adr_les na adr_oddz
        alg_params = {
            'FIELDS_MAPPING': [{'alias': None, 'comment': None, 'expression': 'adr_les', 'length': 25, 'name': 'adr_oddz', 'precision': 0, 'sub_type': 0, 'type': 10, 'type_name': 'text'}],
            'INPUT': outputs['DodajAdr_lesDoOddz_pol']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ZmieAdr_lesNaAdr_oddz'] = processing.run('native:refactorfields', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(13)
        if feedback.isCanceled():
            return {}

        # 13) Dodaj adr_oddz do a_line_lin
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'INPUT': outputs['PodzielA_line_linPomocOddz_lin']['OUTPUT'],
            'JOIN': outputs['ZmieAdr_lesNaAdr_oddz']['OUTPUT'],
            'JOIN_FIELDS': ['adr_oddz'],
            'METHOD': 2,
            'PREDICATE': [0, 1, 5],
            'PREFIX': None,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['DodajAdr_oddzDoA_line_lin'] = processing.run('native:joinattributesbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(14)
        if feedback.isCanceled():
            return {}

        # 14) Dodaj adr_oddz do a_kom_lin
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'INPUT': outputs['PodzielA_kom_linPomocOddz_lin']['OUTPUT'],
            'JOIN': outputs['ZmieAdr_lesNaAdr_oddz']['OUTPUT'],
            'JOIN_FIELDS': ['adr_oddz'],
            'METHOD': 2,
            'PREDICATE': [0, 1, 5],
            'PREFIX': None,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['DodajAdr_oddzDoA_kom_lin'] = processing.run('native:joinattributesbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(15)
        if feedback.isCanceled():
            return {}

        # 15) Oblicz id_oddz do a_kom_lin
        alg_params = {
            'FIELD_LENGTH': 50,
            'FIELD_NAME': 'id_oddz',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 2,
            'FORMULA': '"id_kom" || trim(substr("adr_oddz",1,17))',
            'INPUT': outputs['DodajAdr_oddzDoA_kom_lin']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ObliczId_oddzDoA_kom_lin'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(16)
        if feedback.isCanceled():
            return {}

        # 16) Oblicz id_oddz do a_line_lin
        alg_params = {
            'FIELD_LENGTH': 50,
            'FIELD_NAME': 'id_oddz',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 2,
            'FORMULA': '"id_lin" || trim(substr("adr_oddz",1,17))',
            'INPUT': outputs['DodajAdr_oddzDoA_line_lin']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ObliczId_oddzDoA_line_lin'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(17)
        if feedback.isCanceled():
            return {}

        # 17) Dodaj adr_les_line do a_line_lin
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'FIELD': 'id_oddz',
            'FIELDS_TO_COPY': ['adr_les'],
            'FIELD_2': 'id_oddz',
            'INPUT': outputs['ObliczId_oddzDoA_line_lin']['OUTPUT'],
            'INPUT_2': outputs['DodajId_oddzDoA_line_a']['OUTPUT'],
            'METHOD': 1,
            'PREFIX': None,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['DodajAdr_les_lineDoA_line_lin'] = processing.run('native:joinattributestable', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(18)
        if feedback.isCanceled():
            return {}

        # 18) Dodaj adr_les_line do a_kom_lin
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'FIELD': 'id_oddz',
            'FIELDS_TO_COPY': ['adr_les'],
            'FIELD_2': 'id_oddz',
            'INPUT': outputs['ObliczId_oddzDoA_kom_lin']['OUTPUT'],
            'INPUT_2': outputs['DodajId_oddzDoA_kom_a']['OUTPUT'],
            'METHOD': 1,
            'PREFIX': None,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['DodajAdr_les_lineDoA_kom_lin'] = processing.run('native:joinattributestable', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(19)
        if feedback.isCanceled():
            return {}

        # 19) Złącz a_kom_lin i a_line_lin (wymuszamy CRS 2180)
        alg_params = {
            'CRS': QgsCoordinateReferenceSystem('EPSG:2180'),
            'LAYERS': [outputs['DodajAdr_les_lineDoA_kom_lin']['OUTPUT'],
                       outputs['DodajAdr_les_lineDoA_line_lin']['OUTPUT']],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ZczA_kom_linIA_line_lin'] = processing.run('native:mergevectorlayers', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(20)
        if feedback.isCanceled():
            return {}

        # 20) Usuń duplikaty geometrii
        alg_params = {
            'INPUT': outputs['ZczA_kom_linIA_line_lin']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['UsuDuplikatyGeometrii'] = processing.run('native:deleteduplicategeometries', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(21)
        if feedback.isCanceled():
            return {}

        # 21) Wyodrębnij obiekty z adr_les
        alg_params = {
            'EXPRESSION': '"adr_les" IS NOT NULL',
            'INPUT': outputs['UsuDuplikatyGeometrii']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['WyodrbnijObiektyZAdr_les'] = processing.run('native:extractbyexpression', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(22)
        if feedback.isCanceled():
            return {}

        # 22) Zagreguj id_kom i id_lin -> 'id'
        alg_params = {
            'FIELD_LENGTH': 20,
            'FIELD_NAME': 'id',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 0,
            'FORMULA': ' coalesce(  "id_kom", "id_lin" )',
            'INPUT': outputs['WyodrbnijObiektyZAdr_les']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ZagregujId_komIId_lin'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(23)
        if feedback.isCanceled():
            return {}

        # 23) Oblicz długość segmentów (wstępnie)
        alg_params = {
            'FIELD_LENGTH': 10,
            'FIELD_NAME': 'dlugosc',
            'FIELD_PRECISION': 2,
            'FIELD_TYPE': 0,
            'FORMULA': '$length',
            'INPUT': outputs['ZagregujId_komIId_lin']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ObliczDugo'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(24)
        if feedback.isCanceled():
            return {}

        # 24) Zaokrąglij atrybut 'dlugosc' do 2 miejsc (aktualizacja pola)
        alg_params = {
            'FIELD_LENGTH': 10,
            'FIELD_NAME': 'dlugosc',
            'FIELD_PRECISION': 2,
            'FIELD_TYPE': 0,
            'FORMULA': 'round("dlugosc", 2)',
            'NEW_FIELD': False,
            'INPUT': outputs['ObliczDugo']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ZaokraglijDlugosc'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(25)
        if feedback.isCanceled():
            return {}

        # 25) Wyodrębnij segmenty z długością > 0
        alg_params = {
            'FIELD': 'dlugosc',
            'INPUT': outputs['ZaokraglijDlugosc']['OUTPUT'],
            'OPERATOR': 2,  # greater than
            'VALUE': '0',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['WyodrebnijDlugoscWieksza0'] = processing.run('native:extractbyattribute', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(26)
        if feedback.isCanceled():
            return {}

        # 26) Kolejność atrybutów
        alg_params = {
            'FIELDS_MAPPING': [
                {'alias': None, 'comment': None, 'expression': '"id"', 'length': 20, 'name': 'id', 'precision': 0, 'sub_type': 0, 'type': 6, 'type_name': 'double precision'},
                {'alias': None, 'comment': None, 'expression': '"adr_les"', 'length': 25, 'name': 'adr_les', 'precision': 0, 'sub_type': 0, 'type': 10, 'type_name': 'text'},
                {'alias': None, 'comment': None, 'expression': '"kod_ob"', 'length': 10, 'name': 'kod_ob', 'precision': 0, 'sub_type': 0, 'type': 10, 'type_name': 'text'},
                {'alias': None, 'comment': None, 'expression': '"dlugosc"', 'length': 10, 'name': 'dlugosc', 'precision': 2, 'sub_type': 0, 'type': 6, 'type_name': 'double precision'},
                {'alias': None, 'comment': None, 'expression': '"szer"', 'length': 3, 'name': 'szer', 'precision': 1, 'sub_type': 0, 'type': 6, 'type_name': 'double precision'},
                {'alias': None, 'comment': None, 'expression': '"nazwa"', 'length': 50, 'name': 'nazwa', 'precision': 0, 'sub_type': 0, 'type': 10, 'type_name': 'text'},
                {'alias': None, 'comment': None, 'expression': '"nr_ppoz"', 'length': 6, 'name': 'nr_ppoz', 'precision': 0, 'sub_type': 0, 'type': 10, 'type_name': 'text'},
                {'alias': None, 'comment': None, 'expression': '"nr_droga"', 'length': 6, 'name': 'nr_droga', 'precision': 0, 'sub_type': 0, 'type': 10, 'type_name': 'text'},
                {'alias': None, 'comment': None, 'expression': '"nr_inw"', 'length': 12, 'name': 'nr_inw', 'precision': 0, 'sub_type': 0, 'type': 10, 'type_name': 'text'}
            ],
            'INPUT': outputs['WyodrebnijDlugoscWieksza0']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['KolejnoAtrybutw'] = processing.run('native:refactorfields', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(27)
        if feedback.isCanceled():
            return {}

        # 27) Dodaj pow SILP do wydz_lin_seg  -> WYJŚCIE (tymczasowe lub ścieżka)
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'FIELD': 'adr_les',
            'FIELDS_TO_COPY': ['pow'],
            'FIELD_2': 'adr_les',
            'INPUT': outputs['KolejnoAtrybutw']['OUTPUT'],
            'INPUT_2': parameters['wydzielenia_nr_wew_formularz_z_bo'],
            'METHOD': 1,
            'PREFIX': 'SILP_',
            'OUTPUT': parameters.get('Wydz_lin_seg', QgsProcessing.TEMPORARY_OUTPUT)
        }
        outputs['DodajPowSilpDoWydz_lin_seg'] = processing.run('native:joinattributestable', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Wydz_lin_seg'] = outputs['DodajPowSilpDoWydz_lin_seg']['OUTPUT']

        feedback.setCurrentStep(28)
        if feedback.isCanceled():
            return {}

        # 28) Agregacja wydz_lin_seg -> WYJŚCIE TYMCZASOWE
        alg_params = {
            'AGGREGATES': [
                {'aggregate': 'first_value', 'delimiter': ',', 'input': '"adr_les"', 'length': 25, 'name': 'adr_les', 'precision': 0, 'sub_type': 0, 'type': 10, 'type_name': 'text'},
                {'aggregate': 'first_value', 'delimiter': ',', 'input': '"kod_ob"', 'length': 10, 'name': 'kod_ob', 'precision': 0, 'sub_type': 0, 'type': 10, 'type_name': 'text'},
                {'aggregate': 'sum', 'delimiter': ',', 'input': '"dlugosc"', 'length': 10, 'name': 'dlugosc', 'precision': 2, 'sub_type': 0, 'type': 6, 'type_name': 'double precision'},
                {'aggregate': 'first_value', 'delimiter': ',', 'input': '"SILP_pow"', 'length': 10, 'name': 'SILP_pow', 'precision': 4, 'sub_type': 0, 'type': 6, 'type_name': 'double precision'}
            ],
            'GROUP_BY': '"adr_les"',
            'INPUT': outputs['DodajPowSilpDoWydz_lin_seg']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['AgregacjaWydz_lin_seg'] = processing.run('native:aggregate', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(29)
        if feedback.isCanceled():
            return {}

        # 29) REPROJEKCJA PO AGREGACJI -> EPSG:2180 (PL-1992)
        alg_params = {
            'INPUT': outputs['AgregacjaWydz_lin_seg']['OUTPUT'],
            'TARGET_CRS': QgsCoordinateReferenceSystem('EPSG:2180'),
            'OPERATION': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['AgregacjaW2180'] = processing.run('native:reprojectlayer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(30)
        if feedback.isCanceled():
            return {}

        # 30) KOŃCOWE PRZELICZENIE DŁUGOŚCI W METRACH (EPSG:2180) -> wynik docelowy
        alg_params = {
            'FIELD_LENGTH': 10,
            'FIELD_NAME': 'dlugosc',
            'FIELD_PRECISION': 2,
            'FIELD_TYPE': 0,
            'FORMULA': '$length',
            'INPUT': outputs['AgregacjaW2180']['OUTPUT'],
            'OUTPUT': parameters.get('Wydz_lin_agreg', QgsProcessing.TEMPORARY_OUTPUT)
        }
        outputs['PrzeliczDlugoscPoAgreg'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Wydz_lin_agreg'] = outputs['PrzeliczDlugoscPoAgreg']['OUTPUT']

        feedback.setCurrentStep(31)
        if feedback.isCanceled():
            return {}

        # 31) Wczytaj do projektu: wydz_lin_seg (narzuć nazwę)
        alg_params = {
            'INPUT': results['Wydz_lin_seg'],
            'NAME': 'wydz_lin_seg'
        }
        processing.run('native:loadlayer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(32)
        if feedback.isCanceled():
            return {}

        # 32) Wczytaj do projektu: wydz_lin_agreg (narzuć nazwę)
        alg_params = {
            'INPUT': results['Wydz_lin_agreg'],
            'NAME': 'wydz_lin_agreg'
        }
        processing.run('native:loadlayer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        return results

    def name(self):
        return 'wydz_liniowe'

    def displayName(self):
        return 'wydz_liniowe'

    def group(self):
        return 'LMN'

    def groupId(self):
        return 'LMN'

    def createInstance(self):
        return Wydz_liniowe()
