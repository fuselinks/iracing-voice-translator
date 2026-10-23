from ivt.app import main

if __name__ == '__main__':
    import sys
    if '--self-test' in sys.argv:
        try:
            import tkinter as tk
            import faster_whisper
            from transformers import MarianMTModel, MarianTokenizer
            from ivt.app import App
            root=tk.Tk();root.withdraw()
            app=App(root);root.update();app.quit()
            if '--self-test-audio' in sys.argv:
                from ivt.config import Config
                from ivt.engine import Engine
                audio=sys.argv[sys.argv.index('--self-test-audio')+1]
                for mode in ('direct','two-stage'):
                    engine=Engine(Config(model='small',device='cpu',engine=mode))
                    engine.load()
                    assert engine.process(audio)[1].strip()
            if '--self-test-cuda' in sys.argv:
                from ivt.config import Config
                from ivt.engine import Engine
                engine=Engine(Config(model='small',device='cuda'))
                engine.load()
                assert engine.actual_device=='cuda'
        except Exception:
            sys.exit(2)
    else:
        main()
