# -*- coding: utf-8 -*-
from qgis.core import QgsProcessingProvider
from .algorithm import Wydz_liniowe
from .algorithm_auto import Wydz_liniowe_auto

class WydzLinioweProvider(QgsProcessingProvider):
    def id(self) -> str:
        # identyfikator providera – część przed dwukropkiem
        return 'lmn'

    def name(self) -> str:
        return 'LMN'

    def longName(self) -> str:
        return 'LMN'

    def loadAlgorithms(self):
        # Rejestruj oba algorytmy
        self.addAlgorithm(Wydz_liniowe())        # bazowy (z modelera)
        self.addAlgorithm(Wydz_liniowe_auto())   # wrapper z folderem SLMN
