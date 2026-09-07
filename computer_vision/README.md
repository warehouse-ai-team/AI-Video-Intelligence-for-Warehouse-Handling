# Warehouse CV Module — Computer Vision / Video Intelligence

Status: **Phases 1-7 built and tested against your real 6 videos. One

architectural pivot required before the behaviour engine's output can be

trusted — see below.**

Read `data/annotations/detection_findings.md` first — it's the honest,

verified record of what works, what was tried and failed, and why. This

README summarizes it; that file has the receipts.

## TL;DR status

| Phase | Status |
|---|---|
| 1. Video audit | Done. Real metadata + ground truth for all 6 clips (`data/annotations/ground_truth.csv`) |
| 3. Person detection | Verified working (pretrained YOLO) |
| 4. Person tracking | Working, real ID churn documented (not hidden) |
| 3/5. Product detection | Motion-blob proxy verified BROKEN on busy scenes. YOLO-World built but needs YOU to test (sandbox network-restricted) |
| 5. Motion features | Built, logic sound, currently fed unreliable product input |
| 6. Behaviour engine | Logic built (dropping/throwing/dragging/rough_handling), do not trust current output until product detection is fixed |
| 7. Event JSON/CSV | Schema built and working, same caveat as above |
| 8-9. Clips/pipeline/eval | Not started - blocked on product detection fix |

## THE ONE THING YOU NEED TO DO FIRST

Test YOLO-World on your machine (needs normal internet - it failed in my

sandbox only because CLIP's weight host isn't on the sandbox's restricted

allowlist):

```powershell
pip install ultralytics

python -c "from ultralytics import YOLO; m = YOLO('yolov8s-world.pt'); m.set_classes(['cardboard box','mattress','pallet']); r = m.predict('data/frames/Throwing_Mattresses/Throwing_Mattresses_f000267_t8.90s.jpg'); r[0].show()"