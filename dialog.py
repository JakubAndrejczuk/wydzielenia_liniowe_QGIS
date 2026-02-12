# -*- coding: utf-8 -*-
import os
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QDialogButtonBox, QLabel,
    QMessageBox, QWidget, QFileDialog, QPushButton, QHBoxLayout, QLineEdit,
    QProgressDialog
)
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt import QtCore
from qgis.core import (
    QgsProject, QgsProcessingContext, QgsVectorLayer,
    QgsMapLayerProxyModel, QgsProcessingFeedback
)
from qgis.gui import QgsMapLayerComboBox
from .algorithm import Wydz_liniowe
from .utils import ensure_output_string, load_vector_if_exists, infer_layer_name_from_source

PLACEHOLDER_TMP = '[Zapis do warstwy tymczasowej]'

# nazwy plików wymaganych w folderze "Warstwy SLMN"
SLMN_REQUIRED = {
    'a_kom_a':      'a_kom_a.dbf',
    'a_line_a':     'a_line_a.dbf',
    'a_kom_lin':    'a_kom_lin.shp',
    'a_line_lin':   'a_line_lin.shp',
    'a_oddz_pol':   'a_oddz_pol.shp',
}

class FilePicker(QWidget):
    """Prosty wybór ścieżki wyjściowej dla warstw wynikowych (OGR)."""
    def __init__(self, label_text: str, parent=None):
        super().__init__(parent)
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.lbl = QLabel(label_text)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(PLACEHOLDER_TMP)  # podpowiedź dla trybu tymczasowego
        self.btn = QPushButton('Zapisz jako…')
        self.btn.clicked.connect(self._choose)
        self.layout().addWidget(self.lbl)
        self.layout().addWidget(self.edit, 1)
        self.layout().addWidget(self.btn)

    def _choose(self):
        # Shapefile jako pierwszy (domyślny) format
        path, _ = QFileDialog.getSaveFileName(
            self,
            'Wybierz plik wyjściowy',
            '',
            'ESRI Shapefile (*.shp);;GPKG (*.gpkg);;GeoJSON (*.geojson)'
        )
        if path:
            self.edit.setText(path)

    def text(self) -> str:
        return self.edit.text().strip()

    def setText(self, value: str):
        self.edit.setText(value or '')


class FolderPicker(QWidget):
    """Wybór folderu z warstwami SLMN."""
    def __init__(self, label_text: str, parent=None):
        super().__init__(parent)
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.lbl = QLabel(label_text)
        self.edit = QLineEdit()
        self.btn = QPushButton('Wybierz folder…')
        self.btn.clicked.connect(self._choose)
        self.layout().addWidget(self.lbl)
        self.layout().addWidget(self.edit, 1)
        self.layout().addWidget(self.btn)

    def _choose(self):
        folder = QFileDialog.getExistingDirectory(self, 'Wskaż folder z warstwami SLMN', '')
        if folder:
            self.edit.setText(folder)

    def text(self) -> str:
        return self.edit.text().strip()

    def setText(self, value: str):
        self.edit.setText(value or '')


class ProgressFeedback(QgsProcessingFeedback):
    """
    Sprzęga Processing z QProgressDialog w trybie synchronicznym.
    Pokazujemy WYŁĄCZNIE pasek postępu – bez etykiet/tekstów.
    """
    progressChanged = pyqtSignal(float)

    def __init__(self, progress_dialog: QProgressDialog):
        super().__init__()
        self._dlg = progress_dialog
        self._canceled = False

    def setProgress(self, progress: float):
        super().setProgress(progress)
        try:
            self._dlg.setValue(int(progress))
            # odśwież GUI, żeby pasek się rysował
            QtCore.QCoreApplication.processEvents(QtCore.QEventLoop.AllEvents, 50)
        except Exception:
            pass

    # Wyłączamy aktualizacje tekstów (ma być sam pasek)
    def setProgressText(self, text: str):
        pass

    def pushInfo(self, info: str):
        pass

    def pushWarning(self, warning: str):
        pass

    def isCanceled(self) -> bool:
        return self._canceled or super().isCanceled()

    def cancel(self):
        self._canceled = True
        super().cancel()


class WydzLinioweDialog(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle('Wydzielenia liniowe')
        self.setMinimumWidth(640)

        main = QVBoxLayout(self)

        grid = QGridLayout()
        row = 0

        # Wejście 1: warstwa wydzielenia nr_wew (z projektu)
        self.in_wydzielenia = QgsMapLayerComboBox()
        self.in_wydzielenia.setFilters(QgsMapLayerProxyModel.VectorLayer)
        grid.addWidget(QLabel('wydzielenia_nr_wew (formularz z BO):'), row, 0)
        grid.addWidget(self.in_wydzielenia, row, 1); row += 1

        # Wejście 2: folder z warstwami SLMN
        self.in_folder = FolderPicker('Warstwy SLMN:')
        grid.addWidget(self.in_folder, row, 0, 1, 2); row += 1

        main.addLayout(grid)

        # Wyjścia (obie mogą pozostać puste -> memory:)
        self.out_seg = FilePicker('wydz_lin_seg:')
        self.out_agreg = FilePicker('wydz_lin_agreg:')

        main.addWidget(self.out_seg)
        main.addWidget(self.out_agreg)

        # Przyciski: Cancel + „Uruchom” (rozmiar jak Anuluj)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.btn_run = buttons.addButton('Uruchom', QDialogButtonBox.AcceptRole)
        self.btn_run.clicked.connect(self.run_algorithm)
        buttons.rejected.connect(self.reject)
        main.addWidget(buttons)

    def _resolve_slmn_inputs(self, folder: str) -> dict:
        """
        Zwraca słownik z wczytanymi warstwami z podanego folderu.
        Podnosi wyjątek z listą braków lub błędów.
        """
        missing = []
        invalid = []

        def _make_path(fname): return os.path.join(folder, fname)

        # a_kom_a.dbf
        p_kom_a = _make_path(SLMN_REQUIRED['a_kom_a'])
        lyr_kom_a = load_vector_if_exists(p_kom_a, 'a_kom_a') if os.path.exists(p_kom_a) else None
        if not os.path.exists(p_kom_a):
            missing.append(SLMN_REQUIRED['a_kom_a'])
        elif not (lyr_kom_a and lyr_kom_a.isValid()):
            invalid.append(SLMN_REQUIRED['a_kom_a'])

        # a_line_a.dbf
        p_line_a = _make_path(SLMN_REQUIRED['a_line_a'])
        lyr_line_a = load_vector_if_exists(p_line_a, 'a_line_a') if os.path.exists(p_line_a) else None
        if not os.path.exists(p_line_a):
            missing.append(SLMN_REQUIRED['a_line_a'])
        elif not (lyr_line_a and lyr_line_a.isValid()):
            invalid.append(SLMN_REQUIRED['a_line_a'])

        # a_kom_lin.shp
        p_kom_lin = _make_path(SLMN_REQUIRED['a_kom_lin'])
        lyr_kom_lin = load_vector_if_exists(p_kom_lin, 'a_kom_lin') if os.path.exists(p_kom_lin) else None
        if not os.path.exists(p_kom_lin):
            missing.append(SLMN_REQUIRED['a_kom_lin'])
        elif not (lyr_kom_lin and lyr_kom_lin.isValid()):
            invalid.append(SLMN_REQUIRED['a_kom_lin'])

        # a_line_lin.shp
        p_line_lin = _make_path(SLMN_REQUIRED['a_line_lin'])
        lyr_line_lin = load_vector_if_exists(p_line_lin, 'a_line_lin') if os.path.exists(p_line_lin) else None
        if not os.path.exists(p_line_lin):
            missing.append(SLMN_REQUIRED['a_line_lin'])
        elif not (lyr_line_lin and lyr_line_lin.isValid()):
            invalid.append(SLMN_REQUIRED['a_line_lin'])

        # a_oddz_pol.shp
        p_oddz_pol = _make_path(SLMN_REQUIRED['a_oddz_pol'])
        lyr_oddz_pol = load_vector_if_exists(p_oddz_pol, 'a_oddz_pol') if os.path.exists(p_oddz_pol) else None
        if not os.path.exists(p_oddz_pol):
            missing.append(SLMN_REQUIRED['a_oddz_pol'])
        elif not (lyr_oddz_pol and lyr_oddz_pol.isValid()):
            invalid.append(SLMN_REQUIRED['a_oddz_pol'])

        if missing or invalid:
            msg = []
            if missing:
                msg.append('Brakujące pliki w folderze:\n  - ' + '\n  - '.join(missing))
            if invalid:
                msg.append('Nieprawidłowe/nieczytelne pliki:\n  - ' + '\n  - '.join(invalid))
            raise RuntimeError('\n\n'.join(msg))

        return {
            'a_kom_adbf': lyr_kom_a,
            'a_line_adbf': lyr_line_a,
            'a_kom_linshp': lyr_kom_lin,
            'a_line_linshp': lyr_line_lin,
            'a_oddz_polshp': lyr_oddz_pol,
        }

    def _add_result_layer(self, results: dict, key: str, desired_name: str, dest: str, context: QgsProcessingContext):
        """
        Dodaje do projektu warstwę wynikową.
        - Jeśli wynik jest tymczasowy (memory) → nadaje nazwę desired_name.
        - Jeśli zapisano do pliku → wczytuje z dysku i *wymusza* nazwę na podstawie ścieżki/parametru.
        """
        lyr = None
        ref = results.get(key)

        # 1) Próba pobrania tymczasowej warstwy z context
        if isinstance(ref, str):
            lyr = context.takeResultLayer(ref)

        # 2) Jeżeli zapisano do pliku – wczytaj z dysku i nadaj nazwę z pliku
        src = None
        if lyr is None:
            if isinstance(ref, str) and os.path.exists(ref.split('|')[0]):
                src = ref
            elif dest and not dest.lower().startswith('memory:'):
                src = dest

        # wczytanie z dysku (jeśli dotyczy)
        if lyr is None and src:
            file_name = infer_layer_name_from_source(src)
            lyr = load_vector_if_exists(src, file_name)

        # 3) Jeżeli algorytm zwrócił bezpośrednio warstwę (rzadkie)
        if lyr is None and isinstance(ref, QgsVectorLayer):
            lyr = ref

        if lyr and lyr.isValid():
            # memory → wymuś nazwę z algorytmu
            is_memory = (dest.lower().startswith('memory:') if dest else True)
            if is_memory:
                lyr.setName(desired_name)
            QgsProject.instance().addMapLayer(lyr)

    def run_algorithm(self):
        # Walidacja minimalna wejść
        if self.in_wydzielenia.currentLayer() is None:
            QMessageBox.warning(self, 'Brak danych', 'Wskaż warstwę "wydzielenia_nr_wew (formularz z BO)".')
            return
        folder = self.in_folder.text()
        if not folder or not os.path.isdir(folder):
            QMessageBox.warning(self, 'Brak folderu', 'Wskaż poprawny folder w polu „Warstwy SLMN”.')
            return

        # Jeśli brak ścieżki -> zapis do memory: i wpisz komunikat w pole
        out_agreg_text = self.out_agreg.text()
        out_seg_text = self.out_seg.text()

        if not out_agreg_text or out_agreg_text == PLACEHOLDER_TMP:
            self.out_agreg.setText(PLACEHOLDER_TMP)
            dest_agreg = 'memory:'
        else:
            dest_agreg = ensure_output_string(out_agreg_text)

        if not out_seg_text or out_seg_text == PLACEHOLDER_TMP:
            self.out_seg.setText(PLACEHOLDER_TMP)
            dest_seg = 'memory:'
        else:
            dest_seg = ensure_output_string(out_seg_text)

        # Wczytaj warstwy z folderu SLMN
        try:
            slmn_layers = self._resolve_slmn_inputs(folder)
        except Exception as e:
            QMessageBox.critical(self, 'Błąd wejścia', str(e))
            return

        # Parametry zgodnie z algorytmem
        params = {
            'wydzielenia_nr_wew_formularz_z_bo': self.in_wydzielenia.currentLayer(),
            'a_kom_adbf': slmn_layers['a_kom_adbf'],
            'a_kom_linshp': slmn_layers['a_kom_linshp'],
            'a_line_adbf': slmn_layers['a_line_adbf'],
            'a_line_linshp': slmn_layers['a_line_linshp'],
            'a_oddz_polshp': slmn_layers['a_oddz_polshp'],
            'Wydz_lin_agreg': dest_agreg,
            'Wydz_lin_seg': dest_seg
        }

        # Kontekst przetwarzania
        context = QgsProcessingContext()
        context.setProject(QgsProject.instance())

        # Pokaż WYŁĄCZNIE pasek postępu (bez tekstu)
        progress = QProgressDialog('', 'Anuluj', 0, 100, self)
        progress.setWindowTitle('Wydzielenia liniowe — postęp')
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setLabelText('')   # upewnij się, że etykieta jest pusta
        progress.setValue(0)
        progress.show()
        QtCore.QCoreApplication.processEvents()

        feedback = ProgressFeedback(progress)

        # Obsługa anulowania
        def on_cancel():
            try:
                feedback.cancel()
            except Exception:
                pass
        progress.canceled.connect(on_cancel)

        # --- URUCHOMIENIE SYNCHRONICZNE ---
        alg = Wydz_liniowe()
        try:
            results, ok = alg.run(params, context, feedback)
            if not ok:
                raise RuntimeError('Algorytm zakończony niepowodzeniem lub został przerwany.')
        except Exception as e:
            progress.close()
            QMessageBox.critical(self, 'Błąd', f'Algorytm zakończony błędem:\n{e}')
            return
        finally:
            progress.close()

        # Dodaj warstwy (tymczasowym nadamy stałe nazwy; z pliku – nazwa z pliku)
        try:
            self._add_result_layer(results, 'Wydz_lin_agreg', 'wydz_lin_agreg', dest_agreg, context)
            self._add_result_layer(results, 'Wydz_lin_seg', 'wydz_lin_seg', dest_seg, context)
        except Exception as e:
            QMessageBox.warning(self, 'Uwaga', f'Wyniki obliczeń zakończone, ale nie udało się dodać warstw:\n{e}')
            return

        QMessageBox.information(self, 'Zakończono', 'Przetwarzanie zakończone pomyślnie.')
        self.accept()