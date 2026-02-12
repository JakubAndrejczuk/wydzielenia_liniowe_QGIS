# Wydzielenia liniowe (QGIS Plugin)

Wtyczka QGIS do generowania **wydzieleń liniowych (z „~”)** na podstawie warstw SLMN oraz raportu BO.

## **Przeznaczenie:**  
Wtyczka dedykowana dla pracowników **Lasów Państwowych**.
Do prawidłowego działania wtyczki wymagany jest **dostęp do bazy SILP**:
- SilpWeb > Mapa > Wymiana Danych
- SAP BO > Opis Taksacyjny

---

## Wymagania

- **QGIS:** 3.0 lub nowszy,
- **warstwy wektorowe w strukturze SLMN** - rozpakowany folder z SilpWeb, zawierajacy warstwy:
  - `a_kom_lin.shp`
  - `a_line_lin.shp`
  - `a_kom_a.dbf`
  - `a_line_a.dbf`
  - `a_oddz_pol`
- **raport BO** (zapisany w folderze osobistym użytkownika),
- dostęp do środowiska/danych **SILP**.

---

## Wejście i wyjście

### Dane wejściowe

1. **Warstwy SLMN** – rozpakowany folder warstw pobrany z SilpWeb.  
2. **Raport BO** – raport wymagany przez algorytm (zgodnie z procedurą LP).

### Dane wynikowe

- **`wydz_lin_seg`** – obiekty z warstw `a_kom_lin` i `a_line_lin` z przypisanym adresem leśnym,  
- **`wydz_lin_agreg`** – obiekty zagregowane do adresu leśnego, z przypisaną powierzchnią z SILP.

---

## Ograniczenia i uwagi

- Generowane są tylko obiekty położone w granicach warstwy oddziałów leśnych (`a_oddz_pol`).
- Obiekty liniowe z przypisanym adresem leśnym, które znajdują się poza `a_oddz_pol`, nie są generowane.
- Wtyczka została zaprojektowana dla standardów i struktury danych Lasów Państwowych.

---

## Instalacja

1. Pobierz paczkę ZIP wtyczki (np. z zakładki **Releases** na GitHub).
2. W QGIS wybierz: **Wtyczki → Zarządzaj i instaluj wtyczki → Instaluj z pliku ZIP**
3. Wskaż ZIP i zainstaluj.

---

## Podstawowy workflow

1. Przygotuj i rozpakuj warstwy SLMN.
2. Wygeneruj/zapisz wymagany raport BO do folderu osobistego.
3. Uruchom narzędzie wtyczki i wskaż dane wejściowe.
4. Wygeneruj warstwy wynikowe: `wydz_lin_seg` i `wydz_lin_agreg`.

---

## Autor i kontakt

- **Autor:** Jakub Andrejczuk  
- **E-mail:** jakub.andrejczuk@torun.lasy.gov.pl  

Instrukcja wideo: `https://youtu.be/PSp9XU6YqU0`
Repozytorium: `https://github.com/JakubAndrejczuk/wydzielenia_liniowe_QGIS`
