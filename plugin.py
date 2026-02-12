# -*- coding: utf-8 -*-
import os
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsMessageLog, Qgis, QgsApplication
import processing

from .utils import plugin_dir
from .provider import WydzLinioweProvider

PLUGIN_MENU = 'LMN'
PLUGIN_ACTION_TEXT = 'wydz_liniowe'

class WydzLiniowePlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.provider = None

    def initGui(self):
        # Rejestracja providera Processing – algorytmy dostępne w Toolboxie
        self.provider = WydzLinioweProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

        # Akcja na pasku narzędzi
        icon_path = os.path.join(plugin_dir(), 'icon.png')
        self.action = QAction(QIcon(icon_path), PLUGIN_ACTION_TEXT, self.iface.mainWindow())
        # Teksty zgodnie z prośbą
        self.action.setToolTip('Wydzielenia liniowe')
        self.action.setStatusTip('Wydzielenia liniowe')
        self.action.setWhatsThis('Uruchom algorytm „Wydzielenia liniowe” w oknie Processing')

        # Otwieramy NATYWNY dialog Processing dla wrappera,
        # dzięki czemu pojawią się checkboxy "Wczytaj plik wynikowy po zakończeniu"
        def _open_processing_dialog():
            try:
                processing.execAlgorithmDialog('lmn:wydz_liniowe_auto', {})
            except Exception as e:
                QgsMessageLog.logMessage(f'Nie można uruchomić dialogu: {e}', 'WydzLiniowe', Qgis.Critical)

        self.action.triggered.connect(_open_processing_dialog)

        # Dodaj do UI
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(PLUGIN_MENU, self.action)

        QgsMessageLog.logMessage('Wtyczka WydzLiniowe załadowana.', 'WydzLiniowe', Qgis.Info)

    def unload(self):
        if self.action:
            self.iface.removeToolBarIcon(self.action)
            self.iface.removePluginMenu(PLUGIN_MENU, self.action)
            self.action = None

        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None

        QgsMessageLog.logMessage('Wtyczka WydzLiniowe wyładowana.', 'WydzLiniowe', Qgis.Info)
