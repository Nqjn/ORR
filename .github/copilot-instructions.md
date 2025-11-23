# Copilot / AI Agent Instructions for ORR

Purpose
- Help agents make small, safe, and useful changes to this OCR GUI project.

Big picture
- Components: `main.py` (entry), `GUI.py` (tkinter-based file chooser), `MyOCR.py` (wraps `easyocr`), `Excel.py` (currently empty placeholder for export).
- Data flow: user selects image in `GUI.py` → `soubor_cesta` updated → `ReadData(path)` in `MyOCR.py` produces OCR results. `main.py` also calls `vyrobit_okno()` then `ReadData(res)`; this can produce duplicate processing if `GUI.py` already calls `ReadData`.

Key patterns & conventions
- File naming: modules are capitalized (e.g., `GUI.py`, `MyOCR.py`). Functions and variables use `snake_case` and Czech-language identifiers/strings — preserve Czech text unless instructed otherwise.
- Logging: code uses `print(...)` for runtime messages. Keep that pattern for quick debugging; if adding more logging, prefer the same lightweight approach or introduce the standard `logging` module consistently.
- Types: light use of type hints exists (see `vyber_soubor` annotation). New code should add simple type hints where helpful.

Important code examples & notes (do not change behavior without justification)
- `MyOCR.py` uses:
  - `reader = easyocr.Reader(['en', 'cs'], gpu=True)` — heavy to instantiate and expects appropriate GPU/CUDA environment. Prefer reusing a single `Reader` instance rather than re-creating it per call.
- `GUI.py` behavior:
  - `vyrobit_okno()` launches `tkinter` mainloop and returns `soubor_cesta` after window closes.
  - `vyber_soubor(... )` calls `ReadData(file_path)` directly after selection. This means a call from `main.py` to `ReadData(res)` may double-run OCR. When modifying control flow, centralize where OCR runs (either GUI-triggered or main-triggered) and document the chosen approach.
- `main.py` currently:
  - imports everything (`from Excel import *`) — avoid `*` imports when adding code; prefer explicit imports.

Dev / run workflows (runnable steps)
- Quick run (launch GUI):
  - `python main.py` — opens GUI and then calls OCR after the window closes (depending on selection flow).
  - `python GUI.py` — can be used to run the window directly for GUI-focused testing.
- Headless OCR test (example):
  - `python -c "from MyOCR import ReadData; print(ReadData('path/to/file.png'))"`

Environment & dependencies
- Project uses `easyocr` (which depends on `torch`). Install locally before editing/testing:
  - `pip install easyocr torch torchvision` (choose the `torch` package variant matching your CUDA/CPU environment).
- `MyOCR.py` sets `gpu=True` — change to `gpu=False` if CUDA is not available.

Guidelines for changes
- Preserve Czech UI text and variable names unless you have the user's sign-off to translate.
- Avoid heavy runtime changes in quick PRs: refactor `easyocr.Reader` instantiation to a module-level singleton only when adding unit coverage or explicit benchmarks.
- When adding export logic, implement in `Excel.py` and keep GUI/OCR responsibilities separated. Example function signature suggestion:
  - `def write_results_to_excel(results: list, out_path: str) -> None:`
- Replace `from X import *` with explicit imports when editing files.

Bugs/pitfalls to be aware of
- `GUI.py` contains two `return` statements in `vyrobit_okno()`; the second `return label_s_cestou.cget("text")` is unreachable. If you modify `vyrobit_okno()`, tidy or document the intended return value (prefer returning the selected file path string).
- Double OCR invocation: `vyber_soubor` calls `ReadData()` and `main.py` may call it again. Coordinate to avoid duplicate work.

Where to look for examples
- `MyOCR.py` — OCR invocation and languages (`['en','cs']`).
- `GUI.py` — tkinter flow, `askopenfilename`, and file-path handling via `soubor_cesta`.

When in doubt
- Ask the repository owner whether OCR should run immediately on selection (GUI-driven) or only after window closes (main-driven). Preserve current prints and Czech strings until asked to refactor them.

Next steps for maintainers
- Add a `requirements.txt` listing `easyocr`, `torch`, `torchvision` and any pinned versions.
- Implement `Excel.py` export functions and add a small CLI test harness (e.g., `scripts/test_ocr.py`) for headless runs.

If anything here is unclear or you want me to expand examples (e.g., exact refactor to reuse `easyocr.Reader`), tell me which section to expand.
