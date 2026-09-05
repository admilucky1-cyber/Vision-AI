# Vision AI v5.7.1

Multi-provider AI chat + Model Studio (image/video/LoRA jobs) with Colab/Kaggle workers.

## Start
```bash
python run.py
```

## Verify
- `/health` → version 5.7.1
- `/chat/ping` → chat POST routing
- `/studio.html` → Model Studio

## Identity
Chat system prompts read `VERSION` file dynamically — answers about version/builder should match **v5.7.1**.

## Limits
No unlimited free GPU. Image generation may require paid plan. Video/LoRA train need GPU workers.
