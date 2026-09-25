# Work AIO Tool (PySide6)

Python/Qt rebuild of the JavaFX `work-aio-tool`.

## Run
```
cd aio-work-tool
pip install -r requirements.txt
python -m src
```
Keys 1-7 switch tabs. Window size, position and last tab are remembered.

## Data
Saved as JSON, one file per list, in `%APPDATA%\lertos\Work AIO Tool\`
(`todo.json`, `folders.json`, `copy.json`, `promote.json`, `info.json`, `sql_compare.json`, `surround.json`).
SQL passwords are stored in Windows Credential Manager (service `work-aio-tool`), not in the JSON.

## Tests
```
python -m unittest -v
```

## Layout
```
src/
  main.py, config.py
  model/     items.py (dataclasses), item_store.py (list + undo history),
             item_list_model.py (Qt model), storage.py (JSON + keyring)
  services/  promoter.py (copy/move), sql_compare.py (definition compare), surround.py (prefix/suffix lines)
  ui/        main_window.py, delegates.py (list rows), toast.py, worker.py, widgets.py
    tabs/    item_list_tab.py (shared base), todo, simple (folders/copy/info), promoter, sql_compare, surround
    dialogs/ item_form_dialog.py (shared base), simple, promote, sql_compare, sql_compare_run, surround
```
