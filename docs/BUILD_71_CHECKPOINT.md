# Build 71 checkpoint

**Datum:** 2026-08-16

Build 71 ist der reproduzierbare Sicherungspunkt zwischen dem veröffentlichten Build 70 und Build 72.

- Basisversion: `alpha-0.7.5`
- Ausgangslinie: Build 70
- Checkpoint-Commit: `6547857e9a4f7431218399591a3fef8435115cb6`
- Zweck: unveränderliche Referenz für Build 72 und Mobile v0.1
- Mobile-Code gehört erst in den folgenden Build-72-Stand.

Der Raspberry-Pi-Image-Workflow wird durch `app/BUILD_71_CHECKPOINT` ausgelöst. Die tatsächliche Freigabe als getesteter Build erfolgt erst nach erfolgreichem Workflow und Hardwareprüfung.
