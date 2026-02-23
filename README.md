# Automatizované účtování pomocí OCR

Tento projekt byl vytvořen jako maturitní práce na Gymnáziu Matyáše Lercha. Aplikace slouží k automatizované digitalizaci dat z účetních dokladů (faktur a účtenek) s následným exportem do formátu MS Excel.

## 🚀 Hlavní funkce
* **Automatická detekce textu:** Využití moderní knihovny EasyOCR pro přesné rozpoznávání znaků.
* **Předzpracování obrazu:** Automatické narovnání textu (deskewing) pomocí Houghovy transformace a úprava orientace.
* **Interaktivní GUI:** Možnost manuální korekce dat přímo v obraze posuvných bounding boxů.
* **Export dat:** Automatické vyplňování Excel šablon pomocí knihovny openpyxl.

## 🛠️ Technická specifikace
* **Jazyk:** Python 3.14.0
* **OS:** Vyvíjeno a testováno na Fedora Linux (KDE Plasma)
* **Klíčové technologie:** EasyOCR (PyTorch), OpenCV, CustomTkinter, openpyxl

## 📋 Instalace a spuštění

### 1. Klonování/Stažení projektu
Stáhněte si zdrojové kódy projektu do svého lokálního adresáře.

### 2. Instalace závislostí
Pro zajištění stability jsou v souboru `requirements.txt` fixovány konkrétní verze knihoven (version pinning). Instalaci provedete příkazem:

```bash
pip install -r requirements.txt
