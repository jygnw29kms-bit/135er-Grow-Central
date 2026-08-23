# Kamera-Bedienteil

Das vorhandene Kamera-Menü erzeugt sein Bedienteil dynamisch aus den von UVC/V4L2 gemeldeten Controls. Dadurch erscheinen nur Funktionen, die die angeschlossene Kamera tatsächlich anbietet (z. B. Helligkeit, Kontrast, Sättigung, Schärfe, Weißabgleich, Belichtung, Gegenlicht, Gain, Autofokus, manueller Fokus und Zoom).

Für Grow Central gilt zusätzlich die feste maximale Videoauflösung 1280×720. Die C920-Status-LED wird nur als schaltbarer Control angeboten, wenn Kernel/Kamera einen passenden UVC/V4L2-Control melden; ein nicht vorhandener Schalter wird nicht simuliert.
