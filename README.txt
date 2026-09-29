HOW TO RUN (Windows)

1. Unzip this folder, then open it in VS Code (File > Open Folder).
2. Open the terminal in VS Code (Ctrl + `) and run these, one at a time:

   pip install -r requirements.txt
   python -m uvicorn main:app --reload

3. Open your browser and go to:  http://127.0.0.1:8000

To stop the app, click in the terminal and press Ctrl + C.
Your items are saved in a file called todos.db in this folder.
