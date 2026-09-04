# Colab GPU memory (v2.7.8)

## Google account / Drive
When you run `drive.mount('/content/drive')`, Colab asks you to sign in **once** with the **Google account of that Colab notebook**.
It does **not** ask “which Gmail for models” as a separate Vision AI prompt — the account is whatever account owns the Colab session.
Use the same Gmail that has space in Drive for `MyDrive/vision_ai_models`.

## Sequential CPU offload
Default: `SEQUENTIAL_OFFLOAD=1` and `LOW_VRAM=1`.
Order: sequential offload → model CPU offload → full CUDA.

## Memory guard
Before load/generate, worker checks free VRAM and runs `empty_cache` if low.
If still critical, returns a clear error instead of hanging.

## TensorRT
Full TensorRT engines are not practical on free Colab.
Optional: `ENABLE_TENSORRT=1` tries `torch.compile` on UNet (experimental).

## UI status
`GET /worker/health` includes:
- `loading` (bool)
- `load_status` (exact message, e.g. “Loading weights…”, “Ready — sdxl-turbo warmed”)
- `offload_mode`

Poll this from Boost page while the worker starts so users are not left waiting with no feedback.
