# PranshulOS

A personal desktop assistant combining quick-launch shortcuts and FluidCB (contextual AI chat).

## Folder structure

```
pranshulos/
├── main.py          ← run this
├── shell.py         ← CustomTkinter UI
├── server.py        ← boots FluidCB Flask server
├── requirements.txt
└── fluidcb_v2/      ← existing FluidCB ai interface
```

## Setup

```bash
pip install -r requirements.txt
```

Make sure Ollama is installed and running:
```bash
ollama serve
ollama pull Qwen3:latest
```

## Run

```bash
python main.py
```

## Build as .exe

```bash
pip install pyinstaller
pyinstaller --onefile --windowed main.py
```

> The exe will be in the `dist/` folder. Keep `fluidcb_v2/` next to the exe.
